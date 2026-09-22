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


def test_a_failure_is_said_in_words_rather_than_in_a_traceback():
	"""A fault carries an endpoint and a status, which is right in a log and
	wrong in a panel — so what reaches the reader is a sentence."""
	said = spoken(CHAT, "_ran")
	assert "faults.Again" in said and "faults.Refused" in said
	assert "frappe.throw" in said


# ----------------------------------------------------- the question is stored


def test_the_question_is_stored_before_the_answer_is_asked_for():
	"""Otherwise a run that fails takes what somebody typed with it."""
	said = spoken(CHAT, "say")
	kept = said.index("_keep(")
	asked = said.index("_ran(")
	assert kept < asked, "the conversation is saved after the model is called"


def test_the_whole_conversation_is_kept_and_only_the_tail_is_sent():
	assert "turns[-KEPT:]" in spoken(CHAT, "_ran"), "the whole conversation is sent every round"
	# What is dropped from the sending is not dropped from the keeping.
	assert "shown(turns)" in spoken(CHAT, "say")


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


# ------------------------------------------------------------- the composer


@pytest.mark.parametrize(
	"stored, shown",
	[
		("google-ai-studio:gemini-2.5-flash-lite", "gemini-2.5-flash-lite"),
		("workers-ai:@cf/google/gemma-4-26b-a4b-it", "gemma-4-26b-a4b-it"),
		("", ""),
	],
)
def test_the_pill_names_a_model_the_way_a_person_reads_it(stored, shown):
	"""The catalogue's id carries its provider and path; the pill shows the name."""
	space = {}
	exec("import re\n" + spoken(CHAT, "named"), space)
	assert space["named"](stored) == shown


def test_the_panel_shows_the_model_and_never_picks_one():
	"""The model is the workspace's choice per action, so the panel sends none.

	One person switching it from a pill would switch it for everybody who asks
	after them — which is why the pill opens the setting instead.
	"""
	panel = PANEL.read_text(encoding="utf-8")
	said = panel[panel.index('"onedesk.one_ai.chat.say"'):]
	said = said[: said.index("});")]
	assert "model" not in said
	assert '"AI Action Setting"' in panel


def test_a_chat_started_by_the_paperclip_is_named_by_its_first_question():
	"""`start` saves a placeholder title; the first thing asked replaces it."""
	said = spoken(CHAT, "say")
	assert "doc.title = text[:TITLE]" in said
