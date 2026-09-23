"""What OneAI knows beyond the record: memory, knowledge, past chats, a record's
whole story. Private where it is personal, live where it is a record, and never
written without a card."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

MEMORY = (tree.APP / "one_ai" / "memory.py").read_text()
TOOLS = (tree.APP / "one_ai" / "tools.py").read_text()
DOCTYPES = tree.APP / "one_ai" / "doctype"


def _body(source: str, name: str) -> str:
	return source.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_a_memory_is_its_owners_alone():
	"""if_owner on the doctype, and the owner named in every read as well:
	Administrator is not held by if_owner."""
	meta = json.loads((DOCTYPES / "ai_memory" / "ai_memory.json").read_text())
	assert [(p["role"], p.get("if_owner")) for p in meta["permissions"]] == [("All", 1)]
	reads = MEMORY.count('frappe.get_list(\n\t\t"AI Memory"')
	assert reads and MEMORY.count('"owner": frappe.session.user') >= reads


def test_only_an_administrator_writes_knowledge_and_everybody_reads_it():
	meta = json.loads((DOCTYPES / "ai_knowledge" / "ai_knowledge.json").read_text())
	writers = {p["role"] for p in meta["permissions"] if p.get("write")}
	readers = {p["role"] for p in meta["permissions"] if p.get("read")}
	assert writers == {"Workspace Administrator"}
	assert "All" in readers


def test_remembering_runs_at_once_and_writes_only_the_askers_memory():
	"""The one write that is not a card: it is what the person just said, it is
	theirs alone, and the chat leaves a line to undo it."""
	assert TOOLS.split("KEEPS = (", 1)[1].split(")", 1)[0] == "memory.remember,"
	assert "memory.remember" not in TOOLS.split("SUGGESTS = (", 1)[1].split(")", 1)[0]
	reads = TOOLS.split("READS = (", 1)[1].split(")", 1)[0]
	for tool in ("memory.about_record", "memory.recall", "memory.search_my_chats", "search_everywhere"):
		assert tool in reads, tool
	remember = _body(MEMORY, "remember")
	assert '"doctype": "AI Memory"' in remember
	assert remember.count("frappe.get_doc(") == 1, "it writes nothing but the memory"


def test_the_same_fact_twice_is_one_memory():
	remember = _body(MEMORY, "remember")
	assert "_same(said, one.fact)" in remember and "replaces" in remember
	assert "already remembered" in remember and '"updated"' in remember


def test_global_search_is_frappes_and_checks_each_record():
	"""frappe's search checks has_permission on every hit; we call it rather
	than query the index ourselves."""
	search = _body(TOOLS, "search_everywhere")
	assert "from frappe.utils.global_search import search" in search
	assert "__global_search" not in search


def test_a_records_story_is_read_live_through_the_sidebars_own_function():
	about = _body(MEMORY, "about_record")
	assert "tools.read_record(doctype, name)" in about  # the permission check
	assert "load.get_docinfo(" in about
	for kind in ('"comments"', '"emails"', '"changes"', '"assigned_to"', '"files"', '"links_here"'):
		assert kind in about, kind


def test_past_chats_are_only_the_readers_own():
	assert '"owner": frappe.session.user' in _body(MEMORY, "search_my_chats")


def test_the_context_turn_carries_the_workspace_the_reader_and_what_is_remembered():
	chat = (tree.APP / "one_ai" / "chat.py").read_text()
	asked = _body(chat, "_asked")
	for said in ("_today()", "_workspace()", "_reader()", "memory.told("):
		assert said in asked, said
	assert 'frappe.get_hooks("one_ai_workspace")' in chat


def test_a_memory_is_tied_to_a_record_only_when_the_fact_names_it():
	remember = _body(MEMORY, "remember")
	assert "_names(" in remember
	names = _body(MEMORY, "_names")
	assert "title_field" in names and ".lower() in said" in names


def test_the_same_call_twice_in_one_answer_is_not_run_twice():
	run = (tree.APP / "one_ai" / "run.py").read_text()
	assert "if key in asked:" in run and "already made and answered" in run


def test_a_read_uses_the_one_value_a_link_filter_plainly_meant():
	"""A read changes nothing, so "Annual" for "Annual Leave" is used as meant;
	two candidates are said, never picked between."""
	meant = _body(TOOLS, "_meant")
	assert "len(same) == 1" in meant and "len(holding) == 1" in meant
	assert "_meant(value, there)" in _body(TOOLS, "_known")


def test_past_chats_rank_on_what_was_said_and_skip_the_one_asking():
	search = _body(MEMORY, "search_my_chats")
	assert "_said(one.turns)" in search and "one.name != now" in search
	assert "frappe.flags.one_ai_chat" in search


def test_a_card_hides_what_the_form_hides():
	chat = (tree.APP / "one_ai" / "chat.py").read_text()
	assert 'field.hidden or field.fieldname == "naming_series"' in _body(chat, "_drawn")


def test_a_type_guessed_from_an_id_is_found_by_the_id():
	""""HR-EXP" for HR-EXP-2026-00004: frappe's search says what it is."""
	kind = _body(TOOLS, "_type")
	assert "search_everywhere(name)" in kind and "len(set(found)) == 1" in kind
	assert "_type(doctype, name)" in _body(TOOLS, "read_record")


def test_asked_to_remember_and_nothing_kept_is_asked_for_the_call():
	run = (tree.APP / "one_ai" / "run.py").read_text()
	assert "_unkept(text, called)" in run and "KEEP_IT.format(text)" in run


def test_what_is_remembered_is_told_as_known_not_as_asked():
	""""The reader asked you to remember X" read as being asked again."""
	told = _body(MEMORY, "told")
	assert "Already remembered" in told and "asked you to remember" not in told


def test_each_call_shows_its_own_answer():
	"""Gemini's call id is the tool's name; matched by id, every earlier call to
	a tool showed the last answer it gave."""
	chat = (tree.APP / "one_ai" / "chat.py").read_text()
	shown = _body(chat, "shown")
	assert "_answering(call" in shown and 'call.get("id")' not in shown


def test_keeping_a_memory_is_not_drawn_in_the_conversation():
	chat = (tree.APP / "one_ai" / "chat.py").read_text()
	assert 'QUIET_TOOLS = ("remember",)' in chat
	assert "not in QUIET_TOOLS" in _body(chat, "shown")


def test_an_ai_run_is_waited_on_as_long_as_the_account_waits_on_the_provider():
	account = (tree.APP / "one" / "account.py").read_text()
	assert '"onedesk.one_admin.proxy.ai_run": 75' in account
	assert "PATIENCE_FOR.get(endpoint, PATIENCE)" in account
