"""OneChat (docs/ARC-AI.md, OneChat): a conversation read by its members
alone, a mention that tells the person mentioned and nobody else, an agent's
card approved through the door's own approval, and the panel and the inline
asks on OneChat. No site needed."""

import sys
from pathlib import Path

import frappe
import pytest
from frappe import _dict

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import tree  # noqa: E402

from onedesk.one_chat import agents, cards, channels, messages  # noqa: E402

JS = tree.APP / "public" / "js" / "one_ai"


def _channel(*users, kind="Channel"):
	return _dict({"kind": kind, "members": [_dict({"user": one}) for one in users], "is_new": lambda: False, "get": lambda key, default=None: [_dict({"user": one}) for one in users] if key == "members" else default})


def test_only_members_read_a_conversation():
	assert channels.reads(["huda@x", "omar@x"], "huda@x")
	assert not channels.reads(["huda@x", "omar@x"], "karim@x")
	assert not channels.reads(["huda@x"], "")
	doc = _channel("huda@x", "omar@x")
	assert channels.has_permission(doc, "read", "omar@x")
	assert not channels.has_permission(doc, "read", "karim@x")
	assert not channels.has_permission(doc, "write", "karim@x")


def test_a_message_is_read_by_its_conversation_s_members_and_changed_by_its_writer(monkeypatch):
	monkeypatch.setattr(channels, "readers", lambda channel: ["huda@x", "omar@x"])
	said = _dict({"channel": "c1", "sender": "huda@x"})
	assert channels.message_permission(said, "read", "omar@x")
	assert not channels.message_permission(said, "read", "karim@x")
	assert channels.message_permission(said, "write", "huda@x")
	assert not channels.message_permission(said, "write", "omar@x")
	assert not channels.message_permission(said, "delete", "karim@x")


def test_no_role_reads_around_membership():
	"""The list's condition names the reader alone, and no administrator."""
	for query in (channels.query, channels.message_query):
		source = query.__code__.co_names
		assert "administers" not in source and "get_roles" not in source
	hooks = (tree.APP / "hooks.py").read_text()
	for doctype, path in (
		("Chat Channel", "onedesk.one_chat.channels.has_permission"),
		("Chat Message", "onedesk.one_chat.channels.message_permission"),
		("Chat Channel", "onedesk.one_chat.channels.query"),
		("Chat Message", "onedesk.one_chat.channels.message_query"),
	):
		assert f'"{doctype}": "{path}"' in hooks


def test_a_mention_tells_the_person_mentioned_and_nobody_else(monkeypatch):
	told = []
	from onedesk.one import notify as hub

	monkeypatch.setattr(hub, "notify", lambda kind, users, **said: told.append((kind, list(users), said)))
	monkeypatch.setattr(channels, "members_of", lambda channel: ["huda@x", "omar@x", "karim@x"])
	monkeypatch.setattr(frappe.utils, "get_fullname", lambda user: user.split("@")[0].title())
	doc = _dict({"sender": "huda@x", "text": "@Omar the bank lines are in", "thread": None, "name": "m1"})
	messages.notify(doc, _dict({"name": "c1", "kind": "Channel", "title": "Month end"}), ["omar@x", "huda@x", "stranger@x"])
	assert told == [(messages.MENTIONED, ["omar@x"], told[0][2])]
	assert told[0][2]["who"] == "Huda" and told[0][2]["conversation"] == "Month end"
	assert "channel=c1" in told[0][2]["link"] and "thread=m1" in told[0][2]["link"]


def test_who_is_told_of_a_message():
	assert messages.told("Channel", ["a", "b", "c"], "a", []) == {messages.MENTIONED: [], messages.DIRECT: []}
	assert messages.told("Channel", ["a", "b", "c"], "a", ["b", "b", "a", "z"]) == {messages.MENTIONED: ["b"], messages.DIRECT: []}
	assert messages.told("Direct", ["a", "b"], "a", []) == {messages.MENTIONED: [], messages.DIRECT: ["b"]}
	assert messages.told("Direct", ["a", "b"], "a", ["b"]) == {messages.MENTIONED: ["b"], messages.DIRECT: []}


def test_handles_are_read_longest_first_in_the_order_said():
	handles = {"huda": "Huda", "huda_s": "Huda Saleh", "one_book": "OneBook", "una": "Una"}
	assert agents.mentioned("@Huda Saleh, ask @OneBook", handles) == ["huda_s", "one_book"]
	assert agents.mentioned("ask @una then @huda", handles) == ["una", "huda"]
	assert agents.mentioned("mail huda@onebook.com or @OneBooks", handles) == []
	assert agents.mentioned("", handles) == []


def test_a_reaction_is_added_and_taken_off():
	once = messages.reacted({}, "👍", "a")
	assert once == {"👍": ["a"]}
	assert messages.reacted(messages.reacted(once, "👍", "b"), "👍", "a") == {"👍": ["b"]}
	assert messages.reacted(once, "👍", "a") == {}


