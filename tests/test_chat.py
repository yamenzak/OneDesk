"""An agent's conversation, and the one thing it is allowed to say about a page.

Two rules carry this file. The page the reader is on travels as a **pointer** —
a doctype and an id — and never as the record's values, because the model has
`read_record` and that runs as whoever is signed in; a payload assembled here
would be a way around a permission rather than a convenience. And a question
is **stored before the answer is asked for**, so a run that fails leaves the
question in the conversation rather than throwing it away.

Read off the source, like the rest of this suite.
"""

import ast
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

HERE = tree.APP / "one_ai" / "here.py"
TALK = tree.APP / "one_ai" / "agents" / "talk.py"
DRAWN = tree.APP / "one_ai" / "drawn.py"
ANSWERS = tree.APP / "one_chat" / "answers.py"
TRANSCRIPT = tree.APP / "one_chat" / "transcript.py"
DOCTYPE = tree.APP / "one_ai" / "doctype" / "ai_chat" / "ai_chat.json"
LAUNCHER = tree.APP / "public" / "js" / "one_ai" / "oneai.js"
BUNDLE = tree.APP / "public" / "js" / "one_ai" / "oneai.bundle.js"
PANEL = tree.APP / "public" / "js" / "one_ai" / "panel" / "Panel.vue"

BLIND = ("get_all", "ignore_permissions", "set_user")


def code() -> str:
	"""The source with its prose removed — the docstrings explain the rules."""
	body = ast.parse(TALK.read_text(encoding="utf-8"))
	for node in ast.walk(body):
		if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and ast.get_docstring(node):
			node.body = node.body[1:]
	return ast.unparse(body)


def spoken(where: Path, name: str) -> str:
	for node in ast.walk(ast.parse(where.read_text(encoding="utf-8"))):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return ast.unparse(node)
	raise AssertionError(f"{name} is not in {where.name}")


def test_the_page_is_never_read_for_its_values():
	"""`said_of` turns a route into a sentence and reads no record to do it."""
	said = spoken(HERE, "said_of")
	for reading in ("get_doc", "get_value", "get_list", "get_all", "db."):
		assert reading not in said, f"said_of reads the record: {reading}"


def test_the_page_names_only_what_the_browser_said_it_is():
	said = spoken(HERE, "said_of")
	for key in ("'doctype'", "'name'", "'view'", "'filters'"):
		assert key in said


@pytest.mark.parametrize("blind", BLIND)
def test_nothing_here_reads_past_its_caller(blind):
	assert blind not in code(), f"{blind} in talk.py"


def test_a_card_is_read_with_the_readers_own_permission():
	said = spoken(DRAWN, "suggested")
	assert "get_list" in said
	assert "get_all" not in said


def test_a_failure_is_said_in_words_rather_than_in_a_traceback():
	"""A fault carries an endpoint and a status, which is right in a log and
	wrong in a panel — so what reaches the reader is a sentence."""
	said = spoken(ANSWERS, "_asked")
	assert "faults.Again" in said and "faults.Refused" in said
	assert "frappe.throw" in said


def test_the_question_is_stored_before_the_answer_is_asked_for():
	"""Otherwise a run that fails takes what somebody typed with it."""
	said = spoken(ANSWERS, "ask")
	kept = said.index("transcript.keep(")
	asked = said.index("frappe.enqueue(")
	assert kept < asked, "the conversation is saved after the run is started"
	assert "enqueue_after_commit=True" in said, "the job could start before the question is stored"
	assert "talk.ask(" not in said, "the model is called on the request again"


def test_the_run_is_a_background_job_that_says_each_step():
	"""A web worker held for forty seconds is a worker answering nobody else."""
	answered = spoken(ANSWERS, "answer")
	assert "_asked(" in answered and "_tell(" in answered
	told = spoken(ANSWERS, "_tell")
	assert "publish_realtime" in told and "user=" in told, "a step is sent to somebody else's browser"


def test_a_run_is_only_read_back_by_whoever_started_it():
	said = spoken(ANSWERS, "progress")
	assert "frappe.session.user" in said


def test_a_failed_run_is_logged_when_it_is_a_bug_and_said_when_it_is_not():
	said = spoken(ANSWERS, "answer")
	assert "frappe.ValidationError" in said and "log_error" in said


