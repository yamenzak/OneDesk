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



#: What a person is paid: kept to their own, though their hold on Employee
#: reaches everyone who reports to them, as a foreman's crew's job cards need.
PAY = (
	"Salary Slip",
	"Salary Structure Assignment",
	"Additional Salary",
	"Employee Incentive",
	"Retention Bonus",
	"Overtime Slip",
	"Arrear",
	"Payroll Correction",
	"Gratuity",
	"Full and Final Statement",
)

#: Roles that read pay as its employee and nobody else's.
SELF = {"Employee", "Employee Self Service"}


def _own_pay_only(doctype: str, user: str) -> bool:
	"""Whether this person reads these only as an employee, and so only their own."""
	if user == "Administrator":
		return False
	roles = {
		perm.get("role")
		for perm in frappe.permissions.get_valid_perms(doctype, user)
		if perm.get("read") and not perm.get("permlevel")
	}
	return bool(roles) and roles <= SELF


def pay_query(user: str | None = None, doctype: str | None = None) -> str:
	from onedesk.one_hr import own

	user = user or frappe.session.user
	if not doctype or not _own_pay_only(doctype, user):
		return ""
	return f"`tab{doctype}`.employee = {frappe.db.escape(own.employee_of(user) or '-')}"


def pay_allowed(doc, ptype=None, user=None, debug=False) -> bool:
	"""True leaves frappe's own rules to decide; a hook can only take away."""
	from onedesk.one_hr import own

	user = user or frappe.session.user
	if not _own_pay_only(doc.doctype, user):
		return True
	return bool(doc.get("employee")) and doc.get("employee") == own.employee_of(user)
