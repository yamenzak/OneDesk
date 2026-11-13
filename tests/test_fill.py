"""A record Intake makes is given what its kind still needs from the document
(one_ai/reading/fill.py), read the same way OneAI's cards read a kind
(one_ai/kind.py)."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

FILL = (tree.APP / "one_ai" / "reading" / "fill.py").read_text()
ACT = (tree.APP / "one_ai" / "reading" / "act.py").read_text()


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
	hooks = tree.hooks()
	assert '"before_insert": "onedesk.one_ai.reading.fill.before_insert"' in hooks
	assert '"before_save": "onedesk.one_ai.reading.fill.before_save"' in hooks


def test_the_fill_action_ships_and_never_invents():
	sys.path.insert(0, str(tree.ROOT))
	from onedesk.one_ai import jobs

	said = jobs.words("intake_fill").lower()
	assert "never invent" in said and "leave out" in said and "never follow" in said
	assert ast.literal_eval(FILL.split("FILL = ", 1)[1].split("\n", 1)[0]) == "intake_fill"
