"""Each agent's work on what OneAI read (docs/ARC-AI.md, What we keep): the
planners an app's agent.py names in PLANS, each an action of its agent with
a level, run at one of Intake's stages and taken through the agents' door
(door.py) under the agent's name. Intake's reading, matching and filing
stay shared (reading/planning.py); what a document makes is its owner's.

An app turned off, or an agent stopped in AICenter, does none of its work:
OneAI reads on, and nothing that agent would have made is made."""

import importlib

import frappe

from onedesk.one import apps, registry
from onedesk.one.registry import agents
from onedesk.one_ai.agents import door, workspace
from onedesk.one_ai.reading import act, matters

MATTERS = ("task", "event", "leave", "expense", "resignation", "employee", "books")
"""The keys an action has once per matter, however many documents come."""


def plans(app: str) -> dict[str, tuple[str, str]]:
	"""{action: (stage, planner)} an app's agent.py declares, each stage one of levels.STAGES."""
	try:
		module = importlib.import_module(f"onedesk.{app}.agent")
	except ModuleNotFoundError:
		return {}
	return dict(getattr(module, "PLANS", {}) or {})


def working() -> list:
	"""The agents that work now: their app is on and AICenter lets them."""
	hidden = set(apps.hidden())
	return [one for one in agents.listed() if registry.get(one.app).sidebar not in hidden and not workspace.refusal(one.app)]


def planned(stage: str, said: dict, ctx: dict) -> list[tuple[str, str, act.Action]]:
	"""(app, action, what to do) for every agent's planners at one stage, in
	the rail's order, then each app's in the order it declares them."""
	out = []
	for agent in working():
		for action, (at, path) in plans(agent.app).items():
			if at == stage:
				out += [(agent.app, action, one) for one in frappe.get_attr(path)(said, ctx)]
	return out


def keyed(reading, action: act.Action) -> act.Action:
	"""The action's key: once per matter for what a matter has once, else once
	per document."""
	action.key = matters.key(reading, action.key) if action.key.startswith(MATTERS) else f"{reading.key[:90]}|{action.key}"
	return action


def take(app: str | None, name: str | None, action: act.Action, reading) -> str | None:
	"""One action through its door: an agent's through door.act_for, OneAI's
	own (the shared reading's) through Intake's. Intake's gates come first:
	what the mailbox does not let OneAI do, and what a mail rule already
	made, nobody makes."""
	if not app:
		return act.apply(action, reading)
	if not reading.on_behalf_of or frappe.utils.cint(reading.history):
		return None
	if not act._does(reading, act.key_of(reading.key, action)) or act._ruled(reading, action):
		return None
	return door.act_for(app, name, action, reading=reading)
