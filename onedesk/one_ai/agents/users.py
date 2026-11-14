"""Each app's agent is a user of the workspace (docs/ARC-AI.md, Trust and
permissions), made on install and on every migrate from the registry
(registry/agents.py), holding its app's User roles and its own roles, which
no person holds, and nothing else. It is turned off, so it never signs in
and takes no seat; the door (door.py) and the Worker's calls (api.py) act
as it."""

import frappe
from frappe import _

from onedesk.one import registry
from onedesk.one.registry import agents


def ensure() -> None:
	for agent in (*agents.listed(), *agents.centred()):
		_made(agent)
		_roles(agent)
		_only(agent)
		for contact in frappe.get_all("Contact", filters={"user": agent.email}, pluck="name"):
			frappe.delete_doc("Contact", contact, ignore_permissions=True, force=True)
		frappe.clear_cache(user=agent.email)


def full_name(agent) -> str:
	return _("{0}'s {1}").format(registry.name(agent.app), _(agent.title))


def _made(agent) -> None:
	if frappe.db.exists("User", agent.email):
		frappe.db.set_value("User", agent.email, {"enabled": 0, "user_type": "System User", "first_name": full_name(agent)}, update_modified=False)
		return
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": agent.email,
			"first_name": full_name(agent),
			"enabled": 0,
			"send_welcome_email": 0,
			"user_type": "System User",
		}
	)
	user.flags.ignore_permissions = True
	user.flags.no_welcome_mail = True
	user.insert()


def _only(agent) -> None:
	"""An agent's own role is held by nobody else: a person or another agent
	given it is relieved of it."""
	where = {"role": ["in", agent.only], "parenttype": "User", "parent": ["!=", agent.email]}
	for user in set(frappe.get_all("Has Role", filters=where, pluck="parent")):
		frappe.db.delete("Has Role", {**where, "parent": user})
		frappe.clear_cache(user=user)


def _roles(agent) -> None:
	"""Exactly the manifest's roles: any other a person or an upgrade gave
	the agent is taken away. Written directly, since saving a user queues a
	contact an agent must not have."""
	held = set(frappe.get_all("Has Role", filters={"parent": agent.email, "parenttype": "User"}, pluck="role"))
	for role in held - set(agent.roles):
		frappe.db.delete("Has Role", {"parent": agent.email, "parenttype": "User", "role": role})
	for role in set(agent.roles) - held:
		if frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Has Role", "parent": agent.email, "parenttype": "User", "parentfield": "roles", "role": role}).db_insert()
