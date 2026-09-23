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


# ------------------------------------------------------------------ letters

LETTER = HR / "doctype" / "employee_letter"


def test_only_hr_issues_a_letter():
	spec = json.loads((LETTER / "employee_letter.json").read_text())
	assert spec["is_submittable"] == 1
	submitting = sorted(row["role"] for row in spec["permissions"] if row.get("submit"))
	assert submitting == ["HR Manager", "HR User"]
	employee = next(row for row in spec["permissions"] if row["role"] == "Employee")
	assert employee.get("if_owner") == 1 and not employee.get("submit")


def test_an_employee_asks_only_about_themselves():
	controller = (LETTER / "employee_letter.py").read_text()
	assert "self.employee != own.employee_of()" in controller
	tools = (HR / "ai_letters.py").read_text()
	whose = ast.unparse(next(n for n in ast.parse(tools).body if getattr(n, "name", "") == "_whose"))
	assert "own.employee_of()" in whose and "frappe.get_roles()" in whose


def test_a_letters_kind_is_read_loosely():
	kind = _pure(HR / "ai_letters.py", "KINDS", "_kind")["_kind"]
	assert kind("salary certificate") == "Salary Certificate"
	assert kind("Experience") == "Experience Letter"
	assert kind("a reference for my landlord") == "Other"
	assert kind(None) == "Other"


# ------------------------------------------------------------------ policy


def test_a_long_note_is_handed_over_around_the_words_asked_about():
	passage = _pure(HR / "ai_policy.py", "PASSAGE", "passage")["passage"]
	note = "Welcome to the company. " * 40 + "Sick leave is fifteen days a year, paid in full. " + "Other things. " * 40
	said = passage(note, ["sick"], most=200)
	assert "Sick leave is fifteen days" in said
	assert said.startswith("…") and len(said) <= 202
	assert passage("Short note.", ["sick"]) == "Short note."


def test_a_policy_answer_names_its_source():
	source = (HR / "ai_policy.py").read_text(encoding="utf-8")
	assert "name its source in brackets" in source
	assert "do not answer from what is usual" in source
	assert '"source": f"Leave Type: {one.name}"' in source


# ------------------------------------------------------------------ grievances

GRIEVANCE = HR / "ai_grievance.py"


def test_a_permission_hook_never_answers_none():
	"""frappe reads a falsy answer as a refusal; None shut HR out of every grievance."""
	tree_ = ast.parse(GRIEVANCE.read_text(encoding="utf-8"))
	allowed = next(n for n in tree_.body if getattr(n, "name", "") == "allowed")
	returns = [node.value for node in ast.walk(allowed) if isinstance(node, ast.Return)]
	assert returns and all(isinstance(one, ast.Constant) and one.value in (True, False) for one in returns)


def test_oneai_marks_a_grievance_sensitive_and_never_clears_it():
	source = GRIEVANCE.read_text(encoding="utf-8")
	assert 'values["one_ai_sensitive"] = 1' in source
	assert '"one_ai_sensitive": 0' not in source and "one_ai_sensitive = 0" not in source
	assert "Only an HR Manager can mark a grievance as not sensitive." in source
	hooks = (tree.APP / "hooks.py").read_text()
	assert '"Employee Grievance": "onedesk.one_hr.ai_grievance.allowed"' in hooks
	assert '"Employee Grievance": "onedesk.one_hr.ai_grievance.query"' in hooks


def test_harassment_discrimination_and_safety_are_always_sensitive():
	space = _pure(GRIEVANCE, "CATEGORIES", "SENSITIVE")
	assert set(space["SENSITIVE"]) == {"Harassment", "Discrimination", "Safety"}
	assert set(space["SENSITIVE"]) <= set(space["CATEGORIES"])
	source = GRIEVANCE.read_text(encoding="utf-8")
	assert "sensitive = category in SENSITIVE or bool(answer.get(\"sensitive\"))" in source


# ------------------------------------------------------------------ growth


def test_a_kra_is_one_of_the_workspaces_own():
	meant = _pure(HR / "ai_growth.py", "kra_meant", difflib=__import__("difflib"))["kra_meant"]
	known = ["Quality of work", "Delivery on time", "Working with others"]
	assert meant("quality of works", known) == "Quality of work"
	assert meant("Delivery On Time", known) == "Delivery on time"
	assert meant("Blockchain strategy", known) is None
	assert meant(None, known) is None


def test_goals_are_your_own_your_reports_or_hrs():
	source = (HR / "ai_growth.py").read_text(encoding="utf-8")
	whose = ast.unparse(next(n for n in ast.parse(source).body if getattr(n, "name", "") == "_whose"))
	assert "own.employee_of()" in whose
	assert "'reports_to'" in whose
	assert "frappe.get_roles()" in whose
