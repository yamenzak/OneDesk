"""OneMail's blocks in AutomationCenter (one/automation/kinds.py): mail
arriving in a mailbox starts an automation, what is known of a message is
what its Ifs ask, and what a mail rule always did is what its actions do,
each through OneMail's own function (rules.py, actions.py, tell.py), acting
for the mailbox while `frappe.flags.one_mail_rules` is set, which
`actions.require` lets through and nothing else sets."""

import re

import frappe
from frappe import _, _lt

from onedesk.one import registry
from onedesk.one.automation.kinds import Action, Condition, Param, Trigger
from onedesk.one_mail import starters

ARRIVES = "one_mail.arrives"
ONCE = ("conversation", "day", "week", "month")
CREATES = ("Lead", "Issue", "Task")
KINDS = ("Customer", "Supplier", "Lead", "Contact", "Employee")


def _for_the_mailbox(fn):
	def done(automation, name, step, context):
		frappe.flags.one_mail_rules = True
		try:
			return fn(automation, name, step, context)
		finally:
			frappe.flags.one_mail_rules = False

	done.__doc__ = fn.__doc__
	return done


@_for_the_mailbox
def move(automation, name, step, context):
	"""The message moved to a folder of its mailbox."""
	from onedesk.one_mail import actions

	actions.move([name], step["folder"])


@_for_the_mailbox
def read(automation, name, step, context):
	"""The message marked as read."""
	from onedesk.one_mail import actions

	actions.mark([name], 1)


@_for_the_mailbox
def star(automation, name, step, context):
	"""The message starred."""
	from onedesk.one_mail import actions

	actions.star([name], 1)


@_for_the_mailbox
def junk(automation, name, step, context):
	"""The message moved to its mailbox's Junk."""
	from onedesk.one_mail import actions

	found = actions.folder_of(frappe.db.get_value("Communication", name, "email_account"), "Junk")
	if found:
		actions.move([name], found)


@_for_the_mailbox
def reply(automation, name, step, context):
	"""The sender answered (rules.answer)."""
	from onedesk.one_mail import rules

	rules.answer(automation, step, name, context.get("headers"))


@_for_the_mailbox
def forward(automation, name, step, context):
	"""The message sent on (rules.forward)."""
	from onedesk.one_mail import rules

	rules.forward(automation, step, name)


@_for_the_mailbox
def assign(automation, name, step, context):
	"""The message given to one of its mailbox's people (rules.assign)."""
	from onedesk.one_mail import rules

	rules.assign(automation, step, name)


@_for_the_mailbox
def notify(automation, name, step, context):
	"""Somebody told on the bell (tell.rule_notice)."""
	from onedesk.one_mail import tell

	tell.rule_notice(automation, step["user"], name)


@_for_the_mailbox
def link(automation, name, step, context):
	"""The message filed on its sender's record (rules.link)."""
	from onedesk.one_mail import rules

	rules.link(name)


@_for_the_mailbox
def create(automation, name, step, context):
	"""A lead, an issue or a task made from the message (rules.create)."""
	from onedesk.one_mail import rules

	rules.create(automation, step, name)


def _moves(step):
	return [] if step.get("folder") else [_("Choose the folder to move to.")]


def _replies(step):
	said = []
	if step.get("with") == "OneAI" and not (step.get("instruction") or "").strip():
		said.append(_("Write what {0}'s reply should say.").format(registry.name("one_ai")))
	if step.get("with") != "OneAI" and not (step.get("text") or "").strip():
		said.append(_("Write the reply."))
	if step.get("once") and step["once"] not in ONCE:
		said.append(_("That cannot be set."))
	return said


def _forwards(step):
	return [] if re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+$", (step.get("to") or "").strip()) else [_("Write the address to forward to.")]


def _someone(step):
	return [] if step.get("user") else [_("Choose who.")]


def _creates(step):
	return [] if step.get("doctype") in CREATES else [_("Choose what to create.")]


def _name_of(offers, value):
	return (offers.get("names") or {}).get(value, value)


def _sender_words(one: dict) -> str:
	return (_("Sender isn't a {0}") if one.get("op") == "is_not" else _("Sender is a {0}")).format(_(one.get("value") or ""))


def _with(value: str):
	return (("with", (value,)),)


