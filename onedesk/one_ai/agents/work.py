"""Each agent's work, declared in its app's agent.py and taken through the
agents' door (door.py) under its name: PLANS on what OneAI read, WATCH on
its module's records, WAITS for a card a person approves, WAKES for the
Worker (one_ai/AGENTS.md, The agents). The Worker runs any agent alike,
and without it an agent does the same here (`here`). An app turned off, or
an agent stopped in AICenter, does none of its work."""

import importlib

import frappe
from frappe import _
from frappe.utils import cint

from onedesk.one import apps, registry
from onedesk.one.registry import agents
from onedesk.one_ai.agents import door, levels, workspace
from onedesk.one_ai.reading import act, matters

MATTERS = ("task", "event", "leave", "expense", "resignation", "employee", "books")
"""The keys an action has once per matter, however many documents come."""


HANDED = {"handed": "plan", "record": "watched"}
"""The tool an agent runs for an event its WAKES does not name."""

MOST_STEPS = 50
"""As many tools as one event runs, as the Worker's MOST_STEPS."""


def _declared(app: str, name: str) -> dict:
	try:
		module = importlib.import_module(f"onedesk.{app}.agent")
	except ModuleNotFoundError:
		return {}
	return dict(getattr(module, name, {}) or {})


def plans(app: str) -> dict[str, tuple[str, str]]:
	"""{action: (stage, planner)} an app's agent.py declares, each stage one of levels.STAGES."""
	return _declared(app, "PLANS")


def watches(app: str) -> dict[str, tuple[str, str, str]]:
	"""{action: (record type, when, job)} an app's agent.py declares, each when one of levels.WHEN."""
	return _declared(app, "WATCH")


def waits(app: str) -> dict[str, str]:
	"""{action: record type}: the planners that wait on a record OneAI's card makes."""
	return _declared(app, "WAITS")


def job(app: str, kind: str) -> str | None:
	"""The tool an app's agent runs when the Worker wakes it for an event."""
	return _declared(app, "WAKES").get(kind) or HANDED.get(kind)


def handing(to: str, args: dict) -> dict:
	"""A step that hands a document to another app's agent, with the tool
	that agent runs on it."""
	return {"to": to, "tool": job(to, "handed"), "args": args}


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


def _me():
	"""The agent the tool runs as (api.py sets its user)."""
	agent = agents.by_email(frappe.session.user)
	if not agent:
		frappe.throw(_("Not allowed."), frappe.PermissionError)
	return agent


def plan(reading: str, asked_by: str | None = None) -> dict:
	"""A tool every agent has: its planners on a document handed to it, at
	their stages, as Intake would have run them."""
	from onedesk.one_ai.reading import planning

	app = _me().app
	doc = frappe.get_doc("Reading", reading)
	if doc.state != "Understood" or cint(doc.history):
		return {"made": []}
	made = []
	for stage in levels.STAGES:
		here = [(action, path) for action, (at, path) in plans(app).items() if at == stage]
		if not here:
			continue
		said, ctx = planning.prepared(doc, stage)
		for action, path in here:
			made += [take(app, action, keyed(doc, one), doc) for one in frappe.get_attr(path)(said, ctx)]
	return {"made": [one for one in made if one]}


def watched(action: str, doctype: str | None = None, name: str | None = None, asked_by: str | None = None) -> dict:
	"""A tool every agent has: one of its jobs (WATCH), on a record or on its round."""
	return {"made": do(_me().app, action, doctype, name, asked_by)}


def do(app: str, action: str, doctype: str | None = None, name: str | None = None, asked_by: str | None = None) -> list[str]:
	"""One job of an app's agent through the door: the record it watches, or
	the round's, and what its job makes of it. Answers the Reading Action rows."""
	if action not in watches(app):
		frappe.throw(_("{0} is not one of {1}'s actions.").format(action, registry.name(app)))
	watching, when, path = watches(app)[action]
	if when in levels.ROUNDS:
		found = frappe.get_attr(path)()
	elif doctype == watching and name and frappe.db.exists(doctype, name):
		found = frappe.get_attr(path)(frappe.get_doc(doctype, name))
	else:
		return []
	return [one for one in (door.act_for(app, action, each, asked_by=asked_by) for each in found) if one]


