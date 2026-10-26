"""Who works with everybody's records, and so is not kept to their own."""

import frappe

from onedesk.one import roles


def managers() -> set[str]:
	"""The roles that make somebody work with everybody's records."""
	from onedesk.one.people import APPS

	return {role for *_names, _users, managing in APPS for role in managing} | {roles.ADMINISTRATOR}


def manages(user: str | None) -> bool:
	return bool(user) and bool(managers() & set(frappe.get_roles(user)))


def employee(doc, method=None) -> None:
	"""Employee validate: a manager's own box is unticked."""
	if doc.user_id and doc.create_user_permission and manages(doc.user_id):
		doc.create_user_permission = 0


def user(doc, method=None) -> None:
	"""User on_update: becoming a manager unticks the box, and no longer
	being one ticks it again."""
	before = doc.get_doc_before_save()
	if not before or not frappe.db.exists("DocType", "Employee"):
		return
	was = bool(managers() & {row.role for row in before.roles})
	now = bool(managers() & {row.role for row in doc.roles})
	if was == now:
		return
	for name in frappe.get_all("Employee", filters={"user_id": doc.name}, pluck="name"):
		one = frappe.get_doc("Employee", name)
		if one.create_user_permission == int(not now):
			continue
		one.create_user_permission = int(not now)
		one.flags.ignore_permissions = True
		one.save()