BLOCKS = (
	Trigger(
		ARRIVES,
		_lt("When a message arrives"),
		"inbox",
		scope="Email Account",
		doctype="Communication",
		module="one_mail",
		everything=_lt("All mail"),
		reads=True,
		keeps={
			"scopes": "rules.mailboxes_ruled",
			"offers": "rules.offers",
			"listed": "rules.rules_of_mailbox",
			"save": "rules.save_rule",
			"enable": "rules.enable_rule",
			"delete": "rules.delete_rule",
			"decide": "rules.decide_rule",
			"allowed": "rules.rule_allowed",
			"query": "rules.rule_query",
			"validate": "rules.validate_rule",
		},
		starters=starters.of,
	),
	Condition("from", _lt("From"), "text", ARRIVES),
	Condition("to", _lt("To"), "text", ARRIVES),
	Condition("subject", _lt("Subject"), "text", ARRIVES),
	Condition("text", _lt("Text"), "text", ARRIVES),
	Condition("domain", _lt("Sender's Domain"), "text", ARRIVES),
	Condition("sender_is", _lt("Sender"), "kind", ARRIVES, options=KINDS, words=_sender_words),
	Condition("outside", _lt("From Outside the Workspace"), "flag", ARRIVES, no=_lt("From the Workspace")),
	Condition("starts", _lt("Starts a Conversation"), "flag", ARRIVES, no=_lt("Answers a Conversation")),
	Condition("attachment", _lt("Has Attachment"), "flag", ARRIVES, no=_lt("No Attachment")),
	Condition("after_hours", _lt("After Hours"), "flag", ARRIVES, no=_lt("In Working Hours")),
	Condition("holiday", _lt("On a Holiday"), "flag", ARRIVES, no=_lt("Not on a Holiday")),
	Action(
		"move",
		_lt("Move to Folder"),
		"folder-input",
		move,
		group=_lt("Sorting"),
		triggers=(ARRIVES,),
		params=(Param("folder", _lt("Folder"), "choice", "folders"),),
		check=_moves,
		words=lambda step, offers: _("Move to {0}").format(_name_of(offers, step.get("folder"))),
	),
	Action("read", _lt("Mark as Read"), "mail-open", read, group=_lt("Sorting"), triggers=(ARRIVES,)),
	Action("star", _lt("Star"), "star", star, group=_lt("Sorting"), triggers=(ARRIVES,)),
	Action("junk", _lt("Move to Junk"), "shield-alert", junk, group=_lt("Sorting"), triggers=(ARRIVES,)),
	Action(
		"reply",
		_lt("Reply"),
		"reply",
		reply,
		group=_lt("Replies"),
		triggers=(ARRIVES,),
		params=(
			Param("with", _lt("Written By"), "choice", "writers", default="Text"),
			Param("text", _lt("Message"), "long", shown=_with("Text"), description=_lt("{sender_name} and {subject} fill in from the message.")),
			Param("instruction", _lt("Instruction"), "long", shown=_with("OneAI"), description=_lt("What {one_ai}'s reply should do, such as answering from their orders and promising an answer within a day.")),
			Param("records", _lt("Sender's Records"), "switch", shown=_with("OneAI"), needed=False, description=_lt("{one_ai} may read the orders, invoices and deliveries the sender sees on the portal, once their address is verified.")),
			Param("once", _lt("How Often"), "choice", "once", default="conversation"),
		),
		check=_replies,
		words=lambda step, offers: _("Reply With {0}").format(registry.name("one_ai")) if step.get("with") == "OneAI" else _("Reply"),
	),
	Action(
		"forward",
		_lt("Forward"),
		"forward",
		forward,
		group=_lt("Forwarding"),
		triggers=(ARRIVES,),
		params=(Param("to", _lt("To"), "email", placeholder="name@example.com"),),
		check=_forwards,
		words=lambda step, offers: _("Forward to {0}").format(step.get("to")),
	),
	Action(
		"assign",
		_lt("Assign"),
		"user-check",
		assign,
		group=_lt("People and Records"),
		triggers=(ARRIVES,),
		params=(Param("user", _lt("Person"), "choice", "people"),),
		check=_someone,
		words=lambda step, offers: _("Assign to {0}").format(_name_of(offers, step.get("user"))),
	),
	Action(
		"notify",
		_lt("Tell Someone"),
		"bell",
		notify,
		group=_lt("People and Records"),
		triggers=(ARRIVES,),
		params=(Param("user", _lt("Person"), "choice", "people"),),
		check=_someone,
		words=lambda step, offers: _("Tell {0}").format(_name_of(offers, step.get("user"))),
	),
	Action("link", _lt("Link to Their Record"), "link", link, group=_lt("People and Records"), triggers=(ARRIVES,)),
	Action(
		"create",
		_lt("Create a Record"),
		"file-plus",
		create,
		group=_lt("People and Records"),
		triggers=(ARRIVES,),
		params=(Param("doctype", _lt("Record"), "choice", tuple((one, one) for one in CREATES), default="Lead"),),
		check=_creates,
		words=lambda step, offers: _("Create {0}").format(_(step.get("doctype") or "")),
	),
)


def from_fields(row: dict) -> list:
	"""A rule of the old shape (one set of conditions, one set of actions,
	About for OneAI) as steps."""
	items = [
		{"field": field, "op": "contains", "value": row.get(key)}
		for field, key in (
			("from", "from_contains"),
			("to", "to_contains"),
			("subject", "subject_contains"),
			("text", "body_contains"),
		)
		if row.get(key)
	]
	if row.get("has_attachment"):
		items.append({"field": "attachment", "value": True})
	then = []
	if row.get("move_to"):
		then.append({"type": "move", "folder": row["move_to"]})
	if row.get("mark_read"):
		then.append({"type": "read"})
	if row.get("star"):
		then.append({"type": "star"})
	if row.get("reply"):
		then.append(
			{
				"type": "reply",
				"with": row.get("reply_with") or "Text",
				"text": row.get("reply_text") or "",
				"instruction": row.get("reply_instruction") or "",
				"once": "conversation",
			}
		)
	if row.get("stop"):
		then.append({"type": "stop"})
	test_ = {"any": (row.get("match") or "").startswith("Any"), "items": items}
	if row.get("about"):
		return [{"type": "ask", "id": "a1", "ask": "yes", "question": row["about"], "then": [{"type": "if", "id": "i1", "test": test_, "then": then, "else": []}] if items else then, "else": []}]
	return [{"type": "if", "id": "i1", "test": test_, "then": then, "else": []}]
