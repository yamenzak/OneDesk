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
	monkeypatch.setattr(channels, "members_of", lambda channel: ["huda@x", "omar@x"])
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
	assert '"Reading Action": {"after_insert": "onedesk.one_chat.cards.posted"}' in hooks
	assert "frappe.get_hooks(\"one_ai_chat_kept\")" in (tree.APP / "one_ai" / "chat.py").read_text()
	assert 'one_ai_chat_kept = hook("one_ai_chat_kept")' in hooks


def test_the_panel_is_a_conversation_in_onechat():
	panel = (JS / "panel" / "Panel.vue").read_text()
	for call in ("onedesk.one_chat.panel.say", "onedesk.one_chat.panel.opened", "onedesk.one_chat.panel.conversations"):
		assert call in panel
	for gone in ("onedesk.one_ai.chat.say", "onedesk.one_ai.chat.opened", "onedesk.one_ai.chat.chats"):
		assert gone not in panel


def test_an_inline_ask_is_one_line_that_answers_in_place():
	quick = (JS / "oneai.js").read_text().split("onedesk.oneai.quick = ", 1)[1].split("\n};\n", 1)[0]
	assert '<input type="text"' in quick and "textarea" not in quick
	assert '__("Ask {0}"' in quick and "await run(" in quick


@pytest.mark.parametrize("name", ["Chat Channel", "Chat Message"])
def test_its_records_are_fixtures_of_its_own(name):
	scrub = name.lower().replace(" ", "_")
	assert (tree.APP / "one_chat" / "doctype" / scrub / f"{scrub}.json").exists()
