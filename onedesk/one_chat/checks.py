"""OneChat's part of the integration suite (one_demo/check.py runs it): a
channel only its members read, a mention that tells the person mentioned, a
direct conversation kept one per pair, a reaction, and an agent's card
posted from the door and answered through it. Nothing is sent to a model."""

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
def the_panel_is_a_conversation_with_an_agent():
	"""Huda asks the panel on a purchase invoice: the conversation is with
	OneBook's accountant, her question is a message and, once OneAI keeps
	its answer, so is the accountant's, in the same conversation. She names
	it and opens it in OneChat; she browses, joins and leaves a channel the
	owner made and added Karim to. A model is not called: the answer is said
	here. All undone."""
	from unittest import mock

	from onedesk.one_chat import agent, api, panel

	frappe.db.savepoint("chat_panel_check")
	try:
		with as_user(HUDA):
			page = {"doctype": "Purchase Invoice", "name": ""}
			assert panel.agent_for(page)["agent"] == "one_book", "the app's agent on its page"
			with mock.patch("frappe.enqueue") as queued:
				said = panel.say("Which bills are due this week?", agent="one_book", page=page)
			assert said["run"] and queued.called, "the answer is OneAI's own loop"
			channel = said["name"]
			doc = frappe.get_doc("AI Chat", said["ai_chat"])
			turns = [*frappe.parse_json(doc.turns), {"role": "model", "text": "Two bills are due this week.", "calls": []}]
			agent.kept(doc, turns)
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
