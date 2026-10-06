"""Who works with everybody's records, and so is not kept to their own.

hrms gives every employee a User Permission on their own Employee record (the
employee's Create User Permission box, ticked by default), and from then on
that person sees only what links to themselves: their own timesheets, claims
and leave. Right for most people, and wrong for whoever manages an app. A
project manager could not approve the crew's time, and the books could not
see the timesheets they invoice.

ERPNext's answer is to untick the box. Here it is unticked for whoever People
makes a manager of an app or an administrator of the workspace, and ticked
again when they are neither. It is a rule on the Employee and the User, so it
holds however either is changed: People, the form, a bulk edit or an import.
"""

import frappe

from onedesk.one import roles


def managers() -> set[str]:
	"""The roles that make somebody work with everybody's records."""
	from onedesk.one.settings import APPS

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