def test_the_whole_conversation_is_kept_and_only_the_tail_is_sent():
	assert "transcript.sent(doc, turns)" in spoken(ANSWERS, "_asked"), "the whole conversation is sent every round"
	sent = spoken(TRANSCRIPT, "sent")
	assert "turns[-KEPT:]" in sent and "RECALL_EVERY" in sent and "earlier_upto" in sent, "older turns are recalled, not sent"


def test_the_page_pointer_is_said_to_the_model_and_not_shown_to_the_reader():
	assert "'context': True" in spoken(HERE, "asked")
	assert "QUIET" in spoken(DRAWN, "shown")


def test_a_conversation_that_will_not_parse_loses_nothing():
	"""It starts again rather than raising, and the stored row is left alone."""
	said = spoken(TRANSCRIPT, "turns_of")
	assert "except ValueError" in said
	assert "return []" in said


def test_a_chat_belongs_to_whoever_started_it():
	stored = json.loads(DOCTYPE.read_text(encoding="utf-8"))
	everybody = [row for row in stored["permissions"] if row["role"] == "All"]
	assert everybody, "AI Chat is not readable by the people who have them"
	assert all(row.get("if_owner") for row in everybody), "one person's chat is readable by another"


def test_only_the_launcher_is_on_every_page():
	"""The panel carries Vue; a page nobody asks a question on should not."""
	hooks = tree.hooks()
	assert "js/one_ai/oneai.js" in hooks
	assert "oneai.bundle" not in hooks, "the bundle is loaded on every desk page"
	assert 'frappe.require("oneai.bundle.js")' in LAUNCHER.read_text(encoding="utf-8")
	assert 'from "vue"' not in LAUNCHER.read_text(encoding="utf-8")
	assert 'from "vue"' in BUNDLE.read_text(encoding="utf-8")


def test_the_panel_is_not_inside_the_page_frappe_tears_down():
	"""Mounted on `body`, which is what makes a conversation survive a route change."""
	launcher = LAUNCHER.read_text(encoding="utf-8")
	assert "onedesk.oneai.mount(document.body)" in launcher


def test_the_panel_asks_the_launcher_where_the_reader_is():
	"""One reading of the route, so the two cannot disagree about "here"."""
	launcher = LAUNCHER.read_text(encoding="utf-8")
	assert "frappe.router.on" in launcher
	assert "panel.moved" in launcher
	assert "frappe.get_route" not in PANEL.read_text(encoding="utf-8")


def test_the_panel_has_no_model_to_pick():
	"""A question carries no model and the panel offers none: One picks it,
	by the workspace's tier (docs/AICENTER.md)."""
	panel = PANEL.read_text(encoding="utf-8")
	said = panel[panel.index('"onedesk.one_chat.panel.say"'):]
	said = said[: said.index("});")]
	assert "model" not in said
	assert "choose_model" not in panel and "one-ai-model" not in panel
	talk = TALK.read_text(encoding="utf-8")
	assert "def choose_model" not in talk and "def may_choose" not in talk and "model=" not in spoken(TALK, "ask")


def test_a_chat_started_by_the_paperclip_is_named_by_its_first_question():
	"""A conversation is named by the first thing asked in it."""
	said = spoken(ANSWERS, "ask")
	assert "'title': (text or (urls and urls[0]) or _('New conversation'))[:transcript.TITLE]" in said


def test_several_records_are_one_list_under_the_answer():
	"""Four customers drawn as four cards filled a phone twice over and put
	the answer below them. Several records read at once are one list, and what
	a turn read is moved under the answer it led to."""
	assert "if len(found) < 2" in spoken(DRAWN, "_found")
	assert "return _answer_first(said)" in spoken(DRAWN, "shown")
	panel = PANEL.read_text(encoding="utf-8")
	assert '<Found v-if="look.found"' in panel


def test_oneai_opens_from_the_bar_only():
	"""The bottom bar is on every page once a workspace is set up; a floating
	button showed only where it was not, over the setup wizard."""
	assert "one-ai-dial" not in LAUNCHER.read_text(encoding="utf-8")
