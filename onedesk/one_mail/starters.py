"""The automations a new one on a mailbox may start from: what a mailbox most
often wants, ready to change, in groups (AutomationCenter's New Automation).
Those that ask OneAI are offered only where it may read the mailbox."""

import frappe
from frappe import _

from onedesk.one import registry


def _id() -> str:
	return frappe.generate_hash(length=6)


def _when(items: list, then: list, any_: bool = False, otherwise: list | None = None) -> dict:
	return {"type": "if", "id": _id(), "test": {"any": any_, "items": items}, "then": then, "else": otherwise or []}


def _reply(text: str, once: str = "conversation") -> dict:
	return {"type": "reply", "with": "Text", "text": text, "once": once}


def _starter(group: str, key: str, icon: str, title: str, about: str, steps: list, named: str | None = None) -> dict:
	return {"group": group, "key": key, "icon": icon, "title": title, "about": about, "rule": {"title": named if named is not None else title, "steps": steps}}


def of(offers: dict) -> list[dict]:
	"""Each starter: its group, key, icon, title, a line on what it does, and
	the automation it starts, named and with its steps."""
	folders = offers.get("folders") or []

	def folder(*names: str) -> str | None:
		found = next((one for one in folders if any(name in (one["label"] or "").lower() for name in names)), None)
		return (found or (folders[0] if folders else {})).get("value")

	people = offers.get("people") or []
	person = next((one["value"] for one in people if one["value"] == frappe.session.user), people[0]["value"] if people else None)
	thanks = _("Thank you for your message. We received it and will reply soon.")
	replies, sorting, records, forwarding = _("Replies"), _("Sorting"), _("People and Records"), _("Forwarding")
	outside = {"field": "outside", "value": True}
	starts = {"field": "starts", "value": True}
	customer = {"field": "sender_is", "op": "is", "value": "Customer"}
	supplier = {"field": "sender_is", "op": "is", "value": "Supplier"}
	attached = {"field": "attachment", "value": True}
	closed = {"any": True, "items": [{"field": "after_hours", "value": True}, {"field": "holiday", "value": True}]}
	said = [
		_starter("", "blank", "file", _("Blank"), _("Start from nothing."), [_when([{"field": "from", "op": "contains", "value": ""}], [])], ""),
		_starter(replies, "auto_reply", "reply", _("Auto Reply"), _("Answer every message with the same words, once in each conversation."), [_reply(thanks)]),
		_starter(replies, "acknowledge", "mail-check", _("Acknowledge New Mail"), _("Answer new conversations from outside, once a day to each sender."), [_when([starts, outside], [_reply(thanks, "day")])]),
		_starter(
			replies,
			"closed",
			"moon",
			_("We're Closed"),
			_("Answer mail that arrives after hours or on a holiday."),
			[_when([outside, closed], [_reply(_("Thank you for your message. Our office is closed now, and we will reply when we open."), "day")])],
		),
		_starter(
			replies,
			"attachment_received",
			"paperclip",
			_("Confirm Documents Received"),
			_("Tell suppliers their attached documents arrived."),
			[_when([supplier, attached], [_reply(_("Thank you. We received your documents and will review them."))])],
		),
		_starter(
			sorting,
			"newsletters",
			"newspaper",
			_("Newsletters to a Folder"),
			_("Move newsletters and notices out of the Inbox, already read."),
			[
				_when(
					[{"field": "from", "op": "contains", "value": "newsletter, noreply, no-reply"}, {"field": "text", "op": "contains", "value": _("unsubscribe")}],
					[{"type": "move", "folder": folder("newsletter", "archive")}, {"type": "read"}],
					any_=True,
				)
			],
			_("Newsletters"),
		),
		_starter(
			sorting,
			"invoices",
			"receipt",
			_("Invoices to a Folder"),
			_("Star mail with an invoice attached and move it to a folder."),
			[_when([{"field": "subject", "op": "contains", "value": _("invoice, receipt, statement")}, attached], [{"type": "move", "folder": folder("invoice", "account")}, {"type": "star"}])],
			_("Invoices"),
		),
		_starter(
			sorting,
			"customers",
			"users",
			_("Customers to a Folder"),
			_("Move mail from customers into a folder and file it on their record."),
			[_when([customer], [{"type": "move", "folder": folder("customer")}, {"type": "link"}])],
			_("Customers"),
		),
		_starter(
			sorting,
			"important",
			"star",
			_("Important Sender"),
			_("Star mail from one address or domain and tell someone on the bell."),
			[_when([{"field": "domain", "op": "is", "value": ""}], [{"type": "star"}, {"type": "notify", "user": person}])],
		),
		_starter(
			sorting,
			"block",
			"shield-alert",
			_("Block a Sender"),
			_("Send mail from an address or domain to Junk, and run no other rule on it."),
			[_when([{"field": "domain", "op": "is", "value": ""}], [{"type": "junk"}, {"type": "stop"}])],
		),
		_starter(
			records,
			"support",
			"life-buoy",
			_("Support Requests"),
			_("Make an issue from mail asking for help, and assign it to someone."),
			[_when([{"field": "text", "op": "contains", "value": _("help, problem, not working, broken")}, outside], [{"type": "create", "doctype": "Issue"}, {"type": "assign", "user": person}])],
		),
		_starter(
			records,
			"leads",
			"user-plus",
			_("New Leads"),
			_("Make a lead from a first message by someone the workspace doesn't know yet."),
			[
				_when(
					[starts, outside, *({"field": "sender_is", "op": "is_not", "value": kind} for kind in ("Customer", "Supplier", "Lead"))],
					[{"type": "create", "doctype": "Lead"}, {"type": "notify", "user": person}],
				)
			],
		),
		_starter(
			records,
			"tasks",
			"list-checks",
			_("Tasks From Mail"),
			_("Make a task from mail whose subject starts with Task."),
			[_when([{"field": "subject", "op": "starts_with", "value": _("Task")}], [{"type": "create", "doctype": "Task"}, {"type": "read"}])],
		),
		_starter(
			records,
			"after_hours_team",
			"bell",
			_("Urgent After Hours"),
			_("Tell someone when customer mail marked urgent arrives after hours."),
			[_when([customer, {"field": "after_hours", "value": True}, {"field": "subject", "op": "contains", "value": _("urgent, asap")}], [{"type": "star"}, {"type": "notify", "user": person}])],
		),
		_starter(
			records,
			"assign_new",
			"user-check",
			_("Assign New Conversations"),
			_("Assign each new conversation from outside to one person."),
			[_when([starts, outside], [{"type": "assign", "user": person}])],
		),
		_starter(
			records,
			"route",
			"split",
			_("Route by Subject"),
			_("Assign quote requests to one person and invoices to another."),
			[
				_when(
					[{"field": "subject", "op": "contains", "value": _("quote, quotation, price")}],
					[{"type": "assign", "user": person}],
					otherwise=[_when([{"field": "subject", "op": "contains", "value": _("invoice, payment, statement")}], [{"type": "assign", "user": person}])],
				)
			],
		),
		_starter(
			forwarding,
			"forward_bills",
			"forward",
			_("Forward Supplier Bills"),
			_("Send a copy of supplier mail with an attachment to another address."),
			[_when([supplier, attached], [{"type": "forward", "to": ""}, {"type": "link"}])],
		),
		_starter(forwarding, "auto_forward", "forward", _("Auto Forward"), _("Forward every new message to another address."), [{"type": "forward", "to": ""}]),
		_starter(
			forwarding,
			"forward_after_hours",
			"moon",
			_("Forward After Hours"),
			_("Forward customer mail that arrives after hours or on a holiday to an on-call address."),
			[_when([customer, closed], [{"type": "forward", "to": ""}])],
		),
		_starter(
			forwarding,
			"forward_cvs",
			"file-user",
			_("Forward Job Applications"),
			_("Forward mail with a CV attached to whoever handles hiring."),
			[_when([attached, {"field": "text", "op": "contains", "value": _("CV, resume, application, vacancy")}], [{"type": "forward", "to": ""}])],
		),
	]
	if offers.get("ai"):
		said += _with_oneai(person, folder)
	return said


