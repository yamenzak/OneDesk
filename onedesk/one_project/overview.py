"""A project's page answers first: how far it has got, whether it is on time,
what it has cost against what was budgeted, what has been billed against what
there is to bill, what is late and what comes next, and the hours logged on
it week by week for a quarter.

All of it is ERPNext's own: `expected_end_date`, the project's tasks, and
the money on its documents as money.py adds it up. A project with sub-projects answers for the whole tree
(tree.py), since the villa's question is about the villa, handrails included.
"""

from typing import Annotated

import frappe
from frappe.utils import date_diff, flt, formatdate, getdate, nowdate

from onedesk.one import figures
from onedesk.one_project import members, money, tree

#: What a task that is still to do cannot be.
DONE = ("Completed", "Cancelled", "Template")


def days_left(end, today, finished: bool) -> int | None:
	"""Days until the expected end, negative once past; None when there is no
	end or the project is finished. Pure."""
	if not end or finished:
		return None
	return date_diff(getdate(end), getdate(today))


def share(done: int, total: int) -> int:
	"""How much of the work is done, out of 100. Pure."""
	return round(100 * done / total) if total else 0


def progress(method: str | None, tasks: list, manual: float) -> float:
	"""How much of the work is done, out of 100, as ERPNext measures a
	project's own tasks (its % Complete Method), over a whole tree's: tasks
	completed or cancelled, each task's progress, or that progress by each
	task's weight. A completed task is all done. Pure."""
	if method == "Manual" or not tasks:
		return flt(manual)

	def done(task) -> float:
		return 100.0 if task.get("status") == "Completed" else flt(task.get("progress"))

	if method == "Task Weight":
		weight = sum(flt(task.get("task_weight")) for task in tasks)
		if weight:
			return flt(sum(done(task) * flt(task.get("task_weight")) for task in tasks) / weight, 2)
	if method == "Task Progress":
		return flt(sum(done(task) for task in tasks) / len(tasks), 2)
	finished = sum(1 for task in tasks if task.get("status") in ("Completed", "Cancelled"))
	return flt(100 * finished / len(tasks), 2)


def roll_up(project: str | None) -> None:
	"""Store the tree's progress as ERPNext's own % Complete on the project
	and every project above it that has sub-projects, so the page, the lists,
	the reports and the parents read one figure. A project without
	sub-projects keeps ERPNext's own, and a Manual one what was typed."""
	if not project:
		return
	of = tree.parents()
	down = tree.children(of)
	for one in tree.above(project, of):
		if not down.get(one):
			continue
		doc = frappe.db.get_value(
			"Project", one, ["percent_complete", "percent_complete_method"], as_dict=True
		)
		if not doc or doc.percent_complete_method == "Manual":
			continue
		tasks = frappe.get_all(
			"Task",
			filters={"project": ["in", list(tree.below({one}, of))], "status": ["!=", "Template"]},
			fields=["status", "progress", "task_weight"],
		)
		value = progress(doc.percent_complete_method, tasks, doc.percent_complete)
		if flt(value, 2) != flt(doc.percent_complete, 2):
			frappe.db.set_value("Project", one, "percent_complete", value, update_modified=False)


def task_changed(doc, method=None) -> None:
	"""Task on_update and after_delete, after ERPNext's own: the projects
	above it measure the tree again."""
	roll_up(doc.project)


def project_changed(doc, method=None) -> None:
	"""Project on_update, after ERPNext set its own figure: it and the
	projects above measure their trees again, and the one it left too."""
	roll_up(doc.name)
	before = doc.get_doc_before_save()
	if before and before.get("one_parent") and before.get("one_parent") != doc.get("one_parent"):
		roll_up(before.get("one_parent"))


@frappe.whitelist()
@frappe.read_only()
def overview(project: Annotated[str, "The project."]) -> dict:
	frappe.has_permission("Project", "read", doc=project, throw=True)
	user = frappe.session.user
	doc = frappe.db.get_value(
		"Project",
		project,
		["status", "expected_end_date", "percent_complete", "percent_complete_method"],
		as_dict=True,
	)
	projects = [
		one for one in tree.below({project}, tree.parents()) if one == project or members.sees(one, user)
	]
	today = nowdate()

	counts = frappe.get_all(
		"Task",
		filters={"project": ["in", projects], "status": ["not in", ("Cancelled", "Template")]},
		fields=["status", {"COUNT": "*", "as": "n"}],
		group_by="status",
	)
	total = sum(row.n for row in counts)
	done = sum(row.n for row in counts if row.status == "Completed")
	open_ = [["project", "in", projects], ["status", "not in", DONE]]
	# frappe reads a missing date as the earliest one, so a task with no due
	# date would count as late.
	late_filters = [*open_, ["exp_end_date", "is", "set"], ["exp_end_date", "<", today]]
	late = frappe.db.count("Task", late_filters)
	# A late task is Overdue whatever its status says: ERPNext only marks
	# one so overnight, and the figures count it late from the day after.
	statuses = {row.status: row.n for row in counts}
	if late:
		for row in frappe.get_all(
			"Task", filters=late_filters, fields=["status", {"COUNT": "*", "as": "n"}], group_by="status"
		):
			statuses[row.status] -= row.n
		statuses["Overdue"] = late
		statuses = {status: n for status, n in statuses.items() if n}
	milestone = frappe.get_all(
		"Task",
		filters=[*open_, ["is_milestone", "=", 1], ["exp_end_date", ">=", today]],
		fields=["name", "subject", "exp_end_date"],
		order_by="exp_end_date asc",
		limit=1,
	)
	said = money.money(project)
	return {
		"projects": len(projects),
		"tree": sorted(projects),
		"tasks": total,
		"done": done,
		"statuses": statuses,
		# A completed project is done, whatever its tasks say: one completed
		# with no tasks of its own has none to count.
		# ERPNext's own % Complete, the tree's for a project with sub-projects
		# (roll_up), so this page and the lists say the same.
		"share": 100 if doc.status == "Completed" else round(flt(doc.percent_complete)),
		"end": str(doc.expected_end_date) if doc.expected_end_date else None,
		"days_left": days_left(doc.expected_end_date, today, doc.status in ("Completed", "Cancelled")),
		"estimated": said["budget"],
		"cost": said["spent"],
		"billed": said["invoiced"],
		"to_bill": said["contract"],
		"margin": said["margin"],
		"forecast_margin": said["forecast_margin"],
		"forecast": said["forecast_margin"] is not None,
		"late": late,
		"milestone": milestone[0] if milestone else None,
		"currency": said["currency"],
		"weekly": _weekly(projects, getdate(today)),
	}


def _weekly(projects: list[str], day) -> dict | None:
	"""The hours logged on the tree's timesheets, a bar a week for twelve
	weeks, as the reader's list of timesheets would give them."""
	if not frappe.has_permission("Timesheet", "read"):
		return None
	starts = figures.weeks(day)
	rows = frappe.get_list(
		"Timesheet Detail",
		parent_doctype="Timesheet",
		filters=[
			["Timesheet Detail", "project", "in", projects],
			["Timesheet Detail", "from_time", ">=", str(starts[0])],
			["Timesheet", "docstatus", "<", 2],
		],
		fields=["from_time", "hours"],
		limit_page_length=0,
	)
	values = figures.by_week(((getdate(row.from_time), flt(row.hours)) for row in rows), day)
	if not any(values):
		return None
	return {
		"labels": [formatdate(one, "d MMM") for one in starts],
		"values": [round(one, 1) for one in values],
		"total": round(sum(values), 1),
	}
