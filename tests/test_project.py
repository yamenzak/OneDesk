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


def test_a_member_is_told_in_ours_not_erpnexts_mail():
	# ERPNext's English invitation is never sent, with mail or without; the
	# member hears Added to Project through the hub (tell.py).
	source = (PROJECT / "members.py").read_text()
	invite = _body(source, "invite")
	assert "row.welcome_email_sent = 1" in invite and "Email Account" not in invite
	assert (
		'"onedesk.one_project.members.invite",\n\t\t\t"onedesk.one_project.members.unlist",'
		in HOOKS
	)
	# A member taken off loses the share before ERPNext's System-Manager-only removal.
	unlist = _body(source, "unlist")
	assert '"DocShare"' in unlist and "ignore_permissions=True" in unlist
	tell = (PROJECT / "tell.py").read_text()
	assert 'notify.notify("Added to Project"' in tell and 'notify.notify("Made Project Manager"' in tell
	assert 'notify.notify("Project Health"' in tell and 'WORSE = ("At Risk", "Off Track")' in tell
	assert '"onedesk.one_project.tell.changed"' in HOOKS
	types = (PROJECT / "notifications.py").read_text()
	for name in ("Added to Project", "Made Project Manager", "Project Health"):
		assert f'"name": _lt("{name}")' in types


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
	assert '"Project": "public/js/project_tree.js"' in HOOKS and '"Project": "public/js/project_calendar.js"' in HOOKS
	tree_js = (tree.APP / "public" / "js" / "project_tree.js").read_text()
	assert 'get_tree_nodes: "onedesk.one_project.tree.nodes"' in tree_js and "disable_add_node: true" in tree_js
	timeline = (tree.APP / "public" / "js" / "project_calendar.js").read_text()
	assert '"onedesk.one_project.tree.milestones"' in timeline and "depends_on: null" in timeline
	assert not (PROJECT / "report" / "project_tree").exists()
	assert "onedesk.one_project.patches.tree_is_a_view" in (tree.APP / "patches.txt").read_text()


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


def test_the_overview_is_the_whole_tree_and_its_chart_is_the_bands():
	source = (PROJECT / "overview.py").read_text()
	assert "tree.below({project}, tree.parents())" in source and "members.sees(one, user)" in source
	# What the page says above its fields is its Record Head, over the overview.
	heads = (PROJECT / "heads.py").read_text()
	assert "overview.overview(name)" in heads and '"doctype": "Project"' in heads
	assert '"charts": [{"chart": "project.hours"}]' in heads
	page = "".join((tree.APP / "public" / "js" / name).read_text() for name in ("project.js", "project_actions.js"))
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
	task = HOOKS.split('"Task": {', 1)[1].split("\n\t},", 1)[0]
	assert '"onedesk.one_project.plan.reschedule"' in task.split('"on_update"', 1)[1]
	body = _body((PROJECT / "plan.py").read_text(), "reschedule")
	assert 'has_value_changed("exp_end_date")' in body and "- {doc.project}" in body, (
		"ERPNext's own pass does its project"
	)
	page = "".join((tree.APP / "public" / "js" / name).read_text() for name in ("project.js", "project_actions.js"))
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
	page = "".join((tree.APP / "public" / "js" / name).read_text() for name in ("project.js", "project_actions.js"))
	assert "onedesk.one_project.templates.save_as" in page
	assert '"Project Template": "public/js/project_template.js"' in HOOKS
	# Tasks are OneTask's rail's, which leaves a template's tasks out.
	rail = TASK / "sidebar" / "onetask" / "onetask.json"
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
	# The project and the Extra Work tick, by the same names on both, so the
	# mapping carries them from quotation to order.
	quote = json.loads((PROJECT / "custom" / "quotation.json").read_text())
	assert [f["fieldname"] for f in quote["custom_fields"]] == ["project", "one_extra_work"]
	order_ = json.loads((PROJECT / "custom" / "sales_order.json").read_text())
	assert [f["fieldname"] for f in order_["custom_fields"]] == ["one_extra_work", "one_retention", "one_retention_due"]
	source = (PROJECT / "billing.py").read_text()
	assert "make_project(doc.name)" in source and 'project.set("one_parent", parent)' in source
	assert 'doc.db_set("project", project.name)' in source, "the order is the sub-project's"
	assert "onedesk.one_project.patches.extra_work" in (tree.APP / "patches.txt").read_text()
	assert "Quote Extra Work" in (tree.APP / "public" / "js" / "project.js").read_text()
	assert '"Quotation": "public/js/quotation.js"' in HOOKS
	page = "".join((tree.APP / "public" / "js" / name).read_text() for name in ("project.js", "project_actions.js"))
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
	assert '"Project": ["onedesk.one_project.updates.timeline"]' in HOOKS
	assert 'notify.notify("Project Update Asked"' in _body(source, "_ask") and "if _mail()" in _body(
		source, "_ask"
	), "asked in One, mailed where mail goes"
	custom = json.loads((PROJECT / "custom" / "project.json").read_text())
	frequency = next(p for p in custom["property_setters"] if p["field_name"] == "frequency")
	assert "Hourly" not in frequency["value"]
	page = "".join((tree.APP / "public" / "js" / name).read_text() for name in ("project.js", "project_actions.js"))
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
	source = (PROJECT / "portal.py").read_text()
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
	assert "doc.one_health" in (PROJECT / "heads.py").read_text(), "health leads the band"
	rail = json.loads((PROJECT / "sidebar" / "oneproject" / "oneproject.json").read_text())
	items = {item["label"]: item for item in rail["items"]}
	assert "Employee Boarding" in items["Projects"]["filters"], "somebody's first week is not client work"
	lifecycle = (tree.APP / "one_hr" / "lifecycle.py").read_text()
	assert 'BOARDING = "Employee Boarding"' in lifecycle
	assert HOOKS.count('"on_submit": "onedesk.one_hr.lifecycle.typed"') == 2
	assert 'where = [["project_type", "!=", BOARDING]]' in (PROJECT / "tree.py").read_text()


