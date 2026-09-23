"""OneProject: a project's board, its calendar, its task names and its plan,
over the tasks it shares with OneTask."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree
from test_task import _Board, _Row, _body, _load

PROJECT = tree.APP / "one_project"
TASK = tree.APP / "one_task"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")


def test_the_project_half_is_its_own_place():
	rail = json.loads((PROJECT / "sidebar" / "oneproject" / "oneproject.json").read_text())
	owned = {item["link_to"] for item in rail["items"] if item.get("is_default_module") and item["type"] == "Link"}
	assert "Project" in owned and "Task" not in owned, "tasks stay OneTask's"
	task_rail = json.loads((TASK / "sidebar" / "onetask" / "onetask.json").read_text())
	assert not {"Project", "Project Type", "Projects Settings"} & {i.get("link_to") for i in task_rail["items"]}
	dock = [item["link_to"] for item in json.loads((tree.APP / "dock" / "onedesk" / "onedesk.json").read_text())["items"]]
	assert dock.index("OneProject") == dock.index("OneTask") + 1
	assert '"onedesk.one_project.calendar.LAYERS"' in HOOKS and '"onedesk.one_project.plan.before_validate"' in HOOKS


def test_a_project_board_is_shaped_as_it_is_made():
	space = _load(PROJECT / "board.py", ("COLUMNS", "CARD", "shape"), json=json)
	board = _Board(
		reference_doctype="Task",
		field_name="status",
		columns=[_Row(column_name=name) for name in ("Open", "Working", "Overdue", "Completed", "Cancelled", "Template")],
		fields=None,
		show_labels=1,
	)
	assert space["shape"](board) is True
	shown = {one.column_name: one.status for one in board.columns}
	assert "Overdue" not in shown and shown["Cancelled"] == shown["Template"] == "Archived"
	assert shown["Working"] == "Active" and json.loads(board.fields) == ["priority", "exp_end_date"]
	assert space["shape"](board) is False, "shaping twice changes nothing"
	assert space["shape"](_Board(reference_doctype="Opportunity", field_name="sales_stage", columns=[])) is False


def test_overdue_is_a_date_not_a_status():
	source = (PROJECT / "board.py").read_text()
	assert '"erpnext.projects.doctype.task.task.set_tasks_as_overdue"' in source
	custom = json.loads((TASK / "custom" / "task.json").read_text())
	options = next(p for p in custom["property_setters"] if p["field_name"] == "status" and p["property"] == "options")
	assert "Overdue" not in options["value"].split("\n")
	assert "text-danger" in (tree.APP / "public" / "js" / "task_list.js").read_text()
	assert HOOKS.count('"onedesk.one_project.board.settle"') == 2
	assert '"Kanban Board": {"before_insert": "onedesk.one_project.board.shape"}' in HOOKS


def test_a_task_prefix_is_short_and_starts_with_a_letter():
	import re

	key = _load(PROJECT / "naming.py", ("KEY",), re=re)["KEY"]
	assert key.match("WEB") and key.match("R2D2") and key.match("REEM")
	assert not key.match("W") and not key.match("2FA") and not key.match("WEB-1") and not key.match("ABCDEFGHIJK")
	assert '"onedesk.one_project.naming.validate"' in HOOKS.split('"Project": {', 1)[1].split('}', 1)[0]
	source = (PROJECT / "naming.py").read_text()
	assert '"Document Naming Rule"' in source
	assert '"Task"' not in HOOKS.split("override_doctype_class = {", 1)[1].split("}", 1)[0], "ERPNext's Task class stays theirs"


def test_erpnexts_dependants_can_find_their_project():
	body = _body((PROJECT / "plan.py").read_text(), "before_validate")
	assert 'for row in doc.get("depends_on") or []' in body and "row.project = doc.project" in body


def test_a_project_is_its_members():
	source = (PROJECT / "members.py").read_text()
	assert 'MANAGERS = ("Projects Manager",)' in source and 'WORKER = "Projects User"' in source
	seen = _body(source, "visible")
	assert "unlisted" in seen and "member" in seen and "owned" in seen and "under(" in seen
	assert "return not manages(user) and WORKER in frappe.get_roles(user)" in _body(source, "narrowed"), "select-only roles keep their lists"
	assert '"Project": "onedesk.one_project.members.allowed"' in HOOKS and '"Project": "onedesk.one_project.members.query"' in HOOKS
	assert "onedesk.one_project.members.forget" in HOOKS


def test_a_member_can_be_added_without_outgoing_mail():
	source = (PROJECT / "members.py").read_text()
	invite = _body(source, "invite")
	assert '"default_outgoing": 1, "enable_outgoing": 1' in invite and "row.welcome_email_sent = 1" in invite
	assert '"before_validate": "onedesk.one_project.members.invite"' in HOOKS


def _tree():
	return _load(PROJECT / "tree.py", ("children", "below", "above", "loops", "add_up", "FIGURES"), flt=lambda value: float(value or 0))


def test_a_tree_goes_down_and_up_to_any_depth():
	space = _tree()
	of = {"handrails": "villa", "glass": "handrails", "windows": "villa", "booking": "website"}
	assert space["below"]({"villa"}, of) == {"villa", "handrails", "glass", "windows"}
	assert space["below"]({"glass"}, of) == {"glass"}
	assert space["above"]("glass", of) == ["glass", "handrails", "villa"]


def test_a_project_cannot_sit_under_itself():
	loops = _tree()["loops"]
	of = {"handrails": "villa", "glass": "handrails"}
	assert loops("villa", "glass", of), "the villa under its own glass"
	assert loops("villa", "villa", of)
	assert not loops("windows", "villa", of) and not loops("glass", None, of)


def test_a_tree_adds_up_erpnexts_own_figures():
	space = _tree()
	said = space["add_up"]([{"estimated_costing": 20000, "total_billed_amount": 5000}, {"estimated_costing": 4000}])
	assert said["estimated_costing"] == 24000 and said["total_billed_amount"] == 5000
	assert "gross_margin" in space["FIGURES"] and "total_costing_amount" in space["FIGURES"]


def test_the_tree_report_puts_each_project_under_its_parent():
	ordered = _load(PROJECT / "report" / "project_tree" / "project_tree.py", ("ordered",), tree=type("T", (), {"PARENT": "one_parent"}))["ordered"]
	rows = [
		{"name": "W", "project_name": "Windows", "one_parent": "V"},
		{"name": "V", "project_name": "Villa", "one_parent": None},
		{"name": "G", "project_name": "Glass", "one_parent": "H"},
		{"name": "H", "project_name": "Handrails", "one_parent": "V"},
		{"name": "S", "project_name": "Secret", "one_parent": "X"},
	]
	said = [(row["name"], row["indent"], row["parent"]) for row in ordered(rows)]
	assert said == [("S", 0, None), ("V", 0, None), ("H", 1, "V"), ("G", 2, "H"), ("W", 1, "V")]


def test_sub_projects_are_wired_and_members_see_below():
	assert '"onedesk.one_project.tree.validate"' in HOOKS and '"Project": ["onedesk.one_project.tree.dashboard"]' in HOOKS
	assert "tree.below(projects, tree.parents())" in _body((PROJECT / "members.py").read_text(), "under")
	assert "path(project)" in (TASK / "mine.py").read_text(), "My Tasks names the path"
	custom = json.loads((PROJECT / "custom" / "project.json").read_text())
	assert any(f["fieldname"] == "one_parent" and f["options"] == "Project" for f in custom["custom_fields"])


def test_the_overview_counts_days_and_work():
	from datetime import date

	def date_diff(a, b):
		return (a - b).days

	space = _load(PROJECT / "overview.py", ("days_left", "share"), date_diff=date_diff, getdate=lambda value: value)
	today = date(2026, 9, 23)
	assert space["days_left"](date(2026, 10, 3), today, False) == 10
	assert space["days_left"](date(2026, 9, 20), today, False) == -3, "late"
	assert space["days_left"](date(2026, 9, 20), today, True) is None, "a finished project is not late"
	assert space["days_left"](None, today, False) is None
	assert space["share"](1, 4) == 25 and space["share"](0, 0) == 0


def test_the_overview_is_the_whole_tree_and_only_figures():
	source = (PROJECT / "overview.py").read_text()
	assert "tree.below({project}, tree.parents())" in source and "members.sees(one, user)" in source
	page = (tree.APP / "public" / "js" / "project.js").read_text()
	assert "onedesk.one_project.overview.overview" in page and "onedesk.band.show" in page
	assert "chart" not in page.lower(), "figures, not charts"
