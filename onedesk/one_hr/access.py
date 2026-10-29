"""Who may do what in OneHR, where HRMS's defaults do not fit."""

import frappe

from onedesk.one import roles

USER, MANAGER = "HR User", "HR Manager"

GIVEN = {
	doctype: {USER: roles.WORK, MANAGER: roles.MANAGE}
	for doctype in ("Travel Request", "Employee Advance", "Vehicle Log")
} | {one: {USER: roles.USE, MANAGER: roles.MANAGE} for one in ("Purpose of Travel", "Vehicle Service Item", "Driver", "Vehicle")}

RAISED = {
	doctype: {USER: roles.WORK, MANAGER: roles.MANAGE}
	for doctype in ("Gratuity", "Employee Onboarding", "Employee Separation")
}


REPORTS = ("Vehicle Expenses",)
"""HRMS's reports over what GIVEN hands HR, opened to HR too: Vehicle
Expenses was the Fleet Manager's alone, a role nobody here holds."""


HR_ONLY = ("Employee Analytics", "Employee Birthday")
"""Reports about everybody that HRMS opens to every Employee: the company
in numbers is HR's to read, and to anybody else they were the few records
they happen to reach."""

DASHBOARDS = ("Human Resource", "Attendance Overview", "Attendance", "Employee Lifecycle", "Recruitment", "Payroll", "Expense Claims")
"""HR's dashboards: the company in numbers, which is HR's to read. An
employee's own figures are on Home."""


def settle() -> None:
	roles.give(GIVEN)
	roles.raise_once(RAISED)
	for report in REPORTS:
		roles.open_report(report, USER, MANAGER)
	for report in HR_ONLY:
		_only("report", report, (USER, MANAGER, roles.ADMINISTRATOR))
	_only("page", "organizational-chart", (USER, MANAGER, roles.ADMINISTRATOR))


def _only(field: str, name: str, held: tuple) -> None:
	"""frappe's Custom Role, which replaces a report's or a page's own roles,
	set to `held`. The org chart is HR's for the same reason as HR_ONLY: an
	employee drew a chart of whoever they happen to reach."""
	if not frappe.db.exists(field.title(), name):
		return
	parent = frappe.db.get_value("Custom Role", {field: name})
	custom = frappe.get_doc("Custom Role", parent) if parent else frappe.new_doc("Custom Role")
	if not parent:
		custom.set(field, name)
		if field == "report":
			custom.ref_doctype = frappe.db.get_value("Report", name, "ref_doctype")
	wanted = [role for role in held if frappe.db.exists("Role", role)]
	if sorted(row.role for row in custom.roles) == sorted(wanted):
		return
	custom.set("roles", [{"role": role} for role in wanted])
	custom.save(ignore_permissions=True)


def _hr(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return user == "Administrator" or bool({USER, MANAGER, roles.ADMINISTRATOR} & set(frappe.get_roles(user)))


def dashboard_query(user: str | None = None) -> str:
	"""Dashboard permission_query_conditions: HR's dashboards to HR."""
	if _hr(user):
		return ""
	names = ", ".join(frappe.db.escape(one) for one in DASHBOARDS)
	return f"`tabDashboard`.name not in ({names})"


def dashboard_allowed(doc, ptype=None, user=None) -> bool:
	"""Dashboard has_permission: the same, on the page itself. True rather
	than None elsewhere, since frappe reads a falsy answer as a refusal."""
	return doc.name not in DASHBOARDS or _hr(user)


def interview_query(user: str | None = None) -> str:
	"""Interview permission_query_conditions: an interviewer outside HR sees the
	interviews they sit on. HRMS's Interviewer role read every one of them."""
	user = user or frappe.session.user
	if _hr(user):
		return ""
	who = frappe.db.escape(user)
	return (
		"(exists (select 1 from `tabInterview Detail` sat where sat.parent = `tabInterview`.name"
		f" and sat.interviewer = {who}) or `tabInterview`.owner = {who})"
	)


def interview_allowed(doc, ptype=None, user=None) -> bool:
	"""Interview has_permission: the same, on the record itself."""
	user = user or frappe.session.user
	return _hr(user) or doc.owner == user or any(row.interviewer == user for row in doc.get("interview_details") or [])