def test_the_projects_list_says_status_and_names_the_manager():
	js = (tree.APP / "public" / "js" / "project_list.js").read_text()
	assert "hide_name_column: true" in js and "hide_name_filter: true" in js
	assert 'Open: "blue", "On hold": "orange", Completed: "green"' in js, "Open is not red, and a share is not a status"
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


def test_oneai_reads_a_project_as_its_page_does():
	ai = (PROJECT / "ai.py").read_text()
	assert (
		"overview.overview(project)" in ai and 'frappe.has_permission("Project", "read", doc=project)' in ai
	)
	assert "frappe.get_list(" in ai, "tasks are read as the reader"
	for tool in ("project_facts", "projects_needing_attention"):
		assert f'"onedesk.one_project.ai.{tool}"' in HOOKS
	assert '"onedesk.one_project.ai.SUGGESTIONS"' in HOOKS
	groups = (tree.APP / "one_ai" / "groups.py").read_text()
	assert (
		'"tools": ("project_facts", "projects_needing_attention")' in groups
		and '"One Project": "projects"' in groups
	)
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
		assert f'"{doctype}"' in HOOKS.split("doc_events", 1)[1] and "onedesk.one_project.chain.agree" in HOOKS
	for name in ("request_for_quotation", "material_request"):
		custom = json.loads((PROJECT / "custom" / f"{name}.json").read_text())
		assert [f["fieldname"] for f in custom["custom_fields"]] == ["project"]
	connections = (PROJECT / "tree.py").read_text()
	for doctype in ("Quotation", "Request for Quotation", "Supplier Quotation", "Payment Entry", "Expense Claim"):
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
	assert "said.money" in money_view and all(name in money_view for name in ('__("Forecast Margin")', "__('Customer')", "__('Cost')"))
	assert "onedesk().progress.ask" in (island / "Suppliers.vue").read_text()
	page = "".join((tree.APP / "public" / "js" / name).read_text() for name in ("project.js", "project_actions.js"))
	assert '"one_project_money"' in page
	heads = (PROJECT / "heads.py").read_text()
	assert '"project.forecast": forecast' in heads and '_lt("Forecast Margin")' in heads


