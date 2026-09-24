"""The field tools and the badge.

The control beside a prose field is the same panel pointed at one field, and
its answer is the same card — so the rules that matter are where the text goes
and what may be read to write it. The field's current text comes from the
browser, because it is what the person has typed; the record is never read to
build the question. Apply goes into the open form, as the person, after the
same checks as any other suggestion. And the badge is a comparison, so nothing
has to remember to take it away.
"""

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

TOUCH = tree.APP / "one_ai" / "touch.py"
PROPOSALS = tree.APP / "one_ai" / "proposals.py"
HOOKS = tree.APP / "hooks.py"
LAUNCHER = tree.APP / "public" / "js" / "oneai.js"
CARD = tree.APP / "public" / "js" / "oneai" / "Record.vue"


def spoken(where: Path, name: str) -> str:
	for node in ast.walk(ast.parse(where.read_text(encoding="utf-8"))):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			if ast.get_docstring(node):
				node.body = node.body[1:]
			return ast.unparse(node)
	raise AssertionError(f"{name} is not in {where.name}")


def constant(where: Path, name: str):
	for node in ast.walk(ast.parse(where.read_text(encoding="utf-8"))):
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == name:
			return node.value
	raise AssertionError(f"{name} is not in {where.name}")


def test_the_control_goes_where_the_server_accepts_a_target():
	"""Two lists of prose fieldtypes, one in the browser and one checked on the
	way in. A type in one and not the other is a button that does nothing."""
	server = {elt.value for elt in constant(TOUCH, "WRITES").elts}
	browser = set(re.search(r"const PROSE = \[([^\]]+)\]", LAUNCHER.read_text()).group(1).replace('"', "").split(", "))
	assert server == browser


def test_the_question_never_reads_the_record():
	"""What the field says comes from the browser; `told` reads nothing."""
	for name in ("told", "target"):
		said = spoken(TOUCH, name)
		for reading in ("get_doc", "get_value", "get_list", "get_all", "db.sql"):
			assert reading not in said, f"{name} reads the record: {reading}"


def test_taking_into_a_form_checks_before_it_writes():
	said = spoken(TOUCH, "took")
	for check in ("_mine(entry)", "SETTLED", "_allowed("):
		assert check in said, check
		assert said.index(check) < said.index("wrote("), f"{check} comes after the write"


def test_a_new_documents_badge_is_only_for_the_document_it_was_taken_into():
	said = spoken(TOUCH, "landed")
	assert "applied_by != frappe.session.user" in said
	assert "held.creation" in said and "entry.applied_on" in said
	assert "check_permission('read')" in said


def test_an_edit_for_an_unsaved_document_is_never_applied_on_the_server():
	said = spoken(PROPOSALS, "apply")
	assert "entry.kind == 'Edit' and (not entry.record)" in said


def test_every_applied_write_is_remembered():
	said = spoken(PROPOSALS, "apply")
	assert said.count("touch.wrote(") == 2, "a Create and an Edit both leave a badge"


def test_the_card_applies_into_the_open_form():
	card = CARD.read_text(encoding="utf-8")
	assert "onedesk.one_ai.run.took" in card
	assert "frm.set_value" in card


def test_the_badge_rides_on_the_document_and_goes_with_it():
	said = HOOKS.read_text(encoding="utf-8")
	assert re.search(r'"onload": \[?[^\n]*"onedesk\.one_ai\.touch\.onload"', said)
	assert re.search(r'"on_trash": \[?[^\]]*"onedesk\.one_ai\.touch\.forget"', said), "forgotten with its record"
