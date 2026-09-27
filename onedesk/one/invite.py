"""Inviting somebody: One's own mail, and a link that lasts a week.

Frappe's welcome mail was a password-reset link, and a reset link lives as
long as System Settings' `reset_password_link_expiry_duration`, twenty
minutes here: somebody who opened the mail after lunch could not get in. It
said nothing of who asked them or to what either. So the mail is ours, sent
through the hub as the Invitation type, and its link carries our own key,
good for `DAYS`. Opening it asks frappe for a fresh reset link and goes
there, so the password is still set on frappe's own page, however late they
come. Setting it spends the key.

The key is kept as a hash in frappe's defaults, beside where frappe keeps a
person's two-factor secret, never as it was sent.
"""

import hashlib

import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, get_url, now_datetime

#: How long an invitation's link works.
DAYS = 7


def _key(user: str) -> str:
	return f"{user}_one_invite"


def _hash(token: str) -> str:
	return hashlib.sha256(token.encode()).hexdigest()


def send(user: str, apps: list[str] | None = None) -> None:
	"""Mail an invitation to somebody just added: who asked, to what, what
	they may use besides the five everybody has, and the link to join."""
	from onedesk.one import notify

	token = frappe.generate_hash(length=32)
	frappe.db.set_default(_key(user), f"{_hash(token)}|{add_days(now_datetime(), DAYS).isoformat()}")
	email, lang = frappe.db.get_value("User", user, ["email", "language"])
	notify.mail(
		"Invitation",
		email,
		lang=lang,
		now=False,
		inviter=frappe.utils.get_fullname(),
		workspace=frappe.db.get_single_value("Workspace Account", "workspace_name") or "One",
		apps=(" " + _("You can use {0}.").format(", ".join(apps))) if apps else "",
		address=email,
		days=DAYS,
		link=get_url(f"/api/method/onedesk.one.invite.accept?key={token}"),
	)


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
			_("Ask whoever invited you to send it again, from Workspace, People."),
			http_status_code=410,
			indicator_color="orange",
		)
	doc = frappe.get_doc("User", user)
	if not doc.enabled:
		return frappe.respond_as_web_page(
			_("This invitation was withdrawn"), _("Ask whoever invited you."), http_status_code=410
		)
	link = doc._reset_password()
	# A GET is not committed on its own, and the new reset key must be kept.
	frappe.db.commit()
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = link