def test_progress_bills_the_share_done_and_holds_retention_on_the_work():
	flt = lambda value=0, *args: round(float(value or 0), args[0]) if args else float(value or 0)  # noqa: E731
	space = _load(PROJECT / "progress.py", ("to_bill", "billed_share", "held", "split"), flt=flt)
	to_bill, billed_share, held, split = space["to_bill"], space["billed_share"], space["held"], space["split"]
	# 40% of one Lump Sum, nothing billed: 0.4. At 70% with 0.4 billed: 0.3.
	assert to_bill(1, 0, 40) == 0.4 and round(to_bill(1, 0.4, 70), 6) == 0.3
	# Never a credit for going backwards.
	assert to_bill(1, 0.4, 30) == 0
	assert billed_share([_Row(amount=80000, billed_amt=32000), _Row(amount=20000, billed_amt=0)]) == 32.0
	# Retention is the share of the work billed, whatever advance is set off:
	# 32,000 billed, 8,000 advance, 10% held.
	assert split(24000, 32000, 10) == (20800, 3200)
	# Retention is paid last: what's held is never more than what's owed.
	assert held(3200, 24000) == 3200 and held(3200, 1000) == 1000 and held(3200, 0) == 0


def test_subcontracts_are_billed_through_erpnexts_own_invoice():
	progress = (PROJECT / "progress.py").read_text()
	# ERPNext's own mappers, with the order's rate kept.
	assert "make_purchase_invoice" in progress and "make_sales_invoice" in progress
	assert "row.rate" not in progress
	assert 'LUMP_SUM = "Lump Sum"' in progress and '"must_be_whole_number": 0' in progress
	assert "allocate_advances_automatically = 1" in progress
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
	assert "def _suppliers(" in money and "held(" in money


def test_the_customers_contract_is_billed_the_same_way():
	assert '"Sales Order": "public/js/progress.js"' in HOOKS
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
	assert "new.submit()" in budget and "new.revision_of = old.name" in budget
	# Making one is for whoever ERPNext lets; nobody gets a back door.
	assert 'frappe.has_permission("Budget", "create", throw=True)' in budget
	assert "ignore_permissions" not in budget
	money_view = (tree.ROOT / "frontend" / "src" / "project" / "Money.vue").read_text()
	assert '"onedesk.one_project.budget.lines"' in money_view and "project.cost_type(" in money_view
	page = "".join((tree.APP / "public" / "js" / name).read_text() for name in ("project.js", "project_actions.js"))
	assert "onedesk.one_project.budget.set_budget" in page and '__("Add Cost Type")' in page


