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


def addresses_of(user: str | None = None) -> list[str]:
	"""Every address this person is reached at: their sign-in, and their
	Employee's personal, company and preferred ones. Lower case."""
	user = user or frappe.session.user
	found = {user, frappe.db.get_value("User", user, "email")}
	employee = employee_of(user)
	if employee:
		found.update(frappe.db.get_value("Employee", employee, ["personal_email", "company_email", "prefered_email"]) or ())
	return sorted({one.strip().lower() for one in found if one and "@" in one})
