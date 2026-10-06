"""Who the reader is here."""

import frappe


def installed() -> bool:
	return bool(frappe.db.exists("DocType", "Employee"))


def employee_of(user: str | None = None) -> str:
	"""The Employee this user *is*, or an empty string.

	`ignore_permissions` is right here for the same reason it is right in a
	favourites filter: the only filter is the session's own user, so there is no
	row this can return that is not the caller's own. A seat that cannot read
	Employee at all still has to be able to find out that it is nobody.
	"""
	if not installed():
		return ""
	found = frappe.get_all(
		"Employee",
		filters={"user_id": user or frappe.session.user, "status": "Active"},
		pluck="name",
		limit=1,
		ignore_permissions=True,
	)
	return found[0] if found else ""