def test_the_money_is_told_and_read():
	kinds = (PROJECT / "notifications.py").read_text()
	assert '_lt("Over Budget")' in kinds and '_lt("Progress Bill Drafted")' in kinds
	budget = (PROJECT / "budget.py").read_text()
	# Once for each budget: a revised budget can tell again.
	assert 'dedupe_on=["document_type", "document_name"]' in budget and '("Budget", one["budget_name"])' in budget
	assert "budget.over(project)" in (PROJECT / "money.py").read_text()
	assert HOOKS.count('"onedesk.one_project.progress.drafted"') == 2
	assert "invoice.one_progress = done" in (PROJECT / "progress.py").read_text()
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
	assert guess(False, True, None) == "Time and Materials" and guess(False, False, "C") == "Time and Materials"
	assert guess(False, False, None) == "Internal"
	kinds = (PROJECT / "kinds.py").read_text()
	# The contract is ERPNext's own Sales Order, submitted, so Bill Progress works.
	assert "order.submit()" in kinds and 'project.db_set("sales_order", order)' in kinds
	assert 'frappe.has_permission("Project", "create", throw=True)' in kinds
	assert '"onedesk.one_project.kinds.fill"' in HOOKS and HOOKS.count('"onedesk.one_project.kinds.settle"') == 2
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
	assert "step.form.is_dialog = true;" in page
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
	assert "def views(kind: str, cash: dict, customer" in view and '"views": views(kind, cash, doc.customer)' in view
	assert 'frappe.has_permission("Purchase Order", "read")' in view
	script = (tree.ROOT / "frontend" / "src" / "project" / "ProjectPage.vue").read_text()
	assert '"onedesk.one_project.view.said"' in script
	# The page follows the record as a form does, through the kit's bridge to desk.
	for follows in ('follow("Project"', 'listen("one_project_money"'):
		assert follows in script
	# /desk/project/<name> is the page; ?edit=1 and a new project are the form.
	route = (tree.APP / "public" / "js" / "project_new.js").read_text()
	assert 'return ["project-view", name];' in route and 'has("edit")' in route and '"new-project"' in route
	assert "?edit=1" in script
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
		getdate=lambda value: value.date() if isinstance(value, datetime) else value, get_datetime=lambda value: value
	)
	after = space["after"]
	day = date(2026, 10, 5)
	empty = _Row(time_logs=[])
	assert after(empty, day) == datetime(2026, 10, 5, 9, 0)
	busy = _Row(time_logs=[_Row(to_time=datetime(2026, 10, 5, 12, 30)), _Row(to_time=datetime(2026, 10, 4, 18, 0))])
	assert after(busy, day) == datetime(2026, 10, 5, 12, 30)

	hours = (PROJECT / "hours.py").read_text()
	team = (PROJECT / "team.py").read_text()
	billing = (PROJECT / "billing.py").read_text()
	# Each reads as the reader reads the records behind it, and changes only
	# what the reader may change.
	for source in (hours, team, billing):
		assert 'frappe.has_permission("Project", "read"' in source
	assert 'parent_doctype="Timesheet"' in hours and 'frappe.has_permission("Timesheet", "create", throw=True)' in hours
	assert "timer._this_week(frappe.session.user)" in hours
	assert team.count('doc.check_permission("write")') == 2 and "doc.save()" in team
	assert "ignore_permissions" not in hours + team
	assert 'parent_doctype="Sales Invoice"' in billing and 'frappe.has_permission("Sales Invoice", "read")' in billing
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
	assert rate([{"billing_hours": 4, "billing_amount": 1200}, {"billing_hours": 2, "billing_amount": 600}]) == 300
	assert rate([]) == 0
	assert month_list("2026-08-12", "2026-10-04") == [date(2026, 10, 1), date(2026, 9, 1), date(2026, 8, 1)]
	assert len(month_list("2024-01-01", "2026-10-04")) == space["SHOWN"]

	source = (PROJECT / "retainer.py").read_text()
	# The month's time goes on the invoice, so submitting it marks that time
	# invoiced and Invoice Time never bills it again; a month is billed once.
	assert '"timesheets"' in source and "is invoiced already" in source
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
	assert "onedesk.project.invoice_month" in actions and '"onedesk.one_project.retainer.invoice_month"' in actions


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
	types = {str(one["name"]) for one in _load(PROJECT / "notifications.py", ("TYPES",), _lt=str)["TYPES"]}
	assert {"Retainer Month to Invoice", "Retainer Hours Used"} <= types
	assert '"onedesk.one_project.tell.retainer_months"' in HOOKS
	assert '"on_submit": "onedesk.one_project.tell.hours_used"' in HOOKS
	tell = (PROJECT / "tell.py").read_text()
	# Told once, when this timesheet takes the month past the allowance.
	assert "hours - here[one.name] < flt(one.one_monthly_hours) <= hours" in tell
	assert "retainer.invoiced(one.name, last)" in tell and "one.one_manager or one.owner" in tell
	readme = (PROJECT / "README.md").read_text().split("## Under the hood", 1)[0]
	assert "**Retainer Month to Invoice**" in readme and "**Retainer Hours Used**" in readme


def test_the_project_page_fits_a_phone():
	src = tree.ROOT / "frontend" / "src" / "project"
	# frappe-ui's own way: a list's columns by breakpoint, minor cells hidden.
	for name in ("Time", "Team", "Invoices", "Money", "Months"):
		vue = (src / f"{name}.vue").read_text()
		assert ':columns="{ base: [' in vue and "max-md:hidden" in vue, name
	page = (src / "ProjectPage.vue").read_text()
	assert '<Tabs v-model="tab" class="max-w-full overflow-x-auto' in page
	mount = (tree.ROOT / "frontend" / "src" / "kit" / "mount.js").read_text()
	assert 'setConfig("systemTimezone", zone.system)' in mount


