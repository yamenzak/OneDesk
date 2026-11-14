"""The automations a new one in a channel may start from: what a team most
often has its chat do, ready to change (AutomationCenter's New Automation).
The one with an agent is offered only while OneAI is on."""

import frappe
from frappe import _


def _id() -> str:
	return frappe.generate_hash(length=6)


def _when(items: list, then: list, any_: bool = False) -> dict:
	return {"type": "if", "id": _id(), "test": {"any": any_, "items": items}, "then": then, "else": []}


def _starter(group: str, key: str, icon: str, title: str, about: str, steps: list, named: str | None = None) -> dict:
	return {"group": group, "key": key, "icon": icon, "title": title, "about": about, "rule": {"title": named if named is not None else title, "steps": steps}}


def of(offers: dict) -> list[dict]:
	"""Each starter: its group, key, icon, title, a line on what it does, and
	the automation it starts, named and with its steps."""
	people = offers.get("people") or []
	person = next((one["value"] for one in people if one["value"] == frappe.session.user), people[0]["value"] if people else None)
	replies, records = _("Replies"), _("People and Records")
	closed = {"any": True, "items": [{"field": "after_hours", "value": True}, {"field": "holiday", "value": True}]}
	said = [
		_starter("", "blank", "file", _("Blank"), _("Start from nothing."), [_when([{"field": "text", "op": "contains", "value": ""}], [])], ""),
		_starter(
			replies,
			"closed",
			"moon",
			_("We're Closed"),
			_("Answer messages posted after hours or on a holiday."),
			[_when([closed], [{"type": "chat_reply", "text": _("Thank you for your message. Our office is closed now, and we will reply when we open."), "thread": 1}])],
		),
		_starter(
			records,
			"urgent",
			"siren",
			_("Urgent Messages"),
			_("Tell someone when a message says urgent."),
			[_when([{"field": "text", "op": "contains", "value": _("urgent")}], [{"type": "chat_notify", "user": person}])],
		),
		_starter(
			records,
			"task",
			"list-checks",
			_("Task From a Message"),
			_("Create a task from each message that starts with todo."),
			[_when([{"field": "text", "op": "starts_with", "value": _("todo")}], [{"type": "chat_create", "doctype": "Task"}])],
		),
		_starter(
			records,
			"issue",
			"life-buoy",
			_("Issue From a Message"),
			_("Create an issue from each new message, and say so in its thread."),
			[_when([{"field": "thread", "value": False}], [{"type": "chat_create", "doctype": "Issue"}])],
		),
	]
	opens = {"field": "opens", "value": True}
	said += [
		_starter(
			_("Website Chats"),
			"lead",
			"user-plus",
			_("Lead From a Website Chat"),
			_("Make a lead of each visitor who starts a chat, and say so in its thread."),
			[_when([opens], [{"type": "chat_create", "doctype": "Lead"}])],
		),
		_starter(
			_("Website Chats"),
			"closed_chat",
			"moon",
			_("Closed for Website Chats"),
			_("Answer a visitor who starts a chat after hours or on a holiday."),
			[_when([opens, closed], [{"type": "chat_reply", "text": _("Thank you for your message. Our office is closed now, and we will reply here when we open.")}])],
		),
	]
	if offers.get("ai"):
		said.append(
			_starter(
				replies,
				"agent",
				"bot",
				_("An Agent Answers"),
				_("An agent answers each new message in its thread, from what you tell it."),
				[_when([{"field": "thread", "value": False}], [{"type": "chat_answer", "agent": (offers.get("agents") or [{}])[0].get("value"), "instruction": ""}])],
			)
		)
	return said