def _with_oneai(person: str | None, folder) -> list[dict]:
	ai = registry.name("one_ai")
	group = _("With {0}").format(ai)
	return [
		_starter(
			group,
			"sort",
			"oneai",
			_("Sort by Topic"),
			_("{0} reads each message and picks a label, and each label has its own steps.").format(ai),
			[
				{
					"type": "ask",
					"id": _id(),
					"ask": "pick",
					"labels": [
						{"label": _("Quote Request"), "about": _("Someone asks for a price or a quotation."), "then": [{"type": "create", "doctype": "Lead"}, {"type": "notify", "user": person}]},
						{"label": _("Complaint"), "about": _("Someone is unhappy with what they got or how they were treated."), "then": [{"type": "star"}, {"type": "create", "doctype": "Issue"}]},
						{"label": _("Invoice"), "about": _("A bill, an invoice or a statement to pay."), "then": [{"type": "move", "folder": folder("invoice", "account")}]},
					],
					"then": [],
					"else": [],
				}
			],
		),
		_starter(
			group,
			"upset",
			"siren",
			_("Upset or Urgent"),
			_("{0} says whether the sender is upset or in a hurry, and someone is told.").format(ai),
			[{"type": "ask", "id": _id(), "ask": "yes", "question": _("Is the sender upset, or do they need an answer today?"), "then": [{"type": "star"}, {"type": "notify", "user": person}], "else": []}],
		),
		_starter(
			group,
			"draft",
			"pen-line",
			_("Answer From Their Records"),
			_("{0} answers customers' questions about orders, deliveries and prices from their own records.").format(ai),
			[
				_when(
					[{"field": "sender_is", "op": "is", "value": "Customer"}],
					[
						{
							"type": "ask",
							"id": _id(),
							"ask": "yes",
							"question": _("Is this a question about an order, a delivery or a price?"),
							"then": [
								{
									"type": "reply",
									"with": "OneAI",
									"instruction": _("Answer the question from their records where they answer it. If they don't, say we will follow up within a day."),
									"records": 1,
									"once": "conversation",
								}
							],
							"else": [],
						}
					],
				)
			],
		),
		_starter(
			group,
			"ai_reply",
			"bot",
			_("Auto Reply in Their Language"),
			_("{0} answers new conversations from outside, in the sender's language.").format(ai),
			[_when([{"field": "starts", "value": True}, {"field": "outside", "value": True}], [{"type": "reply", "with": "OneAI", "instruction": _("Thank them, say what you understood they need, and say we will reply soon."), "once": "conversation"}])],
		),
	]
