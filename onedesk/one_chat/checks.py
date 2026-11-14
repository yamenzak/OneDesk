"""OneChat's part of the integration suite (one_demo/check.py runs it): a
channel only its members read, a mention that tells the person mentioned, a
direct conversation kept one per pair, a reaction, an agent's card posted
from the door and answered through it, and what waits once the auditor has
had its say put to the person as cards. Nothing is sent to a model."""

import json

import frappe

from onedesk.one_demo.base import as_user
from onedesk.one_demo.checking import check
from onedesk.one_demo.people import OWNER

HUDA = "huda@one.test"
KARIM = "karim@one.test"


@check
def a_channel_is_read_by_its_members_alone():
	"""Huda makes a private channel with the owner and mentions him. The
	mention is kept and he reads it, with her reaction; Karim, outside it, finds nothing and opens nothing.
	Their direct conversation is one, whoever opens it. All undone."""
	from onedesk.one_chat import api, channels

	frappe.db.savepoint("chat_check")
	try:
		with as_user(HUDA):
			made = api.make("Month end check", private=1, people=json.dumps([OWNER]))["name"]
			owner = frappe.utils.get_fullname(OWNER)
			sent = api.send(made, f"@{owner} the bank lines are in.")
			assert sent["run"] is None, "nobody asked an agent"
			assert {OWNER} == {one["user"] for one in frappe.get_all("Chat Mention", filters={"parent": sent["message"]["name"]}, fields=["user"])}
			api.react(sent["message"]["name"], "👍")
			first = api.direct(KARIM)["name"]
		with as_user(OWNER):
			said = api.channel(made)
			assert said["messages"][-1]["reactions"] == {"👍": [HUDA]}
		with as_user(KARIM):
			assert made not in {one["name"] for one in api.conversations()}
			assert not frappe.get_list("Chat Message", filters={"channel": made})
			try:
				api.channel(made)
			except frappe.PermissionError:
				pass
			else:
				raise AssertionError("Karim read a channel he is not in")
			assert api.direct(HUDA)["name"] == first, "one direct conversation per pair"
		assert channels.reads(channels.members_of(made), HUDA)
	finally:
		frappe.db.rollback(save_point="chat_check")


@check
def an_agent_s_card_lands_in_its_conversation_and_goes_through_the_door():
	"""OneBook's accountant asks Huda first about a new supplier: the card
	is in her conversation with it, Karim cannot answer it, and Dismiss is
	the door's own. All undone."""
	from onedesk.one.registry import agents
	from onedesk.one_chat import api

	frappe.db.savepoint("chat_card_check")
	try:
		row = frappe.get_doc(
			{
				"doctype": "Reading Action",
				"kind": "Create",
				"level": "Proposed",
				"target_doctype": "Supplier",
				"key": "chat-check|supplier",
				"on_behalf_of": HUDA,
				"agent": agents.email("one_book"),
				"agent_level": "Ask First",
				"agent_action": "check",
				"after": json.dumps({"supplier_name": "Chat Check Trading"}),
			}
		).insert(ignore_permissions=True)
		channel = frappe.db.get_value("Chat Message", {"action": row.name}, "channel")
		assert channel and frappe.db.get_value("Chat Channel", channel, "agent") == "one_book", "the card is posted"
		with as_user(KARIM):
			try:
				api.approve(row.name)
			except frappe.PermissionError:
				pass
			else:
				raise AssertionError("Karim answered Huda's card")
		with as_user(HUDA):
			card = api.change(row.name, {"supplier_name": "Chat Check Trading LLC"})
			assert card["fields"][0]["value"] == "Chat Check Trading LLC"
			assert api.dismiss(row.name)["level"] == "Dismissed"
	finally:
		frappe.db.rollback(save_point="chat_card_check")


@check
def what_waits_after_the_auditor_is_a_card_kept_or_undone():
	"""A comment OneAI's own reading proposed and two the accountant made
	that the auditor doubts wait on Huda: each becomes a card once the
	auditor has had its say, the proposal from Una and the doubts from the
	accountant, and none twice. She keeps one doubt and undoes the other,
	and what waits on her falls by two. All undone."""
	from onedesk.one.registry import agents
	from onedesk.one_ai.reading import act
	from onedesk.one_chat import api, cards

	frappe.db.savepoint("chat_waiting_check")
	try:
		reading = frappe.get_doc({"doctype": "Reading", "title": "Chat check", "key": "chat-check|reading", "on_behalf_of": HUDA}).insert(ignore_permissions=True)
		supplier = frappe.get_all("Supplier", pluck="name", limit=1)[0]

		def row(key: str, level: str, agent: str | None, audit: str | None):
			return frappe.get_doc(
				{
					"doctype": "Reading Action",
					"kind": "Comment",
					"level": level,
					"target_doctype": "Supplier",
					"target_name": supplier,
					"reading": reading.name,
					"key": f"chat-check|{key}",
					"on_behalf_of": HUDA,
					"agent": agent,
					"audit": audit,
					"audit_why": "The document says nothing of it." if audit else None,
					"after": json.dumps({"comment": "Chat check"}),
				}
			).insert(ignore_permissions=True)

		book = agents.email("one_book")
		proposed = row("proposed", "Proposed", None, None)
		kept, undone = (row(key, "Done", book, "Wrong") for key in ("kept", "undone"))
		with as_user(HUDA):
			before = act.waiting()
		cards.waiting(reading.name)
		cards.waiting(reading.name)
		posted = {one.action: one.agent for one in frappe.get_all("Chat Message", filters={"action": ["in", [proposed.name, kept.name, undone.name]]}, fields=["action", "agent"])}
		assert posted == {proposed.name: "una", kept.name: "one_book", undone.name: "one_book"}, posted
		assert frappe.db.count("Chat Message", {"action": kept.name}) == 1, "a card is posted once"
		with as_user(KARIM):
			try:
				api.keep(kept.name)
			except frappe.PermissionError:
				pass
			else:
				raise AssertionError("Karim kept Huda's card")
		with as_user(HUDA):
			assert api.channel(frappe.db.get_value("Chat Message", {"action": kept.name}, "channel"))["cards"][kept.name]["doubted"]
			assert api.keep(kept.name) == {"audit": "Kept"}
			api.undo(undone.name)
			assert act.waiting() == before - 2
	finally:
		frappe.db.rollback(save_point="chat_waiting_check")


