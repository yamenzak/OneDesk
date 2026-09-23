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
