"""The panel's conversation, and the one thing it is allowed to say about a page.

Two rules carry this file. The page the reader is on travels as a **pointer** —
a doctype and an id — and never as the record's values, because the model has
`read_record` and that runs as whoever is signed in; a payload assembled here
would be a way around a permission rather than a convenience. And a conversation
is **stored before the answer is asked for**, so a run that fails leaves the
question in the chat rather than throwing it away.

Read off the source, like the rest of this suite.
"""

import ast
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

CHAT = tree.APP / "one_ai" / "chat.py"
DOCTYPE = tree.APP / "one_ai" / "doctype" / "ai_chat" / "ai_chat.json"
HOOKS = tree.APP / "hooks.py"
LAUNCHER = tree.APP / "public" / "js" / "oneai.js"
BUNDLE = tree.APP / "public" / "js" / "oneai.bundle.js"
PANEL = tree.APP / "public" / "js" / "oneai" / "Panel.vue"

#: Ways to read a record that do not check the reader's permission. `get_all` is
#: `get_list` with the checks off and one letter different, which is why it is
#: named rather than left to a reviewer's eye.
BLIND = ("get_all", "ignore_permissions", "set_user")


def code() -> str:
	"""The source with its prose removed — the docstrings explain the rules."""
	body = ast.parse(CHAT.read_text(encoding="utf-8"))
	for node in ast.walk(body):
		if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and ast.get_docstring(node):
			node.body = node.body[1:]
	return ast.unparse(body)


def spoken(where: Path, name: str) -> str:
	for node in ast.walk(ast.parse(where.read_text(encoding="utf-8"))):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return ast.unparse(node)
	raise AssertionError(f"{name} is not in {where.name}")


# ------------------------------------------------------ the page is a pointer


def test_the_page_is_never_read_for_its_values():
	"""`_page` turns a route into a sentence and reads no record to do it."""
	said = spoken(CHAT, "_page")
	for reading in ("get_doc", "get_value", "get_list", "get_all", "db."):
		assert reading not in said, f"_page reads the record: {reading}"


def test_the_page_names_only_what_the_browser_said_it_is():
	said = spoken(CHAT, "_page")
	# Single quotes: `ast.unparse` normalises them, so this is what it reads back as.
	for key in ("'doctype'", "'name'", "'view'", "'filters'"):
		assert key in said


@pytest.mark.parametrize("blind", BLIND)
def test_nothing_here_reads_past_its_caller(blind):
	assert blind not in code(), f"{blind} in chat.py"


def test_a_card_is_read_with_the_readers_own_permission():
	said = spoken(CHAT, "cards")
	assert "get_list" in said
	assert "get_all" not in said


# ----------------------------------------------------- the question is stored


def test_the_question_is_stored_before_the_answer_is_asked_for():
	"""Otherwise a run that fails takes what somebody typed with it."""
	said = spoken(CHAT, "say")
	kept = said.index("_keep(")
	asked = said.index("run.ask(")
	assert kept < asked, "the conversation is saved after the model is called"


def test_the_whole_conversation_is_kept_and_only_the_tail_is_sent():
	said = spoken(CHAT, "say")
	assert "turns[-KEPT:]" in said, "the whole conversation is sent to the model every round"
	# What is dropped from the sending is not dropped from the keeping.
	assert "shown(turns)" in said


def test_the_page_pointer_is_said_to_the_model_and_not_shown_to_the_reader():
	assert "'context': True" in spoken(CHAT, "_asked")
	assert "QUIET" in spoken(CHAT, "shown")


def test_a_conversation_that_will_not_parse_loses_nothing():
	"""It starts again rather than raising, and the stored row is left alone."""
	said = spoken(CHAT, "_turns")
	assert "except ValueError" in said
	assert "return []" in said


# --------------------------------------------------------- whose chat it is


def test_a_chat_belongs_to_whoever_started_it():
	stored = json.loads(DOCTYPE.read_text(encoding="utf-8"))
	everybody = [row for row in stored["permissions"] if row["role"] == "All"]
	assert everybody, "AI Chat is not readable by the people who have them"
	assert all(row.get("if_owner") for row in everybody), "one person's chat is readable by another"


# ------------------------------------------------------------ the two layers


def test_only_the_launcher_is_on_every_page():
	"""The panel carries Vue; a page nobody asks a question on should not."""
	hooks = HOOKS.read_text(encoding="utf-8")
	assert "js/oneai.js" in hooks
	assert "oneai.bundle" not in hooks, "the bundle is loaded on every desk page"
	assert 'frappe.require("oneai.bundle.js")' in LAUNCHER.read_text(encoding="utf-8")
	assert 'from "vue"' not in LAUNCHER.read_text(encoding="utf-8")
	assert 'from "vue"' in BUNDLE.read_text(encoding="utf-8")


def test_the_panel_is_not_inside_the_page_frappe_tears_down():
	"""Mounted on `body`, which is what makes a conversation survive a route change."""
	launcher = LAUNCHER.read_text(encoding="utf-8")
	assert "document.body.appendChild" in launcher
	assert "onedesk.oneai.mount(document.body)" in launcher


def test_the_panel_asks_the_launcher_where_the_reader_is():
	"""One reading of the route, so the two cannot disagree about "here"."""
	launcher = LAUNCHER.read_text(encoding="utf-8")
	assert "frappe.router.on" in launcher
	assert "panel.moved" in launcher
	assert "frappe.get_route" not in PANEL.read_text(encoding="utf-8")
