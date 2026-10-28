"""OnePortal turned off in the app picker (one/apps.py) closes the portal:
nobody outside signs in, a signed-in portal session is ended on its next
request, a link no longer opens, and nobody is invited. Nothing is deleted:
turned back on, every login and link works as it did.

It also keeps the Portal column on Contact (`one_portal`), which OnePortal's
People list is filtered on, in step with where each login stands.
"""

import frappe
from frappe import _

APP = "OnePortal"

SAID = {"invited": "Invited", "active": "Signed In", "revoked": "Revoked"}


def on() -> bool:
	from onedesk.one import apps

	return APP not in apps.hidden()


def closed() -> str:
	return _("The portal is turned off for this workspace.")


def refuse() -> None:
	"""Inviting, a link and the portal's own page ask this first."""
	if not on():
		frappe.throw(closed(), frappe.PermissionError)


def _outside(user: str) -> bool:
	return frappe.get_cached_value("User", user, "user_type") == "Website User"


def signing_in(login_manager) -> None:
	"""`on_login`: a portal login is refused while the portal is off, before
	frappe makes its session; one let in is marked Signed In."""
	user = login_manager.user
	if not user or not _outside(user):
		return
	if not on():
		frappe.throw(closed(), frappe.AuthenticationError)
	_mark(user, SAID["active"])


def ending() -> None:
	"""`before_request`: a portal session still open when the portal was
	turned off is signed out, and the request goes on as a guest's, which
	the portal's page sends to the sign-in that refuses them."""
	session = getattr(frappe.local, "session", None)
	if not session or session.user in (None, "Guest") or (session.data or {}).get("user_type") != "Website User":
		return
	if not on():
		frappe.local.login_manager.logout()


def mark(user: str | None) -> None:
	"""The Portal column of every contact this login belongs to."""
	if user:
		from onedesk.one_portal.invite import status_of

		_mark(user, SAID.get(status_of(user)[0], ""))


def _mark(user: str, value: str) -> None:
	for name in frappe.get_all("Contact", filters={"user": user}, pluck="name"):
		frappe.db.set_value("Contact", name, "one_portal", value, update_modified=False)


def contact(doc, method=None) -> None:
	"""Contact `validate`: the column follows the login linked to it."""
	from onedesk.one_portal.invite import status_of

	doc.one_portal = SAID.get(status_of(doc.user)[0], "")
