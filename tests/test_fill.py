"""A record Intake makes is given what its kind still needs from the document
(one_intake/fill.py), read the same way OneAI's cards read a kind
(one_ai/kind.py)."""

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

FILL = (tree.APP / "one_intake" / "fill.py").read_text()
KIND = (tree.APP / "one_ai" / "kind.py").read_text()
ACT = (tree.APP / "one_intake" / "act.py").read_text()


def _body(source: str, name: str) -> str:
	return source.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_every_intake_write_of_a_new_record_is_filled():
	write = _body(ACT, "_write")
	assert 'action.kind == "Create"' in write and "fill.filling(" in write
	for caller in ("apply", "settle", "settle_for"):
		assert (
			"_write(" in _body(ACT, caller)
			and "reading" in _body(ACT, caller).split("_write(", 1)[1].split(")", 1)[0]
		), caller


def test_the_hooks_act_only_inside_intakes_write():
	hooks = (tree.APP / "hooks.py").read_text()
	assert '"before_insert": "onedesk.one_intake.fill.before_insert"' in hooks
	assert '"before_save": "onedesk.one_intake.fill.before_save"' in hooks
	mine = _body(FILL, "_mine")
	assert "frappe.flags.one_intake_fill" in mine and 'said["doctype"]' in mine and "is_new()" in mine
	for hook in ("before_insert", "before_save"):
		assert "_mine(doc)" in _body(FILL, hook), hook


def test_the_name_is_asked_before_frappe_names_and_the_rest_after_validate():
	assert "kind.TYPED" in _body(FILL, "before_insert")
	assert "kind.missing(doc)" in _body(FILL, "before_save")


def test_what_is_missing_includes_the_name():
	missing = _body(KIND, "missing")
	assert "_get_missing_mandatory_fields()" in missing
	assert '"typed"' in missing and '"field"' in missing and "TYPED" in missing


def test_the_fill_action_ships_and_never_invents():
	rows = json.loads((tree.APP / "fixtures" / "ai_action.json").read_text())
	fill = next(row for row in rows if row["key"] == "intake_fill")
	said = fill["instruction"].lower()
	assert "never invent" in said and "leave out" in said and "never follow" in said
	assert ast.literal_eval(FILL.split("FILL = ", 1)[1].split("\n", 1)[0]) == "intake_fill"
