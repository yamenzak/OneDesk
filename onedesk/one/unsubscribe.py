"""Turn Off These Emails: the link at the foot of a notification's mail, and
the List-Unsubscribe header a mail client offers for it.

Both are frappe's own signed unsubscribe link (`frappe.email.queue`) with this
module's method in place of frappe's: it turns off one type for one person,
as NotificationCenter's switch does, without signing in
(notifications/README.md).
"""

import hmac

import frappe
from frappe import _

KIND = "Notification Type"
METHOD = "/api/method/onedesk.one.unsubscribe.off"
AGAIN = "/api/method/onedesk.one.unsubscribe.on"
SETTINGS = "/desk/one?center=notifications"


def link(email: str, kind: str, method: str = METHOD) -> str:
	"""The signed link that turns `kind` off (or on again) for whoever has
	`email`, as frappe's queue draws it for each recipient."""
	from frappe.email.queue import get_unsubcribed_url

	return get_unsubcribed_url(KIND, kind, email, method, None)


def queued(kind: str) -> dict:
	"""What frappe.sendmail is handed, so its queue keeps the type and our
	method, and the header can be drawn for each recipient as it goes."""
	return {"reference_doctype": KIND, "reference_name": kind, "unsubscribe_method": METHOD}


def offered(user: str, kind: str) -> str | None:
	"""The type a person turns off from a mail of `kind`: the type itself, or
	the one it follows, when NotificationCenter lets them. None when it can't
	be turned off."""
	from onedesk.one import notify

	kind = (notify.declared().get(kind) or {}).get("follows") or kind
	for one in notify.choosable(user):
		if one["name"] == kind and one["allowed"]:
			return kind
	return None


def headed(raw: bytes, queue, recipient: str) -> bytes:
	"""A queued mail as it goes to one recipient: with List-Unsubscribe and
	one-click (RFC 8058) when it was queued with our method."""
	if not (queue.get("add_unsubscribe_link") and queue.get("unsubscribe_method") == METHOD):
		return raw
	if queue.get("reference_doctype") != KIND or not queue.get("reference_name"):
		return raw
	return with_header(raw, link(recipient, queue.reference_name))


def with_header(raw: bytes, url: str) -> bytes:
	"""The message with the two List-Unsubscribe headers added to its own,
	in its own line endings. Pure."""
	end = b"\r\n" if b"\r\n" in raw.split(b"\n\n", 1)[0] else b"\n"
	head, sep, body = raw.partition(end + end)
	kept = [
		line
		for line in head.split(end)
		if not line.lower().startswith((b"list-unsubscribe:", b"list-unsubscribe-post:"))
	]
	added = [b"List-Unsubscribe: <" + url.encode() + b">", b"List-Unsubscribe-Post: List-Unsubscribe=One-Click"]
	return end.join(kept + added) + sep + body


def _signed() -> bool:
	"""Whether the request's own query is the one we signed. frappe's
	verify_request takes a GET only, and a mail client's one-click is a POST."""
	from frappe.utils.verified_command import get_signed_params

	query = frappe.safe_decode(frappe.request.query_string or b"")
	params, _sep, signature = query.partition("&_signature=")
	return bool(signature) and hmac.compare_digest(get_signed_params(params), query)


def _choose(email: str, kind: str, on: int) -> bool:
	"""NotificationCenter's own switch, set as the person whose address it is."""
	from onedesk.one import notification_center

	user = frappe.db.get_value("User", {"email": email, "enabled": 1}, "name")
	if not user:
		return False
	frappe.set_user(user)
	try:
		notification_center.choose(kind, "email", on)
	except frappe.ValidationError:
		frappe.db.rollback()
		frappe.local.message_log = []
		return False
	finally:
		frappe.set_user("Guest")
	frappe.db.commit()
	return True


def _gone() -> None:
	frappe.respond_as_web_page(
		_("This link no longer works"),
		"",
		indicator_color="red",
		primary_action=SETTINGS,
		primary_label=_("Change what you get by mail"),
	)


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def off(email: str, doctype: str, name: str) -> None:
	"""A mail's Turn Off These Emails, opened, or its mail client's one-click."""
	if doctype != KIND or not _signed() or not _choose(email, name, 0):
		return _gone()
	frappe.respond_as_web_page(
		_("Emails Turned Off"),
		_("{0} is no longer emailed to {1}.").format(_(name), email),
		indicator_color="green",
		primary_action=link(email, name, AGAIN),
		primary_label=_("Turn On Again"),
	)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def on(email: str, doctype: str, name: str) -> None:
	"""Turn On Again, from the page `off` shows."""
	if doctype != KIND or not _signed() or not _choose(email, name, 1):
		return _gone()
	frappe.respond_as_web_page(
		_("Emails Turned On"),
		_("{0} is emailed to {1} again.").format(_(name), email),
		indicator_color="green",
		primary_action=SETTINGS,
		primary_label=_("Change what you get by mail"),
	)