def heard(doc, method=None) -> None:
	"""A record some agent watches was saved, submitted or cancelled: each
	working agent that watches it for that does its job once the change is
	committed (`on_record`)."""
	for agent in working():
		for action, (doctype, when, _path) in watches(agent.app).items():
			if doctype == doc.doctype and when == method:
				frappe.enqueue(f"{__name__}.on_record", queue="short", enqueue_after_commit=True, app=agent.app, action=action, doctype=doc.doctype, name=doc.name, asked_by=frappe.session.user)


def rounds() -> None:
	"""The hourly round: each working agent's jobs that run on it."""
	for agent in working():
		for action, (_doctype, when, _path) in watches(agent.app).items():
			if when in levels.ROUNDS:
				frappe.enqueue(f"{__name__}.on_record", queue="short", app=agent.app, action=action)


def on_record(app: str, action: str, doctype: str | None = None, name: str | None = None, asked_by: str | None = None) -> None:
	"""One job, on the Worker when it takes it, else here."""
	from onedesk.one_ai.agents import connect

	if workspace.refusal(app):
		return
	args = {"action": action, "doctype": doctype, "name": name}
	if not connect.wake(app, "record", args, asked_by):
		do(app, action, doctype, name, asked_by)


def here(app: str, kind: str, args: dict, asked_by: str | None = None) -> bool:
	"""What the Worker does with an event, done here: the woken agent's tool
	as its user, then each step its answer names, in turn (worker.ts work)."""
	from onedesk.one_ai.agents import api

	steps = [(app, job(app, kind), args)]
	was = frappe.session.user
	try:
		for _taken in range(MOST_STEPS):
			if not steps:
				break
			at, tool, given = steps.pop(0)
			if not tool:
				continue
			frappe.set_user(agents.email(at))
			answer = api.tool_of(at, tool)(**(given or {}), asked_by=asked_by) or {}
			steps += [(step.get("to") or at, step.get("tool"), step.get("args")) for step in answer.get("next") or []]
	finally:
		frappe.set_user(was)
	return True


def approved(doc, method=None) -> None:
	"""A card that makes a record was approved, by a person or the
	auditor: each working agent's planner that waits on that record type
	(WAITS) runs again on the document, once the approval is committed."""
	before = doc.get_doc_before_save()
	if doc.kind != "Create" or doc.level != "Done" or not doc.reading or not before or before.level != "Proposed":
		return
	if any(doc.target_doctype in waits(agent.app).values() for agent in working()):
		frappe.enqueue(f"{__name__}.waited", queue="short", enqueue_after_commit=True, action=doc.name)


def waited(action: str) -> list[str]:
	"""What waited on an approved card: its document matched to the record
	the card made, then each working agent's planner that waits on that
	record type, through the door, its row saying what it waited for."""
	from onedesk.one_ai.reading import planning

	card = frappe.get_doc("Reading Action", action)
	reading = frappe.get_doc("Reading", card.reading)
	planning.rematch(reading, planning._made_for(reading, planning._said(reading), [card.name]))
	said = _("Waited for {0} {1} to be approved.").format(_(card.target_doctype), card.target_name)
	made = []
	for agent in working():
		for name, doctype in waits(agent.app).items():
			if doctype != card.target_doctype or name not in plans(agent.app):
				continue
			stage, path = plans(agent.app)[name]
			facts, ctx = planning.prepared(reading, stage)
			for one in frappe.get_attr(path)(facts, ctx):
				one.why = act._join(one.why, said)
				made.append(take(agent.app, name, keyed(reading, one), reading))
	return [one for one in made if one]
