"""The one door every agent's write goes through (docs/ARC-AI.md, Trust and
permissions). It is Intake's door (reading/act.py) with an agent in front:
the action is allowed only if both the agent and the person who asked may do
it, its level (levels.py) decides whether it is done, drafted or put to a
person, and every write is a Reading Action row under the agent's name, so
act.undo_one takes it back as it takes back what Intake did."""

import json

import frappe
from frappe import _
from frappe.utils import flt

from onedesk.one.registry import agents
from onedesk.one_ai.agents import levels
from onedesk.one_ai.reading import act, mark

DRAFTS = ("Create",)


def act_for(app: str, name: str, action: act.Action, asked_by: str | None = None, reading=None) -> str | None:
	"""Do, draft or propose one action of an app's agent; `name` is the
	action as LEVELS names it. Answers the Reading Action row, or None when
	the same action was already taken and nothing changes."""
	agent = agents.get(app)
	if not agent or action.kind not in act.KINDS:
		raise ValueError(f"{app} has no agent that can {action.kind}")
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
		}
	)
	refused = [one for one in (agent.email, asked_by) if one and not act.allowed(action, one)]
	if refused or not asker:
		row.level = "Refused"
		row.why = act._join(row.why, _("{0} doesn't have permission for this.").format(refused[0]) if refused else _("Nobody may approve this."))
		return act._insert(row)
	if level == levels.ASK_FIRST or (level == levels.DRAFT and action.kind not in DRAFTS):
		row.level = "Proposed"
		row.why = act._join(row.why, _("Waits for {0}.").format(asker))
		return act._insert(row)
	before = act._before(action)
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


def drafted(action: act.Action) -> act.Action:
	"""The same new record, never submitted: Draft leaves submitting to a person. Pure."""
	values = {key: value for key, value in (action.values or {}).items() if key != "docstatus"}
	return act.Action(**{**action.__dict__, "values": values})


def approver(app: str) -> str | None:
	"""Who an agent working on its own asks first: the first person turned on
	who manages its app (AICenter names one with P8.2)."""
	from onedesk.one import registry

	managed = registry.get(app).roles.manager
	if not managed:
		return None
	held = frappe.get_all("Has Role", filters={"role": ["in", managed], "parenttype": "User"}, pluck="parent", distinct=True)
	return next((one for one in sorted(held) if frappe.db.get_value("User", one, ["enabled", "user_type"]) == (1, "System User") and not agents.by_email(one)), None)
