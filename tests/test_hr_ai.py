"""OneAI in OneHR: a receipt becomes a suggested claim, in the asker's name.

The rules are OneAI's and this checks OneHR keeps them: the tool writes a card,
not a claim; the employee is whoever is asking, never an argument; a receipt in
another currency is said rather than converted; and the type is picked here,
because a model told a type does not exist stops to ask.
"""

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

AI = tree.APP / "one_hr" / "ai.py"
HOOKS = tree.APP / "hooks.py"
SUGGEST = tree.APP / "one_ai" / "suggest.py"
PROPOSALS = tree.APP / "one_ai" / "proposals.py"
GATEWAY = tree.APP / "one_admin" / "gateway.py"


def _source(path: Path, name: str) -> str:
	for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
		if isinstance(node, (ast.FunctionDef, ast.Assign)):
			named = node.name if isinstance(node, ast.FunctionDef) else getattr(node.targets[0], "id", None)
			if named == name:
				return ast.unparse(node)
	raise AssertionError(f"{name} is not in {path.name}")


def _kind():
	space = {}
	exec(_source(AI, "KINDS") + "\n" + _source(AI, "kind"), space)
	return space["kind"]


TYPES = ["Calls", "Food", "Medical", "Others", "Travel"]


@pytest.mark.parametrize(
	"said, description, chosen",
	[
		("Travel", "", "Travel"),
		("taxi", "Careem Taxi from DXB Terminal 3", "Travel"),
		("meal", "Lunch with a client", "Food"),
		("pharmacy", "", "Medical"),
		("stationery", "Pens and paper", "Others"),
	],
)
def test_the_type_is_picked_here_rather_than_asked(said, description, chosen):
	assert _kind()(said, description, TYPES) == chosen


def test_a_claim_is_only_ever_in_the_askers_name():
	said = _source(AI, "claim_expense")
	assert "own.employee_of()" in said
	signature = said.split(")", 1)[0]
	assert "employee" not in signature.split("(", 1)[1], "a caller could name a colleague"


def test_a_receipt_becomes_a_card_and_nothing_else():
	said = _source(AI, "claim_expense")
	assert "proposals.propose('Create', 'Expense Claim'" in said
	for writing in (".insert(", ".save(", ".submit(", "db.set_value", "ignore_permissions"):
		assert writing not in said, writing


def test_another_currency_is_said_rather_than_converted():
	said = _source(AI, "claim_expense")
	assert "said != ours" in said


def test_ohr_registers_its_own_tool_and_suggestion():
	hooks = HOOKS.read_text(encoding="utf-8")
	assert '"onedesk.one_hr.ai.claim_expense"' in hooks.split("one_ai_suggests =", 1)[1].split("\n", 1)[0]
	assert '"onedesk.one_hr.ai.SUGGESTIONS"' in hooks


def test_a_suggestion_is_only_offered_to_somebody_who_can_take_it():
	assert "frappe.has_permission(doctype, ptype=one['can'])" in _source(SUGGEST, "for_page")


def test_a_card_carries_rows_only_of_its_own_tables():
	said = _source(PROPOSALS, "_plain")
	assert "key in tables" in said and "field in allowed" in said and "MOST_ROWS" in said


def test_an_empty_answer_after_a_tool_is_done_and_anywhere_else_is_retried():
	said = _source(GATEWAY, "_said")
	assert "turns[-1] or {}).get('role') == 'tool'" in said
	assert said.count("asking()") == 2
