"""OneAI across the rest of OneHR: payroll, letters, policy, grievances, goals.

Each keeps the rule the others do — a read runs as the person asking, a write
is a card — and each has one thing of its own worth pinning down here.
"""

import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

HR = tree.APP / "one_hr"


def _pure(path: Path, *names, **space):
	space = {"re": re, "json": json, **space}
	for node in ast.parse(path.read_text(encoding="utf-8")).body:
		if isinstance(node, (ast.FunctionDef, ast.Assign)):
			named = node.name if isinstance(node, ast.FunctionDef) else getattr(node.targets[0], "id", None)
			if named in names:
				exec(ast.unparse(node), space)
	return space


# ------------------------------------------------------------------ payroll


def _slip(net, components, days=30, working=30):
	return {"gross": net, "net": net, "days": days, "working": working, "components": components}


def test_a_payroll_change_is_found_by_arithmetic_not_by_the_model():
	changes = _pure(HR / "ai_payroll.py", "changes", "_moved", "SHARE", "LEAST")["changes"]
	before = _slip(6000, {"Basic (earning)": 4000, "Housing (earning)": 1800, "Transport (earning)": 200})
	same = _slip(6000, {"Basic (earning)": 4000, "Housing (earning)": 1800, "Transport (earning)": 200})
	assert changes(same, before) == []

	dropped = _slip(4200, {"Basic (earning)": 4000, "Transport (earning)": 200})
	said = changes(dropped, before)
	assert "net 6000 → 4200" in said
	assert "Housing (earning) is gone (was 1800)" in said

	# Small moves are the month, not a mistake.
	nudged = _slip(6030, {"Basic (earning)": 4000, "Housing (earning)": 1830, "Transport (earning)": 200})
	assert changes(nudged, before) == []


def test_unpaid_days_and_a_first_slip_are_said():
	changes = _pure(HR / "ai_payroll.py", "changes", "_moved", "SHARE", "LEAST")["changes"]
	assert changes(_slip(3000, {}, days=20, working=30), None) == [
		"first slip for this person: nothing to compare with",
		"paid for 20 of 30 working days",
	]


def test_payroll_is_read_as_the_person_asking():
	source = (HR / "ai_payroll.py").read_text(encoding="utf-8")
	assert "frappe.get_list(\n\t\t\"Salary Slip\"" in source or 'frappe.get_list("Salary Slip"' in source
	assert "ignore_permissions" not in source
	assert '"onedesk.one_hr.ai_payroll.payroll_changes"' in (tree.APP / "hooks.py").read_text()
