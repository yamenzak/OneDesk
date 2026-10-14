"""OneProject: a project's board, its calendar, its task names and its plan,
over the tasks it shares with OneTask."""

import json
import re
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
	owned = {
		item["link_to"] for item in rail["items"] if item.get("is_default_module") and item["type"] == "Link"
	}
	assert "Project" in owned and "Task" not in owned, "tasks stay OneTask's"
	task_rail = json.loads((TASK / "sidebar" / "onetask" / "onetask.json").read_text())
	assert not {"Project", "Project Type", "Projects Settings"} & {
		i.get("link_to") for i in task_rail["items"]
	}
	dock = [
		item["link_to"]
		for item in json.loads((tree.APP / "dock" / "onedesk" / "onedesk.json").read_text())["items"]
	]
	assert dock.index("OneProject") == dock.index("OneTask") + 1
	assert '"onedesk.one_project.calendar.LAYERS"' in HOOKS


def test_a_project_board_is_shaped_as_it_is_made():
	from types import SimpleNamespace

	class Board(_Board):
		def append(self, table, row):
			self[table].append(_Row(row))

	meta = SimpleNamespace(get_field=lambda fieldname: None)
	cards = _load(tree.APP / "one" / "boards.py", ("cards",), frappe=SimpleNamespace(get_meta=lambda doctype: meta))
	space = _load(
		PROJECT / "board.py", ("COLUMNS", "CARD", "shape"), json=json, boards=SimpleNamespace(**cards)
	)
	board = Board(
		reference_doctype="Task",
		field_name="status",
		columns=[
			_Row(column_name=name)
			for name in ("Open", "Working", "Overdue", "Completed", "Cancelled", "Template")
		],
		card_fields=[],
		use_kanban_v2=0,
	)
	assert space["shape"](board) is True
	shown = {one.column_name: one.status for one in board.columns}
	assert "Overdue" not in shown and shown["Cancelled"] == shown["Template"] == "Archived"
	assert shown["Working"] == "Active" and board.use_kanban_v2 == 1, "on frappe's new Kanban"
	assert [(row.fieldname, row.icon) for row in board.card_fields] == [("priority", "flag"), ("exp_end_date", "calendar")]
	assert space["shape"](board) is False, "shaping twice changes nothing"
	assert (
		space["shape"](Board(reference_doctype="Opportunity", field_name="sales_stage", columns=[])) is False
	)


def test_overdue_is_a_date_not_a_status():
	source = (PROJECT / "board.py").read_text()
	assert '"erpnext.projects.doctype.task.task.set_tasks_as_overdue"' in source
	custom = json.loads((TASK / "custom" / "task.json").read_text())
	options = next(
		p for p in custom["property_setters"] if p["field_name"] == "status" and p["property"] == "options"
	)
	assert "Overdue" not in options["value"].split("\n")
	assert "text-danger" in (tree.APP / "public" / "js" / "task_list.js").read_text()
	assert HOOKS.count('"onedesk.one_project.board.settle"') == 2
	assert '"Kanban Board": {"before_insert": "onedesk.one_project.board.shape"}' in HOOKS


def test_a_task_prefix_is_short_and_starts_with_a_letter():
	import re

	key = _load(PROJECT / "naming.py", ("KEY",), re=re)["KEY"]
	assert key.match("WEB") and key.match("R2D2") and key.match("REEM")
	assert (
		not key.match("W")
		and not key.match("2FA")
		and not key.match("WEB-1")
		and not key.match("ABCDEFGHIJK")
	)
	assert '"onedesk.one_project.naming.validate"' in HOOKS.split('"Project": {', 1)[1].split("}", 1)[0]
	source = (PROJECT / "naming.py").read_text()
	assert '"Document Naming Rule"' in source
	assert '"Task"' not in HOOKS.split("override_doctype_class = {", 1)[1].split("}", 1)[0], (
		"ERPNext's Task class stays theirs"
	)


def test_a_project_is_its_members():
	source = (PROJECT / "members.py").read_text()
	assert 'MANAGERS = ("Projects Manager",)' in source and 'WORKER = "Projects User"' in source
	assert (
		'"Project": "onedesk.one_project.members.allowed"' in HOOKS
		and '"Project": "onedesk.one_project.members.query"' in HOOKS
	)
	assert "onedesk.one_project.members.forget" in HOOKS


def test_a_member_is_told_in_ours_not_erpnexts_mail():
	# ERPNext's English invitation is never sent, with mail or without; the
	# member hears Added to Project through the hub (tell.py).
	assert '"onedesk.one_project.members.invite",\n\t\t\t"onedesk.one_project.members.unlist",' in HOOKS
	tell = (PROJECT / "tell.py").read_text()
	assert 'notify.notify("Added to Project"' in tell and 'notify.notify("Made Project Manager"' in tell
	assert 'notify.notify("Project Health"' in tell and 'WORSE = ("At Risk", "Off Track")' in tell
	assert '"onedesk.one_project.tell.changed"' in HOOKS
	types = tree.notifications()
	for name in ("Added to Project", "Made Project Manager", "Project Health"):
		assert types[name]["module"] == "one_project", name


def _tree():
	return _load(
		PROJECT / "tree.py",
		("children", "below", "above", "loops", "add_up", "FIGURES"),
		flt=lambda value: float(value or 0),
	)


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
	said = space["add_up"](
		[{"estimated_costing": 20000, "total_billed_amount": 5000}, {"estimated_costing": 4000}]
	)
	assert said["estimated_costing"] == 24000 and said["total_billed_amount"] == 5000
	assert "gross_margin" in space["FIGURES"] and "total_costing_amount" in space["FIGURES"]


def test_the_tree_view_puts_each_project_under_its_parent():
	space = _load(PROJECT / "tree.py", ("PARENT", "under", "_yes"), flt=lambda value: float(value or 0))
	under, yes = space["under"], space["_yes"]
	rows = [
		{"name": "W", "project_name": "Windows", "one_parent": "V"},
		{"name": "V", "project_name": "Villa", "one_parent": None},
		{"name": "G", "project_name": "Glass", "one_parent": "H"},
		{"name": "H", "project_name": "Handrails", "one_parent": "V"},
		{"name": "S", "project_name": "Secret", "one_parent": "X"},
	]
	# A project whose parent the reader can't see is at the top.
	assert [(one["value"], one["expandable"]) for one in under(rows, None)] == [("S", False), ("V", True)]
	assert [one["title"] for one in under(rows, "V")] == ["Handrails", "Windows"]
	assert [one["value"] for one in under(rows, "H")] == ["G"]
	assert yes(True) and yes("true") and yes("1") and not yes("0") and not yes(None)
	# frappe's own Tree and Gantt views, from the Projects list's switcher.
	assert (
		'"Project": "public/js/project_tree.js"' in HOOKS
		and '"Project": "public/js/project_calendar.js"' in HOOKS
	)
	tree_js = (tree.APP / "public" / "js" / "project_tree.js").read_text()
	assert (
		'get_tree_nodes: "onedesk.one_project.tree.nodes"' in tree_js and "disable_add_node: true" in tree_js
	)
	timeline = (tree.APP / "public" / "js" / "project_calendar.js").read_text()
	assert '"onedesk.one_project.tree.milestones"' in timeline and "depends_on: null" in timeline
	assert not (PROJECT / "report" / "project_tree").exists()
	assert "onedesk.one_project.patches.tree_is_a_view" in (tree.APP / "patches.txt").read_text()


def test_sub_projects_are_wired_and_members_see_below():
	assert (
		'"onedesk.one_project.tree.validate"' in HOOKS
		and '"Project": ["onedesk.one_project.tree.dashboard"]' in HOOKS
	)
	assert "path(project)" in (TASK / "mine.py").read_text(), "My Tasks names the path"
	custom = json.loads((PROJECT / "custom" / "project.json").read_text())
	assert any(f["fieldname"] == "one_parent" and f["options"] == "Project" for f in custom["custom_fields"])


def test_the_overview_counts_days_and_work():
	from datetime import date

	def date_diff(a, b):
		return (a - b).days

	space = _load(
		PROJECT / "overview.py", ("days_left", "share"), date_diff=date_diff, getdate=lambda value: value
	)
	today = date(2026, 9, 23)
	assert space["days_left"](date(2026, 10, 3), today, False) == 10
	assert space["days_left"](date(2026, 9, 20), today, False) == -3, "late"
	assert space["days_left"](date(2026, 9, 20), today, True) is None, "a finished project is not late"
	assert space["days_left"](None, today, False) is None
	assert space["share"](1, 4) == 25 and space["share"](0, 0) == 0


def test_the_overview_is_the_whole_tree_and_its_chart_is_the_bands():
	source = (PROJECT / "overview.py").read_text()
	assert "tree.scope(project)" in source and "members.sees(one, user)" in source
	# What the page says above its fields is its Record Head, over the overview.
	heads = (PROJECT / "heads.py").read_text()
	assert "overview.overview(name)" in heads and '"doctype": "Project"' in heads
	assert '"charts": [{"chart": "project.hours"}]' in heads
	page = "".join(
		(tree.APP / "public" / "js" / name).read_text() for name in ("project.js", "project_actions.js")
	)
	# The band is the Record Head's; the page only borrows its figures for
	# the Costing tab.
	assert "onedesk.band.show" not in page
	# The hours are the reader's own list of timesheets, and the chart is the
	# band's (frappe.Chart in band.js), never one drawn here.
	weekly = source.split("def _weekly(", 1)[1]
	assert 'frappe.get_list(\n\t\t"Timesheet Detail"' in weekly and "frappe.get_all" not in weekly
	assert "frappe.Chart" not in page


def test_a_dependant_moves_after_what_it_waits_on():
	from datetime import date, timedelta

	space = _load(
		PROJECT / "plan.py",
		("MOVES", "moved_after"),
		date_diff=lambda a, b: (a - b).days,
		add_days=lambda day, n: day + timedelta(days=n),
	)
	moved = space["moved_after"]
	starts, ends = date(2026, 10, 1), date(2026, 10, 3)
	assert moved(starts, ends, date(2026, 10, 5), "Open") == (date(2026, 10, 6), date(2026, 10, 8)), (
		"keeps its length"
	)
	assert moved(starts, ends, date(2026, 9, 20), "Open") is None, "already after it"
	assert moved(starts, ends, date(2026, 10, 5), "Working") == (date(2026, 10, 6), date(2026, 10, 8)), (
		"started work moves too, as ERPNext's does"
	)
	assert moved(starts, ends, date(2026, 10, 5), "Completed") is None, "done work stays"
	assert moved(None, ends, date(2026, 10, 5), "Open") is None


def test_a_slip_crosses_sub_projects_and_the_plan_is_the_tree():
	task = HOOKS.split('"Task": {', 1)[1].split("\n\t},", 1)[0]
	assert '"onedesk.one_project.plan.reschedule"' in task.split('"on_update"', 1)[1]
	page = "".join(
		(tree.APP / "public" / "js" / name).read_text() for name in ("project.js", "project_actions.js")
	)
	assert 'project: ["in", said.tree]' in page and '"List", "Task", "Gantt"' in page
	assert 'remove_custom_button(__("Gantt Chart"), __("View"))' in page
	gantt = (tree.APP / "public" / "js" / "task_list.js").read_text()
	assert "Gantt.prototype.prepare_tasks" in gantt and "start: task.end" in gantt, (
		"a due date alone is a day"
	)
	assert "gantt.config.view_mode.name === name" in gantt, "the lit pill is the chart's mode"
	css = (tree.APP / "public" / "css" / "desk.css").read_text()
	assert ".result.result:has(> .gantt-container)" in css, "the chart scrolls, to today"


def test_a_template_counts_days_from_the_projects_start():
	from datetime import date

	space = _load(
		PROJECT / "templates.py",
		("start_of", "days"),
		date_diff=lambda a, b: (a - b).days,
		getdate=lambda value: value,
	)
	begins = space["start_of"](
		date(2026, 9, 10), [{"exp_start_date": date(2026, 9, 8), "exp_end_date": None}]
	)
	assert begins == date(2026, 9, 8), "no task begins before the project"
	assert space["start_of"](None, [{"exp_start_date": None, "exp_end_date": None}]) is None
	days = space["days"]
	assert days(begins, date(2026, 9, 10), date(2026, 9, 13)) == {"start": 2, "duration": 3}
	assert days(begins, None, date(2026, 9, 12)) == {"start": 4, "duration": 0}, "a due date alone is a day"
	assert days(begins, None, None) == {"start": 0, "duration": 0}
	assert days(None, date(2026, 9, 10), None) == {"start": 0, "duration": 0}


def test_a_template_is_the_whole_teams_and_keeps_what_erpnext_drops():
	# What a template hands on, and who reads it, is checked on the demo
	# (oneproject_a_template_hands_on_what_erpnext_leaves_out).
	assert '"onedesk.one_project.templates.task_made"' in HOOKS.split('"Task": {', 1)[1].split("},", 1)[0]
	assert "after_rollback.add(_forget)" in (PROJECT / "naming.py").read_text()
	page = "".join(
		(tree.APP / "public" / "js" / name).read_text() for name in ("project.js", "project_actions.js")
	)
	assert "onedesk.one_project.templates.save_as" in page
	assert '"Project Template": "public/js/project_template.js"' in HOOKS
	# Tasks are OneTask's rail's, which leaves a template's tasks out.
	rail = TASK / "sidebar" / "onetask" / "onetask.json"
	tasks = next(i for i in json.loads(rail.read_text())["items"] if i.get("label") == "All Tasks")
	assert "is_template" in tasks["filters"], rail.name


def _flt(value, precision=None):
	return round(float(value or 0), precision) if precision is not None else float(value or 0)


def test_time_is_invoiced_by_activity():
	space = _load(PROJECT / "billing.py", ("lines",), flt=_flt)
	rows = [
		{"activity_type": "Execution", "billing_hours": 3, "billing_amount": 840},
		{"activity_type": "Planning", "billing_hours": 2, "billing_amount": 600},
		{"activity_type": "Execution", "billing_hours": 4, "billing_amount": 1120},
		{"activity_type": None, "billing_hours": 0, "billing_amount": 0},
	]
	lines = space["lines"](rows)
	assert [(one["activity"], one["hours"], one["rate"]) for one in lines] == [
		("Execution", 7, 280),
		("Planning", 2, 300),
	]


def test_time_billed_is_its_lines_to_the_cent():
	# Hours at a rate turned into another currency: each row rounds apart,
	# and the last row of a line takes what is left, so they add up to it.
	space = _load(PROJECT / "billing.py", ("lines",), flt=_flt)
	rate = 180 * 0.2723
	rows = [
		{"activity_type": "Design", "billing_hours": hours, "billing_amount": hours * rate}
		for hours in (1.33, 2.17, 0.75, 3.1)
	]
	lines = space["lines"](rows)
	assert len(lines) == 1
	assert round(sum(row["billing_amount"] for row in rows), 2) == lines[0]["amount"]
	assert lines[0]["amount"] == round(round(1.33 + 2.17 + 0.75 + 3.1, 2) * lines[0]["rate"], 2)
	# A different rate for the same activity is a line of its own.
	rows.append({"activity_type": "Design", "billing_hours": 1, "billing_amount": 200})
	assert [one["rate"] for one in space["lines"](rows)] == [lines[0]["rate"], 200]


def test_an_order_for_extra_work_is_named_by_what_it_orders():
	from types import SimpleNamespace as Row

	space = _load(PROJECT / "billing.py", ("ordered_title",), _=lambda text: text)

	class Order(dict):
		name = "SAL-ORD-1"

	def order(*names):
		return Order(items=[Row(item_name=one, item_code=one) for one in names])

	assert space["ordered_title"](order("Handrail Installation")) == "Handrail Installation"
	assert space["ordered_title"](order("Handrails", "Glass", "Fixings")) == "Handrails and 2 more"
	assert space["ordered_title"](order()) == "SAL-ORD-1"


def test_an_order_under_a_project_becomes_its_sub_project():
	orders = HOOKS.split('"Sales Order": {', 1)[1].split("},", 1)[0]
	assert '"onedesk.one_project.billing.ordered"' in orders
	# The project and the Extra Work tick, by the same names on both, so the
	# mapping carries them from quotation to order.
	quote = json.loads((PROJECT / "custom" / "quotation.json").read_text())
	assert [f["fieldname"] for f in quote["custom_fields"]] == ["project", "one_extra_work"]
	order_ = json.loads((PROJECT / "custom" / "sales_order.json").read_text())
	assert [f["fieldname"] for f in order_["custom_fields"]] == [
		"one_extra_work",
		"one_retention",
		"one_retention_due",
		"one_retention_handover",
	]
	assert "onedesk.one_project.patches.extra_work" in (tree.APP / "patches.txt").read_text()
	assert "Quote Extra Work" in (tree.APP / "public" / "js" / "project.js").read_text()
	assert '"Quotation": "public/js/quotation.js"' in HOOKS
	page = "".join(
		(tree.APP / "public" / "js" / name).read_text() for name in ("project.js", "project_actions.js")
	)
	assert '"onedesk.one_project.billing.invoice_time"' in page and "frappe.model.open_mapped_doc" in page


def test_a_project_asks_once_at_the_time_it_is_set_to():
	from datetime import time

	space = _load(PROJECT / "updates.py", ("MORNING", "due"), time=time, get_time=lambda value: value)
	due = space["due"]
	daily = {"frequency": "Daily", "daily_time_to_send": time(10)}
	assert not due(daily, time(9), "Monday", 0) and due(daily, time(10), "Monday", 0)
	assert not due(daily, time(15), "Monday", 1), "once a day, not every hour after"
	twice = {"frequency": "Twice Daily", "first_email": time(9), "second_email": time(16)}
	assert due(twice, time(9), "Monday", 0) and not due(twice, time(10), "Monday", 1), (
		"not in two hours running"
	)
	assert due(twice, time(16), "Monday", 1) and not due(twice, time(17), "Monday", 2)
	weekly = {"frequency": "Weekly", "day_to_send": "Friday"}
	assert due(weekly, time(9), "Friday", 0) and not due(weekly, time(8), "Friday", 0), (
		"no time set is the morning"
	)
	assert not due(weekly, time(9), "Thursday", 0)
	assert not due({"frequency": "Hourly"}, time(12), "Monday", 0), "hourly is not offered"


