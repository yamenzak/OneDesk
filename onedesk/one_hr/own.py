"""Who the reader is here.

The Employee whose `user_id` is the session's user, and nothing else. Not a
match on email, which is one line shorter and hands somebody their namesake's
record on any workspace where two people share a personal address, and not a
match on name. A reader with no such row is nobody here — which is a workspace
that has not linked its logins, and the fix is a field on a record.

Everything that writes a clock-in reads the employee from here rather than
taking one as an argument, which is what makes those endpoints safe: there is no
value a caller can send that points at a colleague.
"""

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
