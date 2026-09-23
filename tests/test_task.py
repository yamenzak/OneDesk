"""OneTask: every to-do is a task, and a task with no project is its own
people's. The rules are read off the source; the behaviour was measured on the
bench (a to-do about nothing made a task, a Projects User did not see it, and
ticking off the assignment completed it)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

TASK = tree.APP / "one_task"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")


def _body(source: str, name: str) -> str:
	return source.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_both_permission_hooks_are_wired_and_the_grant_comes_first():
	assert '"Task": "onedesk.one_task.access.allowed"' in HOOKS
	assert '"Task": "onedesk.one_task.access.query"' in HOOKS
	assert HOOKS.count('"onedesk.one_task.access.settle"') == 2, "after_install and after_migrate"


def test_a_task_with_no_project_is_seen_by_its_own_people_only():
	source = (TASK / "access.py").read_text()
	query = _body(source, "query")
	assert "`tabTask`.`owner`" in query and "`tabTask`.`_assign` like" in query
	assert "ifnull(`tabTask`.`project`, '') != ''" in query, "only project tasks widen"
	allowed = _body(source, "allowed")
	assert "return bool(doc.project) and sees_projects(user)" in allowed
	assert 'ptype != "delete"' in allowed, "given to me is not mine to delete"
	assert "SYSTEM_USER_ROLE" in _body(source, "sees_projects"), "Desk User is not a projects role"


def test_every_to_do_about_nothing_becomes_a_task():
	source = (TASK / "capture.py").read_text()
	made = _body(source, "todo_made")
	assert "if doc.reference_type or doc.reference_name" in made
	assert 'doc.reference_type, doc.reference_name = "Task", task.name' in made
	assert "task.flags.one_assigned = True" in made, "the to-do is already the assignment"
	assert "doc.flags.one_assigned" in _body(source, "task_made")
	for event, path in (
		("before_insert", "onedesk.one_task.capture.todo_made"),
		("on_update", "onedesk.one_task.capture.todo_changed"),
		("after_insert", "onedesk.one_task.capture.task_made"),
	):
		assert f'"{event}": "{path}"' in HOOKS


def test_only_a_task_in_no_project_is_completed_by_its_last_assignment():
	changed = _body((TASK / "capture.py").read_text(), "todo_changed")
	assert "task.project" in changed and '"status": "Open"' in changed


def test_the_calendar_does_not_show_a_task_twice():
	todos = _body((TASK / "calendar.py").read_text(), "todos")
	assert '["reference_type", "!=", "Task"]' in todos


def test_the_inbox_is_the_tasks_in_no_project():
	rail = json.loads((TASK / "sidebar" / "onetask" / "onetask.json").read_text())
	inbox = next(item for item in rail["items"] if item["label"] == "Inbox")
	assert ["Task", "project", "is", "not set"] in json.loads(inbox["filters"])
	dock = json.loads((tree.APP / "dock" / "onedesk" / "onedesk.json").read_text())
	assert any(item["link_to"] == "OneTask" for item in dock["items"])


def _mine():
	from datetime import date, timedelta

	space = {"date": date, "timedelta": timedelta}
	source = (TASK / "mine.py").read_text()
	exec("def when(" + source.split("def when(", 1)[1].split("\n@frappe", 1)[0], space)
	return space["when"]


def test_my_tasks_are_grouped_by_when_they_are_due():
	from datetime import date

	when = _mine()
	today = date(2026, 9, 23)
	said = [when(day, today) for day in (None, date(2026, 9, 1), today, date(2026, 9, 24), date(2026, 9, 30), date(2026, 10, 1))]
	assert said == ["none", "overdue", "today", "tomorrow", "week", "later"]


def test_my_tasks_writes_through_frappe_and_reads_as_the_reader():
	page = (TASK / "page" / "my_tasks" / "my_tasks.js").read_text()
	assert 'frappe.db.set_value("Task"' in page and 'frappe.db.insert({ doctype: "Task"' in page
	source = (TASK / "mine.py").read_text()
	assert 'frappe.get_list(\n\t\t"Task"' in source and "ignore_permissions" not in source
	rail = json.loads((TASK / "sidebar" / "onetask" / "onetask.json").read_text())
	assert rail["items"][0]["link_to"] == "my-tasks", "OneTask opens on My Tasks"


def _load(path, names, **space):
	import ast

	tree_ = ast.parse(path.read_text())
	for node in tree_.body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in names:
			exec(ast.unparse(node), space)
	for node in tree_.body:
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return space


def test_a_checklist_is_the_progress():
	share = _load(TASK / "task.py", ("share",), flt=lambda value, digits: round(value, digits))["share"]
	assert share([1, 0, 1]) == 66.7 and share([]) == 0 and share([1]) == 100


class _Row(dict):
	__getattr__ = dict.get

	def __setattr__(self, key, value):
		self[key] = value


class _Board(_Row):
	def set(self, key, value):
		self[key] = value


def test_sub_tasks_are_a_connection_and_erpnexts_projects_rail_is_gone():
	assert '"Task": ["onedesk.one_task.task.dashboard"]' in HOOKS
	assert '"onedesk.one_task.task.before_validate",' in HOOKS
	dock = json.loads((tree.APP / "dock" / "onedesk" / "onedesk.json").read_text())
	assert not any(item["link_to"] == "Projects" for item in dock["items"]), "OneProject, not ERPNext's Projects"


def test_a_task_dragged_keeps_its_length_and_its_times():
	from datetime import date, datetime, timedelta

	shifted = _load(TASK / "calendar.py", ("shifted",), timedelta=timedelta, datetime=datetime)["shifted"]
	starts, ends = datetime(2026, 9, 21, 9), datetime(2026, 9, 25, 17)
	assert shifted(starts, ends, date(2026, 9, 28)) == (datetime(2026, 9, 24, 9), datetime(2026, 9, 28, 17))
	assert shifted(None, ends, date(2026, 9, 24)) == (None, datetime(2026, 9, 24, 17))
	assert shifted(starts, None, date(2026, 9, 22)) == (datetime(2026, 9, 22, 9), None), "drawn by its start"


def test_a_timer_stopped_at_once_was_a_slip():
	from datetime import datetime, timedelta

	space = _load(TASK / "timer.py", ("SLIP", "slip"))
	starts = datetime(2026, 9, 23, 10)
	assert space["slip"](starts, starts + timedelta(seconds=20))
	assert not space["slip"](starts, starts + timedelta(minutes=2))


def test_the_timer_writes_the_persons_timesheet_through_its_own_save():
	source = (TASK / "timer.py").read_text()
	assert "doc.check_permission(\"read\")" in source and "ignore_permissions" not in source
	assert '"to_time": ["is", "not set"]' in source, "running is a start with no end, as on the Timesheet form"
	assert "now_datetime()" in source and "stop()" in source.split("def start(", 1)[1].split("\ndef ", 1)[0]
	assert '"/assets/onedesk/js/task_timer.js"' in HOOKS and '"Task": "public/js/task.js"' in HOOKS
	page = (TASK / "page" / "my_tasks" / "my_tasks.js").read_text()
	assert 'frappe.model.can_create("Timesheet")' in page


def test_a_repeat_is_due_when_it_repeats_and_given_to_the_same_people():
	source = (TASK / "task.py").read_text()
	body = _body(source, "recurring")
	assert "auto_repeat_doc.next_schedule_date" in body and '"status": "Open"' in body and "step.done = 0" in body
	assert "doc.flags.one_assign_to" in _body((TASK / "capture.py").read_text(), "task_made")
	assert '"on_recurring": "onedesk.one_task.task.recurring"' in HOOKS
	custom = json.loads((TASK / "custom" / "task.json").read_text())
	assert any(p["property"] == "allow_auto_repeat" and p["value"] == "1" for p in custom["property_setters"])
	assert any(f["fieldname"] == "auto_repeat" for f in custom["custom_fields"])