def test_updates_replace_erpnexts_asking_and_are_kept_on_the_project():
	source = (PROJECT / "updates.py").read_text()
	for job in (
		"hourly_reminder",
		"project_status_update_reminder",
		"collect_project_status",
		"send_project_status_email_to_users",
	):
		assert f"project.project.{job}" in source
	assert HOOKS.count('"onedesk.one_project.updates.settle"') == 2
	assert '"onedesk.one_project.updates.ask"' in HOOKS.split('"hourly": [', 1)[1].split("]", 1)[0]
	assert (
		'"onedesk.one_project.updates.answered"' in HOOKS.split('"Communication": {', 1)[1].split("},", 1)[0]
	)
	assert '"Project": ["onedesk.one_project.updates.timeline"]' in HOOKS
	custom = json.loads((PROJECT / "custom" / "project.json").read_text())
	frequency = next(p for p in custom["property_setters"] if p["field_name"] == "frequency")
	assert "Hourly" not in frequency["value"]
	page = "".join(
		(tree.APP / "public" / "js" / name).read_text() for name in ("project.js", "project_actions.js")
	)
	assert "onedesk.one_project.updates.asked" in page and "onedesk.one_project.updates.post" in page


def test_a_customer_is_told_when_in_plain_words():
	space = _load(PROJECT / "portal.py", ("when",), _=lambda text: text)
	assert space["when"](None) is None
	assert space["when"](0) == "Due today"
	assert space["when"](12) == "In 12 days"
	assert space["when"](-3) == "3 days late"


def test_a_customer_reaches_their_projects_and_nothing_of_the_team():
	assert '"has_permission": "onedesk.check_app_permission"' in HOOKS, (
		"a customer signing in is not sent to the desk"
	)
	assert "is_website_user()" in (tree.APP / "__init__.py").read_text()
	assert '"onedesk.one.portal.invited"' in HOOKS.split('"Contact": {', 1)[1].split("},", 1)[0]
	assert (
		'{"doctype": "Portal User", **where, "user": doc.user}'
		in (tree.APP / "one" / "portal.py").read_text()
	), "the only thing ERPNext's portal reads"
	page = (tree.APP / "www" / "projects.py").read_text()
	assert "portal.view(project)" in page, "One's page at ERPNext's address"
	html = (tree.APP / "www" / "projects.html").read_text()
	assert "_assign" not in html and "timesheet" not in html.lower() and "/tasks/new" not in html, (
		"nothing of the team's"
	)


def test_a_tasks_hours_fall_in_the_days_of_the_week_they_cover():
	from datetime import date, timedelta

	today = date(2026, 9, 24)
	space = _load(
		PROJECT / "report" / "workload" / "workload.py",
		("in_week", "load"),
		getdate=lambda value: value,
		date_diff=lambda a, b: (a - b).days,
		nowdate=lambda: today,
	)
	in_week = space["in_week"]
	monday, sunday = date(2026, 9, 21), date(2026, 9, 27)
	assert in_week(date(2026, 9, 25), date(2026, 10, 2), monday, sunday, 24) == 9, "three of eight days"
	assert in_week(None, date(2026, 9, 26), monday, sunday, 6) == 6, "a due date alone is a day"
	assert in_week(None, date(2026, 9, 10), monday, sunday, 3) == 3, "late work is this week's"
	assert in_week(None, date(2026, 9, 10), monday + timedelta(7), sunday + timedelta(7), 3) is None, (
		"not next week's"
	)
	assert in_week(date(2026, 10, 1), date(2026, 10, 3), monday, sunday, 5) is None
	assert space["load"](12, 40) == 30 and space["load"](5, 0) is None


def test_workload_is_a_report_of_figures_in_the_rail():
	source = (PROJECT / "report" / "workload" / "workload.py").read_text()
	assert 'frappe.get_list(\n\t\t"Task"' in source, "only what the reader may see"
	assert '"standard_working_hours"' in source and '"Leave Application"' in source
	rail = json.loads((PROJECT / "sidebar" / "oneproject" / "oneproject.json").read_text())
	assert any(
		item.get("link_to") == "Workload" and item.get("link_type") == "Report" for item in rail["items"]
	)
	assert "chart" not in (PROJECT / "report" / "workload" / "workload.js").read_text().lower().replace(
		"not a chart", ""
	)


def test_what_the_old_oneproject_had_that_is_kept():
	custom = {
		f["fieldname"]: f
		for f in json.loads((PROJECT / "custom" / "project.json").read_text())["custom_fields"]
	}
	assert custom["one_health"]["options"].split("\n") == ["On Track", "At Risk", "Off Track"]
	assert custom["one_manager"]["options"] == "User" and custom["one_manager"]["default"] == "__user"
	assert "doc.one_health" in (PROJECT / "heads.py").read_text(), "health leads the band"
	rail = json.loads((PROJECT / "sidebar" / "oneproject" / "oneproject.json").read_text())
	items = {item["label"]: item for item in rail["items"]}
	# Somebody's first week is not client work: left out quietly in every view.
	assert "filters" not in items["Projects"]
	assert '"project_type", "!=", "Employee Boarding"' in (tree.APP / "public" / "js" / "project_list.js").read_text()
	lifecycle = (tree.APP / "one_hr" / "lifecycle.py").read_text()
	assert 'BOARDING = "Employee Boarding"' in lifecycle
	assert HOOKS.count('"on_submit": "onedesk.one_hr.lifecycle.typed"') == 2
	assert 'where = [["project_type", "!=", BOARDING]]' in (PROJECT / "tree.py").read_text()


def test_the_projects_list_says_status_and_names_the_manager():
	js = (tree.APP / "public" / "js" / "project_list.js").read_text()
	assert "hide_name_column: true" in js and "hide_name_filter: true" in js
	assert 'Open: "blue", "On hold": "orange", Completed: "green"' in js, (
		"Open is not red, and a share is not a status"
	)
	# Customer is a column; it filters under Filters, not in the quick filters.
	user = json.loads((tree.APP / "one" / "custom" / "user.json").read_text())
	assert any(
		row["property"] == "show_title_field_in_link" and row["value"] == "1"
		for row in user["property_setters"]
	)
	assert '"Project": "public/js/project_list.js"' in HOOKS
	custom = json.loads((PROJECT / "custom" / "project.json").read_text())
	said = {
		(row["doc_type"], row.get("field_name"), row["property"]): row["value"]
		for row in custom["property_setters"]
	}
	for field in ("project_type", "expected_start_date", "estimated_costing"):
		assert said[("Project", field, "in_list_view")] == "0"
	assert said[("Project", "customer", "in_list_view")] == "1"
	assert said[("Project", "customer", "in_standard_filter")] == "0"


def test_a_projects_page_puts_its_dates_and_members_on_details():
	custom = json.loads((PROJECT / "custom" / "project.json").read_text())
	said = {
		(row["doc_type"], row.get("field_name"), row["property"]): row["value"]
		for row in custom["property_setters"]
	}
	order = json.loads(said[("Project", None, "field_order")])
	assert (
		order.index("customer")
		< order.index("section_break_18")
		< order.index("users")
		< order.index("costing_tab")
	)
	assert said[("Project", "section_break_18", "collapsible")] == "0"
	assert (
		said[("Project", "users", "label")] == "Members" and said[("Project", "users", "description")] == ""
	)
	assert said[("Project User", "view_attachments", "in_list_view")] == "0"
	# One asks in its own words when the project has none (updates.py).
	assert said[("Project", "subject", "mandatory_depends_on")] == ""
	assert said[("Project", "message", "mandatory_depends_on")] == ""
	assert said[("Project", "total_costing_amount", "label")] == "Time Cost"
	# Hourly is not offered, so it is not where a project starts, and the
	# projects that said it say Weekly (patches/no_hourly_asks.py).
	assert (
		"Hourly" not in said[("Project", "frequency", "options")]
		and said[("Project", "frequency", "default")] == "Weekly"
	)
	assert "onedesk.one_project.patches.no_hourly_asks" in (tree.APP / "patches.txt").read_text()
	# Our fields carry no notes; the README says what they are. An empty note
	# is written out, since frappe's sync leaves a missing one as it was.
	assert all(
		one.get("description") == "" for one in custom["custom_fields"] if one["fieldname"].startswith("one_")
	)


def test_a_bill_lands_on_the_one_project_it_names():
	import re

	space = _load(PROJECT / "intake.py", ("SHORTEST", "pick"), re=re)
	pick = space["pick"]
	projects = [("P1", "Villa Al Barsha"), ("P2", "Villa Windows"), ("P3", "Handrails"), ("P4", "Web")]
	assert pick("Glass panels for villa al barsha, site 4", projects) == "P1"
	assert pick("Frames: Villa Windows, phase 2", projects) == "P2"
	assert pick("Handrails and Villa Windows", projects) is None, "two projects is a person's call"
	assert pick("Web hosting for March", projects) is None, "a short name says too little"
	assert pick("Handrailsteel", projects) is None, "a name counts whole"
	assert pick("", projects) is None
	planning = (tree.APP / "one_intake" / "planning.py").read_text()
	money = (tree.APP / "one_intake" / "money.py").read_text()
	assert 'ctx["project"] = _project_named(reading)' in planning and "intake.named(" in planning
	assert '"project": ctx.get("project")' in money and '{**row, "project": head["project"]}' in money


def test_updates_keep_their_health_and_lines_and_say_when_the_team_is_asked():
	asking = _load(PROJECT / "updates.py", ("asking",), _=lambda text: text)["asking"]
	assert asking({"collect_progress": 0, "frequency": "Daily"}) is None
	assert asking({"collect_progress": 1, "frequency": "Daily"}) == "Asked daily"
	assert asking({"collect_progress": 1, "frequency": "Twice Daily"}) == "Asked twice a day"
	assert (
		asking({"collect_progress": 1, "frequency": "Weekly", "day_to_send": "Monday"})
		== "Asked every Monday"
	)
	import re

	plain = _load(
		PROJECT / "ai.py", ("plain",), re=re, strip_html_tags=lambda html: re.sub(r"<[^>]+>", "", html)
	)["plain"]
	assert plain("Frames are on site.<br>Glass is late.<p>Next: <b>pergola</b></p>") == (
		"Frames are on site.\nGlass is late.\nNext: pergola"
	)
	source = (PROJECT / "updates.py").read_text()
	answer = _body(source, "_answer")
	assert '"one_health": frappe.db.get_value("Project", update.project, "one_health")' in answer
	assert '"one_project_update"' in answer and "after_commit=True" in answer
	custom = json.loads((PROJECT / "custom" / "project_user.json").read_text())["custom_fields"]
	assert [(one["fieldname"], one["read_only"]) for one in custom] == [("one_health", 1)]
	view_py = (PROJECT / "view.py").read_text()
	assert (
		'"update_due": asking.asked(doc.name)' in view_py
		and '"asking": asking.asking(doc.as_dict())' in view_py
	)
	panel = (tree.ROOT / "frontend" / "src" / "project" / "Updates.vue").read_text()
	# Health is set in the head; the line shows it, read-only.
	assert ':colors="HEALTH" :label="__(\'Health\')" readonly' in panel and "setValue" not in panel
	assert 'listen("one_project_update"' in panel and 'listen("one_project_draft"' in panel
	page = (tree.ROOT / "frontend" / "src" / "project" / "ProjectPage.vue").read_text()
	assert 'label: __("Post Update"), onClick: writeUpdate' in page and "desk().project.ask_updates(" in page
	actions = (tree.APP / "public" / "js" / "project_actions.js").read_text()
	assert 'frappe.xcall("frappe.client.save", { doc: { ...doc, ...values } })' in actions
	# OneAI drafts; nothing is posted until the reader posts it.
	ai = (PROJECT / "ai.py").read_text()
	assert '"expects": "draft_update"' in ai and 'proposals.propose("Update", "Project"' in ai
	assert '"onedesk.one_project.ai.draft_update",' in HOOKS
	proposals = (tree.APP / "one_ai" / "proposals.py").read_text()
	update = proposals.split('if entry.kind == "Update":', 1)[1].split("\n\n", 1)[0]
	assert '"one_project_draft"' in update and "insert" not in update and "save" not in update


def test_oneai_reminds_a_customer_and_adds_people_only_on_approval():
	ai = (PROJECT / "ai.py").read_text()
	for tool in ("remind_customer", "add_member", "add_contact"):
		assert f'"onedesk.one_project.ai.{tool}",' in HOOKS
	assert 'proposals.propose(\n\t\t\t"Mail",' in ai
	# Its facts carry the invoices past their date and what is due to each subcontractor.
	assert '"invoices": _invoices(project),' in ai
	for key in ('"to_pay"', '"overdue"', '"late"', '"due"'):
		assert key in ai.split("def _money", 1)[1].split("def ", 1)[0]
	# A mail is opened to send, never sent; a member or contact is added by the Team view's own code.
	proposals = (tree.APP / "one_ai" / "proposals.py").read_text()
	mail = proposals.split('if entry.kind == "Mail":', 1)[1].split("\n\n", 1)[0]
	assert '"email"' in mail and "sendmail" not in mail and "make(" not in mail
	approved = ai.split("def approved", 1)[1].split("\ndef ", 1)[0]
	assert "team.add(" in approved and "contacts.save(" in approved
	setup = (tree.APP / "one" / "ai_setup.py").read_text()
	assert 'if what in ("project", "status", "milestone", "time", "budget", "member", "contact"):' in setup


def test_workload_reads_true_follows_and_is_asked_about():
	report = (PROJECT / "report" / "workload")
	source = (report / "workload.py").read_text()
	# Hours to a tenth through frappe's format, and only the projects the reader may open.
	assert '"precision": 1' in source.split("def hours", 1)[1] and "frappe.format(" in source
	assert 'frappe.get_list("Project"' in source.split("def team", 1)[1].split("def ", 1)[0]
	script = (report / "workload.js").read_text()
	assert 'frappe.realtime.on("list_update"' in script and '"oneproject_workload.week"' in script
	ai = (PROJECT / "ai.py").read_text()
	assert '"report:Workload": [WEEK]' in ai and '"expects": "team_week"' in ai
	assert '"onedesk.one_project.ai.team_week",' in HOOKS


def test_oneai_reads_a_project_as_its_page_does():
	for tool in ("project_facts", "projects_needing_attention"):
		assert f'"onedesk.one_project.ai.{tool}"' in HOOKS
	assert '"onedesk.one_project.ai.SUGGESTIONS"' in HOOKS
	groups = (tree.APP / "one_ai" / "groups.py").read_text()
	tools = groups.split('"projects": {', 1)[1].split("},", 1)[0]
	for tool in ("project_facts", "projects_needing_attention", "draft_update", "remind_customer", "add_member", "add_contact", "project_templates", "draft_template"):
		assert f'"{tool}"' in tools
	assert '"One Project": "projects"' in groups
	readme = (PROJECT / "README.md").read_text().split("## Under the hood", 1)[0]
	for heading in ("## Being told", "## Asking OneAI", "## Who sees a project"):
		assert heading in readme
	legal = (PROJECT / "legal.py").read_text()
	assert 'key="oneproject-asks"' in legal


def test_an_amount_reads_the_way_it_is_written():
	shell = (tree.APP / "public" / "js" / "shell.js").read_text()
	assert (
		"onedesk.shell.ltr = " in shell
		and "\\u200e" in shell
		and "window.format_currency = function" in shell
	)
	band = (tree.APP / "public" / "js" / "band.js").read_text()
	assert "onedesk.shell.ltr(when(value))" in band


def test_every_money_document_names_its_project_once():
	space = _load(PROJECT / "chain.py", ("LINES", "agree"))
	agree, lines = space["agree"], space["LINES"]

	class Doc(dict):
		def __init__(self, doctype, project=None, rows=()):
			super().__init__(project=project, items=[_Line(row) for row in rows])
			self.doctype = doctype

		def __getattr__(self, key):
			return self.get(key)

		def __setattr__(self, key, value):
			if key == "doctype":
				object.__setattr__(self, key, value)
			else:
				self[key] = value

	class _Line(dict):
		def set(self, key, value):
			self[key] = value

	# A line with no project takes the document's.
	doc = Doc("Purchase Order", "P1", [{"project": None}, {"project": "P2"}])
	agree(doc)
	assert [row["project"] for row in doc["items"]] == ["P1", "P2"]
	# A document with none takes its lines' when they agree, and not otherwise.
	doc = Doc("Sales Invoice", None, [{"project": "P1"}, {"project": "P1"}, {"project": None}])
	agree(doc)
	assert doc["project"] == "P1" and doc["items"][2]["project"] == "P1"
	doc = Doc("Sales Invoice", None, [{"project": "P1"}, {"project": "P2"}])
	agree(doc)
	assert doc["project"] is None
	# A request for quotation's lines call it project_name.
	doc = Doc("Request for Quotation", "P1", [{"project_name": None}])
	agree(doc)
	assert doc["items"][0]["project_name"] == "P1"
	for doctype in lines:
		assert (
			f'"{doctype}"' in HOOKS.split("doc_events", 1)[1] and "onedesk.one_project.chain.agree" in HOOKS
		)
	for name in ("request_for_quotation", "material_request"):
		custom = json.loads((PROJECT / "custom" / f"{name}.json").read_text())
		assert [f["fieldname"] for f in custom["custom_fields"]] == ["project"]
	connections = (PROJECT / "tree.py").read_text()
	for doctype in (
		"Quotation",
		"Request for Quotation",
		"Supplier Quotation",
		"Payment Entry",
		"Expense Claim",
	):
		assert f'"{doctype}"' in connections