def test_a_card_s_approve_is_the_door_s_own(monkeypatch):
	from onedesk.one_ai.reading import act

	settled, reached = [], []
	monkeypatch.setattr(act, "settle", lambda action, take=1: settled.append((action, take)) or {"level": "Done" if take else "Dismissed"})
	monkeypatch.setattr(cards, "reach", reached.append)
	monkeypatch.setattr(cards, "_told", lambda name: None)
	assert cards.approve("RA-1") == {"level": "Done"}
	assert cards.dismiss("RA-2") == {"level": "Dismissed"}
	assert settled == [("RA-1", 1), ("RA-2", 0)]
	assert reached == ["RA-1", "RA-2"], "a card is answered only from a conversation the reader is in"
	source = (tree.APP / "one_chat" / "cards.py").read_text()
	for writing in (".insert(", ".submit(", "_write(", "set_value"):
		assert writing not in source.split("def approve", 1)[1].split("def change", 1)[0]


def test_change_edits_only_the_plain_values_a_card_proposed():
	values = {"supplier_name": "Acme", "items": [{"item_code": "A"}], "docstatus": 0}
	edits = {"supplier_name": "Acme LLC", "items": [], "tax_id": "123", "docstatus": 1}
	assert cards.changed(values, edits) == {"supplier_name": "Acme LLC", "items": [{"item_code": "A"}], "docstatus": 1}
	assert [one["fieldname"] for one in cards.shown_values({"a": 1, "_b": 2, "doctype": "X", "c": [1]})] == ["a"]


def test_the_door_s_cards_land_in_onechat():
	hooks = (tree.APP / "hooks.py").read_text()
	assert '"Reading Action": {"after_insert": "onedesk.one_chat.cards.posted",' in hooks
	answer = (tree.APP / "one_chat" / "answers.py").read_text().split("def answer(", 1)[1].split("\ndef ", 1)[0]
	assert "posted(doc, turns)" in answer and "talk.ask(" in (tree.APP / "one_chat" / "answers.py").read_text()


def test_the_panel_is_a_conversation_in_onechat():
	panel = (JS / "panel" / "Panel.vue").read_text()
	for call in ("onedesk.one_chat.panel.say", "onedesk.one_chat.panel.opened", "onedesk.one_chat.panel.conversations"):
		assert call in panel
	for gone in ("onedesk.one_ai.chat.",):
		assert gone not in panel


def test_an_inline_ask_is_one_line_that_answers_in_place():
	quick = (JS / "oneai.js").read_text().split("onedesk.oneai.quick = ", 1)[1].split("\n};\n", 1)[0]
	assert '<input type="text"' in quick and "textarea" not in quick
	assert '__("Ask {0}"' in quick and "await run(" in quick


@pytest.mark.parametrize("name", ["Chat Channel", "Chat Message"])
def test_its_records_are_fixtures_of_its_own(name):
	scrub = name.lower().replace(" ", "_")
	assert (tree.APP / "one_chat" / "doctype" / scrub / f"{scrub}.json").exists()


def test_a_channel_s_automations_are_its_members_and_run_on_what_people_post(monkeypatch):
	"""AutomationCenter lists OneChat's automations by channel: a member reads
	them, a member who may make channels changes them, and only a person's
	message starts one, never an agent's or an automation's own."""
	from onedesk.one import rights
	from onedesk.one_chat import automations

	monkeypatch.setattr(channels, "members_of", lambda channel: ["huda@x", "omar@x"])
	monkeypatch.setattr(frappe, "db", _dict({"get_value": lambda *args, **kwargs: channels.CHANNEL, "exists": lambda *args, **kwargs: True, "escape": lambda value: f"'{value}'"}), raising=False)
	monkeypatch.setattr(rights, "held", lambda doctype, ptype, user=None: user == "huda@x")
	row = _dict({"scope": "c1"})
	assert automations.allowed(row, "read", "omar@x") and not automations.allowed(row, "write", "omar@x")
	assert automations.allowed(row, "write", "huda@x") and not automations.allowed(row, "read", "karim@x")
	assert "`tabChat Channel Member`" in automations.query("omar@x")
	queued = []
	monkeypatch.setattr(frappe, "enqueue", lambda *args, **kwargs: queued.append(kwargs))
	channel = _dict({"name": "c1", "kind": channels.CHANNEL})
	for posted in (_dict({"name": "m1", "automation": "A1", "agent": ""}), _dict({"name": "m2", "automation": None, "agent": "one_book"})):
		automations.fire(posted, channel)
	assert not queued, "nothing an automation or an agent posts starts one"
	automations.fire(_dict({"name": "m3", "automation": None, "agent": ""}), channel)
	assert queued and queued[0]["message"] == "m3" and queued[0]["enqueue_after_commit"]


