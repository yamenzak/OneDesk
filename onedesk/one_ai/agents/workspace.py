"""What a workspace says about its agents, in AICenter (docs/ARC-AI.md,
AICenter): an action's level where an administrator chose one over what its
app declares, a month's credits for each agent and for them all, and the
switch that turns every agent off. Kept as the workspace's defaults, beside
OneAI's own; levels.of, the door (door.py), the Worker's way in (api.py) and
its wake (connect.py) read it."""

import json

import frappe
from frappe import _
from frappe.utils import flt, nowdate

LEVELS_KEY = "one_agent_levels"
LIMITS_KEY = "one_agent_limits"
SPENT_KEY = "one_agent_spent"
OFF_KEY = "one_agents_off"

ALL = "*"
"""The limits' key for every agent together."""

OFF, OVER, ALL_OVER = "off", "over", "all over"


def _held(key: str) -> dict:
	try:
		held = json.loads(frappe.db.get_default(key) or "{}")
	except ValueError:
		return {}
	return held if isinstance(held, dict) else {}


def _keep(key: str, value: dict) -> None:
	frappe.db.set_default(key, json.dumps(value, sort_keys=True))


def chosen() -> dict[str, dict[str, str]]:
	"""{app: {action: level}}, each level an administrator chose."""
	return _held(LEVELS_KEY)


def chosen_level(app: str, action: str) -> str | None:
	return chosen().get(app, {}).get(action)


def choose(app: str, action: str, level: str | None) -> None:
	"""An action's level for this workspace; none puts back what its app declares."""
	held = chosen()
	own = held.setdefault(app, {})
	if level:
		own[action] = level
	else:
		own.pop(action, None)
	_keep(LEVELS_KEY, {key: value for key, value in held.items() if value})


def limits() -> dict[str, float]:
	"""{app or ALL: credits a month}; none set is no limit."""
	return {key: flt(value) for key, value in _held(LIMITS_KEY).items() if flt(value) > 0}


def set_limit(app: str, credits) -> None:
	held = _held(LIMITS_KEY)
	if flt(credits) > 0:
		held[app] = flt(credits)
	else:
		held.pop(app, None)
	_keep(LIMITS_KEY, held)


def month() -> str:
	return nowdate()[:7]


def spent() -> dict[str, float]:
	"""This month's credits by app; a count from a month before is nothing."""
	held = _held(SPENT_KEY)
	return {key: flt(value) for key, value in (held.get("by") or {}).items()} if held.get("month") == month() else {}


def spend(app: str, credits) -> None:
	"""Credits a model call used while an agent worked (run.py, `_counted`)."""
	if not flt(credits):
		return
	by = spent()
	by[app] = round(by.get(app, 0.0) + flt(credits), 6)
	_keep(SPENT_KEY, {"month": month(), "by": by})


def on() -> bool:
	return not frappe.utils.cint(frappe.db.get_default(OFF_KEY))


def switch(on: bool) -> None:
	frappe.db.set_default(OFF_KEY, "0" if on else "1")


def refused(off: bool, limits: dict, spent: dict, app: str) -> str | None:
	"""Why an agent may not work now: every agent off, this agent over its
	month's credits, or all of them over theirs. Pure."""
	if off:
		return OFF
	if limits.get(app) and spent.get(app, 0.0) >= limits[app]:
		return OVER
	if limits.get(ALL) and sum(value for key, value in spent.items() if key != ALL) >= limits[ALL]:
		return ALL_OVER
	return None


def refusal(app: str) -> str | None:
	"""The reason an agent stops, in the words a person reads, or None."""
	from onedesk.one.registry import agents
	from onedesk.one_ai.agents import users

	held = limits()
	why = refused(not on(), held, spent(), app)
	if why == OFF:
		return _("Agents are turned off for this workspace.")
	agent = agents.get(app)
	name = users.full_name(agent) if agent else app
	if why == OVER:
		return _("{0} has used its {1} credits for this month.").format(name, frappe.format(held[app], {"fieldtype": "Float"}))
	if why == ALL_OVER:
		return _("The agents have used their {0} credits for this month.").format(frappe.format(held[ALL], {"fieldtype": "Float"}))
	return None


def refuse(app: str) -> None:
	"""Every agent's call asks this before it runs."""
	why = refusal(app)
	if why:
		frappe.throw(why, frappe.PermissionError)
