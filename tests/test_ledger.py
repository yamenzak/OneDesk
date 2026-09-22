"""The rules that make a balance trustworthy, read off the source.

None of these are about arithmetic — `test_credits.py` has that. These are the
structural ones: that there is no second place a balance could come from, that
a row cannot be edited after it is written, and that the decision to let a call
happen is made on data nobody else can be halfway through changing.
"""

import ast
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

LEDGER = tree.APP / "one_admin" / "ledger.py"
ENTRY = tree.APP / "one_admin" / "doctype" / "credit_ledger_entry" / "credit_ledger_entry.json"
HOLD = tree.APP / "one_admin" / "doctype" / "credit_reservation" / "credit_reservation.json"

#: What a stored balance would be called if somebody added one. A field like
#: this is the thing this whole module exists to not have: it can disagree with
#: the rows it is meant to summarise, and when it does there is no way to tell
#: which of the two is lying.
A_STORED_BALANCE = ("credit_balance", "credits_left", "credits_remaining", "balance")


def _spec(path: Path) -> dict:
	return json.loads(path.read_text(encoding="utf-8"))


def test_there_is_no_stored_balance_on_any_doctype():
	found = []
	for path in tree.fixtures():
		if path.parent.parent.name != "doctype" or path.stem != path.parent.name:
			continue
		spec = _spec(path)
		for field in spec.get("fields") or []:
			if field.get("fieldname") in A_STORED_BALANCE:
				found.append(f"{spec.get('name')}.{field['fieldname']}")
	assert not found, (
		f"{found} would be a balance that can disagree with its own history. "
		"It is a sum over Credit Ledger Entry; see one_admin/ledger.py."
	)


def test_a_ledger_entry_is_submitted_and_never_edited():
	spec = _spec(ENTRY)
	assert spec.get("is_submittable"), "an append-only record is submittable in frappe"
	for row in spec.get("permissions") or []:
		for may in ("write", "create", "delete", "submit", "cancel", "amend"):
			assert not row.get(may), f"{row['role']} may {may} a ledger entry"


def test_a_hold_is_a_second_doctype_and_that_is_the_point():
	"""A reservation changes — taken, then settled for what the call cost. A
	ledger entry is written once. Keeping them apart is what lets the ledger be
	append-only."""
	assert not _spec(HOLD).get("is_submittable")
	assert {f["fieldname"] for f in _spec(HOLD)["fields"]} >= {"state", "credits", "settled"}


def _function(name: str) -> ast.FunctionDef:
	body = ast.parse(LEDGER.read_text(encoding="utf-8"))
	return next(
		node for node in body.body if isinstance(node, ast.FunctionDef) and node.name == name
	)


@pytest.mark.parametrize("name", ["reserve", "commit"])
def test_the_decision_is_made_on_locking_reads(name):
	"""Measured, and the measurement is the reason this file exists.

	Two processes reserving seven credits against a balance of ten both
	succeeded. The second waited on the lock exactly as intended, and then read
	a balance from the snapshot its transaction had taken before the first one
	committed — InnoDB fixes that snapshot at a transaction's first read, and no
	plain SELECT afterwards sees past it.
	"""
	source = ast.unparse(_function(name))
	assert "_lock(" in source, f"{name} does not take the lock"
	assert "locking=True" in source, (
		f"{name} decides on a plain read. Under repeatable read that is a "
		"snapshot from before the lock was waited for, and two calls can both "
		"spend the last credit."
	)


def test_the_lock_is_taken_before_anything_is_written():
	source = ast.unparse(_function("reserve"))
	assert source.index("_lock(") < source.index("frappe.get_doc(")


def test_a_call_is_refused_before_it_is_made_and_never_after():
	"""Refusing after would mean a call we paid for and then told the customer
	they could not have."""
	assert "NotEnough" in ast.unparse(_function("reserve"))
	assert "NotEnough" not in ast.unparse(_function("commit"))


def test_only_the_ledger_knows_a_balance_is_made_of_rows():
	"""Everything above it asks for a number. A second module querying these
	tables is a second definition of what a balance is."""
	elsewhere = []
	#: hooks.py names both doctypes to gate them, which is registration rather
	#: than a query — and the gate is the one thing that has to name them.
	exempt = {LEDGER, tree.APP / "hooks.py"}
	for path in tree.python():
		if path in exempt or path.parent.name in ("credit_ledger_entry", "credit_reservation"):
			continue
		text = path.read_text(encoding="utf-8")
		if "Credit Ledger Entry" in text or "Credit Reservation" in text:
			elsewhere.append(str(path.relative_to(tree.ROOT)))
	assert not elsewhere, f"{elsewhere} read the ledger directly. Ask ledger.py instead."


def test_a_hold_that_never_came_back_is_let_go():
	"""A worker that died mid-flight would otherwise eat a customer's credits
	for good, and nothing else would ever release them."""
	source = LEDGER.read_text(encoding="utf-8")
	assert "STALE_MINUTES" in source
	assert "def nightly(" in source
	hooks = (tree.APP / "hooks.py").read_text(encoding="utf-8")
	assert "onedesk.one_admin.ledger.nightly" in hooks