def test_an_automation_s_agent_answers_from_the_instruction_and_the_thread_alone(monkeypatch):
	from onedesk.one_chat import automations

	monkeypatch.setattr(frappe.utils, "get_fullname", lambda user: user.split("@")[0].title())
	said = [_dict({"sender": "huda@x", "text": "Is the printer fixed?"}), _dict({"sender": "it@agents", "agent": "", "text": "Not yet."}), _dict({"sender": "omar@x", "text": ""})]
	turns = automations.told("You are IT's agent.", "Say the printer is fixed on Monday.", said, "it@agents")
	assert turns[0]["context"] and "Say the printer is fixed on Monday." in turns[0]["text"] and "cannot look anything up" in turns[0]["text"]
	assert [one["role"] for one in turns[1:]] == ["user", "model"], "its own words are its own, an empty message is left out"
	assert turns[1]["text"] == "Huda: Is the printer fixed?"
	assert automations.last_words({"turns": [{"role": "model", "text": "First"}, {"role": "tool"}, {"role": "model", "text": " Last "}]}) == "Last"
	answered = (tree.APP / "one_chat" / "automations.py").read_text().split("def answered(", 1)[1].split("\ndef ", 1)[0]
	assert "tools=((), ())" in answered, "no tools: nothing a record holds reaches the conversation"


def test_the_working_day_runs_past_midnight_too():
	from datetime import time

	from onedesk.one.automation import hours

	assert hours.outside(time(20), time(8), time(17)) and not hours.outside(time(9), time(8), time(17))
	assert not hours.outside(time(23), time(22), time(6)) and hours.outside(time(12), time(22), time(6))


def test_a_room_is_read_by_its_members_and_its_channel_s(monkeypatch):
	monkeypatch.setattr(channels, "members_of", lambda channel: {"desk": ["karim@x"]}.get(channel, []))
	monkeypatch.setattr(frappe, "db", _dict({"escape": lambda value: f"'{value}'"}), raising=False)
	room = _dict({"kind": channels.ROOM, "desk": "desk", "members": [_dict({"user": "huda@x"})], "is_new": lambda: False})
	room["get"] = lambda key, default=None: room[key] if key in room else default
	assert set(channels.readers(room)) == {"huda@x", "karim@x"}, "somebody who joins the channel later reads its rooms"
	assert channels.has_permission(room, "read", "karim@x") and not channels.has_permission(room, "read", "omar@x")
	assert ".kind = 'Room'" in channels.query("omar@x") and "kind = 'Room'" in channels.message_query("omar@x")


def test_a_visitor_holds_a_key_only_its_hash_is_kept_and_they_read_words_alone(monkeypatch):
	from onedesk.one_chat import widget

	assert widget.key_of("abc") == widget.key_of("abc") != widget.key_of("abd") and len(widget.key_of("abc")) == 64
	assert widget.checked(" Rana ", "Rana@Example.com ", " Hi ") == ("Rana", "rana@example.com", "Hi")
	assert widget.EMAIL.match("rana@example.com") and not widget.EMAIL.match("nobody")
	monkeypatch.setattr(frappe.utils, "get_fullname", lambda user: "Huda Saleh")
	room = _dict({"visitor_name": "Rana"})
	assert widget.shown({"name": "m", "sender": "huda@x", "text": "Yes", "creation": "t"}, room) == {"name": "m", "text": "Yes", "mine": 0, "who": "Huda", "at": "t"}
	assert widget.shown({"name": "n", "sender": channels.VISITOR, "text": "Hi"}, room)["who"] == "Rana"
	said = (tree.APP / "one_chat" / "widget.py").read_text().split("def said(", 1)[1].split("\ndef ", 1)[0]
	assert '"thread": ("is", "not set")' in said and '"action": ("is", "not set")' in said, "never a thread or a card"
	source = (tree.APP / "one_chat" / "widget.py").read_text()
	assert source.count("@rate_limit(") == 5 and source.count("allow_guest=True") == 4, "every guest call is limited"
	assert "/assets/onedesk/js/one_chat/widget.js" in tree.hooks()


def test_an_agent_in_a_room_answers_the_visitor_until_the_team_does():
	source = (tree.APP / "one_chat" / "automations.py").read_text()
	answered = source.split("def answered(", 1)[1].split("\ndef ", 1)[0]
	assert "taken_over(channel.name)" in answered and "held.thread if room else" in answered
	assert 'channel.kind in (channels.CHANNEL, channels.ROOM)' in (tree.APP / "one_chat" / "answers.py").read_text(), "a mentioned agent answers in a thread, never to the visitor"


def test_onechat_declares_its_own_blocks_and_the_engine_names_none():
	blocks = (tree.APP / "one_chat" / "blocks.py").read_text()
	assert "Trigger(\n\t\tPOSTED," in blocks and 'scope="Chat Channel"' in blocks
	for key in ("chat_reply", "chat_answer", "chat_share", "chat_forward", "chat_notify", "chat_create"):
		assert f'"{key}"' in blocks, key
	engine = "".join((tree.APP / "one" / "automation" / name).read_text() for name in ("engine.py", "flow.py", "kinds.py"))
	assert "one_chat" not in engine and "Chat Message" not in engine
	assert "automations.fire(message, doc)" in (tree.APP / "one_chat" / "api.py").read_text()
