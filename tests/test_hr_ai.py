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
	suggests = hooks.split("one_ai_suggests =", 1)[1].split("]", 1)[0]
	for tool in ("claim_expense", "book_leave", "add_applicant"):
		assert f'"onedesk.one_hr.ai.{tool}"' in suggests, tool
	assert '"onedesk.one_hr.ai.SUGGESTIONS"' in hooks


def test_a_suggestion_is_only_offered_to_somebody_who_can_take_it():
	assert "frappe.has_permission(on, ptype=one['can'])" in _source(SUGGEST, "for_page")


def test_a_card_carries_rows_only_of_its_own_tables():
	said = _source(PROPOSALS, "_plain")
	assert "key in tables" in said and "field in allowed" in said and "MOST_ROWS" in said


def test_an_empty_answer_after_a_tool_is_done_and_anywhere_else_is_retried():
	said = _source(GATEWAY, "_said")
	assert "turns[-1] or {}).get('role') == 'tool'" in said
	assert said.count("asking()") == 2


# ----------------------------------------------------------------- leave


def test_leave_is_only_ever_booked_in_the_askers_name_and_only_as_a_card():
	said = _source(AI, "book_leave")
	assert "own.employee_of()" in said
	assert "employee" not in said.split(")", 1)[0].split("(", 1)[1]
	assert "proposals.propose('Create', 'Leave Application'" in said
	for writing in (".insert(", ".save(", ".submit(", "ignore_permissions"):
		assert writing not in said, writing


def test_leave_days_are_counted_the_way_hrms_counts_them():
	"""Holidays and weekly offs, per leave type, by HRMS's own function."""
	assert "get_number_of_leave_days(" in _source(AI, "book_leave")
	assert "days > left" in _source(AI, "book_leave"), "more days than are left would be suggested"


def test_leave_with_nobody_to_approve_it_is_refused_before_the_card():
	"""HR Settings can make the approver mandatory; Approve would then fail on a
	field the person never saw."""
	said = _source(AI, "book_leave")
	assert "leave_approver_mandatory_in_leave_application" in said
	assert said.index("leave_approver_mandatory") < said.index("proposals.propose(")


def test_a_suggestion_card_follows_the_form_order():
	"""Stored changes come back alphabetical; the card reads them in form order."""
	said = _source(tree.APP / "one_ai" / "chat.py", "_suggests")
	assert "sorted(changes.items()" in said


def test_who_is_off_is_what_the_leave_calendar_already_shows():
	"""HRMS's own rule, not a second one: its department view, gated by HR Settings."""
	said = _source(AI, "my_leave")
	assert "add_department_leaves(" in said
	assert "own.employee_of()" in said


@pytest.mark.parametrize(
	"said, chosen",
	[("annual", "Annual Leave"), ("Sick Leave", "Sick Leave"), ("casual", "Casual Leave"), ("vacation", "Annual Leave")],
)
def test_the_leave_type_is_picked_here(said, chosen):
	space = {}
	exec(_source(AI, "_leave_type"), space)
	assert space["_leave_type"](said, ["Casual Leave", "Sick Leave", "Annual Leave"]) == chosen


def test_an_applicant_is_only_ever_a_card_and_never_a_score():
	"""A number a model gave is a number someone will sort by."""
	said = _source(AI, "add_applicant")
	assert "proposals.propose('Create', 'Job Applicant'" in said
	assert "applicant_rating" not in said.split('"""', 2)[-1].replace("the rating", "")
	for writing in (".insert(", ".save(", ".submit(", "ignore_permissions"):
		assert writing not in said, writing


def test_the_same_person_is_not_added_twice():
	said = _source(AI, "add_applicant")
	assert "frappe.db.get_value('Job Applicant', {'email_id': email}" in said


def test_a_batch_of_files_is_asked_about_once_they_are_all_in():
	panel = (tree.APP / "public" / "js" / "oneai" / "Panel.vue").read_text()
	attach = panel.split("async function attach(then) {", 1)[1].split("\n}\n", 1)[0]
	assert "clearTimeout(settle)" in attach and "SETTLE" in attach


def test_a_cv_is_matched_to_its_file_the_way_a_person_would():
	"""The model names the file as it pictures it: "Layla Nasser CV.pdf" for
	layla-nasser-cv.pdf."""
	said = _source(tree.APP / "one_ai" / "files.py", "uploaded")
	assert "for said in (named, person)" in said and "difflib.get_close_matches" in said


def test_the_record_on_screen_is_told_by_what_it_says():
	chat = (tree.APP / "one_ai" / "chat.py").read_text()
	page = chat.split("def _page(", 1)[1].split("\ndef ", 1)[0]
	assert "_brief(doctype, record)" in page


def test_the_fit_line_fits_the_notes_field_without_cutting_a_word():
	said = _source(AI, "add_applicant")
	assert "_short(fit, NOTE)" in said
	assert "rsplit(' ', 1)" in _source(AI, "_short")


def test_a_suggestion_for_one_record_is_not_offered_on_the_list():
	assert 'one.get("view") and one["view"] != view' in (tree.APP / "one_ai" / "suggest.py").read_text()
	openings = (tree.APP / "one_hr" / "ai.py").read_text().split('"Job Opening": [', 1)[1].split("\n\t],", 1)[0]
	assert '"view": "Form"' in openings and '"view": "List"' in openings


def test_appraisal_facts_are_read_as_the_reader():
	said = _source(AI, "appraisal_facts")
	assert "doc.check_permission('read')" in said
	assert "frappe.get_all" not in said and "ignore_permissions" not in said


def test_feedback_is_a_card_in_the_readers_own_name_and_never_a_rating():
	said = _source(AI, "draft_feedback")
	assert "own.employee_of()" in said
	assert "reviewer == doc.employee" in said, "their own appraisal is reflections, not feedback"
	assert "feedback_ratings" not in said and "total_score" not in said
	assert "proposals.propose('Edit'" in said and "proposals.propose('Create'" in said


def test_a_suggestion_that_exists_to_make_a_card_is_asked_for_it():
	""""Draft my feedback" answered with the draft in the chat and no card."""
	run = (tree.APP / "one_ai" / "run.py").read_text()
	assert "expects not in called" in run and "CALL_IT.format(expects)" in run
	assert "expects=suggest.expected(text)" in (tree.APP / "one_ai" / "chat.py").read_text()
	hr = (tree.APP / "one_hr" / "ai.py").read_text()
	for tool in ("claim_expense", "add_applicant", "draft_feedback"):
		assert f'"expects": "{tool}"' in hr, tool


def test_why_people_leave_is_read_as_the_reader_and_counts_each_person_once():
	said = _source(AI, "why_people_leave")
	assert "frappe.get_all" not in said and "ignore_permissions" not in said
	assert "one.name not in heard" in said, "an interviewed leaver is not counted twice"
	assert '"onedesk.one_hr.ai.why_people_leave"' in HOOKS.read_text()
