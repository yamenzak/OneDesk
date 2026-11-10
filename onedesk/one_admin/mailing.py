"""Sending for the mail domain: a workspace's message, handed to Cloudflare.

A workspace holds no Cloudflare credential; it builds the message and asks
here, where the From, the size and the sends left are checked.
"""

import base64

import frappe
import requests
from frappe.utils import now_datetime

from onedesk.one_admin import cloudflare, faults

LARGEST = 5 * 1024 * 1024

HOURLY, DAILY = 200, 2000
SENDING_USD = 0.35 / 1000

SUPPRESSED_CODE = "recipient_suppressed"
SUPPRESSED = "Cloudflare suppresses this address."
BOUNCED = "Cloudflare reported a permanent bounce."


def allowed(sender: str, slug: str, domain: str) -> bool:
	"""Whether a workspace may send as this address. Pure."""
	from onedesk.one_mail import addresses

	local, _at, host = (sender or "").strip().lower().rpartition("@")
	return host == domain.lower() and addresses.is_workspace_name(local, slug)


def spend(slug: str) -> None:
	"""Count one send against the hour and the day, or refuse it."""
	now = now_datetime()
	for window, limit, ttl in (
		(now.strftime("%Y%m%d%H"), frappe.conf.get("one_mail_hourly") or HOURLY, 3600),
		(now.strftime("%Y%m%d"), frappe.conf.get("one_mail_daily") or DAILY, 86400),
	):
		key = f"one_mail_sent:{slug}:{window}"
		count = frappe.cache.incrby(key, 1)
		if count == 1:
			frappe.cache.expire(key, ttl)
		if count > int(limit):
			frappe.cache.decrby(key, 1)
			raise faults.Again(f"{slug} has sent its {limit} for now")


def send(tenant, sender: str, recipient: str, message: str) -> dict:
	domain = cloudflare.mail_domain()
	if not allowed(sender, tenant.slug, domain):
		raise frappe.PermissionError(f"{sender} is not one of {tenant.slug}'s addresses")
	raw = base64.b64decode(message)
	if len(raw) > LARGEST:
		frappe.throw(frappe._("This message is larger than 5 MB. Share large files as OneCloud links."))
	why = stopped(recipient)
	if why:
		return {"skipped": why}
	spend(tenant.slug)
	from onedesk.one_admin import ledger, price_list

	holding = ledger.reserve(tenant.name, price_list.MAIL_CREDITS, why="mail", reference=f"OneMail to {recipient}", action="mail_send")
	try:
		said = _sent(sender, recipient, raw)
	except Exception:
		ledger.release(holding)
		raise
	if said.get("skipped"):
		ledger.release(holding)
		return said
	ledger.commit(holding, price_list.MAIL_CREDITS, SENDING_USD, model="cloudflare/email")
	return said


def _sent(sender: str, recipient: str, raw: bytes) -> dict:
	"""One message handed to Cloudflare. An address it suppresses is
	remembered and skipped, and one it says bounced for good is remembered,
	so neither is sent to again (`stopped`)."""
	account, token, _namespace = cloudflare._settings()
	answered = requests.post(
		f"{cloudflare.API}/accounts/{account}/email/sending/send_raw",
		headers={"Authorization": f"Bearer {token}"},
		json={"from": sender, "recipients": [recipient], "mime_message": raw.decode("utf-8", "replace")},
		timeout=30,
	)
	body = answered.json() if answered.headers.get("content-type", "").startswith("application/json") else {}
	if not answered.ok or not body.get("success"):
		if suppressed(body):
			remember(recipient, SUPPRESSED)
			return {"skipped": SUPPRESSED}
		raise faults.raised("cloudflare", answered.status_code, cloudflare._detail(answered))
	result = body.get("result") or {}
	if bounced(result, recipient):
		remember(recipient, BOUNCED)
	return result


def suppressed(body: dict) -> bool:
	"""Whether Cloudflare refused because it suppresses the recipient
	(`email.sending.error.email.recipient_suppressed`), in a code or a
	message. Pure."""
	said = (body or {}).get("errors") or []
	return any(SUPPRESSED_CODE in f"{one.get('code', '')} {one.get('message', '')}" for one in said if isinstance(one, dict))


def bounced(result: dict, recipient: str) -> bool:
	"""Whether Cloudflare's answer lists the recipient as a permanent
	bounce. Pure."""
	held = (result or {}).get("permanent_bounces") or []
	return recipient.strip().lower() in {str(one).strip().lower() for one in held}


def stopped(recipient: str) -> str | None:
	"""Why One no longer sends to an address, or None: one Cloudflare
	suppressed or bounced, kept on Email Unsubscribe."""
	return frappe.db.get_value(
		"Email Unsubscribe", {"email": recipient.strip().lower(), "global_unsubscribe": 1, "one_bounce": ["is", "set"]}, "one_bounce"
	)


def remember(recipient: str, why: str) -> None:
	from onedesk.one_mail import rules

	rules.remember(recipient.strip().lower(), why)
	frappe.db.commit()


def ours() -> str | None:
	"""The address One's own mails come from, on the admin site only."""
	from onedesk.one_admin import site

	if not site.is_admin():
		return None
	return (
		(frappe.db.get_single_value("One Admin Settings", "sender_email") or "noreply@4dl.app")
		.strip()
		.lower()
	)


def send_ours(recipient: str, raw: bytes) -> dict:
	"""One of the admin site's own mails, from Sender Email, straight to
	Cloudflare: no workspace to check it against and no hourly allowance,
	since these are sign-in links and notices a customer is waiting for.
	An address Cloudflare suppressed or bounced is skipped all the same."""
	if len(raw) > LARGEST:
		frappe.throw(frappe._("This message is larger than 5 MB."))
	why = stopped(recipient)
	if why:
		return {"skipped": why}
	return _sent(ours(), recipient, raw)
