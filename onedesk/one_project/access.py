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