def test_the_rail_is_projects_workload_time_and_setup():
	rail = json.loads((PROJECT / "sidebar" / "oneproject" / "oneproject.json").read_text())
	said = [(item["label"], item.get("link_to")) for item in rail["items"]]
	assert said == [
		("Projects", "Project"),
		("Workload", "Workload"),
		("Time", "Timesheet"),
		("Setup", None),
		("Project Templates", "Project Template"),
		("Rates", "Activity Type"),
	]
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
	# A sub-project reads after its parent, the parent's part quieter.
	assert "project_name(value, df, doc)" in listing and "`${up} › ${value}`" in listing
	assert '"one_health",' in listing and '"one_parent"' in listing
	custom = json.loads((PROJECT / "custom" / "project.json").read_text())
	setters = {
		(one.get("field_name"), one["property"]): one["value"] for one in custom["property_setters"]
	}
	assert setters[("customer", "in_standard_filter")] == "0"
	assert setters[("expected_end_date", "label")] == "Due Date"
	assert setters[("project_name", "width")] == "260"
	assert setters[(None, "sort_field")] == "modified" and setters[(None, "sort_order")] == "DESC"
	fields = {one["fieldname"]: one for one in custom["custom_fields"]}
	assert not fields["one_health"]["in_list_view"] and fields["one_health"]["in_standard_filter"]
	# The Tree's button is the list's.
	assert '__("Add {0}", [__("Project")])' in (tree.APP / "public" / "js" / "project_tree.js").read_text()
	# On a phone the list is as wide as the screen.
	css = (tree.APP / "public" / "css" / "desk.css").read_text()
	assert '[data-page-route="List/Project/List"] .frappe-list .result .list-row-container' in css


def test_the_other_views_of_projects_are_oneprojects_own():
	listing = (tree.APP / "public" / "js" / "project_list.js").read_text()
	# Every view leaves out the HR checklists until the filter is cleared.
	assert 'filters: [["project_type", "!=", "Employee Boarding"]]' in listing
	# Report: the ID column is the Project column, and Project Name is not repeated.
	assert 'name !== "project_name"' in listing and 'built.name = built.content = __("Project")' in listing
	# Dashboard: OneProject's cards and charts, not ERPNext's two.
	assert 'module: "One Project"' in listing
	cards = {
		json.loads(path.read_text())["label"]: json.loads(path.read_text())
		for path in (PROJECT / "number_card").glob("*/*.json")
	}
	assert set(cards) == {"Open Projects", "At Risk or Off Track", "Past Due"}
	for card in cards.values():
		assert card["is_standard"] and card["is_public"] and card["document_type"] == "Project"
		assert ["Project", "project_type", "!=", "Employee Boarding", False] in json.loads(card["filters_json"])
	charts = {path.stem: json.loads(path.read_text()) for path in (PROJECT / "dashboard_chart").glob("*/*.json")}
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
	assert "built.colors = labels.map((label) => named[label]" in colours and "built.showLegend = 0" in colours
	assert '"/assets/onedesk/js/chart_colors.js"' in (tree.APP / "hooks.py").read_text()
	# Kanban: a board by health, made once.
	board = (PROJECT / "board.py").read_text()
	assert 'HEALTH_BOARD = "Projects by Health"' in board
	assert 'HEALTH = {"On Track": "Green", "At Risk": "Orange", "Off Track": "Red"}' in board
	# Calendar is not a view of Projects.
	assert 'if (this.doctype === "Project") delete found.Calendar;' in listing


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
	assert space["project_of"]("@records/Project/PROJ-0008") is None and space["project_of"]("@featured/") is None
	# The file is marked; the project has a Cover, its picture wherever frappe shows one.
	file_fields = json.loads((PROJECT / "custom" / "file.json").read_text())["custom_fields"]
	assert [one["fieldname"] for one in file_fields] == ["one_featured"]
	custom = json.loads((PROJECT / "custom" / "project.json").read_text())
	cover = next(one for one in custom["custom_fields"] if one["fieldname"] == "one_cover")
	assert cover["fieldtype"] == "Attach Image" and cover["read_only"]
	assert any(one["property"] == "image_field" and one["value"] == "one_cover" for one in custom["property_setters"])
	# OneCloud shows it inside the project's own folder, and only there.
	names = (tree.APP / "one_storage" / "namespace.py").read_text()
	assert 'FEATURED = "@featured/"' in names and 'if doctype == "Project":' in names
	api = (tree.APP / "one_storage" / "api.py").read_text()
	assert 'return ("record", "Project", kind[1], "featured")' in api and "def _refeature(" in api
	upload = (tree.APP / "one_storage" / "upload.py").read_text()
	assert "media.check(fields[\"file_name\"])" in upload and "fields.update(one_featured=1, is_private=0)" in upload
	# The cover follows the folder, and hands over before a delete frappe would refuse.
	hooks = (tree.APP / "hooks.py").read_text()
	assert hooks.count('"onedesk.one_project.media.changed"') == 3
	assert "media.handing_over(self)" in (tree.APP / "one_storage" / "file.py").read_text()
	# The portal shows it; the agreements say who can open it.
	assert '"media": media.shown(project)' in (PROJECT / "portal.py").read_text()
	assert 'key="oneproject-featured"' in (PROJECT / "legal.py").read_text()