@check
def the_panel_is_a_conversation_with_an_agent():
	"""Huda asks the panel on a purchase invoice: the conversation is with
	OneBook's accountant, her question is a message, the accountant answers
	it in the background with its own tools and, once it has, its answer
	is a message in the same conversation. She names
	it and opens it in OneChat; she browses, joins and leaves a channel the
	owner made and added Karim to. A model is not called: the answer is said
	here. All undone."""
	from unittest import mock

	from onedesk.one_chat import answers, api, panel

	frappe.db.savepoint("chat_panel_check")
	try:
		with as_user(HUDA):
			page = {"doctype": "Purchase Invoice", "name": ""}
			assert panel.agent_for(page)["agent"] == "one_book", "the app's agent on its page"
			with mock.patch("frappe.enqueue") as queued:
				said = panel.say("Which bills are due this week?", agent="one_book", page=page)
			assert said["run"] and queued.call_args.kwargs["agent"] == "one_book", "the accountant answers"
			channel = said["name"]
			doc = frappe.get_doc("AI Chat", said["ai_chat"])
			turns = [*frappe.parse_json(doc.turns), {"role": "model", "text": "Two bills are due this week.", "calls": []}]
			answers.posted(doc, turns)
			opened = panel.opened(channel)
			assert [one["role"] for one in opened["said"]] == ["you", "model"] and opened["agent"]["agent"] == "one_book"
			assert panel.rename(channel, "Bills due")["title"] == "Bills due"
			assert channel in {one["name"] for one in panel.conversations()}
			assert panel.actions([]) == []
			api.seen(channel)
			assert api.talk("one_book")["name"] == channel, "the latest conversation with an agent"
			assert panel.start("una")["agent"]["agent"] == "una"
			assert api.start()["agents"][0]["agent"] == "una"
		with as_user(OWNER):
			made = api.make("Site news")["name"]
			api.add(made, [KARIM])
		with as_user(HUDA):
			assert made in {one["name"] for one in api.browse()}
			api.join(made)
			api.leave(made)
	finally:
		frappe.db.rollback(save_point="chat_panel_check")


@check
def a_channel_s_automation_files_and_answers_what_it_watches_for():
	"""Huda makes a channel with the owner and, in AutomationCenter, an
	automation on it: a message that starts with todo becomes a task, said
	in its thread with a reply in her name. The owner reads it and cannot
	change it without making channels; Karim, outside, finds none. The run
	is done here, as its background job does it. All undone."""
	from onedesk.one import automation_center, rights
	from onedesk.one_chat import api, automations

	frappe.db.savepoint("chat_automation_check")
	try:
		with as_user(HUDA):
			made = api.make("Automation check", private=1, people=json.dumps([OWNER]))["name"]
			places = automation_center.places()
			assert made in {scope["scope"] for place in places if place["trigger"] == automations.POSTED for scope in place["scopes"]}
			offered = automation_center.blocks(automations.POSTED, made)
			assert {"chat_reply", "chat_share", "chat_notify", "chat_create"} <= {one["key"] for one in offered["actions"]}
			assert offered["starters"] and offered["trigger"]["where"] == "Automation check"
			then = [{"type": "chat_create", "doctype": "Task"}, {"type": "chat_reply", "text": "On it, {sender_name}.", "thread": 1}]
			steps = [{"type": "if", "id": "i1", "test": {"items": [{"field": "text", "op": "starts_with", "value": "todo"}]}, "then": then, "else": []}]
			assert automation_center.problems(automations.POSTED, json.dumps(steps)) == []
			name = automation_center.save(automations.POSTED, made, json.dumps({"title": "Todo", "enabled": 1, "steps": steps}))
			listed = automation_center.automations(automations.POSTED, made)
			assert [one["name"] for one in listed["rules"]] == [name] and listed["rules"][0]["then"]
			sent = api.send(made, "todo count the petty cash")["message"]["name"]
			other = api.send(made, "The petty cash is counted.")["message"]["name"]
		assert automations.run(sent, made) == [name]
		assert automations.run(other, made) == [], "what it does not watch for runs nothing"
		replies = frappe.get_all("Chat Message", filters={"thread": sent}, fields=["text", "automation", "sender"])
		assert len(replies) == 2 and {one.automation for one in replies} == {name} and {one.sender for one in replies} == {HUDA}
		assert frappe.db.exists("Task", {"subject": "todo count the petty cash"}), "the task is made"
		with as_user(OWNER):
			assert name in {one.name for one in frappe.get_list("Automation", filters={"scope": made})}
			if not rights.held("Chat Channel", "chat_channels"):
				try:
					automation_center.enable(name, 0)
				except frappe.PermissionError:
					pass
				else:
					raise AssertionError("the owner changed an automation without making channels")
		with as_user(KARIM):
			assert not frappe.get_list("Automation", filters={"scope": made}), "Karim reads no automation of a channel he is not in"
		with as_user(HUDA):
			automation_center.enable(name, 0)
			automation_center.delete(name)
	finally:
		frappe.db.rollback(save_point="chat_automation_check")
