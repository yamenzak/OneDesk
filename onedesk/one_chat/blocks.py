"""OneChat's blocks in AutomationCenter (one/automation/kinds.py): a message
posted in a channel starts an automation, what is known of the message is
what its Ifs ask, and each action is OneChat's own function
(automations.py). What people automate in a team chat, as Slack's Workflow
Builder and Discord's AutoMod offer it: a reply to words they watch for, a
message passed to another channel, somebody told, a task or an issue made,
and an agent answering."""

from frappe import _, _lt

from onedesk.one.automation.kinds import Action, Condition, Param, Trigger
from onedesk.one_ai.blocks import agents_offered
from onedesk.one_chat import automations, starters
from onedesk.one_chat.automations import CREATES, POSTED


def reply(automation, name, step, context):
	"""The automation's words posted in the conversation (automations.reply)."""
	automations.reply(automation, name, step)


def share(automation, name, step, context):
	"""The message posted in another channel (automations.share)."""
	automations.share(automation, name, step)


def notify(automation, name, step, context):
	"""Somebody in the channel told (automations.notify)."""
	automations.notify(automation, name, step)


def create(automation, name, step, context):
	"""A task or an issue made from the message (automations.create)."""
	automations.create(automation, name, step)


def answer(automation, name, step, context):
	"""An agent's answer in the message's thread (automations.answer)."""
	automations.answer(automation, name, step)


def _replies(step):
	return [] if (step.get("text") or "").strip() else [_("Write the reply.")]


def _shares(step):
	return [] if step.get("channel") else [_("Choose the channel.")]


def _someone(step):
	return [] if step.get("user") else [_("Choose who.")]


def _creates(step):
	return [] if step.get("doctype") in CREATES else [_("Choose what to create.")]


def _answers(step):
	said = []
	if not step.get("agent"):
		said.append(_("Choose the agent."))
	if not (step.get("instruction") or "").strip():
		said.append(_("Write what the agent should do."))
	return said


def _name_of(offers, value):
	return (offers.get("names") or {}).get(value, value)


def _agent_words(step, offers):
	from onedesk.one_chat import agents

	return _("{0} Answers").format(agents.name_of(step.get("agent") or ""))


BLOCKS = (
	Trigger(
		POSTED,
		_lt("When a message is posted"),
		"message-square",
		scope="Chat Channel",
		doctype="Chat Message",
		module="one_chat",
		everything=_lt("Every message"),
		keeps={
			"scopes": "automations.scopes",
			"offers": "automations.offers",
			"listed": "automations.listed",
			"save": "automations.save",
			"enable": "automations.enable",
			"delete": "automations.delete",
			"decide": "automations.decide",
			"allowed": "automations.allowed",
			"query": "automations.query",
			"validate": "automations.validate",
		},
		starters=starters.of,
		runs=_lt("Run in order on each message somebody posts in the channel."),
	),
	Condition("text", _lt("Text"), "text", POSTED),
	Condition("from", _lt("From"), "text", POSTED),
	Condition("thread", _lt("In a Thread"), "flag", POSTED, no=_lt("Not in a Thread")),
	Condition("file", _lt("Has File"), "flag", POSTED, no=_lt("No File")),
	Condition("after_hours", _lt("After Hours"), "flag", POSTED, no=_lt("In Working Hours")),
	Condition("holiday", _lt("On a Holiday"), "flag", POSTED, no=_lt("Not on a Holiday")),
	Action(
		"chat_reply",
		_lt("Reply"),
		"reply",
		reply,
		group=_lt("Replies"),
		triggers=(POSTED,),
		params=(
			Param("text", _lt("Message"), "long", description=_lt("{sender_name} fills in from the message.")),
			Param("thread", _lt("Reply in Thread"), "switch", needed=False),
		),
		check=_replies,
	),
	Action(
		"chat_answer",
		_lt("Let an Agent Answer"),
		"bot",
		answer,
		group=_lt("Replies"),
		triggers=(POSTED,),
		params=(
			Param("agent", _lt("Agent"), "choice", "agents"),
			Param(
				"instruction",
				_lt("Instruction"),
				"long",
				description=_lt("What the agent knows and how it answers. It reads only this and the conversation."),
			),
		),
		check=_answers,
		words=_agent_words,
		ai=True,
		offers=agents_offered,
	),
	Action(
		"chat_share",
		_lt("Post in a Channel"),
		"forward",
		share,
		group=_lt("Forwarding"),
		triggers=(POSTED,),
		params=(Param("channel", _lt("Channel"), "choice", "channels"),),
		check=_shares,
		words=lambda step, offers: _("Post in {0}").format(_name_of(offers, step.get("channel"))),
	),
	Action(
		"chat_notify",
		_lt("Tell Someone"),
		"bell",
		notify,
		group=_lt("People and Records"),
		triggers=(POSTED,),
		params=(Param("user", _lt("Person"), "choice", "people"),),
		check=_someone,
		words=lambda step, offers: _("Tell {0}").format(_name_of(offers, step.get("user"))),
	),
	Action(
		"chat_create",
		_lt("Create a Record"),
		"file-plus",
		create,
		group=_lt("People and Records"),
		triggers=(POSTED,),
		params=(Param("doctype", _lt("Record"), "choice", "creates", default="Task"),),
		check=_creates,
		words=lambda step, offers: _("Create {0}").format(_(step.get("doctype") or "")),
	),
)