def test_a_projects_page_is_laid_out_for_its_kind():
	space = _load(PROJECT / "view.py", ("percent",), flt=float)
	percent = space["percent"]
	# Budget Used says the real share, past 100 when over; a bar stops at 100.
	assert percent(156, 100) == 156 and percent(5, 0) == 0 and percent(-5, 10) == 0
	view = (PROJECT / "view.py").read_text()
	assert '"value": f"{percent(cash[\'spent\'], cash[\'budget\'])}%"' in view
	# A task with no due date is not late: frappe reads a missing date as the
	# earliest one, so the date is asked for.
	assert view.count('["exp_end_date", "is", "set"],\n\t\t\t["exp_end_date", "<", today]') == 1
	assert '["exp_end_date", "is", "set"], ["exp_end_date", "<", today]' in (PROJECT / "overview.py").read_text()
	# Each thing shows once: a retainer's months and time not invoiced have
	# sections of their own, and a Fixed Price project's budget is its own.
	needs = view[view.index("def needs(") : view.index("def _budget_lines(")]
	assert "retainer.waiting" not in needs and "billing.unbilled" not in needs
	assert "if kind != kinds.FIXED:" in needs
	# This month's hours are the tree's, as Hours by Week counts them.
	assert '{"key": "hours", "hours": _month_hours(view["tree"])}' in view
	overview = (tree.ROOT / "frontend" / "src" / "project" / "Overview.vue").read_text()
	for kind in ("'Fixed Price'", "'Time and Materials'", "'Retainer'"):
		assert f'kind === {kind}' in overview
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
	assert '@frappe.whitelist(methods=["POST"])\ndef add()' in media and "upload._place(node(project)" in media


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
	for part in ("muted", "playsinline", ':loop="media.length === 1"', '@ended="i === at && next()"', "lessMotion()", "@mouseenter"):
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
		space.update(contract=lambda doc: order, quotation=lambda doc: quote)
		return space["_first"](None, {"contract": 500})

	assert first("SO-1", None) == {"key": "contract", "money": 500, "route": "/desk/sales-order/SO-1"}
	quoted = first(
		None, {"name": "QTN-1", "value": 180, "count": 1, "valid_till": "2026-11-05", "alternatives": False}
	)
	assert quoted["key"] == "quoted" and quoted["money"] == 180 and quoted["route"] == "/desk/quotation/QTN-1"
	assert first(None, None) == {"key": "contract", "money": 0, "action": "add_contract"}
	# With several open, which one is ordered is picked on their list.
	several = first(
		None, {"name": "QTN-2", "value": 195, "count": 2, "list": "/desk/quotation?x", "valid_till": None}
	)
	assert several["route"] == "/desk/quotation?x" and "action" not in several
	# While quoted, the quote's last day stands where Billed will be.
	days = lambda a, b: int(a[-2:]) - int(b[-2:])  # noqa: E731
	space = _load(PROJECT / "view.py", ("_valid",), _=lambda text: text, nowdate=lambda: "2026-10-05", date_diff=days)
	valid = space["_valid"]
	assert valid("2026-10-15") == {"key": "valid", "value": "2026-10-15", "date": True, "note": "In 10 days"}
	assert valid(None)["note"] is None
	assert 'second = [_valid(valid)]' in (PROJECT / "view.py").read_text()
	# Quoted, the order is the next step: the page's main button, while one
	# quote is open. A Fixed Price project can be quoted again until ordered.
	page = (tree.ROOT / "frontend" / "src" / "project" / "ProjectPage.vue").read_text()
	assert 'if (s.kind === "Fixed Price" && !s.contract && s.quotation?.count === 1 && can("create", "Sales Order"))' in page
	assert 'if (s.kind === "Fixed Price" && !s.contract) list.push({ label: __("New Quotation")' in page
	# Its quotations are listed, and work against billing waits for an order.
	view_py = (PROJECT / "view.py").read_text()
	assert '"quotes": _quotes(doc),' in view_py and "if contract(doc)\n\t\t\telse None" in view_py
	overview_vue = (tree.ROOT / "frontend" / "src" / "project" / "Overview.vue").read_text()
	assert '<Section v-if="view.billing" :title="__(\'Work and Billing\')">' in overview_vue
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
	assert 'can("create", "Sales Order")' in overview and "__(\"Add Contract\")" in overview
	assert '<Button v-if="one.button"' in (tree.ROOT / "frontend" / "src" / "kit" / "Figures.vue").read_text()
	actions = (tree.APP / "public" / "js" / "project_actions.js").read_text()
	assert "erpnext.selling.doctype.quotation.mapper.make_sales_order" in actions
	assert "onedesk.one_project.kinds.add_contract" in actions
	page = (tree.ROOT / "frontend" / "src" / "project" / "ProjectPage.vue").read_text()
	assert '__("New Quotation")' in page and '__("Quote Extra Work")' in page and '__("Make Order")' in page


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
		assert any(f"bill_in({doc}, {party})" in path.read_text() for doc in ("order", "invoice", "doc")), path
	# Hours are turned into the invoice's currency from each timesheet's own.
	billing = _load(
		PROJECT / "billing.py", ("in_currency",), flt=float, currency_rate=lambda a, b: {"AED": 1 / 4}.get(a, 1.0)
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
	assert "<Pill v-if=\"said.status === 'Open'\" :value=\"said.health\"" in facts, "health is an open project's"
	assert '"On hold": "amber"' in (tree.ROOT / "frontend" / "src" / "project" / "colors.js").read_text()
	assert '"On hold": "orange"' in (tree.APP / "public" / "js" / "project_list.js").read_text()
	assert "'amber' if doc.status == 'On hold'" in (tree.APP / "www" / "projects.html").read_text()
	# Completing or cancelling asks first, and closes the open tasks and
	# sub-projects with it; a task already closed keeps its status.
	change = status[status.index("def change(") : status.index("def due(")]
	assert "if (below or tasks) and not int(close):" in change
	assert 'OPEN_TASK = ["not in", ("Completed", "Cancelled", "Template")]' in status
	assert 'frappe.db.set_value("Task", name, "status", status)' in change
	# Opening a project ERPNext turned to progress by hand puts it back on its
	# tasks; one whose tasks are all done says it can't be opened.
	assert 'doc.percent_complete_method = "Task Completion"' in change
	page = (tree.ROOT / "frontend" / "src" / "project" / "ProjectPage.vue").read_text()
	assert 'if (fieldname === "status") return changeStatus(value);' in page
	assert '"onedesk.one_project.status.ask"' in page and '"onedesk.one_project.status.change"' in page
	# A completed project says what's still owed, and its manager is told.
	view = (PROJECT / "view.py").read_text()
	assert 'if doc.status == "Completed" and frappe.has_permission("Sales Invoice", "read"):' in view
	tell = (PROJECT / "tell.py").read_text()
	assert "completed(doc, before)" in tell and '"Project Completed"' in tell
	assert '"name": _lt("Project Completed")' in (PROJECT / "notifications.py").read_text()
