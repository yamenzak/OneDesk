"""Who sees a task.

ERPNext lets a Projects User see every task and everybody else none. In One
every person keeps their own to-dos as tasks, so every desk user may now make
one, and sees:

- **the tasks they made, and the ones assigned to them**, always;
- **a task in a project they may see**, if a role other than Desk User already
  lets them read tasks — a Projects User, an HR Manager for boarding tasks.
  Which projects that is, is OneProject's rule (one_project/members.py): a
  Projects Manager sees them all, anybody else the ones they made, are
  members of, or that list nobody;
- **a task somebody shared with them**, which is frappe's own rule.

A task with no project is somebody's own to-do, so nobody else sees it, a
Projects User included, unless it is assigned or shared to them.

frappe's permission hooks can only take access away, so the grant is a
Custom DocPerm for Desk User (`settle`) and the rest is the two hooks below
narrowing it. Who "already reads tasks" is read off the doctype's own rules,
so a workspace that gives another role Task read changes the answer without
touching this file.
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
	if members.manages(user):
		return f"({mine} or ifnull(`tabTask`.`project`, '') != '')"
	return f"({mine} or `tabTask`.`project` in ({members.names(members.visible(user))}))"