def test_the_forecast_is_never_under_the_budget_and_counts_open_orders():
	flt = lambda value=0, *args: float(value or 0)  # noqa: E731
	space = _load(PROJECT / "money.py", ("forecast", "unbilled"), flt=flt)
	forecast, unbilled = space["forecast"], space["unbilled"]
	# Spending under budget: the budget is the forecast.
	assert forecast(50_000, 10_000, 5_000, 40_000) == {"cost": 40_000, "margin": 10_000}
	# An order that takes spending past the budget shows the day it's placed.
	assert forecast(50_000, 10_000, 45_000, 40_000) == {"cost": 55_000, "margin": -5_000}
	# What a supplier still has to bill, in the company's currency.
	rows = [
		_Row(amount=1000, billed_amt=400, base_net_amount=3670),
		_Row(amount=500, billed_amt=600, base_net_amount=500),
		_Row(amount=0, billed_amt=0, base_net_amount=0),
	]
	assert round(unbilled(rows), 2) == 2202.0


def test_the_forecast_is_per_cost_type_and_none_without_a_budget():
	flt = lambda value=0, *args: float(value or 0)  # noqa: E731
	forecast = _load(PROJECT / "money.py", ("forecast",), flt=flt)["forecast"]
	# Villa Al Barsha: Cost of Goods Sold 10,000 over with its order; the rest
	# of the budget under. The totals alone would hide it.
	types = [{"budget": 100_000, "spent": 32_000, "committed": 78_000}]
	rest = {"budget": 40_500, "spent": 32_785, "committed": 0}
	assert forecast(375_000, 64_785, 78_000, 140_500) == {"cost": 142_785, "margin": 232_215}
	assert forecast(375_000, 64_785, 78_000, 140_500, types, rest) == {"cost": 150_500, "margin": 224_500}
	# No budget, nothing to forecast against.
	assert forecast(39_000, 0, 0, 0) == {"cost": None, "margin": None}
	vue = (tree.ROOT / "frontend" / "src" / "project" / "Money.vue").read_text()
	assert ".filter((one) => one.value)" in vue and "__('So Far')" in vue


def test_paid_is_read_from_the_invoices_however_they_were_paid():
	flt = lambda value=0, *args: float(value or 0)  # noqa: E731
	paid_share = _load(PROJECT / "money.py", ("paid_share",), flt=flt)["paid_share"]
	# Half of a 1,000 invoice is the project's; 1,050 with tax, 50 still owed.
	invoices = [
		_Row(name="A", base_net_total=1000, base_grand_total=1050, outstanding_amount=50, conversion_rate=1)
	]
	assert paid_share(invoices, {"A": 500}) == 500.0
	money = (PROJECT / "money.py").read_text()
	assert "pe.unallocated_amount > 0" in money and "advance_paid" in money
	# Journal entries on the project's expense accounts are its cost.
	assert '(gl.voucher_type == "Journal Entry")' in money and '(account.root_type == "Expense")' in money
	chain = (PROJECT / "chain.py").read_text()
	assert "def paid_for(" in chain and '"onedesk.one_project.chain.paid_for"' in HOOKS
	assert '"Sales Invoice": "public/js/customer_project.js"' in HOOKS


def test_an_invoice_says_what_it_is_for_and_what_is_owed_now():
	from types import SimpleNamespace

	flt = lambda value=0, *args: float(value or 0)  # noqa: E731
	space = _load(PROJECT / "billing.py", ("for_what",), flt=flt)
	for_what = space["for_what"]
	row = lambda **kw: {
		"is_return": 0,
		"one_progress": 0,
		"one_retainer_month": None,
		"total_billing_hours": 0,
		**kw,
	}  # noqa: E731
	assert for_what(row(is_return=1), []) == {"kind": "credit"}
	assert for_what(row(one_progress=50), []) == {"kind": "progress", "value": 50.0}
	assert for_what(row(one_retainer_month="2026-09-01"), []) == {"kind": "month", "value": "2026-09-01"}
	assert for_what(row(total_billing_hours=9), [{"one_rebills": "PINV-1"}]) == {
		"kind": "time_costs",
		"value": 9.0,
	}
	assert for_what(row(), [{"one_rebills": "PINV-1"}]) == {"kind": "costs"}
	assert for_what(row(), [{"item_name": "Fit-out Works"}, {"item_name": "Glass"}]) == {
		"kind": "items",
		"value": "Fit-out Works",
		"more": 1,
	}
	owed_share = _load(PROJECT / "money.py", ("owed_share",), flt=flt)["owed_share"]
	invoice = SimpleNamespace(name="A", base_net_total=1000, outstanding_amount=500, conversion_rate=1)
	assert owed_share([invoice], {"A": 500}) == 250.0
	billing = (PROJECT / "billing.py").read_text()
	assert "retention.held_on(" in billing and '"retention_due"' in billing
	assert '"payment_term": ["not in", retention.HELD]' in billing
	head = (tree.APP / "one" / "head.py").read_text()
	assert "def offer(doctype: str, name: str, verb: str)" in head
	vue = (tree.ROOT / "frontend" / "src" / "project" / "Invoices.vue").read_text()
	assert '"invoice.record_payment"' in vue and 'emailRecord("Sales Invoice"' in vue
	assert 'followList("Payment Entry"' in vue
	view = (PROJECT / "view.py").read_text()
	assert 'if doc.status != "Completed":\n\t\tfound += _overdue_invoices(view["tree"], user)' in view


def test_subcontracts_are_cards_goods_are_bought_and_bills_are_listed():
	from types import SimpleNamespace as row

	flt = lambda value=0, *args: float(value or 0)  # noqa: E731
	space = _load(PROJECT / "money.py", ("subcontract", "next_due"), flt=flt, LUMP_SUM="Lump Sum")
	# A Lump Sum, or anything not kept in stock, is a package of work.
	assert "LUMP_SUM" in (PROJECT / "money.py").read_text()
	subcontract = space["subcontract"]
	stock = {"Handrail Bracket"}
	brackets = [row(uom="Nos", item_code="Handrail Bracket")]
	glazing = [row(uom="Nos", item_code="Glazing Package")]
	assert subcontract(brackets, stock) is False and subcontract(glazing, stock) is True
	next_due = space["next_due"]
	term = lambda due, amount, held=False: {"due_date": due, "amount": amount, "held": held}  # noqa: E731
	# Paid the first part, the second still coming; retention never counts.
	terms = [term("2026-09-01", 1000), term("2026-11-01", 1000), term("2027-09-01", 200, True)]
	assert next_due(terms, 1200, "2026-10-06") == "2026-11-01"
	assert next_due(terms, 200, "2026-10-06") is None
	billing = (PROJECT / "billing.py").read_text()
	assert "\ndef bills(" in billing and 'said = _listed(project, "Purchase Invoice")' in billing
	vue = (tree.ROOT / "frontend" / "src" / "project" / "Suppliers.vue").read_text()
	assert (
		"orders.value.filter((one) => one.subcontract)" in vue and "onedesk.one_project.billing.bills" in vue
	)
	assert "project.pay_advance(one.order)" in vue and '"invoice.record_payment"' in vue
	actions = (tree.APP / "public" / "js" / "project_actions.js").read_text()
	assert "onedesk.project.pay_advance = (order)" in actions and "get_payment_entry" in actions
	buying = (PROJECT / "buying.py").read_text()
	assert "money.kinds(list(names))" in buying


def test_buying_lists_what_is_bought_for_the_project():
	shown = _load(PROJECT / "buying.py", ("shown",), _=lambda text: text)["shown"]
	assert shown([]) is None and shown(["Glass"]) == "Glass"
	assert shown(["Glass", "Frames", None]) == "{0} +{1}".format("Glass", 1)
	buying = (PROJECT / "buying.py").read_text()
	for doctype in ("Material Request", "Request for Quotation", "Supplier Quotation", "Purchase Receipt"):
		assert f'"{doctype}"' in buying
	vue = (tree.ROOT / "frontend" / "src" / "project" / "Suppliers.vue").read_text()
	assert "onedesk.one_project.buying.papers" in vue and "__('Request Prices')" in vue


def test_costing_shows_both_sides_and_opens_what_is_behind_each_figure():
	money = (PROJECT / "money.py").read_text()
	for label in ('_("Quoted")', '_("Delivered")', '_("Invoiced")', '_("Received")', '_("Stock Used")'):
		assert label in money
	# Every figure is submitted documents, read for the reader only if they may.
	assert '"docstatus": 1' in money and "_sees(" in money
	# A submit or cancel anywhere redraws the open project and those above it.
	assert HOOKS.count('"onedesk.one_project.money.moved"') == 2
	assert "tree.above(" in money and "after_commit=True" in money
	layout = json.loads((PROJECT / "custom" / "project.json").read_text())
	fields = {f["fieldname"]: f for f in layout["custom_fields"]}
	# The money is the page's Money and Suppliers views; the form's HTML
	# sections that drew it are gone, from the layout and from every site.
	gone = {"one_customer", "one_cost", "one_forecast", "one_suppliers", "one_budget"}
	assert not gone & set(fields)
	patch = (PROJECT / "patches" / "costing_on_the_page.py").read_text()
	assert all(f'"{name}"' in patch for name in gone)
	assert "onedesk.one_project.patches.costing_on_the_page" in (tree.APP / "patches.txt").read_text()
	hidden = {
		p["field_name"] for p in layout["property_setters"] if p["property"] == "hidden" and p["value"] == "1"
	}
	assert {"total_purchase_cost", "gross_margin", "total_billed_amount"} <= hidden
	view = (PROJECT / "view.py").read_text()
	assert '"money": cash' in view
	island = tree.ROOT / "frontend" / "src" / "project"
	money_view = (island / "Money.vue").read_text()
	assert "said.money" in money_view and all(
		name in money_view for name in ('__("Forecast Margin")', "__('Customer')", "__('Cost')")
	)
	assert "onedesk().progress.ask" in (island / "Suppliers.vue").read_text()
	page = "".join(
		(tree.APP / "public" / "js" / name).read_text() for name in ("project.js", "project_actions.js")
	)
	assert '"one_project_money"' in page
	heads = (PROJECT / "heads.py").read_text()
	assert '"project.forecast": forecast' in heads and '_lt("Forecast Margin")' in heads


def test_progress_bills_the_share_done_and_holds_retention_on_the_work():
	flt = lambda value=0, *args: round(float(value or 0), args[0]) if args else float(value or 0)  # noqa: E731
	space = _load(PROJECT / "progress.py", ("to_bill", "billed_share", "split"), flt=flt)
	to_bill, billed_share, split = space["to_bill"], space["billed_share"], space["split"]
	still_held = _load(PROJECT / "retention.py", ("still_held",), flt=flt)["still_held"]
	# 40% of one Lump Sum, nothing billed: 0.4. At 70% with 0.4 billed: 0.3.
	assert to_bill(1, 0, 40) == 0.4 and round(to_bill(1, 0.4, 70), 6) == 0.3
	# Never a credit for going backwards.
	assert to_bill(1, 0.4, 30) == 0
	assert billed_share([_Row(amount=80000, billed_amt=32000), _Row(amount=20000, billed_amt=0)]) == 32.0
	# Retention is the share of the work billed, whatever advance is set off:
	# 32,000 billed, 8,000 advance, 10% held.
	assert split(24000, 32000, 10) == (20800, 3200)
	# Retention is paid last: what's held is never more than what's owed.
	assert still_held([("2027-03-31", 3200)], 24000) == [("2027-03-31", 3200)]
	assert still_held([("2027-03-31", 3200)], 1000) == [("2027-03-31", 1000)]
	assert still_held([("2027-03-31", 3200)], 0) == []


def test_subcontracts_are_billed_through_erpnexts_own_invoice():
	progress = (PROJECT / "progress.py").read_text()
	assert 'LUMP_SUM = "Lump Sum"' in progress and '"must_be_whole_number": 0' in progress
	assert HOOKS.count('"onedesk.one_project.progress.settle"') == 2
	assert '"onedesk.one_project.progress.release"' in HOOKS
	assert '"onedesk.one_project.progress.retained"' in HOOKS
	order = json.loads((PROJECT / "custom" / "purchase_order.json").read_text())
	fields = {f["fieldname"]: f for f in order["custom_fields"]}
	assert fields["one_retention_due"]["allow_on_submit"] == 1
	assert fields["one_retention_due"]["mandatory_depends_on"] == "one_retention"
	page = (tree.APP / "public" / "js" / "progress.js").read_text()
	assert "frappe.model.open_mapped_doc" in page and '__("Bill Progress")' in page
	assert '"Purchase Order": "public/js/progress.js"' in HOOKS
	money = (PROJECT / "money.py").read_text()
	assert "def _suppliers(" in money and "retention.held_on(" in money


def test_the_customers_contract_is_billed_the_same_way():
	assert '"Sales Order": ["public/js/progress.js", "public/js/customer_project.js"]' in HOOKS
	page = (tree.APP / "public" / "js" / "progress.js").read_text()
	assert '["Purchase Order", "Sales Order"]' in page
	for name in ("sales_order.json", "purchase_order.json"):
		fields = {
			f["fieldname"]: f for f in json.loads((PROJECT / "custom" / name).read_text())["custom_fields"]
		}
		assert fields["one_retention"]["allow_on_submit"] == 1
		assert fields["one_retention_due"]["allow_on_submit"] == 1
	# A new date moves the retention on both sides' invoices, and both sides'
	# invoices hold the share of the work.
	assert HOOKS.count('"onedesk.one_project.progress.release"') == 2
	assert HOOKS.count('"onedesk.one_project.progress.retained"') == 2
	money = (PROJECT / "money.py").read_text()
	assert '_("Retention Held")' in money and "def _retained(" in money


def test_a_cost_type_is_erpnexts_own_budget_on_the_project():
	flt = lambda value=0, *args: float(value or 0)  # noqa: E731
	left = _load(PROJECT / "budget.py", ("left",), flt=flt)["left"]
	assert left(100000, 48000, 32000) == 20000 and left(100000, 78000, 32000) == -10000
	budget = (PROJECT / "budget.py").read_text()
	# ERPNext checks it; orders and spending together, not only each alone.
	assert '"budget_against": "Project"' in budget and '"applicable_on_cumulative_expense": 1' in budget
	money_view = (tree.ROOT / "frontend" / "src" / "project" / "Money.vue").read_text()
	assert "cash.value.cost_types" in money_view and "project.cost_type(" in money_view
	page = "".join(
		(tree.APP / "public" / "js" / name).read_text() for name in ("project.js", "project_actions.js")
	)
	assert "onedesk.one_project.budget.set_budget" in page and '__("Add Cost Type")' in page


def test_milestones_say_where_and_when_and_may_be_billed_on_completion():
	from types import SimpleNamespace

	above = _load(PROJECT / "tree.py", ("above",))["above"]
	space = _load(
		PROJECT / "milestones.py",
		("pick", "where", "billable"),
		tree=SimpleNamespace(above=above),
		flt=float,
		SHOWN=8,
		DONE_SHOWN=2,
	)
	pick, where, billable = space["pick"], space["where"], space["billable"]
	rows = [
		{"subject": f"Done {n}", "done": True, "due": f"2026-09-0{n}", "share": 0} for n in range(1, 5)
	] + [
		{"subject": "Undated", "done": False, "due": None, "share": 0},
		{"subject": "Handover", "done": False, "due": "2026-10-13", "share": 0},
		{"subject": "Frames", "done": False, "due": "2026-09-27", "share": 0},
	]
	# The last two done, then the ones to come soonest first, undated last.
	assert [one["subject"] for one in pick(rows)] == ["Done 3", "Done 4", "Frames", "Handover", "Undated"]
	of = {"GLASS": "RAILS", "RAILS": "VILLA"}
	titles = {"GLASS": "Glass for handrails", "RAILS": "Handrails", "VILLA": "Villa Al Barsha"}
	assert where("GLASS", "VILLA", of, titles) == "Handrails › Glass for handrails"
	assert where("VILLA", "VILLA", of, titles) is None
	# Billing on milestones is only for a project whose milestones carry a share.
	assert billable(rows) is None
	shared = [
		{"subject": "Frames", "done": True, "share": 20},
		{"subject": "Handover", "done": False, "share": 30},
	]
	assert billable(shared) == {"share": 20, "names": ["Frames"]}
	lenient = lambda value=0, *args: float(value or 0)  # noqa: E731
	work = _load(PROJECT / "view.py", ("work_and_billing",), _=lambda text: text, flt=lenient)[
		"work_and_billing"
	]
	cash = {"contract": 375000, "invoiced": 60000, "customer": [{"label": "Paid", "value": 57000}]}
	assert work(29, cash, 0, None, billable(shared))["unbilled"] == 15000
	assert work(29, cash, 0)["unbilled"] == round(375000 * 0.29 - 60000)
	custom = json.loads((PROJECT / "custom" / "task.json").read_text())["custom_fields"]
	assert [(one["fieldname"], one["depends_on"]) for one in custom] == [("one_bill_share", "is_milestone")]
	assert '"onedesk.one_project.milestones.reached",' in HOOKS
	assert "Milestone Done" in tree.notifications()
	page = (tree.APP / "public" / "js" / "project_actions.js").read_text()
	assert "onedesk.project.add_milestone = (projects, billed, done)" in page and "is_milestone: 1" in page
	panel = (tree.ROOT / "frontend" / "src" / "project" / "TaskPanel.vue").read_text()
	assert "'is_milestone', v ? 1 : 0" in panel


