"""Sending for the mail domain: a workspace's message, handed to Cloudflare.

A workspace holds no Cloudflare credential, as for storage. It builds the
message — Frappe's Email Queue does, headers and attachments and all — and
asks here. What is checked here, because a workspace could lie about it:
- the From is on the mail domain and is the workspace's own, `<slug>@` or
  `<name>.<slug>@`;
- the message fits Cloudflare's 5 MiB;
- the workspace has sends left this hour and this day.

The counts are atomic increments in the cache, one key per workspace per
hour and per day, so two workers sending at once cannot both slip under the
limit. A send refused for the limit raises `faults.Again`, and Email Queue
retries it later.

Cloudflare's `send_raw` takes the finished MIME message, so nothing is
rebuilt: what the workspace's Email Queue made is what goes out, signed by
Cloudflare with the mail domain's DKIM key.
"""

import base64

import frappe
import requests
from frappe.utils import now_datetime

from onedesk.one_admin import cloudflare, faults

#: Cloudflare's limit on one message, attachments included.
LARGEST = 5 * 1024 * 1024

#: Sends per workspace, unless site config says otherwise.
HOURLY, DAILY = 200, 2000


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
	spend(tenant.slug)
	account, token, _namespace = cloudflare._settings()
	answered = requests.post(
		f"{cloudflare.API}/accounts/{account}/email/sending/send_raw",
		headers={"Authorization": f"Bearer {token}"},
		json={"from": sender, "recipients": [recipient], "mime_message": raw.decode("utf-8", "replace")},
		timeout=30,
	)
	body = answered.json() if answered.headers.get("content-type", "").startswith("application/json") else {}
	if not answered.ok or not body.get("success"):
		raise faults.raised("cloudflare", answered.status_code, cloudflare._detail(answered))
	return body.get("result") or {}
