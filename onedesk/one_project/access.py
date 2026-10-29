"""Who may do what in OneProject, where ERPNext's defaults do not fit."""

import frappe
from frappe.permissions import add_permission, setup_custom_perms, update_permission_property

from onedesk.one import roles

GIVEN = {
	"Projects Settings": {"Projects Manager": ("read", "write")},
	"Budget": {"Projects Manager": (*roles.WORK, "cancel", "amend")},
	"Project": {"Accounts User": roles.USE, "Accounts Manager": roles.USE},
}

MANAGER = "Projects Manager"
USER = "Projects User"


def settle() -> None:
	roles.give(GIVEN)
	_templates()
	_every()
	_billing()


def _every() -> None:
	"""Whoever managed projects saw every project before See Every Project
	was an ability (abilities.py): each such person is made a OneProject
	Manager once, when nobody holds that role yet."""
	if not frappe.db.exists("Role", "OneProject Manager") or frappe.db.exists(
		"Has Role", {"role": "OneProject Manager", "parenttype": "User"}
	):
		return
	for user in frappe.get_all("Has Role", filters={"role": MANAGER, "parenttype": "User"}, pluck="parent", distinct=True):
		if user not in ("Administrator", "Guest") and frappe.db.get_value("User", user, "enabled"):
			doc = frappe.get_doc("User", user)
			doc.flags.ignore_permissions = True
			doc.add_roles("OneProject Manager")


def _templates() -> None:
	"""A Projects Manager may keep templates. Written once, like
	one_task/access.py: a Project Template with Custom DocPerm rows has been
	decided by the workspace."""
	if frappe.db.exists("Custom DocPerm", {"parent": "Project Template"}):
		return
	setup_custom_perms("Project Template")
	if not frappe.db.exists("Custom DocPerm", {"parent": "Project Template", "role": MANAGER, "permlevel": 0}):
		add_permission("Project Template", MANAGER, 0)
	for ptype in ("read", "write", "create", "delete"):
		update_permission_property("Project Template", MANAGER, 0, ptype, 1, validate=False)
	if frappe.db.exists("Custom DocPerm", {"parent": "Project Template", "role": USER, "permlevel": 0}):
		update_permission_property("Project Template", USER, 0, "read", 1, validate=False)


def _billing() -> None:
	"""A Projects Manager reads what time bills (a timesheet's level 1:
	billing hours, rates and amounts). erpnext keeps those to Accounts User,
	yet copies each amount into a field anyone may read, so its Timesheet
	Billing Summary showed a project manager the money and 0 hours; the
	project page shows them what was billed anyway. Written once, like the
	templates: a level-1 row for the role is the workspace's to change."""
	if frappe.db.exists("Custom DocPerm", {"parent": "Timesheet", "role": MANAGER, "permlevel": 1}):
		return
	setup_custom_perms("Timesheet")
	add_permission("Timesheet", MANAGER, 1)
	update_permission_property("Timesheet", MANAGER, 1, "read", 1, validate=False)
