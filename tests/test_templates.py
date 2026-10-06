"""Project templates: the library's presets, the template's page and where a
person picks one. These read the code and the preset files."""

import importlib.util
import json
import re
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "onedesk"
LIBRARY = APP / "one_project" / "library"
HOOKS = (APP / "hooks.py").read_text()


def _library():
	"""library.py without a site: frappe only for what it calls at import."""
	fake = types.ModuleType("frappe")
	fake.whitelist = lambda **_kw: lambda fn: fn
	fake._ = lambda text: text
	before = sys.modules.get("frappe")
	sys.modules["frappe"] = fake
	try:
		spec = importlib.util.spec_from_file_location("library", APP / "one_project" / "library.py")
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	finally:
		if before is None:
			sys.modules.pop("frappe")
		else:
			sys.modules["frappe"] = before
	return module


def _presets():
	return {path.stem: json.loads(path.read_text()) for path in sorted(LIBRARY.glob("*.json"))}


def test_the_library_has_every_preset_asked_for():
	titles = {one["title"] for one in _presets().values()}
	assert titles == {
		"Aluminium & Glazing",
		"Interior Fit-Out",
		"Small Building Works",
		"Architectural Design Stages",
		"Website",
		"Mobile App",
		"Marketing Campaign",
		"ERP Rollout",
		"Office Move",
		"Event",
		"New Client Onboarding",
		"Year-End Audit",
	}
	orders = [one["order"] for one in _presets().values()]
	assert len(orders) == len(set(orders)), "each preset has its own place in the list"
	assert _presets()["aluminium_and_glazing"]["order"] == 1


def test_aluminium_and_glazing_is_five_phases_of_25_tasks_each_ending_in_a_milestone():
	preset = _presets()["aluminium_and_glazing"]
	assert len(preset["tasks"]) == 5
	assert sum(len(phase["tasks"]) for phase in preset["tasks"]) == 25
	assert all(phase["milestone"] for phase in preset["tasks"])


def test_every_preset_reads_into_rows():
	library = _library()
	for key, preset in _presets().items():
		rows = library.rows(preset)
		assert rows, key
		for at, row in enumerate(rows):
			assert row["start"] >= 0 and row["duration"] >= 0, (key, row["subject"])
			assert row["parent"] is None or row["parent"] < at, "a parent comes before its tasks"
			assert all(one != at for one in row["after"]), "nothing waits on itself"
		groups = [at for at, row in enumerate(rows) if row["is_group"]]
		for at in groups:
			inside = [row for row in rows if row["parent"] == at]
			assert rows[at]["start"] == min(row["start"] for row in inside), key
			assert rows[at]["start"] + rows[at]["duration"] == max(
				row["start"] + row["duration"] for row in inside
			), key


def test_a_task_waits_on_the_one_before_only_when_that_one_ends_first():
	library = _library()
	rows = library.rows(
		{
			"tasks": [
				{
					"subject": "A",
					"tasks": [
						{"subject": "a", "day": 0, "days": 3},
						{"subject": "b", "day": 3, "days": 2},
						{"subject": "c", "day": 4, "days": 1},
					],
				},
				{"subject": "B", "tasks": [{"subject": "d", "day": 9, "days": 1, "after": ["a"]}]},
			]
		}
	)
	by = {row["subject"]: row for row in rows}
	assert by["b"]["after"] == [1] and by["c"]["after"] == [], "c begins before b ends"
	assert by["B"]["after"] == [0] and by["d"]["after"] == [1], "said in the file wins"
	assert by["A"]["start"] == 0 and by["A"]["duration"] == 5


def test_a_preset_is_said_in_plain_words():
	for key, preset in _presets().items():
		said = [preset["title"], preset["about"]]
		stack = list(preset["tasks"])
		while stack:
			task = stack.pop()
			said.append(task["subject"])
			stack.extend(task.get("tasks") or [])
		for text in said:
			assert not re.search(r"[:;]", text), (key, text)
			assert text == text.strip() and text, (key, text)


def test_a_preset_is_copied_in_the_workspaces_language():
	source = (APP / "one_project" / "library.py").read_text()
	assert 'one["subject"] = _(subject)' in source and "title = _(title)" in source
	assert (
		"onedesk/one_project/library/*.json,onedesk.one.babel.project_template"
		in (ROOT / "babel_extractors.csv").read_text()
	)


def test_the_library_is_offered_where_a_template_is_picked():
	new = (APP / "public" / "js" / "project_new.js").read_text()
	actions = (APP / "public" / "js" / "project_actions.js").read_text()
	listed = (APP / "public" / "js" / "project_template_list.js").read_text()
	for source in (new, actions, listed):
		assert "onedesk.project.library(" in source
	assert '"onedesk.one_project.library.presets"' in new
	assert "values.library and library.copy(values.library)" in (APP / "one_project" / "kinds.py").read_text()
	assert (
		"template = template or (library and copy(library))"
		in (APP / "one_project" / "templates.py").read_text()
	)
	assert '"Project Template": "public/js/project_template_list.js"' in HOOKS


def test_a_template_opens_on_its_page_and_every_change_saves_it():
	view = (APP / "one_project" / "template_view.py").read_text()
	for method in ("read", "change", "add", "nest", "wait", "remove"):
		assert f"def {method}(" in view, method
	assert view.count("_saved(doc)") >= 5, "every change saves the template, so its checks run"
	assert 'frappe.has_permission("Project Template", "write", template, throw=True)' in view
	assert '"onedesk.template": "onedesk_template"' in HOOKS
	assert '"onedesk.one_project.templates.days_kept"' in HOOKS
	page = (ROOT / "frontend" / "src" / "template" / "TemplatePage.vue").read_text()
	assert 'follow("Project Template"' in page
	tasks = (ROOT / "frontend" / "src" / "template" / "Tasks.vue").read_text()
	assert '__("Day {0}", [one.start || 0])' in tasks
