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
	assert (
		'"onedesk.one_project.calendar.LAYERS"' in HOOKS
		and '"onedesk.one_project.plan.before_validate"' in HOOKS
	)


def test_a_project_board_is_shaped_as_it_is_made():
	space = _load(PROJECT / "board.py", ("COLUMNS", "CARD", "shape"), json=json)
	board = _Board(
		reference_doctype="Task",
		field_name="status",
		columns=[
			_Row(column_name=name)
			for name in ("Open", "Working", "Overdue", "Completed", "Cancelled", "Template")
		],
		fields=None,
		show_labels=1,
	)
	assert space["shape"](board) is True
	shown = {one.column_name: one.status for one in board.columns}
	assert "Overdue" not in shown and shown["Cancelled"] == shown["Template"] == "Archived"
	assert shown["Working"] == "Active" and json.loads(board.fields) == ["priority", "exp_end_date"]
	assert space["shape"](board) is False, "shaping twice changes nothing"
	assert (
		space["shape"](_Board(reference_doctype="Opportunity", field_name="sales_stage", columns=[])) is False
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


def test_erpnexts_dependants_can_find_their_project():
	body = _body((PROJECT / "plan.py").read_text(), "before_validate")
	assert 'for row in doc.get("depends_on") or []' in body and "row.project = doc.project" in body


def test_a_project_is_its_members():
	source = (PROJECT / "members.py").read_text()
	assert 'MANAGERS = ("Projects Manager",)' in source and 'WORKER = "Projects User"' in source
	seen = _body(source, "visible")
	assert "unlisted" in seen and "member" in seen and "owned" in seen and "under(" in seen
	assert "return not manages(user) and WORKER in frappe.get_roles(user)" in _body(source, "narrowed"), (
		"select-only roles keep their lists"
	)
	assert (
		'"Project": "onedesk.one_project.members.allowed"' in HOOKS
		and '"Project": "onedesk.one_project.members.query"' in HOOKS
	)
	assert "onedesk.one_project.members.forget" in HOOKS


def test_a_member_can_be_added_without_outgoing_mail():
	source = (PROJECT / "members.py").read_text()
	invite = _body(source, "invite")
	assert '"default_outgoing": 1, "enable_outgoing": 1' in invite and "row.welcome_email_sent = 1" in invite
	assert '"before_validate": "onedesk.one_project.members.invite"' in HOOKS


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


def test_the_tree_report_puts_each_project_under_its_parent():
	ordered = _load(
		PROJECT / "report" / "project_tree" / "project_tree.py",
		("ordered",),
		tree=type("T", (), {"PARENT": "one_parent"}),
	)["ordered"]
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
	assert (
		'"onedesk.one_project.tree.validate"' in HOOKS
		and '"Project": ["onedesk.one_project.tree.dashboard"]' in HOOKS
	)
	assert "tree.below(projects, tree.parents())" in _body((PROJECT / "members.py").read_text(), "under")
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


def test_the_overview_is_the_whole_tree_and_only_figures():
	source = (PROJECT / "overview.py").read_text()
	assert "tree.below({project}, tree.parents())" in source and "members.sees(one, user)" in source
	page = (tree.APP / "public" / "js" / "project.js").read_text()
	assert "onedesk.one_project.overview.overview" in page and "onedesk.band.show" in page
	assert "chart" not in page.lower().replace('__("gantt chart")', ""), "figures, not charts"


def test_a_dependant_moves_after_what_it_waits_on():
	from datetime import date, timedelta

	space = _load(
		PROJECT / "plan.py",
		("moved_after",),
		date_diff=lambda a, b: (a - b).days,
		add_days=lambda day, n: day + timedelta(days=n),
	)
	moved = space["moved_after"]
	starts, ends = date(2026, 10, 1), date(2026, 10, 3)
	assert moved(starts, ends, date(2026, 10, 5), "Open") == (date(2026, 10, 6), date(2026, 10, 8)), (
		"keeps its length"
	)
	assert moved(starts, ends, date(2026, 9, 20), "Open") is None, "already after it"
	assert moved(starts, ends, date(2026, 10, 5), "Working") is None, "started work stays"
	assert moved(None, ends, date(2026, 10, 5), "Open") is None


def test_a_slip_crosses_sub_projects_and_the_plan_is_the_tree():
	assert (
		'"on_update": "onedesk.one_project.plan.reschedule"'
		in HOOKS.split('"Task": {', 1)[1].split("},", 1)[0]
	)
	body = _body((PROJECT / "plan.py").read_text(), "reschedule")
	assert 'has_value_changed("exp_end_date")' in body and "- {doc.project}" in body, (
		"ERPNext's own pass does its project"
	)
	page = (tree.APP / "public" / "js" / "project.js").read_text()
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
	source = (PROJECT / "templates.py").read_text()
	assert '"is_milestone", "expected_time"' in source and '"one_steps"' in _body(source, "task_made")
	assert '"onedesk.one_project.templates.task_made"' in HOOKS.split('"Task": {', 1)[1].split("},", 1)[0]
	assert HOOKS.count('"onedesk.one_project.templates.settle"') == 2, "after_install and after_migrate"
	assert "doc.is_template" in _body((TASK / "capture.py").read_text(), "task_made"), "nobody's work"
	access = (TASK / "access.py").read_text()
	assert (
		'doc.get("is_template") and sees_projects(user)' in access and "`tabTask`.`is_template` = 1" in access
	)
	assert "_write(doc)" in _body((PROJECT / "naming.py").read_text(), "validate"), (
		"the prefix names a template's tasks"
	)
	assert "after_rollback.add(_forget)" in (PROJECT / "naming.py").read_text()
	page = (tree.APP / "public" / "js" / "project.js").read_text()
	assert "onedesk.one_project.templates.save_as" in page
	assert '"Project Template": "public/js/project_template.js"' in HOOKS
	for rail in (
		PROJECT / "sidebar" / "oneproject" / "oneproject.json",
		TASK / "sidebar" / "onetask" / "onetask.json",
	):
		tasks = next(i for i in json.loads(rail.read_text())["items"] if i.get("label") == "Tasks")
		assert "is_template" in tasks["filters"], rail.name


def test_time_is_invoiced_by_activity():
	space = _load(PROJECT / "billing.py", ("lines",), flt=lambda value: float(value or 0))
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


def test_an_order_for_extra_work_is_named_by_what_it_orders():
	from types import SimpleNamespace as Row

	space = _load(PROJECT / "billing.py", ("title",), _=lambda text: text)

	class Order(dict):
		name = "SAL-ORD-1"

	def order(*names):
		return Order(items=[Row(item_name=one, item_code=one) for one in names])

	assert space["title"](order("Handrail Installation")) == "Handrail Installation"
	assert space["title"](order("Handrails", "Glass", "Fixings")) == "Handrails and 2 more"
	assert space["title"](order()) == "SAL-ORD-1"


def test_an_order_under_a_project_becomes_its_sub_project():
	orders = HOOKS.split('"Sales Order": {', 1)[1].split("},", 1)[0]
	assert '"onedesk.one_project.billing.ordered"' in orders
	for doctype in ("quotation", "sales_order"):
		custom = json.loads((PROJECT / "custom" / f"{doctype}.json").read_text())
		assert [f["fieldname"] for f in custom["custom_fields"]] == ["one_project"], (
			"the same field, so the mapping carries it"
		)
	source = (PROJECT / "billing.py").read_text()
	assert "make_project(doc.name)" in source and 'project.set("one_parent", parent)' in source
	assert 'data["non_standard_fieldnames"]["Quotation"] = "one_project"' in (PROJECT / "tree.py").read_text()
	assert '"Quotation": "public/js/quotation.js"' in HOOKS
	page = (tree.APP / "public" / "js" / "project.js").read_text()
	assert '"onedesk.one_project.billing.invoice_time"' in page and "frappe.model.open_mapped_doc" in page
	assert "get_projectwise_timesheet_data" in source, "ERPNext's own list of hours not yet billed"


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
	assert 'additional_timeline_content = {"Project": ["onedesk.one_project.updates.timeline"]}' in HOOKS
	assert '"Notification Log"' in _body(source, "_ask") and "if _mail()" in _body(source, "_ask"), (
		"asked in One, mailed where mail goes"
	)
	custom = json.loads((PROJECT / "custom" / "project.json").read_text())
	frequency = next(p for p in custom["property_setters"] if p["field_name"] == "frequency")
	assert "Hourly" not in frequency["value"]
	page = (tree.APP / "public" / "js" / "project.js").read_text()
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
	assert '"onedesk.one_project.portal.invited"' in HOOKS.split('"Contact": {', 1)[1].split("},", 1)[0]
	source = (PROJECT / "portal.py").read_text()
	assert 'customer.append("portal_users", {"user": doc.user})' in source, (
		"the only thing ERPNext's portal reads"
	)
	assert "has_website_permission(doc" in _body(source, "may_see")
	page = (tree.APP / "www" / "projects.py").read_text()
	assert "portal.view(project)" in page, "One's page at ERPNext's address"
	html = (tree.APP / "www" / "projects.html").read_text()
	assert "_assign" not in html and "timesheet" not in html.lower() and "/tasks/new" not in html, (
		"nothing of the team's"
	)
	fields = source.split('"Task",', 1)[1].split("order_by", 1)[0]
	assert "_assign" not in fields and "owner" not in fields


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
	assert '"one_manager": user' in _body((PROJECT / "members.py").read_text(), "visible"), (
		"who runs it sees it"
	)
	assert "frm.doc.one_health" in (tree.APP / "public" / "js" / "project.js").read_text()
	rail = json.loads((PROJECT / "sidebar" / "oneproject" / "oneproject.json").read_text())
	items = {item["label"]: item for item in rail["items"]}
	assert "is_milestone" in items["Milestones"]["filters"]
	assert "Employee Boarding" in items["Projects"]["filters"], "somebody's first week is not client work"
	lifecycle = (tree.APP / "one_hr" / "lifecycle.py").read_text()
	assert 'BOARDING = "Employee Boarding"' in lifecycle
	assert HOOKS.count('"on_submit": "onedesk.one_hr.lifecycle.typed"') == 2
	assert (
		'where["project_type"] = ["!=", BOARDING]'
		in (PROJECT / "report" / "project_tree" / "project_tree.py").read_text()
	)
