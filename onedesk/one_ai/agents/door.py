"""The one door every agent's write goes through (docs/ARC-AI.md, Trust and
permissions). It is Intake's door (reading/act.py) with an agent in front:
what the person who asked may not do is refused; what the agent's own roles
may not do is put to that person as a card, so only they make it; its level
(levels.py) decides whether it is done, drafted or put to a person, and
Intake's floor (`floor`) still holds what Intake would have held. Every
write is a Reading Action row under the agent's name, so act.undo_one takes
it back as it takes back what Intake did."""

import json

import frappe
from frappe import _
from frappe.utils import flt

from onedesk.one.registry import agents
from onedesk.one_ai.agents import levels, workspace
from onedesk.one_ai.reading import act, mark

DRAFTS = ("Create",)


def act_for(app: str, name: str, action: act.Action, asked_by: str | None = None, reading=None) -> str | None:
	"""Do, draft or propose one action of an app's agent; `name` is the
	action as LEVELS names it. Answers the Reading Action row, or None when
	the same action was already taken or would change nothing. Refused, with
	the reason, while agents are off or this one is over its month's
	credits (workspace.py), and nothing is written, so it can come again."""
	agent = agents.get(app)
	if not agent or action.kind not in act.KINDS:
		raise ValueError(f"{app} has no agent that can {action.kind}")
	workspace.refuse(app)
	level = levels.of(app, name)
	key = act.key_of(reading.key if reading else f"agent|{app}|{name}", action)
	held = frappe.db.get_value("Reading Action", {"key": key}, "name")
	if held:
		return held
	asker = asked_by or (reading.on_behalf_of if reading else None) or approver(app)
	row = frappe.new_doc("Reading Action")
	row.update(
		{
			"kind": action.kind,
			"target_doctype": action.doctype,
			"target_name": action.name,
			"reading": reading.name if reading else None,
			"key": key,
			"on_behalf_of": asker,
			"agent": agent.email,
			"agent_level": level,
			"agent_action": name,
			"confidence": min(100, flt(action.confidence, 1) * 100),
			"why": action.why[:1000] if action.why else None,
			"after": json.dumps(action.values, default=str),
			"flow": action.flow,
			"as_person": int(bool(action.as_person)),
		}
	)
	refused = [one for one in (asked_by or asker,) if one and not act.allowed(action, one)]
	if refused or not asker:
		row.level = "Refused"
		row.why = act._join(row.why, _("{0} doesn't have permission for this.").format(refused[0]) if refused else _("Nobody may approve this."))
		return act._insert(row)
	if level == levels.ASK_FIRST or (level == levels.DRAFT and action.kind not in DRAFTS) or not act.allowed(action, agent.email):
		row.level = "Proposed"
		row.why = act._join(row.why, _("Waits for {0}.").format(asker))
		return act._insert(row)
	before = act._before(action)
	if action.kind == "Update" and before and all(act._same(before.get(key), value) for key, value in (action.values or {}).items()):
		return None
	waits = floor(action, before, reading)
	if waits:
		row.level = "Proposed"
		row.before = json.dumps(before, default=str) if before else None
		row.why = act._join(row.why, waits)
		return act._insert(row)
	planned = drafted(action) if level == levels.DRAFT else action
	frappe.db.savepoint("one_agent_act")
	try:
		with act.as_oneai(agent.email, asker):
			done = act._write(planned, before, reading.name if reading else None)
	except Exception as raised:
		frappe.db.rollback(save_point="one_agent_act")
		frappe.clear_messages()
		row.level = "Proposed" if action.propose_on_error else "Refused"
		row.why = act._join(row.why, frappe.utils.strip_html_tags(str(raised))[:500] or type(raised).__name__)
		return act._insert(row)
	row.level = "Done"
	row.target_name = done.get("name") or action.name
	row.before = json.dumps(before, default=str) if before else None
	row.after = json.dumps(done, default=str)
	if action.kind == "Create":
		mark.mark(action.doctype, row.target_name, reading.name if reading else None)
	return act._insert(row)


def for_a_person(row) -> bool:
	"""Whether an agent's card waits for a person by its level or by what
	the agent's roles may not do, rather than by Intake's floor: the auditor
	(reading/audit.py) never applies such a card, since an agent goes
	further only by a person's choice."""
	agent = agents.by_email(row.agent)
	if not agent:
		return True
	level = levels.of(agent.app, row.agent_action)
	return level == levels.ASK_FIRST or (level == levels.DRAFT and row.kind not in DRAFTS) or not act.allowed(act.planned_of(row), agent.email)


def floor(action: act.Action, before: dict, reading=None) -> str | None:
	"""Why an action the agent may take still waits for a person, as
	Intake's door decides it: it ends somebody's employment, its planner
	leaves it to a person, it overwrites what a person wrote, it is below the
	workspace's confidence floor, or people took it back often enough."""
	owned = action.kind == "Update" and bool(action.name) and mark.is_marked(action.doctype, action.name)
	level, why, fields = act.level(action, reading.as_dict() if reading else {}, before, act._floor(), owned)
	if level != "Done":
		return act.waits(why, fields, action.doctype)
	if reading is None or (action.kind == "Create" and action.doctype == "File"):
		return None
	from onedesk.one_ai.reading import lessons

	return lessons.rule_says(reading, action)


def drafted(action: act.Action) -> act.Action:
	"""The same new record, never submitted: Draft leaves submitting to a person. Pure."""
	values = {key: value for key, value in (action.values or {}).items() if key != "docstatus"}
	return act.Action(**{**action.__dict__, "values": values})


def approver(app: str) -> str | None:
	"""Who an agent working on its own asks first: the first person turned on
	who manages its app, as AICenter shows."""
	from onedesk.one import registry

	managed = registry.get(app).roles.manager
	if not managed:
		return None
	held = frappe.get_all("Has Role", filters={"role": ["in", managed], "parenttype": "User"}, pluck="parent", distinct=True)
	return next((one for one in sorted(held) if frappe.db.get_value("User", one, ["enabled", "user_type"]) == (1, "System User") and not agents.by_email(one)), None)
