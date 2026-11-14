"""OneAI's block in AutomationCenter (one/automation/kinds.py): Hand to an
Agent gives the record a run is about to an app's agent with what to do
with it. The agent works on it as it answers a person (agents/talk.py),
asked by whoever made the automation, so it may do only what both it and
they may, through the agents' door at its levels: what it may not just do
waits as a card. Offered only where OneAI may read what the trigger starts on."""

import frappe
from frappe import _, _lt

from onedesk.one.automation.kinds import Action, Param

ONCE_IN = 30 * 24 * 3600


def hand(automation, name, step, context):
	"""The record handed to the agent once per automation and record, after
	the run is committed."""
	key = f"one_automation_agent:{automation.name}:{name}"
	if frappe.cache.get_value(key):
		return
	frappe.cache.set_value(key, 1, expires_in_sec=ONCE_IN)
	frappe.enqueue(
		f"{__name__}.handed",
		queue="long",
		enqueue_after_commit=True,
		app=step["agent"],
		doctype=context.get("doctype"),
		name=name,
		instruction=step.get("instruction") or "",
		owner=automation.owner,
	)


def handed(app: str, doctype: str, name: str, instruction: str, owner: str) -> dict | None:
	"""The agent at work on the record, as the automation's owner asked it:
	nothing while agents are off or over their month, or once the owner may
	no longer talk to it."""
	from onedesk.one_ai import here
	from onedesk.one_ai.agents import talk, workspace
	from onedesk.one_chat import agents as members

	if workspace.refusal(app) or not doctype or not frappe.db.exists(doctype, name):
		return None
	was = frappe.session.user
	frappe.set_user(owner)
	try:
		if not members.reaches(app):
			return None
		question = f"{instruction}\n\nThe record: {doctype} {name}."
		return talk.ask(app, "chat", question, here.asked(question, None, who=talk.who(app)), reference=name)
	finally:
		frappe.set_user(was)


def agents_offered() -> dict:
	"""The agents an automation may hand a record to: those at work that the
	reader may talk to."""
	from onedesk.one_ai.agents import users, work
	from onedesk.one_chat import agents as members

	return {"agents": [{"value": one.app, "label": users.full_name(one)} for one in work.working() if members.reaches(one.app)]}


def _checked(step) -> list[str]:
	said = []
	if not step.get("agent"):
		said.append(_("Choose the agent."))
	if not (step.get("instruction") or "").strip():
		said.append(_("Write what the agent should do."))
	return said


def _words(step, offers) -> str:
	from onedesk.one.registry import agents
	from onedesk.one_ai.agents import users

	one = agents.get(step.get("agent") or "")
	return _("Hand to {0}").format(users.full_name(one) if one else step.get("agent") or "")


BLOCKS = (
	Action(
		"agent",
		_lt("Hand to an Agent"),
		"bot",
		hand,
		group=_lt("Agents"),
		params=(
			Param("agent", _lt("Agent"), "choice", "agents"),
			Param("instruction", _lt("Instruction"), "long", description=_lt("What the agent should do with it, whole: it sees only this and the record.")),
		),
		check=_checked,
		words=_words,
		ai=True,
		offers=agents_offered,
	),
)
