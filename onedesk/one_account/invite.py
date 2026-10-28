"""Inviting somebody: One's own mail, and a link that lasts a week.

Opening the link asks frappe for a fresh reset link and goes there, so the
password is still set on frappe's own page, however late they come.
"""

import hashlib

import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, get_url, now_datetime

DAYS = 7


def _key(user: str) -> str:
	return f"{user}_one_invite"


def _hash(token: str) -> str:
	return hashlib.sha256(token.encode()).hexdigest()


def send(
	user: str, apps: list[str] | None = None, inviter: str | None = None, what: str | None = None
) -> None:
	"""Mail an invitation to somebody just added: who asked, to what, what
	they may use besides the five everybody has, and the link to join. The
	owner of a new workspace is invited by One (one_account/owner.py), since nobody
	on it asked. A customer's or supplier's contact (one_portal/invite.py)
	gets the Portal Invitation instead, saying `what` they will see."""
	from onedesk.one import tell

	token = frappe.generate_hash(length=32)
	frappe.db.set_default(_key(user), f"{_hash(token)}|{add_days(now_datetime(), DAYS).isoformat()}")
	email, lang = frappe.db.get_value("User", user, ["email", "language"])
	said = {
		"lang": lang,
		"now": False,
		"inviter": inviter or frappe.utils.get_fullname(),
		"workspace": frappe.db.get_single_value("Workspace Account", "workspace_name") or "One",
		"address": email,
		"days": DAYS,
		"link": get_url(f"/api/method/onedesk.one_account.invite.accept?key={token}"),
	}
	if what:
		tell.invited_to_portal(email, what, **said)
		return
	tell.invited(email, apps, **said)


def pending(user: str) -> bool:
	return bool(frappe.db.get_default(_key(user)))


def spend(user: str) -> bool:
	"""The invitation is used: its key stops working. Whether there was one."""
	had = pending(user)
	if had:
		frappe.defaults.clear_default(_key(user))
	return had


@frappe.whitelist(allow_guest=True, methods=["GET"])
def accept(key: str):
	"""The link in the mail: a fresh reset link from frappe, and there."""
	found = frappe.db.sql(
		"select defkey, defvalue from `tabDefaultValue` where parent = '__default' and defkey like %s and defvalue like %s",
		("%\\_one\\_invite", f"{_hash(key or '')}|%"),
		as_dict=True,
	)
	user = found[0].defkey[: -len("_one_invite")] if found else None
	if not user or get_datetime(found[0].defvalue.split("|", 1)[1]) < now_datetime():
		return frappe.respond_as_web_page(
			_("This invitation has expired"),
			_("Ask the person who invited you to send it again."),
			http_status_code=410,
			indicator_color="orange",
		)
	doc = frappe.get_doc("User", user)
	if doc.user_type == "Website User":
		from onedesk.one_portal import gate

		if not gate.on():
			return frappe.respond_as_web_page(
				_("This invitation can't be used now"), gate.closed(), http_status_code=403, indicator_color="orange"
			)
	if not doc.enabled:
		return frappe.respond_as_web_page(
			_("This invitation was withdrawn"), _("Ask the person who invited you."), http_status_code=410
		)
	link = doc._reset_password()
	frappe.db.commit()
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = link
