"""Who sees a task: the ones they made or were given, a task in a project they
may see, a template task, and a task shared with them.
"""

import json

import frappe
from frappe.permissions import SYSTEM_USER_ROLE, add_permission, update_permission_property

from onedesk.one_project import members

#: What every desk user may do to a task the two hooks let them near.
GRANTS = ("read", "write", "create", "delete", "share")


def settle() -> None:
	"""Desk User may keep tasks. Written once, like one_crm/access.py: a Task
	with Custom DocPerm rows has been decided by the workspace."""
	if frappe.db.exists("Custom DocPerm", {"parent": "Task", "role": SYSTEM_USER_ROLE}):
		return
	where = {"parent": "Task", "role": SYSTEM_USER_ROLE, "permlevel": 0}
	if not (frappe.db.exists("Custom DocPerm", where) or frappe.db.exists("DocPerm", where)):
		add_permission("Task", SYSTEM_USER_ROLE, 0)
	for ptype in GRANTS:
		update_permission_property("Task", SYSTEM_USER_ROLE, 0, ptype, 1, validate=False)


def sees_projects(user: str) -> bool:
	"""Whether a role other than Desk User lets this person read tasks."""
	roles = set(frappe.get_roles(user)) - {SYSTEM_USER_ROLE, "All", "Guest"}
	return any(rule.read and not rule.permlevel and rule.role in roles for rule in frappe.get_meta("Task").permissions)


def assigned(doc, user: str) -> bool:
	return user in (frappe.parse_json(doc.get("_assign")) or [])


def allowed(doc, ptype=None, user=None, debug=False) -> bool:
	user = user or frappe.session.user
	if user == "Administrator" or doc.is_new():
		return True
	if doc.owner == user:
		return True
	if assigned(doc, user):
		# Somebody else's to-do given to me is mine to do, not mine to delete.
		return ptype != "delete" or in_view(doc.project, user)
	if doc.get("is_template") and sees_projects(user):
		return True
	return in_view(doc.project, user)


def in_view(project: str | None, user: str) -> bool:
	"""Whether a task's project puts it in front of this person."""
	return bool(project) and sees_projects(user) and members.sees(project, user)


def query(user=None, doctype=None) -> str:
	user = user or frappe.session.user
	if user == "Administrator":
		return ""
	said = frappe.db.escape
	mine = f"(`tabTask`.`owner` = {said(user)} or `tabTask`.`_assign` like {said(f'%{json.dumps(user)}%')})"
	if not sees_projects(user):
		return mine
	template = "`tabTask`.`is_template` = 1"
	if members.manages(user):
		return f"({mine} or {template} or ifnull(`tabTask`.`project`, '') != '')"
	return f"({mine} or {template} or `tabTask`.`project` in ({members.names(members.visible(user))}))"