def test_subcontracts_say_what_where_how_far_and_what_to_pay():
	from types import SimpleNamespace as row

	bought = _load(PROJECT / "money.py", ("bought",), _=lambda text: text)["bought"]
	assert bought([row(item_name="Glazing Package")]) == "Glazing Package"
	assert bought([row(item_name="Glazing Package"), row(item_name="Fixings"), row(item_name="Sealant")]) == (
		"Glazing Package +2"
	)
	assert bought([]) is None
	money_py = (PROJECT / "money.py").read_text()
	suppliers = money_py[money_py.index("def _suppliers(") : money_py.index("def bought(")]
	assert '"to_pay": max(0.0, owing - retained)' in suppliers and '"for": bought(own)' in suppliers
	view_py = (PROJECT / "view.py").read_text()
	subs = view_py[view_py.index("def _subcontracts(") : view_py.index("def late(")]
	assert "milestones.where(" in subs and 'done[project] = view["share"]' in subs
	assert '"subcontracts_count": len(cash["suppliers"])' not in view_py  # set on said, below
	# Goods bought for the job are on Buying; the Overview counts the packages.
	assert 'said["subcontracts_count"] = len(packages)' in view_py
	bills = view_py[view_py.index("def _overdue_bills(") : view_py.index("def _late_route(")]
	# By the payment schedule, retention not yet due left out.
	assert '_("Pay {0}")' in bills and '_("Chase {0}")' in bills and '"Purchase Invoice", projects' in bills
	flt = lambda value=0, *args: float(value or 0)  # noqa: E731
	past_due = _load(PROJECT / "money.py", ("past_due",), flt=flt)["past_due"]
	term = lambda due, amount, held=False: {"due_date": due, "amount": amount, "held": held}  # noqa: E731
	# The villa's handrails: 57,000 paid of 60,000, the 3,000 retention due
	# next year. Nothing is past due, whatever the per-term outstanding says.
	handrails = [term("2026-09-30", 57000), term("2027-09-30", 3000, True)]
	assert past_due(handrails, 3000, "2026-10-06") is None
	# Unpaid and past its date: all of it, since the term's day.
	assert past_due([term("2026-09-19", 7500)], 7500, "2026-10-06") == {
		"due": 7500,
		"since": "2026-09-19",
		"held": False,
	}
	# Paid but for the retention, now due: retention only.
	assert past_due(handrails, 3000, "2027-10-01") == {"due": 3000, "since": "2027-09-30", "held": True}
	assert 'found += _overdue_bills(view["tree"], user)' in view_py
	late = _load(PROJECT / "view.py", ("late",), _=lambda text: text)["late"]
	assert late(1) == "1 day late" and late(3) == "3 days late"
	overview = (tree.ROOT / "frontend" / "src" / "project" / "Overview.vue").read_text()
	assert "billed(one) > one.done" in overview and '__("{0} to pay"' in overview
	assert ':aside="view.subcontracts_count"' in overview and "$emit('view', 'suppliers')" in overview


def test_the_overview_budget_adds_up_to_numbers():
	flt = lambda value=0, *args: float(value or 0)  # noqa: E731
	space = _load(PROJECT / "budget.py", ("left", "other"), flt=flt)
	other = space["other"]
	# Villa Al Barsha: Cost of Goods Sold budgeted on the project itself; a
	# sub-project's bill and the team's time are outside it.
	lines = [{"budget": 100000, "spent": 32000, "committed": 78000}]
	rest = other(lines, 140500, 63210, 78000)
	assert rest == {"budget": 40500, "spent": 31210, "committed": 0, "left": 9290}
	assert sum(one["budget"] for one in [*lines, rest]) == 140500
	assert other(lines, 100000, 32000, 78000) is None
	assert other(lines, 90000, 30000, 70000) is None
	budget = (PROJECT / "budget.py").read_text()
	# A cost type counts only the projects that budget for it, as ERPNext checks.
	assert (
		"committed.get((one.project, one.account), 0.0)" in budget
		and "spent.get((one.project, one.account), 0.0)" in budget
	)
	view_py = (PROJECT / "view.py").read_text()
	assert 'said["budget"] = _budget_lines(cash)' in view_py
	assert (
		'budget.other(types, flt(kept["estimated_costing"]), spent, open_orders)'
		in (PROJECT / "money.py").read_text()
	)
	overview = (tree.ROOT / "frontend" / "src" / "project" / "Overview.vue").read_text()
	assert "__(\"No cost types\")" in overview and "$emit('view', 'money')" in overview
	assert ":y=\"['spent', 'committed', 'left']\"" in overview and "left: Math.max(one.left || 0, 0)" in overview


def test_the_money_is_told_and_read():
	kinds = tree.notifications()
	assert "Over Budget" in kinds and "Progress Bill Drafted" in kinds
	told = _body((PROJECT / "tell.py").read_text(), "over_budget")
	# Once for each budget: a revised budget can tell again.
	assert 'dedupe_on=["document_type", "document_name"]' in told and '("Budget", one["budget_name"])' in told
	assert "budget.over(project)" in (PROJECT / "money.py").read_text()
	assert HOOKS.count('"onedesk.one_project.progress.drafted"') == 2
	for name in ("purchase_invoice.json", "sales_invoice.json"):
		field = json.loads((PROJECT / "custom" / name).read_text())["custom_fields"][0]
		assert field["fieldname"] == "one_progress" and field["read_only"] == 1 and field["no_copy"] == 1
	ai = (PROJECT / "ai.py").read_text()
	assert '"money": _money(project)' in ai and '_lt("Where is the money going?")' in ai
	legal = (PROJECT / "legal.py").read_text()
	assert "its money with the customer and with suppliers" in legal


def test_a_project_has_a_kind_and_new_project_asks_by_kind():
	space = _load(PROJECT / "kinds.py", ("FIXED", "TIME", "RETAINER", "INTERNAL", "KINDS", "guess"))
	guess = space["guess"]
	assert guess(True, True, "C") == "Fixed Price"
	assert (
		guess(False, True, None) == "Time and Materials" and guess(False, False, "C") == "Time and Materials"
	)
	assert guess(False, False, None) == "Internal"
	kinds = (PROJECT / "kinds.py").read_text()
	assert 'frappe.has_permission("Project", "create", throw=True)' in kinds
	assert (
		'"onedesk.one_project.kinds.fill"' in HOOKS and HOOKS.count('"onedesk.one_project.kinds.settle"') == 2
	)
	assert '"/assets/onedesk/js/project_new.js"' in HOOKS
	assert "onedesk.one_project.patches.kinds" in (tree.APP / "patches.txt").read_text()
	layout = json.loads((PROJECT / "custom" / "project.json").read_text())
	kind = next(f for f in layout["custom_fields"] if f["fieldname"] == "one_kind")
	assert kind["options"].split("\n")[1:] == list(space["KINDS"])
	page = (tree.APP / "public" / "js" / "project_new.js").read_text()
	assert "frappe.ui.form.ProjectQuickEntryForm" in page and "onedesk.one_project.kinds.make" in page
	# Three steps on frappe's Slides: the kind, its details, the plan.
	assert "new frappe.ui.Slides(" in page and "extends frappe.ui.Slide" in page
	for step in ('name: "kind"', 'name: "details"', 'name: "plan"'):
		assert step in page
	# Each step is a dialog's form from the start, so a field marks itself
	# missing only once the primary button is pressed.
	assert "is_dialog: true," in page and "fulfil()" in page
	# A retainer runs month to month: Plan asks when it starts, not when it ends.
	assert 'depends_on: kind(["Fixed Price", "Time and Materials", "Internal"]),' in page
	assert 'if (this.kind === "Retainer") delete values.ends;' in page
	# The cards are drawn with frappe's tokens of today: --border-radius-* are gone,
	# and a corner written with one is square.
	for sheet in (tree.APP / "public" / "css").glob("*.css"):
		assert "var(--border-radius" not in sheet.read_text(), sheet.name
	# The dialog's fieldnames are its own: a quick entry takes the doctype's
	# label and hidden flag for a field of the same name.
	for taken in ('fieldname: "project_name"', 'fieldname: "one_kind"', 'fieldname: "customer"'):
		assert taken not in page


def test_a_project_opens_on_its_own_page():
	space = _load(PROJECT / "view.py", ("share",), flt=float)
	share = space["share"]
	assert share(30, 120) == 25 and share(5, 0) == 0 and share(300, 100) == 100 and share(-5, 10) == 0
	page = json.loads((PROJECT / "page" / "project_view" / "project_view.json").read_text())
	assert page["name"] == "project-view" and page["module"] == "One Project"
	view = (PROJECT / "view.py").read_text()
	assert 'frappe.has_permission("Project", "read", doc=project, throw=True)' in view
	# Every kind has its cards; Money and Suppliers show for whoever may see
	# them, Suppliers where a Fixed Price project expects subcontracts.
	assert (
		"def views(kind: str, cash: dict, customer" in view
		and '"views": views(kind, cash, doc.customer, doc.name)' in view
	)
	assert 'frappe.has_permission("Purchase Order", "read")' in view
	script = (tree.ROOT / "frontend" / "src" / "project" / "ProjectPage.vue").read_text()
	assert '"onedesk.one_project.view.said"' in script
	# The page follows the record as a form does, through the kit's bridge to desk.
	for follows in ('follow("Project"', 'listen("one_project_money"'):
		assert follows in script
	# /desk/project/<name> is the page; ?edit=1 and a new project are the form.
	route = (tree.APP / "public" / "js" / "project_new.js").read_text()
	assert '{ Project: "project-view", "Project Template": "project-template-view", Task: "task-view", Item: "item-view" }' in route
	assert "return [page, name];" in route and 'has("edit")' in route and 'name.startsWith("new-")' in route
	# The page edits every field itself; the form stays only at ?edit=1.
	assert "?edit=1" not in script
	# What the page and the form both do is one file, loaded by both.
	assert '"Project": ["public/js/project_actions.js", "public/js/project.js"]' in HOOKS
	loader = (PROJECT / "page" / "project_view" / "project_view.js").read_text()
	assert "/assets/onedesk/js/project_actions.js" in loader and 'island: "onedesk.project"' in loader


def test_time_invoices_and_team_are_views_of_erpnexts_own_records():
	from datetime import date, datetime, time as clock

	space = _load(PROJECT / "hours.py", ("state", "after", "DAY_STARTS"), time=clock, datetime=datetime)
	state = space["state"]
	assert state(0, True, None) == "Draft" and state(1, True, "SINV-1") == "Invoiced"
	assert state(1, True, None) == "To Invoice" and state(1, False, None) == "Not Billable"
	# A hand-logged entry starts after the day's last one, so none overlap.
	space.update(
		getdate=lambda value: value.date() if isinstance(value, datetime) else value,
		get_datetime=lambda value: value,
	)
	after = space["after"]
	day = date(2026, 10, 5)
	empty = _Row(time_logs=[])
	assert after(empty, day) == datetime(2026, 10, 5, 9, 0)
	busy = _Row(
		time_logs=[_Row(to_time=datetime(2026, 10, 5, 12, 30)), _Row(to_time=datetime(2026, 10, 4, 18, 0))]
	)
	assert after(busy, day) == datetime(2026, 10, 5, 12, 30)
	# Or after one on another of the person's timesheets, submitted ones too.
	assert after(busy, day, [datetime(2026, 10, 5, 15, 0)]) == datetime(2026, 10, 5, 15, 0)

	hours = (PROJECT / "hours.py").read_text()
	team = (PROJECT / "team.py").read_text()
	billing = (PROJECT / "billing.py").read_text()
	# Each reads as the reader reads the records behind it, and changes only
	# what the reader may change.
	for source in (hours, team, billing):
		assert 'frappe.has_permission("Project", "read"' in source
	assert (
		'parent_doctype="Timesheet"' in hours
		and 'frappe.has_permission("Timesheet", "create", throw=True)' in hours
	)
	view = (PROJECT / "view.py").read_text()
	for shown in ('shown.append("time")', 'shown.append("invoices")', 'shown.append("team")'):
		assert shown in view
	island = tree.ROOT / "frontend" / "src" / "project"
	assert '"onedesk.one_project.hours.entries"' in (island / "Time.vue").read_text()
	assert '"onedesk.one_project.billing.invoices"' in (island / "Invoices.vue").read_text()
	assert '"onedesk.one_project.team.team"' in (island / "Team.vue").read_text()
	actions = (tree.APP / "public" / "js" / "project_actions.js").read_text()
	assert "onedesk.project.log_time" in actions and "onedesk.project.add_member" in actions


