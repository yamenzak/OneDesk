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
	assert '"validate": "onedesk.one_project.naming.validate"' in HOOKS.split('"Project": {', 1)[1].split('}', 1)[0]
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
