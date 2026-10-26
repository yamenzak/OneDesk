"""Inviting a customer's or supplier's contact to the portal, and taking it
back. See one/portal.py.

Revoke Access turns the login off and signs it out everywhere; Restore Access
turns it back on.
"""

import frappe
from frappe import _
from frappe.utils import pretty_date

from onedesk.one import roles
from onedesk.one_account import invite
from onedesk.one.portal import PARTIES

MANAGERS = {"Customer": "Sales Manager", "Supplier": "Purchase Manager"}


def _parties(contact) -> list[tuple[str, str]]:
	return [(row.link_doctype, row.link_name) for row in contact.links or [] if row.link_doctype in PARTIES]


def _may(contact) -> bool:
	"""A workspace administrator, or the manager of one of the contact's
	parties."""
	if roles.administers():
		return True
	mine = set(frappe.get_roles())
	return any(MANAGERS[kind] in mine for kind, _name in _parties(contact))


def _contact(name: str):
	contact = frappe.get_doc("Contact", name)
	contact.check_permission("read")
	if not _may(contact):
		frappe.throw(
			_("Only an administrator or the customer's or supplier's manager can do this."),
			frappe.PermissionError,
		)
	return contact


def _what(contact) -> str:
	kinds = {kind for kind, _name in _parties(contact)}
	if kinds == {"Supplier"}:
		return _("the quote requests and orders sent to you")
	return _("your quotations, orders and invoices")


def _login(contact) -> str | None:
	"""The contact's portal login: theirs, a Website User's."""
	if contact.user and frappe.db.get_value("User", contact.user, "user_type") == "Website User":
		return contact.user
	return None


@frappe.whitelist()
def state(contact: str) -> dict:
	"""What the contact's form says of the portal, and what may be done."""
	doc = frappe.get_doc("Contact", contact)
	doc.check_permission("read")
	may = bool(_parties(doc)) and _may(doc)
	user = _login(doc)
	if not user:
		staff = bool(doc.user)
		return {"status": "staff" if staff else None, "may": may and not staff and bool(doc.email_id)}
	enabled, last_login = frappe.db.get_value("User", user, ["enabled", "last_login"])
	if not enabled:
		status = "revoked"
	elif last_login:
		status = "active"
	else:
		status = "invited"
	return {
		"status": status,
		"may": may,
		"when": pretty_date(last_login) if last_login else None,
		"user": user,
	}


@frappe.whitelist(methods=["POST"])
def invite_contact(contact: str) -> dict:
	"""Invite the contact: their login made or found, linked, and mailed."""
	doc = _contact(contact)
	if not _parties(doc):
		frappe.throw(_("Link the contact to a customer or supplier first."))
	email = (doc.email_id or "").strip()
	if not email:
		frappe.throw(_("Add the contact's email first."))
	existing = frappe.db.get_value("User", {"email": email}, ["name", "user_type", "enabled"], as_dict=True)
	if existing and existing.user_type != "Website User":
		frappe.throw(_("{0} is someone in the workspace. They sign in to One, not the portal.").format(email))
	if existing:
		user = existing.name
		if not existing.enabled:
			frappe.db.set_value("User", user, "enabled", 1)
	else:
		user = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": doc.first_name or email.split("@")[0],
					"last_name": doc.last_name,
					"user_type": "Website User",
					"send_welcome_email": 0,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
	doc = frappe.get_doc("Contact", doc.name)
	if doc.user != user:
		doc.user = user
		doc.flags.ignore_permissions = True
		doc.save()
	if not frappe.db.get_value("User", user, "last_login"):
		_mail(doc, user)
	return state(contact)


def _mail(doc, user: str) -> None:
	invite.send(user, what=_what(doc))


@frappe.whitelist(methods=["POST"])
def invite_again(contact: str) -> dict:
	"""A new link, for an invitation not yet used; the old link stops."""
	doc = _contact(contact)
	user = _login(doc)
	if not user or frappe.db.get_value("User", user, "last_login"):
		frappe.throw(_("They have already signed in."))
	_mail(doc, user)
	return state(contact)


@frappe.whitelist(methods=["POST"])
def revoke(contact: str) -> dict:
	"""The login turned off and signed out everywhere, its invitation spent."""
	from frappe.sessions import clear_sessions

	doc = _contact(contact)
	user = _login(doc)
	if user:
		frappe.db.set_value("User", user, "enabled", 0)
		clear_sessions(user=user, force=True)
		invite.spend(user)
	return state(contact)


@frappe.whitelist(methods=["POST"])
def restore(contact: str) -> dict:
	"""The login turned back on; somebody who never signed in is mailed
	again."""
	doc = _contact(contact)
	user = _login(doc)
	if user:
		frappe.db.set_value("User", user, "enabled", 1)
		if not frappe.db.get_value("User", user, "last_login"):
			_mail(doc, user)
	return state(contact)
