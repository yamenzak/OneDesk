"""Who sees a task: the ones they made or were given, a task in a project they
may see, a template task, and a task shared with them.
"""

import json

import frappe
from frappe.permissions import (
	SYSTEM_USER_ROLE,
	add_permission,
	setup_custom_perms,
	update_permission_property,
)

from onedesk.one_project import members

GRANTS = ("read", "write", "create", "delete", "share")


def settle() -> None:
	"""Desk User may keep tasks. Written once, like one_crm/access.py: a Task
	with Custom DocPerm rows has been decided by the workspace."""
	_repeats()
	if frappe.db.exists("Custom DocPerm", {"parent": "Task", "role": SYSTEM_USER_ROLE}):
		return
	where = {"parent": "Task", "role": SYSTEM_USER_ROLE, "permlevel": 0}
	if not (frappe.db.exists("Custom DocPerm", where) or frappe.db.exists("DocPerm", where)):
		add_permission("Task", SYSTEM_USER_ROLE, 0)
	for ptype in GRANTS:
		update_permission_property("Task", SYSTEM_USER_ROLE, 0, ptype, 1, validate=False)


def _repeats() -> None:
	"""Desk User may make, change and stop repeats of their own: Repeat on a
	task is frappe's Auto Repeat, which frappe gives only to the books. frappe
	asks itself that whoever makes one may change what it repeats. Written
	once."""
	where = {"parent": "Auto Repeat", "role": SYSTEM_USER_ROLE, "permlevel": 0, "if_owner": 1}
	if frappe.db.exists("Custom DocPerm", where):
		return
	setup_custom_perms("Auto Repeat")
	rights = dict.fromkeys(("read", "write", "create", "delete"), 1)
	frappe.get_doc({"doctype": "Custom DocPerm", **where, **rights}).insert(ignore_permissions=True)
	frappe.clear_cache(doctype="Auto Repeat")


def sees_projects(user: str) -> bool:
	"""Whether a role other than Desk User lets this person read tasks."""
	roles = set(frappe.get_roles(user)) - {SYSTEM_USER_ROLE, "All", "Guest"}
	return any(rule.read and not rule.permlevel and rule.role in roles for rule in frappe.get_meta("Task").permissions)


def assigned(doc, user: str) -> bool:
	return user in (frappe.parse_json(doc.get("_assign") or "[]") or [])


def every(user: str) -> bool:
	"""Whether this person sees every task: OneTask's See Every Task
	(abilities.py), a OneTask Manager's."""
	from onedesk.one import rights

	return rights.held("Task", "task_every", user)


def allowed(doc, ptype=None, user=None, debug=False) -> bool:
	user = user or frappe.session.user
	if user == "Administrator" or doc.is_new() or every(user):
		return True
	if doc.owner == user:
		return True
	if assigned(doc, user):
		return ptype != "delete" or in_view(doc.project, user)
	if doc.get("is_template") and sees_projects(user):
		return True
	return in_view(doc.project, user)


def in_view(project: str | None, user: str) -> bool:
	"""Whether a task's project puts it in front of this person."""
	return bool(project) and sees_projects(user) and members.sees(project, user)


def query(user=None, doctype=None) -> str:
	user = user or frappe.session.user
	if user == "Administrator" or every(user):
		return ""
	said = frappe.db.escape
	mine = f"(`tabTask`.`owner` = {said(user)} or `tabTask`.`_assign` like {said(f'%{json.dumps(user)}%')})"
	if not sees_projects(user):
		return mine
	template = "`tabTask`.`is_template` = 1"
	if members.manages(user):
		return f"({mine} or {template} or ifnull(`tabTask`.`project`, '') != '')"
	return f"({mine} or {template} or `tabTask`.`project` in ({members.names(members.visible(user))}))"