def test_a_retainer_is_invoiced_by_the_month():
	from datetime import date

	def add_months(day, n):
		month = day.month - 1 + n
		return date(day.year + month // 12, month % 12 + 1, 1)

	space = _load(
		PROJECT / "retainer.py",
		("over", "rate", "month_list", "SHOWN"),
		flt=lambda value, *a: float(value or 0),
		getdate=lambda value: date.fromisoformat(value) if isinstance(value, str) else value,
		get_first_day=lambda day: day.replace(day=1),
		add_months=add_months,
	)
	over, rate, month_list = space["over"], space["rate"], space["month_list"]
	assert over(46, 40) == 6 and over(32, 40) == 0 and over(10, 0) == 0
	assert (
		rate([{"billing_hours": 4, "billing_amount": 1200}, {"billing_hours": 2, "billing_amount": 600}])
		== 300
	)
	assert rate([]) == 0
	assert month_list("2026-08-12", "2026-10-04") == [date(2026, 10, 1), date(2026, 9, 1), date(2026, 8, 1)]
	assert len(month_list("2024-01-01", "2026-10-04")) == space["SHOWN"]

	source = (PROJECT / "retainer.py").read_text()
	assert 'frappe.has_permission("Sales Invoice", "create", throw=True)' in source
	assert 'parent_doctype="Timesheet"' in source and "ignore_permissions" not in source
	billing = (PROJECT / "billing.py").read_text()
	assert 'source.one_kind == "Retainer"' in billing
	custom = json.loads((PROJECT / "custom" / "sales_invoice.json").read_text())
	assert "one_retainer_month" in {one["fieldname"] for one in custom["custom_fields"]}
	view = (PROJECT / "view.py").read_text()
	assert 'said["months"] = retainer.months(doc.name)' in view
	# A month waiting for its invoice has Invoice Month in Months, the one
	# place it shows.
	overview = (tree.ROOT / "frontend" / "src" / "project" / "Overview.vue").read_text()
	assert "onedesk().project.invoice_month(frm(), month)" in overview
	page = (tree.ROOT / "frontend" / "src" / "project" / "ProjectPage.vue").read_text()
	assert "desk().project.invoice_month(frm())" in page
	actions = (tree.APP / "public" / "js" / "project_actions.js").read_text()
	assert (
		"onedesk.project.invoice_month" in actions
		and '"onedesk.one_project.retainer.invoice_month"' in actions
	)


def test_the_project_page_tells_oneai_where_it_is():
	# The panel names the open view as the page's section (oneai.js where()),
	# and is told when the view changes without a route change (kit setQuery).
	oneai = (tree.APP / "public" / "js" / "oneai.js").read_text()
	assert "params.section || params.view" in oneai
	kit = (tree.ROOT / "frontend" / "src" / "kit" / "desk.js").read_text()
	assert "oneai.panel.moved(oneai.where())" in kit
	assert '"onedesk.one_project.ai.page"' in HOOKS
	ai = (PROJECT / "ai.py").read_text()
	assert 'PAGE = "project-view"' in ai and 'frappe.has_permission("Project", "read", doc=name)' in ai
	# A suggestion for one kind of project is checked on the record the page
	# is open on, and only one the reader may read.
	suggest = (tree.APP / "one_ai" / "suggest.py").read_text()
	assert 'page.get("name") or page.get("record")' in suggest
	assert 'frappe.has_permission(doctype, "read", doc=name)' in suggest
	# Every view has its own, and the Tasks layouts share the Tasks view's.
	for view in ("", "/tasks", "/board", "/timeline", "/time", "/money", "/invoices", "/suppliers", "/team"):
		assert f"page:{{PAGE}}{view}" in ai or (view in ("/board", "/timeline") and "LAYOUTS" in ai)
	assert "_here(UPDATE, kinds=BILLED)" in ai and "_here(ALLOWANCE, kinds=(kinds.RETAINER,))" in ai
	for part in ('"time": _time(', '"team": _team(', '"months": _months('):
		assert part in ai


def test_a_retainer_tells_whoever_runs_it():
	assert {"Retainer Month to Invoice", "Retainer Hours Used"} <= set(tree.notifications())
	assert '"onedesk.one_project.tell.retainer_months"' in HOOKS
	assert '"on_submit": ["onedesk.one_project.tell.hours_used", "onedesk.one_project.tell.time_over"]' in HOOKS
	readme = (PROJECT / "README.md").read_text().split("## Under the hood", 1)[0]
	assert "**Retainer Month to Invoice**" in readme and "**Retainer Hours Used**" in readme


def test_the_project_page_fits_a_phone():
	src = tree.ROOT / "frontend" / "src" / "project"
	# frappe-ui's own way: a list's columns by breakpoint, minor cells hidden.
	for name in ("Time", "Team", "Invoices", "Money", "Months"):
		vue = (src / f"{name}.vue").read_text()
		assert ":columns=" in vue and "base:" in vue and "max-md:hidden" in vue, name
	page = (src / "ProjectPage.vue").read_text()
	assert '<ViewTabs v-model="tab" :views="VIEWS"' in page, "the views fit a phone, the row scrolling"
	mount = (tree.ROOT / "frontend" / "src" / "kit" / "mount.js").read_text()
	assert 'setConfig("systemTimezone", zone.system)' in mount


def test_the_rail_is_projects_workload_time_and_templates_and_is_open_on_them():
	rail = json.loads((PROJECT / "sidebar" / "oneproject" / "oneproject.json").read_text())
	said = [(item["label"], item.get("link_to")) for item in rail["items"]]
	assert said == [
		("Projects", "Project"),
		("Workload", "Workload"),
		("Timesheet", "Timesheet"),
		("Templates", "Project Template"),
		# ERPNext's and HRMS's project reports, under the names the rail gives
		# them (one/titles.py), with Company filled and hidden (reports.js).
		("Reports", None),
		("Project Summary", "Project Summary"),
		("Profit on Billed Hours", "Project Profitability"),
		("Billable Hours", "Timesheet Billing Summary"),
		("Hours by Day", "Daily Timesheet Summary"),
		("Stock by Project", "Project wise Stock Tracking"),
	]
	# The panel is open on the four and shut on a record; the breadcrumb
	# switches between its rows, as in every module (public/js/crumb_switch.js,
	# tests/guards/test_record_page.py).
	places = (tree.APP / "public" / "js" / "project_places.js").read_text()
	assert "TabButtons" not in places and "hide_sidebar" not in places
	assert '"/assets/onedesk/js/project_places.js"' in HOOKS
	template_js = (PROJECT / "page" / "project_template_view" / "project_template_view.js").read_text()
	assert "hide_sidebar: !frappe.is_mobile()" in template_js and 'record: "Project Template"' in template_js
	# Setup is in the Projects list's menu.
	menu = (tree.APP / "public" / "js" / "project_list.js").read_text()
	assert '__("Rates")' in menu and '__("Project Templates")' not in menu
	# A project's name in its breadcrumb switches to the others: the reader's
	# open projects before anything is typed, any project as it is.
	view_js = (PROJECT / "page" / "project_view" / "project_view.js").read_text()
	assert "hide_sidebar: !frappe.is_mobile()" in view_js and 'record: "Project"' in view_js
	assert "onedesk.crumbs.suggest.Project = onedesk.project.picker" in places
	shell = (tree.APP / "public" / "js" / "shell.js").read_text()
	assert "one_record: true" in shell and "one_menu: menu" in shell
	switch = (tree.APP / "public" / "js" / "crumb_switch.js").read_text()
	assert "frappe.desk.search.search_link" in switch and "new frappe.ui.Popover({" in switch
	view_py = (PROJECT / "view.py").read_text()
	picker = view_py[view_py.index("def picker(") : view_py.index("PICKED = ")]
	assert 'frappe.has_permission("Project", "read", doc=project, throw=True)' in picker
	assert '"project_type": ["!=", "Employee Boarding"]' in picker and "frappe.get_list(" in picker
	# A task with an empty assignment is assigned to nobody.
	assert 'frappe.parse_json(task._assign or "[]")' in (PROJECT / "report" / "workload" / "workload.py").read_text()
	# Rates: an activity's rates for a person are its connection, and lead back to it.
	assert '"Activity Type": ["onedesk.one_project.rates.dashboard"]' in HOOKS
	assert '"onedesk.one_project.rates.homes"' in HOOKS
	rates = (PROJECT / "rates.py").read_text()
	assert 'data["fieldname"] = "activity_type"' in rates and '"Activity Cost"' in rates
	# Projects Settings is in the Projects list's menu, for whoever may change it.
	listing = (tree.APP / "public" / "js" / "project_list.js").read_text()
	assert 'frappe.model.can_write("Projects Settings")' in listing
	assert '"route": "/desk/project/view/tree"' in (PROJECT / "heads.py").read_text()


def test_the_projects_list_names_where_each_stands_and_what_it_is_under():
	listing = (tree.APP / "public" / "js" / "project_list.js").read_text()
	# One pill: an open project's health, a finished one's status.
	assert 'doc.status === "Open" && doc.one_health' in listing
	assert '"On Track": "green", "At Risk": "orange", "Off Track": "red"' in listing
	# A sub-project reads by its own name, its parent after it and quieter.
	assert "project_name(value, df, doc)" in listing and "`${value} · ${up}`" in listing
	# How far along is a figure beside frappe's bar, through frappe.format.
	assert "percent_complete(value)" in listing and 'fieldtype: "Percent"' in listing
	assert '"one_health",' in listing and '"one_parent"' in listing
	custom = json.loads((PROJECT / "custom" / "project.json").read_text())
	setters = {(one.get("field_name"), one["property"]): one["value"] for one in custom["property_setters"]}
	assert setters[("customer", "in_standard_filter")] == "0"
	assert setters[("expected_end_date", "label")] == "Due Date"
	assert setters[("project_name", "width")] == "260"
	assert setters[(None, "sort_field")] == "modified" and setters[(None, "sort_order")] == "DESC"
	fields = {one["fieldname"]: one for one in custom["custom_fields"]}
	assert not fields["one_health"]["in_list_view"] and fields["one_health"]["in_standard_filter"]
	# The Tree's button is the list's.
	assert '__("Add {0}", [__("Project")])' in (tree.APP / "public" / "js" / "project_tree.js").read_text()
	# On a phone the list is as wide as the screen, as every list is.
	css = (tree.APP / "public" / "css" / "desk.css").read_text()
	assert '[data-page-route^="List/"] .frappe-list .result .list-row-container' in css


def test_the_other_views_of_projects_are_oneprojects_own():
	listing = (tree.APP / "public" / "js" / "project_list.js").read_text()
	# Every view leaves out the HR checklists without a filter anybody set,
	# and the address carries only what somebody chose.
	assert "List.prototype.get_filters_for_args = function" in listing
	assert 'params.delete("project_type")' in listing
	kanban = (tree.APP / "public" / "js" / "project_kanban.js").read_text()
	assert "Page.prototype.get_effective_filters = function" in kanban
	assert '"Project": "public/js/project_kanban.js"' in HOOKS
	# An internal project's card does not ask for a customer.
	assert 'card.one_kind === "Internal"' in kanban
	# Report: the ID column is the Project column reading the name, Project
	# Name is not repeated and Cover is not a column.
	assert '["project_name", "one_cover"].includes(name)' in listing
	assert 'built.name = built.content = __("Project")' in listing
	assert 'frappe.utils.add_link_title("Project", row.name, row.project_name)' in listing
	# Dashboard: OneProject's cards and charts, not ERPNext's two.
	assert 'module: "One Project"' in listing
	cards = {
		json.loads(path.read_text())["label"]: json.loads(path.read_text())
		for path in (PROJECT / "number_card").glob("*/*.json")
	}
	assert set(cards) == {"Open Projects", "At Risk or Off Track", "Past Due"}
	for card in cards.values():
		assert card["is_standard"] and card["is_public"] and card["document_type"] == "Project"
		assert ["Project", "project_type", "!=", "Employee Boarding", False] in json.loads(
			card["filters_json"]
		)
	charts = {
		path.stem: json.loads(path.read_text()) for path in (PROJECT / "dashboard_chart").glob("*/*.json")
	}
	assert set(charts) == {
		"projects_by_health",
		"projects_by_kind",
		"projects_by_manager",
		"projects_by_customer",
		"projects_started",
	}
	for chart in charts.values():
		assert chart["module"] == "One Project" and chart["document_type"] == "Project"
		assert chart["chart_type"] in ("Count", "Group By")
	assert {name: chart["type"] for name, chart in charts.items()} == {
		"projects_by_health": "Donut",
		"projects_by_kind": "Pie",
		"projects_by_manager": "Bar",
		"projects_by_customer": "Bar",
		"projects_started": "Line",
	}
	# A slice's colour follows what it is: health in the pill's colours.
	health = json.loads(charts["projects_by_health"]["custom_options"])["one_colors"]
	assert list(health) == ["On Track", "At Risk", "Off Track"]
	kinds = json.loads(charts["projects_by_kind"]["custom_options"])["one_colors"]
	assert set(kinds) == {"Fixed Price", "Time and Materials", "Retainer", "Internal"}
	colours = (tree.APP / "public" / "js" / "chart_colors.js").read_text()
	assert (
		"built.colors = labels.map((label) => named[label]" in colours and "built.showLegend = 0" in colours
	)
	assert '"/assets/onedesk/js/chart_colors.js"' in (tree.APP / "hooks.py").read_text()
	# Kanban: a board by health, made once.
	board = (PROJECT / "board.py").read_text()
	assert 'HEALTH_BOARD = "Projects by Health"' in board
	assert 'HEALTH = {"On Track": "Green", "At Risk": "Orange", "Off Track": "Red"}' in board
	# Every view frappe offers stays: Calendar too (docs/PASSOVER.md, point 4).
	assert "delete found." not in listing


def test_a_person_in_a_link_reads_as_their_name_to_whoever_may_pick_them():
	hooks = (tree.APP / "hooks.py").read_text()
	assert '"frappe.desk.search.get_link_title": "onedesk.one.link_titles.get_link_title"' in hooks
	source = (tree.APP / "one" / "link_titles.py").read_text()
	assert '("select", "read")' in source and "return docname" in source
	# Administrator runs no project.
	assert '"onedesk.one_project.members.nobody",' in hooks
	assert "onedesk.one_project.patches.nobody_runs_it" in (tree.APP / "patches.txt").read_text()


def test_a_projects_featured_media_is_a_folder_of_its_own():
	import mimetypes

	space = _load(PROJECT / "media.py", ("PREFIX", "kind_of", "project_of"), mimetypes=mimetypes)
	assert space["kind_of"]("front.JPG") == "photo" and space["kind_of"]("walk.mp4") == "video"
	assert space["kind_of"]("brief.pdf") is None and space["kind_of"](None) is None
	assert space["project_of"]("@featured/PROJ-0008") == "PROJ-0008"
	assert (
		space["project_of"]("@records/Project/PROJ-0008") is None
		and space["project_of"]("@featured/") is None
	)
	# The file is marked; the project has a Cover, its picture wherever frappe shows one.
	file_fields = json.loads((PROJECT / "custom" / "file.json").read_text())["custom_fields"]
	assert [one["fieldname"] for one in file_fields] == ["one_featured"]
	custom = json.loads((PROJECT / "custom" / "project.json").read_text())
	cover = next(one for one in custom["custom_fields"] if one["fieldname"] == "one_cover")
	assert cover["fieldtype"] == "Attach Image" and cover["read_only"]
	assert any(
		one["property"] == "image_field" and one["value"] == "one_cover" for one in custom["property_setters"]
	)
	# OneCloud shows it inside the project's own folder, and only there.
	names = (tree.APP / "one_storage" / "namespace.py").read_text()
	assert 'FEATURED = "@featured/"' in names and 'if doctype == "Project":' in names
	api = (tree.APP / "one_storage" / "api.py").read_text()
	assert 'return ("record", "Project", kind[1], "featured")' in api and "def _refeature(" in api
	upload = (tree.APP / "one_storage" / "upload.py").read_text()
	assert (
		'media.check(fields["file_name"])' in upload
		and "fields.update(one_featured=1, is_private=0)" in upload
	)
	# The cover follows the folder, and hands over before a delete frappe would refuse.
	hooks = (tree.APP / "hooks.py").read_text()
	assert hooks.count('"onedesk.one_project.media.changed"') == 3
	# The portal shows it; the agreements say who can open it.
	assert '"media": media.shown(project)' in (PROJECT / "portal.py").read_text()
	assert 'key="oneproject-featured"' in (PROJECT / "legal.py").read_text()
	assert 'key="oneproject-contacts"' in (PROJECT / "legal.py").read_text()


def test_a_projects_page_is_laid_out_for_its_kind():
	space = _load(PROJECT / "view.py", ("percent",), flt=float)
	percent = space["percent"]
	# Budget Used says the real share, past 100 when over; a bar stops at 100.
	assert percent(156, 100) == 156 and percent(5, 0) == 0 and percent(-5, 10) == 0
	view = (PROJECT / "view.py").read_text()
	assert "\"value\": f\"{percent(cash['spent'], cash['budget'])}%\"" in view
	# A task with no due date is not late: frappe reads a missing date as the
	# earliest one, so the date is asked for.
	assert (
		view.count(
			'["exp_end_date", "is", "set"],\n\t\t\t# Before tomorrow: the due date is kept with a time.\n'
			'\t\t\t["exp_end_date", "<", str(add_days(today, 1))]'
		)
		== 1
	)
	assert (
		'["exp_end_date", "is", "set"], ["exp_end_date", "<", today]' in (PROJECT / "overview.py").read_text()
	)
	# Each thing shows once: a retainer's months and time not invoiced have
	# sections of their own, and a Fixed Price project's budget is its own.
	needs = view[view.index("def needs(") : view.index("def _budget_lines(")]
	assert "retainer.waiting" not in needs and "billing.unbilled" not in needs
	assert "if kind != kinds.FIXED:" in needs
	# Needs You: verb first, where each task is, the reader's own first, due
	# today too, counted whole, and over budget across the tree.
	assert '_("Check bill from {0}")' in needs and '_("Check invoice to {0}")' in needs
	assert "milestones.where(task.project, doc.name, of, titles)" in needs
	assert 'sorted(found, key=lambda one: not one.get("mine"))' in needs
	assert '"today": not late' in needs and 'budget.across(view["tree"])' in needs
	assert '"needs_count": len(needed)' in view and '"needs_all": _late_route(view["tree"])' in view
	overview_vue = (tree.ROOT / "frontend" / "src" / "project" / "Overview.vue").read_text()
	assert ":aside=\"view.needs_count || ''\"" in overview_vue and "go(view.needs_all)" in overview_vue
	assert 'one.today ? __("Today")' in overview_vue
	# This month's hours are the tree's, as Hours by Week counts them.
	assert '{"key": "hours", "hours": _month_hours(view["tree"])}' in view
	overview = (tree.ROOT / "frontend" / "src" / "project" / "Overview.vue").read_text()
	for kind in ("'Fixed Price'", "'Time and Materials'", "'Retainer'"):
		assert f"kind === {kind}" in overview
	assert '<Section v-if="said.notes"' in overview and "__('Add Brief')" in overview
	assert "<Updates " in overview
	# The head shows the cover and the rest of Featured Media, and adds to it
	# through frappe's upload dialog.
	header = (tree.ROOT / "frontend" / "src" / "project" / "Header.vue").read_text()
	assert 'method: "onedesk.one_project.media.add"' in header and '"image/*", "video/*"' in header
	assert '"media": media.shown(doc.name)' in view
	page = (tree.ROOT / "frontend" / "src" / "project" / "ProjectPage.vue").read_text()
	assert 'listen("one_project_media"' in page
	media = (PROJECT / "media.py").read_text()
	assert (
		'@frappe.whitelist(methods=["POST"])\ndef add()' in media and "upload._place(node(project)" in media
	)


def test_featured_media_turns_on_the_page_and_the_portal():
	# A project may have as many photos and videos as it needs: ERPNext's four
	# attachments would stop its folder and Featured Media at four.
	custom = json.loads((PROJECT / "custom" / "project.json").read_text())
	assert {"property": "max_attachments", "value": "0"}.items() <= next(
		one for one in custom["property_setters"] if one["property"] == "max_attachments"
	).items()
	# The cover first, on both.
	assert 'sorted(found, key=lambda one: one["url"] != cover)' in (PROJECT / "media.py").read_text()
	# The page: each in turn, a video muted to its end, one video on a loop,
	# paused under the pointer, still for whoever asked for less motion.
	hero = (tree.ROOT / "frontend" / "src" / "project" / "Hero.vue").read_text()
	for part in (
		"muted",
		"playsinline",
		':loop="media.length === 1"',
		'@ended="i === at && next()"',
		"lessMotion()",
		"@mouseenter",
	):
		assert part in hero, part
	# The portal: the same, in plain JavaScript beside the project's facts.
	page = (tree.APP / "www" / "projects.html").read_text()
	assert "data-one-gallery" in page and "/assets/onedesk/js/one_gallery.js" in page
	assert "muted playsinline" in page and "{% if media | length == 1 %} loop{% endif %}" in page
	gallery = (tree.APP / "public" / "js" / "one_gallery.js").read_text()
	for part in ('addEventListener("ended"', "prefers-reduced-motion", '"mouseenter"', "clip.play()"):
		assert part in gallery, part


def test_a_fixed_price_project_is_quoted_then_contracted_from_its_page():
	# The first figure: the contract once ordered, the quote while one is out,
	# and Add Contract with neither.
	def first(order, quote):
		space = _load(PROJECT / "view.py", ("_first",), _=lambda text: text)
		space.update(contract=lambda doc: order, quotation=lambda doc: quote, ordered_above=lambda doc: above)
		return space["_first"](None, {"contract": 500})

	above = None

	assert first("SO-1", None) == {"key": "contract", "money": 500, "route": "/desk/sales-order/SO-1"}
	quoted = first(
		None, {"name": "QTN-1", "value": 180, "count": 1, "valid_till": "2026-11-05", "alternatives": False}
	)
	assert quoted["key"] == "quoted" and quoted["money"] == 180 and quoted["route"] == "/desk/quotation/QTN-1"
	assert first(None, None) == {"key": "contract", "money": 0, "action": "add_contract"}
	# A sub-project whose work is on its parent's order says so, not 0.00.
	above = ("Bayview Tower Curtain Wall", "SO-9")
	on_parent = first(None, None)
	assert on_parent["value"] == "–" and on_parent["route"] == "/desk/sales-order/SO-9" and on_parent["above"]
	assert on_parent["note"] == "On {0}'s order".format("Bayview Tower Curtain Wall")
	above = None
	# With several open, which one is ordered is picked on their list.
	several = first(
		None, {"name": "QTN-2", "value": 195, "count": 2, "list": "/desk/quotation?x", "valid_till": None}
	)
	assert several["route"] == "/desk/quotation?x" and "action" not in several
	# While quoted, the quote's last day stands where Billed will be.
	days = lambda a, b: int(a[-2:]) - int(b[-2:])  # noqa: E731
	space = _load(
		PROJECT / "view.py", ("_valid",), _=lambda text: text, nowdate=lambda: "2026-10-05", date_diff=days
	)
	valid = space["_valid"]
	assert valid("2026-10-15") == {"key": "valid", "value": "2026-10-15", "date": True, "note": "In 10 days"}
	assert valid(None)["note"] is None
	assert "second = [_valid(valid)]" in (PROJECT / "view.py").read_text()
	# Quoted, the order is the next step: the page's main button, while one
	# quote is open. A Fixed Price project can be quoted again until ordered.
	page = (tree.ROOT / "frontend" / "src" / "project" / "ProjectPage.vue").read_text()
	assert (
		'if (s.kind === "Fixed Price" && !s.contract && s.quotation?.count === 1 && can("create", "Sales Order"))'
		in page
	)
	# Quoting is the + on the Overview's Quotations: New Quotation until the contract.
	overview = (tree.ROOT / "frontend" / "src" / "project" / "Overview.vue").read_text()
	assert 'if (s.kind === "Fixed Price" && !s.contract)\n    return { text: true, icon: "lucide-plus", label: __("New Quotation")' in overview
	# Its quotations are listed, and work against billing waits for an order.
	view_py = (PROJECT / "view.py").read_text()
	assert (
		'"quotes": _quotes(doc),' in view_py
		and 'said["milestones"]["billable"],' in view_py
		and '_last_billed(view["tree"]),' in view_py
		and "if contract(doc)" in view_py
	)
	overview_vue = (tree.ROOT / "frontend" / "src" / "project" / "Overview.vue").read_text()
	assert '<Section v-if="view.billing" :title="__(\'Work and Billing\')" icon="lucide-receipt">' in overview_vue
	assert ":title=\"__('Quotations')\"" in overview_vue
	view = (PROJECT / "view.py").read_text()
	assert '"quotation": None if contract(doc) else quotation(doc)' in view
	assert '"one_extra_work": 0' in view and '_("{0}% of the quote")' in view
	# Add Contract makes the dialog's own order, once, for whoever may change
	# the project and make orders, in the customer's currency.
	kinds = (PROJECT / "kinds.py").read_text()
	add = kinds[kinds.index("def add_contract(") : kinds.index("CONTRACT_ITEM =")]
	for part in (
		'frappe.has_permission("Project", "write", doc=doc, throw=True)',
		'frappe.has_permission("Sales Order", "create", throw=True)',
		"if ordered(doc):",
		"order = _contract(doc, values, flt(contract))",
	):
		assert part in add, part
	assert 'bill_in(order, "Customer", project.customer)' in kinds
	# The page asks for the next step under the figure, with frappe-ui's
	# Button, and makes the order with ERPNext's own quotation mapper.
	overview = (tree.ROOT / "frontend" / "src" / "project" / "Overview.vue").read_text()
	assert 'can("create", "Sales Order")' in overview and '__("Add Contract")' in overview
	assert '<Button v-if="one.button"' in (tree.ROOT / "frontend" / "src" / "kit" / "Figures.vue").read_text()
	actions = (tree.APP / "public" / "js" / "project_actions.js").read_text()
	assert "erpnext.selling.doctype.quotation.mapper.make_sales_order" in actions
	assert "onedesk.one_project.kinds.add_contract" in actions
	page = (tree.ROOT / "frontend" / "src" / "project" / "ProjectPage.vue").read_text()
	assert '__("Make Order")' in page
	overview = (tree.ROOT / "frontend" / "src" / "project" / "Overview.vue").read_text()
	assert '__("New Quotation")' in overview and '__("Quote Extra Work")' in overview


def test_a_quote_counts_while_it_stands_and_names_its_project():
	money = (PROJECT / "money.py").read_text()
	assert 'QUOTED = ("Open", "Replied", "Partially Ordered", "Ordered")' in money
	assert "q.status.isin(QUOTED)" in money and '(q.status != "Lost")' not in money
	view = (PROJECT / "view.py").read_text()
	to_quote = view[view.index("def to_quote(") : view.index("def _first(")]
	assert '"one_kind": kinds.FIXED' in to_quote and "if not contract(one)" in to_quote
	assert "return found[0] if len(found) == 1 else None" in to_quote
	script = (tree.APP / "public" / "js" / "quotation.js").read_text()
	assert 'frm.set_query("project"' in script and "onedesk.one_project.view.to_quote" in script


def test_a_party_billed_in_another_currency_is_billed_in_it(monkeypatch):
	import types

	space = _load(tree.APP / "one_book" / "currency.py", ("rate",), flt=float, nowdate=lambda: "2026-10-04")
	rates = {("USD", "AED"): 3.6725}
	setup = types.ModuleType("erpnext.setup.utils")
	setup.get_exchange_rate = lambda a, b, date: rates.get((a, b), 0)
	for name in ("erpnext", "erpnext.setup"):
		monkeypatch.setitem(sys.modules, name, sys.modules.get(name) or types.ModuleType(name))
	monkeypatch.setitem(sys.modules, "erpnext.setup.utils", setup)
	rate = space["rate"]
	assert rate("AED", "AED") == 1.0 and rate(None, "AED") == 1.0
	assert rate("USD", "AED") == 3.6725
	# ERPNext keeps the rate one way; the other way is its inverse.
	assert abs(rate("AED", "USD") - 1 / 3.6725) < 1e-12
	# Every document OneDesk makes for a party goes through bill_in.
	for path, party in (
		(PROJECT / "kinds.py", '"Customer", project.customer'),
		(PROJECT / "billing.py", '"Customer", source.customer'),
		(PROJECT / "retainer.py", '"Customer", doc.customer'),
		(tree.APP / "one_inventory" / "order.py", '"Supplier", name'),
	):
		assert any(f"bill_in({doc}, {party})" in path.read_text() for doc in ("order", "invoice", "doc")), (
			path
		)
	# Hours are turned into the invoice's currency from each timesheet's own.
	billing = _load(
		PROJECT / "billing.py",
		("in_currency",),
		flt=float,
		currency_rate=lambda a, b: {"AED": 1 / 4}.get(a, 1.0),
	)
	rows = billing["in_currency"]([{"currency": "AED", "billing_amount": 400.0}], "USD")
	assert rows[0]["billing_amount"] == 100.0
	# A retainer's fee is shown, and the New Project dialog asks for it, in the
	# customer's currency.
	assert '"currency": retainer.fee_currency(doc)' in (PROJECT / "view.py").read_text()
	assert 'options: "currency"' in (tree.APP / "public" / "js" / "project_new.js").read_text()


def test_a_projects_status_holds_and_closing_it_closes_what_is_open():
	status = (PROJECT / "status.py").read_text()
	# ERPNext's four, On hold among them, everywhere the status is picked or shown.
	assert '"On hold": _lt("On hold")' in status
	facts = (tree.ROOT / "frontend" / "src" / "project" / "Facts.vue").read_text()
	assert ":options=\"['Open', 'On hold', 'Completed', 'Cancelled']\"" in facts
	assert '<Pill v-if="said.status === \'Open\'" :value="said.health"' in facts, (
		"health is an open project's"
	)
	assert '"On hold": "amber"' in (tree.ROOT / "frontend" / "src" / "project" / "colors.js").read_text()
	assert '"On hold": "orange"' in (tree.APP / "public" / "js" / "project_list.js").read_text()
	assert "'amber' if doc.status == 'On hold'" in (tree.APP / "www" / "projects.html").read_text()
	# Completing or cancelling asks first, and closes the open tasks and
	# sub-projects with it; a task already closed keeps its status.
	change = status[status.index("def change(") : status.index("def due(")]
	assert "and not int(close):" in change and 'doc.flags.one_close_work = bool(int(close))' in change
	assert 'OPEN_TASK = ["not in", ("Completed", "Cancelled", "Template")]' in status
	# The rule is the Project's own (held, before ERPNext reads progress), so
	# a bulk edit or an import closes nothing with open work and keeps the rest.
	held = status[status.index("def held(") : status.index("def change(")]
	assert 'frappe.db.set_value("Task", name, "status", doc.status)' in held
	assert 'if not doc.flags.get("one_close_work"):' in held
	assert '"onedesk.one_project.status.held"' in HOOKS
	# Opening a project ERPNext turned to progress by hand puts it back on its
	# tasks; one whose tasks are all done says it can't be opened.
	assert 'doc.percent_complete_method = "Task Completion"' in held
	page = (tree.ROOT / "frontend" / "src" / "project" / "ProjectPage.vue").read_text()
	assert 'if (fieldname === "status") return changeStatus(value);' in page
	assert '"onedesk.one_project.status.ask"' in page and '"onedesk.one_project.status.change"' in page
	# A completed project says what's still owed, and its manager is told.
	view = (PROJECT / "view.py").read_text()
	assert 'if doc.status == "Completed" and frappe.has_permission("Sales Invoice", "read"):' in view
	tell = (PROJECT / "tell.py").read_text()
	assert "completed(doc, before)" in tell and '"Project Completed"' in tell
	assert "Project Completed" in tree.notifications()


def test_a_completed_project_reads_as_done():
	# ERPNext keeps a project completed without tasks of its own at its old
	# share, so the page, the head, OneAI and the portal read Completed as 100%.
	assert '"share": 100\n\t\tif doc.status == "Completed"\n\t\telse' in (PROJECT / "overview.py").read_text()
	assert (
		'100\n\t\tif doc.status == "Completed"\n\t\telse overview.share('
		in (PROJECT / "portal.py").read_text()
	)
	assert '"share": 100 if one["status"] == "Completed" else' in (PROJECT / "view.py").read_text()


def test_a_project_with_several_orders_bills_and_holds_each():
	view = (PROJECT / "view.py").read_text()
	assert '"orders": orders(doc, view["tree"]),' in view
	assert 'filters={"project": ["in", projects], "docstatus": 1}' in view
	# The head names the order, or says how many; Bill Progress asks which.
	facts = (tree.ROOT / "frontend" / "src" / "project" / "Facts.vue").read_text()
	assert '__("{0} orders", [said.orders.length])' in facts
	page = (tree.ROOT / "frontend" / "src" / "project" / "ProjectPage.vue").read_text()
	assert (
		"desk().project.bill_progress(s.orders, s.contract, s.currency, s.overview?.billing?.billable?.share)"
		in page
	)
	actions = (tree.APP / "public" / "js" / "project_actions.js").read_text()
	assert "onedesk.project.bill_progress = (orders, contract, currency, share) =>" in actions
	assert "if (open.length <= 1) return bill(open.length ? open[0].name : contract);" in actions
	overview = (tree.ROOT / "frontend" / "src" / "project" / "Overview.vue").read_text()
	assert '<Section v-if="said.orders?.length > 1" :title="__(\'Orders\')"' in overview


def test_orders_cover_the_tree_and_say_where_what_for_and_what_is_left():
	view = (PROJECT / "view.py").read_text()
	# Every order on the project and those under it, where and what for, and
	# whether it's extra work; Retention reads the same orders.
	assert '"where": milestones.where(one.project, doc.name, of, titles),' in view
	assert '"for": money.bought(lines.get(one.name, [])),' in view
	assert '"extra": bool(one.one_extra_work),' in view
	assert (
		'retention.sides(view["tree"], orders(doc, view["tree"]), cash["suppliers"])\n\t\t\tif retention.on()'
		in view
	)
	assert '_route("Sales Order", {"project": ["in", projects], "docstatus": 1})' in view
	overview = (tree.ROOT / "frontend" / "src" / "project" / "Overview.vue").read_text()
	assert 'badge: one.extra ? __("Extra Work") : undefined,' in overview
	assert '__("{0} left", [money(one.left, props.said.currency)])' in overview
	assert 'one.billable ? __("{0}% billed", [one.billed]) : __(one.status)' in overview
	assert "onClick: () => go(said.orders_route) }" in overview
	rows = (tree.ROOT / "frontend" / "src" / "kit" / "Rows.vue").read_text()
	assert '<Badge v-if="item.badge" :label="item.badge.label || item.badge"' in rows
	# Bill Progress offers each order under the project too, saying where, and
	# the milestones' share starts only the page's own.
	actions = (tree.APP / "public" / "js" / "project_actions.js").read_text()
	assert "!one || one.own ? share : null" in actions
	assert '[one.name, one.where, __("{0} left", [format_currency(one.left, currency)])]' in actions


def test_retention_is_switched_on_held_both_ways_released_in_parts_and_told():
	flt = lambda value=0, *args: round(float(value or 0), args[0]) if args else float(value or 0)  # noqa: E731
	space = _load(
		PROJECT / "retention.py",
		("parts", "still_held", "side", "HANDOVER", "RETENTION"),
		flt=flt,
	)
	parts, still_held, side = space["parts"], space["still_held"], space["side"]
	# 5% held, half of it at handover; none at handover is one part, as before.
	assert parts(5, 50) == [(None, 95), ("Retention at Handover", 2.5), ("Retention", 2.5)]
	assert parts(5, 0) == [(None, 95), ("Retention", 5)]
	assert parts(5, 100) == [(None, 95), ("Retention at Handover", 5)]
	# Paid last, and the handover part before the rest.
	held = [("2027-09-30", 500), ("2026-12-03", 500)]
	assert still_held(held, 57500) == [("2026-12-03", 500), ("2027-09-30", 500)]
	assert still_held(held, 700) == [("2026-12-03", 200), ("2027-09-30", 500)]
	assert still_held(held, 300) == [("2027-09-30", 300)]
	# A side: what's held, the rate when the orders agree, the first due.
	assert side([("2027-09-30", 3000)], {5.0}) == {"held": 3000, "percent": 5.0, "due": "2027-09-30"}
	assert side([("2027-03-31", 1000), ("2027-01-01", 500)], {5.0, 10.0}) == {
		"held": 1500,
		"percent": None,
		"due": "2027-01-01",
	}
	assert side([], {5.0}) is None
	# The switch: off unless the workspace holds retention, and the desk hides it.
	settings = json.loads((PROJECT / "custom" / "projects_settings.json").read_text())
	switch = {f["fieldname"]: f for f in settings["custom_fields"]}["one_retention"]
	assert switch["label"] == "Hold Retention" and switch["default"] == "0"
	assert "onedesk.one_project.patches.retention_switch" in (tree.APP / "patches.txt").read_text()
	assert '"onedesk.one_project.retention.boot"' in HOOKS
	for name in ("sales_order.json", "purchase_order.json"):
		fields = {
			f["fieldname"]: f for f in json.loads((PROJECT / "custom" / name).read_text())["custom_fields"]
		}
		assert fields["one_retention"]["depends_on"] == "eval:frappe.boot.one_retention || doc.one_retention"
		assert fields["one_retention_handover"]["label"] == "Released at Handover"
		assert fields["one_retention_handover"]["allow_on_submit"] == 1
	for name in ("project_new.js", "project_actions.js"):
		page = (tree.APP / "public" / "js" / name).read_text()
		assert "hidden: !frappe.boot.one_retention" in page and 'fieldname: "retention_handover"' in page
	# Handover falls due when the project is completed; the day it's due is told.
	assert '"onedesk.one_project.retention.handed_over"' in HOOKS
	assert '"onedesk.one_project.retention.due"' in HOOKS
	assert tree.notifications()["Retention Due"]["subject"] == "Retention on {project} is due today"
	# Needs You asks the customer for it, and says when a supplier's is to pay.
	view = (PROJECT / "view.py").read_text()
	assert 'found += retention.asks(view["tree"], user)' in view
	assert '_("Pay retention to {0}") if one["held"] else _("Pay {0}")' in view
	assert '_("Ask for retention from {0}")' in (PROJECT / "retention.py").read_text()
	overview = (tree.ROOT / "frontend" / "src" / "project" / "Overview.vue").read_text()
	assert (
		'["customer", __("From the Customer")]' in overview
		and '["suppliers", __("To Suppliers")]' in overview
	)


def test_about_says_what_the_head_doesnt_and_is_changed_in_place():
	overview = (tree.ROOT / "frontend" / "src" / "project" / "Overview.vue").read_text()
	about = overview.split("const facts = computed(() => {", 1)[1].split("});", 1)[0]
	# Only what the head doesn't say.
	for gone in ("s.customer", "s.manager", "s.contract", "s.starts", "s.parent"):
		assert gone not in about
	for said in ('__("Progress")', '__("Due")', '__("Team")', '__("Priority")'):
		assert said in about
	assert "__('About', null, 'Project')" in overview
	# Changed in place, with frappe's controls, against the loaded record.
	actions = (tree.APP / "public" / "js" / "project_actions.js").read_text()
	assert '[__("Work"), ["one_manager", "expected_start_date", "expected_end_date"' in actions
	assert 'frappe.meta.get_docfield("Project", fieldname)' in actions
	assert "{ doc: { ...doc, ...values, modified } }" in actions
	assert "onedesk().project.edit_brief(props.said.name, props.said.modified" in overview
	assert "edit=1" not in overview
	# A sub-project's breadcrumb names its parents.
	view = (PROJECT / "view.py").read_text()
	assert '"above": _above(doc.name),' in view
	assert (
		"...between.map((one) => ({ label: one.label, href: one.route }))"
		in (tree.APP / "public" / "js" / "shell.js").read_text()
	)
	page = (tree.ROOT / "frontend" / "src" / "project" / "ProjectPage.vue").read_text()
	assert "props.onTitle?.({ title: s.title, between:" in page


def test_sub_projects_say_how_each_is_going_and_what_it_is_worth():
	flt = lambda value=0, *args: float(value or 0)  # noqa: E731
	branch_money = _load(PROJECT / "view.py", ("branch_money",), flt=flt)["branch_money"]
	# Villa Windows: 30,000 bought and 1,210 of time against a 20,000 budget.
	windows = {"estimated_costing": 20000, "total_costing_amount": 1210, "total_purchase_cost": 30000}
	assert branch_money(windows) == {"ordered": 0, "billed": 0, "spent": 31210, "budget": 20000, "over": True}
	handrails = {"total_sales_amount": 200000, "total_billed_amount": 60000, "estimated_costing": 5500}
	assert branch_money(handrails)["ordered"] == 200000 and not branch_money(handrails)["over"]
	view = (PROJECT / "view.py").read_text()
	assert '"count": len(under),' in view and '"extra": one["name"] in extra,' in view
	assert 'money._route("Project", {"one_parent": project}) if len(under) > SHOWN else None' in view
	overview = (tree.ROOT / "frontend" / "src" / "project" / "Overview.vue").read_text()
	assert ':aside="view.sub_projects.count"' in overview
	assert 'dot: one.health === "Off Track" || late || one.over ? "red"' in overview
	assert 'newDoc("Project", { one_parent: props.said.name, customer: props.said.customer })' in overview
	assert "label: __('Add Sub-project'), onClick: addSub" in overview
	page = (tree.ROOT / "frontend" / "src" / "project" / "ProjectPage.vue").read_text()
	assert (
		'doc.one_parent ? __("New Sub-project") : __("New Project")'
		in (tree.APP / "public" / "js" / "project_new.js").read_text()
	)


def test_the_tasks_table_says_what_waits_and_how_long_and_nests_sub_tasks():
	view = (PROJECT / "view.py").read_text()
	assert 'one["waiting"] = waiting.get(one["name"], [])' in view
	assert '"Task Depends On"' in view.split("def _waiting(", 1)[1]
	tasks = (tree.ROOT / "frontend" / "src" / "project" / "Tasks.vue").read_text()
	assert '__("Waiting on {0}", [item.waiting.join(", ")])' in tasks
	assert (
		"$emit('set', item.name, 'expected_time'" in tasks
		and '<ListHeaderCell>{{ __("Planned") }}</ListHeaderCell>' in tasks
	)
	assert ':items="nest(group.tasks)"' in tasks and "<TextInput" in tasks
	group = (tree.ROOT / "frontend" / "src" / "project" / "group.js").read_text()
	assert "export function nest(tasks)" in group and "subDone" in group


def test_the_task_panel_is_the_same_task_onetask_opens():
	panel = (tree.ROOT / "frontend" / "src" / "project" / "TaskPanel.vue").read_text()
	# Its checklist, sub-tasks, what it waits on, the timer and Repeat.
	for said in (
		"onedesk.one_task.task.tick",
		"onedesk.one_task.task.add_step",
		"onedesk.one_task.timer.start",
	):
		assert said in panel
	assert 'emit("add", props.task.project, text, { parent_task: props.task.name })' in panel
	assert '__("Depends On")' in panel and '__("Repeat")' in panel and '__("Stop Repeating")' in panel
	actions = (tree.APP / "public" / "js" / "project_actions.js").read_text()
	assert "onedesk.project.task_details = async (task, modified, done) =>" in actions
	assert 'frappe.utils.new_auto_repeat_prompt({ doc: { doctype: "Task", name: task }' in actions
	assert "{ doc: { ...doc, ...values, depends_on, modified } }" in actions
	steps = (tree.APP / "one_task" / "task.py").read_text()
	assert "def tick(task: str, step: str" in steps and "def add_step(task: str, step: str)" in steps
	task = json.loads((tree.APP / "one_task" / "custom" / "task.json").read_text())
	assert any(one["property"] == "show_title_field_in_link" for one in task["property_setters"])


def test_a_task_goes_to_a_group_a_template_joins_a_running_project_and_people_hear():
	people = (tree.ROOT / "frontend" / "src" / "kit" / "People.vue").read_text()
	assert 'group: __("Groups")' in people and 'emit("group"' in people
	for panel in ("Tasks.vue", "TaskPanel.vue"):
		said = (tree.ROOT / "frontend" / "src" / "project" / panel).read_text()
		assert ':groups="canWrite ? work.user_groups || [] : []"' in said
	assert "def _user_groups() -> list[dict]:" in (PROJECT / "view.py").read_text()
	templates = (PROJECT / "templates.py").read_text()
	# ERPNext's own copy, dated from the day chosen, beside the tasks it has.
	assert (
		"doc.create_task_from_template(one)" in templates
		and "doc.dependency_mapping(sources, made)" in templates
	)
	assert (
		"desk().project.add_template(s.name, loadWork)"
		in (tree.ROOT / "frontend" / "src" / "project" / "ProjectPage.vue").read_text()
	)
	assert {"Task Ready", "Pending Review", "Due Date Changed"} <= set(tree.notifications())
	assert '"onedesk.one_task.tell.changed"' in (tree.APP / "hooks.py").read_text()


def test_time_is_counted_apart_from_how_the_customer_pays():
	from datetime import date

	space = _load(
		PROJECT / "hours.py",
		("count", "billed_by_the_hour"),
		flt=lambda value=0, *args: round(float(value or 0), *args),
		getdate=lambda value: date.fromisoformat(str(value)[:10]),
		kinds=type("kinds", (), {"TIME": "Time and Materials", "RETAINER": "Retainer"}),
	)
	assert space["billed_by_the_hour"]("Time and Materials") and space["billed_by_the_hour"]("Retainer")
	assert not space["billed_by_the_hour"]("Fixed Price") and not space["billed_by_the_hour"]("Internal")
	rows = [
		{
			"hours": 4,
			"from_time": "2026-09-22",
			"docstatus": 1,
			"is_billable": 1,
			"base_billing_amount": 1120,
			"base_costing_amount": 520,
		},
		{
			"hours": 2,
			"from_time": "2026-10-02",
			"docstatus": 1,
			"is_billable": 1,
			"sales_invoice": "SINV-1",
			"base_billing_amount": 600,
			"base_costing_amount": 300,
		},
		{
			"hours": 3,
			"from_time": "2026-10-03",
			"docstatus": 0,
			"is_billable": 1,
			"base_billing_amount": 840,
			"base_costing_amount": 390,
		},
	]
	money = space["count"](rows, date(2026, 10, 1), True)
	# A draft is hours, not yet cost or billing.
	assert money == {"month": 5, "hours": 9, "drafts": 3, "to_invoice": 1120, "invoiced": 600, "cost": 820}
	assert space["count"](rows, date(2026, 10, 1), False) == {"month": 5, "hours": 9, "drafts": 3}
	hooks = (tree.APP / "hooks.py").read_text()
	assert '"onedesk.one_project.hours.fill"' in hooks
	project = json.loads((PROJECT / "custom" / "project.json").read_text())
	said = {one["fieldname"]: one for one in project["custom_fields"]}
	assert said["one_time"]["options"] == "\nTimesheets\nAttendance on Site\nNot Tracked"
	assert said["one_site"]["options"] == "Shift Location"
	assert "onedesk.one_project.patches.time_counted" in (tree.APP / "patches.txt").read_text()
	timer = (tree.APP / "one_task" / "timer.py").read_text()
	assert '"is_billable": 1 if bills_hours(doc.project) else 0' in timer
	billing = (PROJECT / "billing.py").read_text()
	assert "for one in sorted(tree.scope(project))" in billing
	view = (tree.ROOT / "frontend" / "src" / "project" / "Time.vue").read_text()
	assert "ListGroup" in view and '__("Time Cost")' in view and "said.money" in view


def test_a_day_on_site_is_a_day_on_the_project():
	space = _load(
		PROJECT / "site_time.py",
		("WORKED", "worked"),
		flt=lambda value=0, precision=None: (
			float(value or 0) if precision is None else round(float(value or 0), precision)
		),
	)
	worked = space["worked"]
	# What attendance measured, else the standard day, half for a Half Day.
	assert worked(9.1, "Present", 8.5) == 9.1
	assert worked(0, "Present", 8.5) == 8.5 and worked(0, "Half Day", 8.5) == 4.25
	assert worked(0, "Absent", 8.5) == 0
	hooks = (tree.APP / "hooks.py").read_text()
	assert '"on_submit": "onedesk.one_project.site_time.attended"' in hooks
	assert '"on_cancel": "onedesk.one_project.site_time.cancelled"' in hooks
	timesheet = json.loads((PROJECT / "custom" / "timesheet.json").read_text())
	assert timesheet["custom_fields"][0]["fieldname"] == "one_attendance"


def test_what_was_bought_for_a_time_and_materials_job_is_billed_once():
	charge = _load(PROJECT / "billing.py", ("charge",), flt=lambda value=0, *args: float(value or 0))[
		"charge"
	]
	assert charge(30000, 10) == 33000 and charge(250, 0) == 250
	billing = (PROJECT / "billing.py").read_text()
	# Only a Time and Materials project's costs, and never one already on an invoice.
	assert "if one.one_kind == kinds.TIME and one.customer == customer" in billing
	assert '"one_rebills": ["in", [one["key"] for one in found] or [""]], "docstatus": ["<", 2]' in billing
	item = json.loads((PROJECT / "custom" / "sales_invoice_item.json").read_text())
	assert item["doctype"] == "Sales Invoice Item" and item["custom_fields"][0]["fieldname"] == "one_rebills"
	actions = (tree.APP / "public" / "js" / "project_actions.js").read_text()
	assert "args: { item, cost_item: with_costs ? cost_item : null }" in actions


def test_a_task_over_its_hours_is_told_and_timing_it_does_not_finish_it():
	assert "Hours Over Plan" in tree.notifications()
	tell = (PROJECT / "tell.py").read_text()
	# Once, as the hours pass the plan.
	assert "if not (flt(before.actual_time) <= planned < flt(doc.actual_time)):" in tell
	assert '"onedesk.one_project.tell.over_plan"' in (tree.APP / "hooks.py").read_text()
	# ERPNext completes a task when a submitted timesheet's row says so.
	assert "one.completed = 1" not in (tree.APP / "one_task" / "timer.py").read_text()
	assert '"completed": 0,' in (PROJECT / "hours.py").read_text()


def test_bill_progress_bills_each_line_of_a_bill_of_quantities_by_its_own_share():
	from types import SimpleNamespace as Line

	space = _load(
		PROJECT / "progress.py", ("to_bill", "overall"), flt=lambda value=0, *args: float(value or 0)
	)
	lights = Line(name="lights", qty=40, amount=18000)
	cabling = Line(name="cabling", qty=600, amount=15000)
	commissioning = Line(name="commissioning", qty=1, amount=6000)
	done = {"lights": 50, "cabling": 30}
	# By value: 9,000 and 4,500 of 39,000.
	assert space["overall"]([lights, cabling, commissioning], done) == 34.62
	assert space["to_bill"](40, 0, 50) == 20 and space["to_bill"](600, 0, 30) == 180
	assert space["to_bill"](600, 180, 30) == 0
	dialog = (tree.APP / "public" / "js" / "progress.js").read_text()
	assert 'fieldname: "by_line"' in dialog and 'fieldtype: "Table"' in dialog
	assert "shares.get(line.name, 0) if shares else done" in (PROJECT / "progress.py").read_text()


def test_the_cost_figure_says_why_it_is_red_and_what_is_on_order():
	note = _load(PROJECT / "view.py", ("cost_note",), _=lambda text: text)["cost_note"]
	over = {"budget": 140500, "forecast_cost": 141210, "open_orders": 78000}
	assert note(over) == [["Forecast over by {0}", [710]], ["{0} on order", [78000]]]
	under = {"budget": 200000, "forecast_cost": 141210, "open_orders": 0}
	assert note(under) == [["of {0} budget", [200000]]]
	assert note({"budget": 0, "forecast_cost": 0, "open_orders": 5000}) == [["{0} on order", [5000]]]
	# Billed opens Invoices; Cost and Forecast Margin open Money, and so does
	# a finished project's Margin.
	view = (PROJECT / "view.py").read_text()
	assert '"view": "invoices",' in view and view.count('"view": "money",') == 3
	assert 'def _made(cash: dict)' in view and '"key": "margin"' in view
	overview = (tree.ROOT / "frontend" / "src" / "project" / "Overview.vue").read_text()
	assert "card.view && !card.route && props.said.views?.includes(card.view)" in overview


def test_work_done_is_measured_as_the_project_says_and_billing_as_amounts():
	progress = _load(
		PROJECT / "overview.py",
		("progress", "share"),
		flt=lambda value=0, *args: round(float(value or 0), *args),
	)["progress"]
	tasks = [
		{"status": "Completed", "progress": 0, "task_weight": 1},
		{"status": "Open", "progress": 50, "task_weight": 3},
	]
	assert progress("Task Completion", tasks, 0) == 50
	assert progress("Task Progress", tasks, 0) == 75
	assert progress("Task Weight", tasks, 0) == (100 * 1 + 50 * 3) / 4
	assert progress("Manual", tasks, 40) == 40 and progress("Task Completion", [], 12) == 12
	# As ERPNext measures its own: a cancelled task is finished.
	assert progress("Task Completion", [*tasks, {"status": "Cancelled", "progress": 0}], 0) == round(
		200 / 3, 2
	)
	# One figure: the tree's stored as ERPNext's % Complete, read by the page.
	overview = (PROJECT / "overview.py").read_text()
	assert '\t\telse round(flt(doc.percent_complete)),' in overview and '"share": 100\n\t\tif doc.status == "Completed"' in overview
	assert 'frappe.db.set_value("Project", one, "percent_complete", value, update_modified=False)' in overview
	assert '"onedesk.one_project.overview.task_changed"' in HOOKS
	assert '"onedesk.one_project.overview.project_changed"' in HOOKS
	assert "onedesk.one_project.patches.tree_progress" in (tree.APP / "patches.txt").read_text()
	# The Tasks tab reads every project under, at any depth, by path.
	view = (PROJECT / "view.py").read_text()
	assert "milestones.where(one, project, of, titles)" in view.split("def work(", 1)[1]
	billing = _load(PROJECT / "view.py", ("work_and_billing",), _=lambda text: text, flt=float)[
		"work_and_billing"
	]
	cash = {
		"contract": 375000,
		"invoiced": 60000,
		"customer": [{"label": "Paid", "value": 57000}, {"label": "Retention Held", "value": 3000}],
		"owed": 3000,
		"advance": 0,
	}
	said = billing(17, cash, 0)
	assert said["unbilled"] == 3750 and said["ahead"] == 0
	assert said["owed"] == 3000 and said["retention"] == 3000 and said["advance"] == 0
	ahead = billing(10, cash, 0)
	assert ahead["ahead"] == 22500 and ahead["unbilled"] == 0
	early = billing(0, {**cash, "invoiced": 0, "owed": 0, "advance": 57000}, 0)
	assert early["advance"] == 57000 and early["owed"] == 0
	# Paid with 5% VAT on a 100,000 invoice is no advance: owed and paid
	# ahead are both read from the invoices, tax included (money._paid_on).
	taxed = billing(17, {**cash, "invoiced": 100000, "owed": 0, "advance": 0}, 0)
	assert taxed["advance"] == 0 and taxed["owed"] == 0
	assert said["last"] is None
	last = billing(17, cash, 0, {"posting_date": "2026-10-04", "one_progress": 0})
	assert last["last"] == {"date": "2026-10-04", "share": 16}
	assert billing(17, cash, 0, {"posting_date": "2026-10-04", "one_progress": 15})["last"]["share"] == 15


def test_a_project_lists_who_outside_the_company_is_on_it():
	space = _load(PROJECT / "contacts.py", ("ROLES", "SUPPLYING", "_person"))
	assert space["ROLES"][:2] == space["SUPPLYING"] == ("Subcontractor", "Supplier")
	assert "Client's Representative" in space["ROLES"] and space["ROLES"][-1] == "Other"
	person = space["_person"]
	# The phone, or the mobile when there's none; nothing without a Contact.
	assert person({"phone": "", "mobile_no": "+971 50 1"}, "phone", "mobile_no") == "+971 50 1"
	assert person({"phone": "+971 4 5"}, "phone", "mobile_no") == "+971 4 5"
	assert person(None, "phone") is None
	table = json.loads((PROJECT / "doctype" / "project_contact" / "project_contact.json").read_text())
	assert table["istable"] == 1
	fields = {one["fieldname"]: one for one in table["fields"]}
	assert fields["role"]["options"].split("\n") == list(space["ROLES"]) and fields["role"]["reqd"]
	assert fields["organisation"]["depends_on"] == "eval:!doc.supplier"
	assert fields["email"]["fetch_from"] == "contact.email_id"
	custom = json.loads((PROJECT / "custom" / "project.json").read_text())["custom_fields"]
	assert any(one["fieldname"] == "one_contacts" and one["options"] == "Project Contact" for one in custom)
	contacts_py = (PROJECT / "contacts.py").read_text()
	save = contacts_py[contacts_py.index("def save(") : contacts_py.index("def remove(")]
	assert 'doc.check_permission("write")' in save
	# Each row names somebody, and its contact names the project, as the Project's own rules.
	assert "linked(row.contact, doc.name)" in contacts_py and '"onedesk.one_project.contacts.held"' in HOOKS
	assert '_("Give the supplier, the company or the contact.")' in save
	assert 'person.has_permission("write")' in contacts_py
	actions = (tree.APP / "public" / "js" / "project_actions.js").read_text()
	assert "onedesk.project.contact = (project, row, done, preset = {})" in actions
	assert '__("Remove {0} from the project?"' in actions
	src = tree.ROOT / "frontend" / "src" / "project"
	team = (src / "Team.vue").read_text()
	assert "onedesk.one_project.contacts.contacts" in team and "__('Add Contact')" in team
	suppliers = (src / "Suppliers.vue").read_text()
	assert "__('Add Supplier')" in suppliers and "order.supplier_id === one.supplier" in suppliers
	assert '"supplier_id": head.supplier' in (PROJECT / "money.py").read_text()
	assert '"contacts": _contacts(project)' in (PROJECT / "ai.py").read_text()


def test_the_head_shows_everyone_team_lists_and_any_user_can_be_made_a_member():
	view_py = (PROJECT / "view.py").read_text()
	assert 'for one in team.team(doc.name)["people"]' in view_py
	team_py = (PROJECT / "team.py").read_text()
	assert 'one["can_join"] = bool(known and known.enabled) and not one["member"]' in team_py
	src = tree.ROOT / "frontend" / "src"
	header = (src / "project" / "Header.vue").read_text()
	assert "props.said.people.map" in header and ':max="5"' in header and "$emit('view', 'team')" in header
	assert "s.people?.length" in (src / "project" / "Overview.vue").read_text()
	team = (src / "project" / "Team.vue").read_text()
	assert "person.can_join" in team and "onedesk.one_project.team.add" in team
	assert '__("Remove {0} from the project?"' in team
	assert "stack.users.length > props.max" in (src / "kit" / "People.vue").read_text()


def test_activity_is_the_projects_history_not_only_its_record():
	from datetime import datetime

	space = _load(
		PROJECT / "activity.py",
		("SAME_SITTING", "PAGE", "events", "moved", "page", "grouped"),
		get_datetime=lambda value: datetime.fromisoformat(str(value)),
		defaultdict=__import__("collections").defaultdict,
		re=__import__("re"),
	)
	events, moved, page = space["events"], space["moved"], space["page"]
	doc = {"creation": "2026-10-04 14:50:00", "owner": "wren", "docstatus": 1, "modified": "2026-10-04 15:00:00", "modified_by": "wren"}
	# Made and submitted in one sitting by the same person: one row.
	assert events(doc, [("2026-10-04 14:55:00", "wren", 1)]) == [("submitted", "2026-10-04 14:55:00", "wren")]
	# Submitted by somebody else, then cancelled: three rows.
	said = events({**doc, "docstatus": 2}, [("2026-10-04 15:00:00", "samir", 1), ("2026-10-05 09:00:00", "samir", 2)])
	assert [one[0] for one in said] == ["created", "submitted", "cancelled"]
	# A type that keeps no Versions: submitted when last changed.
	assert events({**doc, "creation": "2026-10-01 09:00:00"}, [])[1] == ("submitted", "2026-10-04 15:00:00", "wren")
	assert events({**doc, "docstatus": 0}, []) == [("created", "2026-10-04 14:50:00", "wren")]
	assert moved('{"changed":[["status","Draft","To Bill"],["docstatus",0,1]]}') == 1
	assert moved('{"changed":[["docstatus", 1, 2]]}') == 2 and moved('{"changed":[]}') is None
	rows = [{"timestamp": f"2026-10-0{day} 10:00:00", "key": str(day)} for day in range(1, 7)]
	shown, more = page(rows, None, 4)
	assert [one["key"] for one in shown] == ["6", "5", "4", "3"] and more
	assert [one["key"] for one in page(rows, "2026-10-03 00:00:00", 4)[0]] == ["2", "1"]
	activity = (PROJECT / "activity.py").read_text()
	for doctype in ("Purchase Order", "Sales Invoice", "Payment Entry", "Expense Claim", "Stock Entry", "Journal Entry"):
		assert f'"{doctype}":' in activity
	assert 'frappe.has_permission(doctype, "read")' in activity and "frappe.get_list(doctype" in activity
	custom = json.loads((PROJECT / "custom" / "project.json").read_text())
	assert any(one["property"] == "track_changes" and one["value"] == "1" for one in custom["property_setters"])
	src = tree.ROOT / "frontend" / "src" / "project"
	view = (src / "ProjectActivity.vue").read_text()
	assert "onedesk.one_project.activity.activity" in view and 'useActivityTimeline("Project", props.project' in view
	assert "#item-document" in view and "isPagedRow" in view and '__("Show earlier activity")' in view
	assert '<ProjectActivity v-else-if="view === \'activity\'"' in (src / "ProjectPage.vue").read_text()


def test_a_projects_views_are_one_row_of_tabs_under_its_head():
	"""As a form's tabs: across the top under the head, scrolling with the
	page, frappe's form sidebar on the right (tests/guards/test_record_page.py)."""
	page = (tree.ROOT / "frontend" / "src" / "project" / "ProjectPage.vue").read_text()
	assert "<Page wide>" in page and "grid-cols" not in page
	assert page.index("<Header ") < page.index("<ViewTabs ")
	assert "sticky" not in page and "vertical" not in page
	assert "lg:max-w-[85rem]': wide" in (tree.ROOT / "frontend" / "src" / "kit" / "Page.vue").read_text()


def test_the_overview_puts_its_figures_in_cards_and_charts_tasks_hours_and_budget():
	src = tree.ROOT / "frontend" / "src"
	overview = (src / "project" / "Overview.vue").read_text()
	assert '<Figures :figures="figures" boxed :columns="figures.length === 4 ? 2 : figures.length" />' in overview
	# A group of cards is its own divide: no rule above or below one.
	assert overview.count("data-cards") == 2 and "border-b" not in overview
	assert "[&:has(+[data-cards])]:border-b-0" in (src / "kit" / "Section.vue").read_text()
	assert '<Section boxed :title="__(\'Needs You\')"' in overview
	assert "<DonutChart" in overview and "<ChartCard" in overview and "horizontal stacked" in overview
	# Colours from frappe-ui's tokens on the island's own root, never hex.
	assert "useChartTokens(root)" in overview and not re.search(r"#[0-9a-fA-F]{6}", overview)
	# The ring draws the largest first: the colours are listed in that order.
	assert ".sort((a, b) => b.n - a.n)" in overview
	assert not (src / "project" / "Statuses.vue").exists()
	assert "rounded-4 border border-outline-gray-1 bg-surface-elevation-2" in (src / "kit" / "Figures.vue").read_text()
	# Every kind charts its tasks and hours, and a late task is Overdue.
	view = (PROJECT / "view.py").read_text().split("def _overview(", 1)[1].split("\ndef ", 1)[0]
	assert '"statuses": view["statuses"]' in view and '"weekly": view["weekly"]' in view
	assert 'said["weekly"]' not in view and 'said["statuses"]' not in view
	overview_py = (PROJECT / "overview.py").read_text()
	assert 'statuses["Overdue"] = late' in overview_py


def test_orders_and_quotations_sit_together_and_an_ordered_quote_is_its_order():
	overview = (tree.ROOT / "frontend" / "src" / "project" / "Overview.vue").read_text()
	left, right = overview.split("<Section boxed :title=\"__('Needs You')\"", 1)
	billing = left.index("__('Work and Billing')")
	assert billing < left.index("__('Orders')") < left.index("__('Quotations')") < left.index("__('Budget')")
	assert "__('Orders')" not in right and "__('Quotations')" not in right
	quotes = (PROJECT / "view.py").read_text().split("def _quotes(", 1)[1].split("\ndef ", 1)[0]
	assert '"status": ["!=", "Ordered"]' in quotes


def test_every_avatar_on_a_project_shows_the_persons_picture():
	src = tree.ROOT / "frontend" / "src"
	# Every Avatar is given a picture, save the "+N" one and one that shows an
	# icon for nobody in particular.
	for path in [*(src / "project").glob("*.vue"), *(src / "kit").glob("*.vue")]:
		for line in path.read_text().splitlines():
			if "<Avatar" in line or "h(Avatar" in line:
				assert ":image=" in line or "image:" in line or 'label: "+"' in line or 'v-else-if="item.icon"' in line, f"{path.name}: {line.strip()}"
	view = (PROJECT / "view.py").read_text()
	assert '"manager_image"' in view and "def _faces(" in view and "row.image = faces.get(row.user)" in view
	assert "faces = _faces(people.values())" in (PROJECT / "hours.py").read_text()
	assert '"image": _person(people.get(one.contact), "image")' in (PROJECT / "contacts.py").read_text()


def test_a_suppliers_logo_shows_where_the_supplier_does():
	money = (PROJECT / "money.py").read_text()
	assert '"image": logos.get(head.supplier),' in money
	src = tree.ROOT / "frontend" / "src" / "project"
	assert '<Avatar :label="one.supplier" :image="one.image" shape="square"' in (src / "Suppliers.vue").read_text()
	assert "image: one.image,\n      square: true," in (src / "Overview.vue").read_text()
	assert "or logos.get(one.supplier)" in (PROJECT / "contacts.py").read_text()
	# The bills, invoices and buying lists carry each party's logo too.
	assert '"party_image": logos.get(row.party_id),' in (PROJECT / "billing.py").read_text()
	assert 'one["party_image"] = logos.get(one.pop("supplier"))' in (PROJECT / "buying.py").read_text()
	assert (src / "Suppliers.vue").read_text().count(':image="item.party_image" shape="square"') == 2
	assert '<Avatar :label="item.party" :image="item.party_image" shape="square"' in (src / "Invoices.vue").read_text()
	# And the customer's on the head, beside the project's name.
	assert '"customer_image": frappe.db.get_value("Customer", doc.customer, "image")' in (PROJECT / "view.py").read_text()
	assert ':image="said.customer_image" shape="square"' in (src / "Facts.vue").read_text()
	# The Overview's orders and the customer's retention carry it too.
	assert 'image: props.said.customer_image } : { icon: "lucide-truck" }),' in (src / "Overview.vue").read_text()
	assert "    image: props.said.customer_image,\n    square: true," in (src / "Overview.vue").read_text()


def test_a_parent_can_be_read_without_what_is_under_it():
	# tree.narrow makes tree.scope the project alone for the rest of the
	# request; a call inside it that doesn't ask keeps what the page asked.
	import types

	frappe = types.SimpleNamespace(local=types.SimpleNamespace())
	of = {"Handrails": "Villa", "Glass": "Handrails", "Pergola": "Villa"}
	space = _load(
		PROJECT / "tree.py",
		("narrow", "narrowed", "scope", "below", "children"),
		frappe=frappe,
		cint=lambda value: int(value or 0),
		parents=lambda: of,
	)
	assert space["scope"]("Villa") == {"Villa", "Handrails", "Glass", "Pergola"}
	space["narrow"]("Villa", None)
	assert not space["narrowed"]("Villa")
	space["narrow"]("Villa", 1)
	space["narrow"]("Villa", None)
	assert space["narrowed"]("Villa") and not space["narrowed"]("Handrails")
	assert space["scope"]("Villa") == {"Villa"}
	assert space["scope"]("Handrails") == {"Handrails", "Glass"}

	# Every view the page reads takes `only` and counts through tree.scope.
	ONLY = 'only: Annotated[bool | None, "Only the project\'s own work, not what is under it."] = None'
	for module, name in (
		("view.py", "said"),
		("view.py", "work"),
		("view.py", "files"),
		("billing.py", "invoices"),
		("billing.py", "bills"),
		("hours.py", "entries"),
		("team.py", "team"),
		("activity.py", "activity"),
		("buying.py", "papers"),
	):
		body = (PROJECT / module).read_text().split(f"\ndef {name}(", 1)[1].split("\ndef ", 1)[0]
		assert ONLY in body and "tree.narrow(project, only)" in body, (module, name)
	for module in ("money.py", "overview.py", "team.py", "activity.py", "buying.py", "hours.py"):
		assert "tree.scope(project)" in (PROJECT / module).read_text(), module
	assert '"own" if tree.narrowed(project) else "tree"' in (PROJECT / "money.py").read_text()

	# The page: Main first in Sub-projects, the crumb switches, the address keeps it.
	src = tree.ROOT / "frontend" / "src" / "project"
	view = (PROJECT / "view.py").read_text()
	assert '"main": {' in view and "overview.own_progress(" in view
	assert '_("{0} extra work")' in view
	overview_vue = (src / "Overview.vue").read_text()
	assert ':rows="[...mainRow, ...subProjects]"' in overview_vue and 'onClick: () => emit("main")' in overview_vue
	page = (src / "ProjectPage.vue").read_text()
	assert "after: scopeCrumb(s)" in page and '"below": _below(doc.name)' in view
	assert 'const only = ref(props.query.only === "1");' in page and 'setQuery("only", now ? "1" : null);' in page
	for one in ("Files.vue", "Invoices.vue", "ProjectActivity.vue", "Team.vue", "Time.vue", "Suppliers.vue"):
		assert "...onlyArg(only)" in (src / one).read_text(), one
	assert '"main": _main(project)' in (PROJECT / "ai.py").read_text()


def test_a_whole_jobs_milestones_are_a_row_per_part():
	of = {"Handrails": "Villa", "Glass": "Handrails", "Pergola": "Villa"}
	space = _load(PROJECT / "milestones.py", ("lane", "lanes"), tree=type("T", (), {"above": staticmethod(_load(PROJECT / "tree.py", ("above",))["above"])}))
	lane, lanes = space["lane"], space["lanes"]
	assert lane("Villa", "Villa", of) == "Villa" and lane("Glass", "Villa", of) == "Handrails" and lane("Pergola", "Villa", of) == "Pergola"
	row = lambda subject, due, done, at: {"subject": subject, "due": due, "done": done, "lane": at}  # noqa: E731
	rows = [
		row("Handover", "2026-10-13", False, "Handrails"),
		row("Site ready", "2026-09-20", True, "Villa"),
		row("Frame up", "2026-10-02", False, "Pergola"),
		row("Keys", None, False, "Villa"),
	]
	found = lanes(rows, "Villa", {"Handrails": "Handrails", "Pergola": "Pergola"})
	# Main first, then by each part's next milestone; within a part, soonest first and undated last.
	assert [one["key"] for one in found] == ["Villa", "Pergola", "Handrails"]
	assert found[0]["title"] is None and [one["subject"] for one in found[0]["milestones"]] == ["Site ready", "Keys"]
	assert found[0]["done"] == 1
	assert lanes(rows[:2][1:], "Villa", {}) == []
	read = (PROJECT / "milestones.py").read_text()
	assert '"lanes": lanes(rows, project, titles) if not tree.narrowed(project) else [],' in read
	src = tree.ROOT / "frontend" / "src" / "project"
	assert '<MilestoneLanes v-if="view.milestones.lanes?.length"' in (src / "Overview.vue").read_text()
	vue = (src / "MilestoneLanes.vue").read_text()
	assert "<Tooltip" in vue and '__("Today")' in vue and '<Rows class="md:hidden"' in vue


def test_hours_on_an_invoice_respect_a_whole_unit():
	"""A retainer's fee item is usually a visit or a month, counted in Nos;
	its hours over, and Invoice Time's, go through one line maker that
	never asks ERPNext for part of a whole unit."""
	billing = (PROJECT / "billing.py").read_text(encoding="utf-8")
	retainer = (PROJECT / "retainer.py").read_text(encoding="utf-8")
	maker = billing[billing.index("def hours_line") :].split("\n\n\n")[0]
	assert "must_be_whole_number" in maker
	assert "hours_line(item, line[\"hours\"]" in billing
	assert "billing.hours_line(" in retainer and '"qty": round(extra' not in retainer


def test_time_groups_add_up_every_entry_not_only_those_sent():
	flt = lambda value=0, *args: float(value or 0)  # noqa: E731
	space = _load(PROJECT / "hours.py", ("state", "sums"), flt=flt)
	rows = [
		_Row(parent="TS-1", activity_type="Fitting", task="T1", project="P", hours=4, is_billable=1, sales_invoice=None, docstatus=1, base_billing_amount=400, base_costing_amount=200),
		_Row(parent="TS-1", activity_type="Fitting", task="T1", project="P", hours=2, is_billable=1, sales_invoice=None, docstatus=1, base_billing_amount=200, base_costing_amount=100),
		_Row(parent="TS-2", activity_type="Fitting", task=None, project="P", hours=3, is_billable=0, sales_invoice=None, docstatus=0, base_billing_amount=0, base_costing_amount=90),
	]
	people = {"TS-1": {"user": "a@x", "name": "Arun"}, "TS-2": {"user": "b@x", "name": "Bilal"}}
	found = space["sums"](rows, people, {"T1": "Install glass"}, lambda row: None)
	arun = next(one for one in found if one["who"] == "Arun")
	assert (arun["entries"], arun["hours"], arun["amount"], arun["task_subject"]) == (2, 6.0, 600.0, "Install glass")
	assert next(one for one in found if one["who"] == "Bilal")["state"] == "Draft"
	hours = (PROJECT / "hours.py").read_text()
	assert '"sums": sums(rows, people, tasks' in hours and '"all_route": money_route("Timesheet"' in hours
	vue = (tree.ROOT / "frontend" / "src" / "project" / "Time.vue").read_text()
	assert "said.value.sums" in vue and "__('Open {0} Older Entries', [said.more])" in vue


def test_money_shows_its_totals_to_every_reader_and_links_only_for_those_who_may_open():
	money = (PROJECT / "money.py").read_text()
	# The figure is the project's, its route only for whoever reads the doctype.
	assert "if doctype and _sees(doctype):" in money
	assert "if _sees(doctype):\n\t\t\tcustomer.append" not in money
	assert '_opens(received)' in money and '_opens(paid)' in money
	# Amounts are in the project's company's currency, as its base amounts are.
	assert '"currency": currency(project)' in money and 'frappe.db.get_default("currency")' not in money


def test_a_debit_note_is_never_late_and_the_rules_stand_in_hooks():
	flt = lambda value=0, *args: float(value or 0)  # noqa: E731
	past_due = _load(PROJECT / "money.py", ("past_due",), flt=flt)["past_due"]
	note = [{"due_date": "2026-07-01", "amount": -1200, "held": False}]
	assert past_due(note, -1200, "2026-10-08") is None
	bill = [{"due_date": "2026-07-01", "amount": 1200, "held": False}]
	assert past_due(bill, 1200, "2026-10-08")["due"] == 1200
	# A disabled user can't join through the desk form, nor a retainer's
	# hours be billed outside their month.
	assert '"onedesk.one_project.members.enabled"' in HOOKS
	assert '"onedesk.one_project.retainer.billed_by_month"' in HOOKS
