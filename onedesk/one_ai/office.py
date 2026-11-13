"""AICenter as the agents' office (docs/ARC-AI.md, AICenter): every app's
agent, who it is, how far it may go with each action and how that went,
what it learned, what it did and what it cost this month; and for them all,
the rules they follow, their credits and the switch that turns them off.
A workspace administrator's to read and to change; what is chosen is kept
by agents/workspace.py."""

import importlib

import frappe
from frappe import _
from frappe.utils import cint, flt

from onedesk.one import registry, roles
from onedesk.one.registry import agents as registry_agents
from onedesk.one_ai.agents import door, levels, users, workspace

MOST_DONE = 30

MOST_LEARNED = 10


def _agent(app: str):
	agent = registry_agents.get(app)
	if not agent:
		frappe.throw(_("{0} has no agent.").format(app))
	return agent


def _agent_py(app: str):
	try:
		return importlib.import_module(f"onedesk.{app}.agent")
	except ModuleNotFoundError:
		return None


def record(email: str) -> dict[str, dict[str, int]]:
	"""{action: {done, corrected, refused, waiting}} from what the agent did."""
	rows = frappe.get_all(
		"Reading Action",
		filters={"agent": email},
		fields=["agent_action", "level", {"COUNT": "*", "as": "n"}],
		group_by="agent_action, level",
	)
	return tallied(rows)


def tallied(rows) -> dict[str, dict[str, int]]:
	"""Reading Action counts by action and level, as AICenter reads them:
	what was undone was done and corrected, a dismissed card corrected,
	Proposed is waiting. Pure."""
	out: dict[str, dict[str, int]] = {}
	for one in rows:
		held = out.setdefault(one["agent_action"] or "", {"done": 0, "corrected": 0, "refused": 0, "waiting": 0})
		n = cint(one["n"])
		if one["level"] == "Undone":
			held["done"] += n
			held["corrected"] += n
		elif one["level"] == "Dismissed":
			held["corrected"] += n
		elif one["level"] == "Done":
			held["done"] += n
		elif one["level"] == "Refused":
			held["refused"] += n
		elif one["level"] == "Proposed":
			held["waiting"] += n
	return out


def _person(user: str | None) -> str | None:
	return frappe.utils.get_fullname(user) if user else None


def _summed(record: dict) -> dict[str, int]:
	keys = ("done", "corrected", "refused", "waiting")
	return {key: sum(one[key] for one in record.values()) for key in keys}


@frappe.whitelist(methods=["GET"])
def team() -> dict:
	"""Every agent at a glance, the rules they all follow, and their credits."""
	roles.require()
	spent, limits = workspace.spent(), workspace.limits()
	listed = []
	never = 0
	for one in registry_agents.listed():
		module = _agent_py(one.app)
		never += len(getattr(module, "NOT_FOR_AI", {}) or {})
		listed.append(
			{
				"app": one.app,
				"module": registry.name(one.app),
				"name": users.full_name(one),
				"record": _summed(record(one.email)),
				"spent": spent.get(one.app, 0.0),
				"limit": limits.get(one.app),
			}
		)
	return {
		"on": workspace.on(),
		"agents": listed,
		"never_roles": list(registry_agents.NEVER),
		"never": never,
		"spent": round(sum(spent.values()), 6),
		"limit": limits.get(workspace.ALL),
	}


def _actions(app: str, email: str) -> list[dict]:
	declared = levels.declared(app)
	done = record(email)
	empty = {"done": 0, "corrected": 0, "refused": 0, "waiting": 0}
	return [
		{
			"action": action,
			"label": levels.label(app, action),
			"level": levels.of(app, action),
			"declared": declared.get(action) if declared.get(action) in levels.LEVELS else levels.CAUTIOUS,
			"record": done.get(action, empty),
		}
		for action in levels.actions(app)
	]


def _learned(email: str) -> list[dict]:
	"""What people corrected of the agent's work, which it reads next time
	(reading/lessons.py)."""
	actions = frappe.get_all("Reading Action", filters={"agent": email}, pluck="name")
	if not actions:
		return []
	return frappe.get_all(
		"Reading Lesson",
		filters={"action": ["in", actions]},
		fields=["name", "what", "said", "party_name", "by", "creation"],
		order_by="creation desc",
		limit=MOST_LEARNED,
	)


def _did(app: str, email: str) -> list[dict]:
	rows = frappe.get_all(
		"Reading Action",
		filters={"agent": email},
		fields=["name", "kind", "level", "target_doctype", "target_name", "agent_action", "why", "creation"],
		order_by="creation desc",
		limit=MOST_DONE,
	)
	for one in rows:
		one["kind_label"] = _(one.kind)
		one["level_label"] = _(one.level)
		one["action_label"] = levels.label(app, one.agent_action) if one.agent_action else None
		one["opens"] = bool(one.target_doctype and one.target_name and frappe.db.exists(one.target_doctype, one.target_name))
	return rows


@frappe.whitelist(methods=["GET"])
def agent(app: str) -> dict:
	"""One agent's tab: who it is, what it may do with its record on each,
	what it never does and why, what it learned, what it did and its credits."""
	roles.require()
	held = _agent(app)
	module = _agent_py(app)
	return {
		"app": app,
		"module": registry.name(app),
		"name": users.full_name(held),
		"line": str(registry.get(app).line or ""),
		"roles": [_(role) for role in held.roles],
		"approver": _person(door.approver(app)),
		"actions": _actions(app, held.email),
		"never": list((getattr(module, "NOT_FOR_AI", {}) or {}).values()),
		"learned": _learned(held.email),
		"did": _did(app, held.email),
		"spent": workspace.spent().get(app, 0.0),
		"limit": workspace.limits().get(app),
	}


@frappe.whitelist(methods=["POST"])
def set_level(app: str, action: str, level: str) -> str:
	"""An action's level for this workspace; the level its app declares is
	kept as no choice at all."""
	roles.require()
	_agent(app)
	if action not in levels.actions(app):
		frappe.throw(_("{0} is not one of {1}'s actions.").format(action, registry.name(app)))
	if level not in levels.LEVELS:
		frappe.throw(_("Choose Act, Draft or Ask First."))
	declared = levels.declared(app).get(action)
	workspace.choose(app, action, None if level == declared else level)
	return levels.of(app, action)


@frappe.whitelist(methods=["POST"])
def set_limit(app: str, credits: float | str = 0) -> float | None:
	"""Credits a month for one agent, or for all of them as `*`; 0 is no limit."""
	roles.require()
	if app != workspace.ALL:
		_agent(app)
	if flt(credits) < 0:
		frappe.throw(_("Set to 0 for no limit."))
	workspace.set_limit(app, credits)
	return workspace.limits().get(app)


@frappe.whitelist(methods=["POST"])
def set_on(on: int | str) -> bool:
	"""Every agent on or off for the whole workspace."""
	roles.require()
	workspace.switch(bool(cint(on)))
	return workspace.on()
