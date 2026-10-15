"""What a customer sees of their projects, on ERPNext's portal."""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from onedesk.one_project import overview, tree

#: What a task is called on the customer's page, by its status.
SHOWN = {
	"Open": (lambda: _("To Do"), "gray"),
	"Working": (lambda: _("In Progress"), "blue"),
	"Pending Review": (lambda: _("In Review"), "orange"),
	"Completed": (lambda: _("Done"), "green"),
}


def view(project: str) -> dict:
	"""What the customer's page for a project shows. Raises when the reader
	may not see it. Progress is the whole tree the customer sees, since a
	villa's progress is its windows' and its handrails'."""
	doc = frappe.get_doc("Project", project)
	if not may_see(doc):
		raise frappe.PermissionError
	tasks = frappe.get_all(
		"Task",
		filters={"project": project, "status": ["in", list(SHOWN)]},
		fields=[
			"name",
			"subject",
			"status",
			"exp_end_date",
			"exp_start_date",
			"is_milestone",
			"parent_task",
			"lft",
		],
		order_by="lft asc",
	)
	of = tree.parents()
	share, done, total = progress(doc, of)
	for one in tasks:
		label, one.colour = SHOWN[one.status]
		one.shown = label()
		one.due = one.exp_end_date or one.exp_start_date
		one.late = bool(one.due and one.status != "Completed" and getdate(one.due) < getdate(nowdate()))
	under = tree.children(of).get(project, [])
	from onedesk.one_project import media

	# A member of the project sees its time unless Hide Timesheets is on, and
	# its files when View Attachments is, as on ERPNext's own page.
	member = next((row for row in doc.users if row.user == frappe.session.user), None)

	return {
		"doc": doc,
		# The photos and videos the project is shown with, its cover first.
		"media": media.shown(project),
		"parent": frappe.db.get_value("Project", doc.get(tree.PARENT), ["name", "project_name"], as_dict=True)
		if doc.get(tree.PARENT) and may_see(frappe.get_doc("Project", doc.get(tree.PARENT)))
		else None,
		"share": share,
		"done": done,
		"total": total,
		"days_left": overview.days_left(doc.expected_end_date, nowdate(), doc.status == "Completed"),
		"milestones": [one for one in tasks if one.is_milestone],
		"tasks": [one for one in tasks if not one.is_milestone],
		"projects": [
			one
			for one in frappe.get_all(
				"Project",
				filters={"name": ["in", under], "customer": doc.customer, "status": ["!=", "Cancelled"]},
				fields=["name", "project_name", "status", "percent_complete", "expected_end_date"],
				order_by="creation asc",
			)
		]
		if under
		else [],
		"order": frappe.db.get_value(
			"Sales Order",
			{"name": doc.sales_order, "docstatus": 1},
			["name", "grand_total", "currency"],
			as_dict=True,
		)
		if doc.sales_order
		else None,
		"invoices": frappe.get_all(
			"Sales Invoice",
			filters={"project": project, "docstatus": 1, "customer": doc.customer},
			fields=["name", "posting_date", "grand_total", "outstanding_amount", "currency", "status"],
			order_by="posting_date desc",
		),
		"time": time(project) if member and not member.hide_timesheets else None,
		"files": frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Project", "attached_to_name": project, "is_private": 0, "is_folder": 0},
			fields=["file_name", "file_url"],
			order_by="creation desc",
		)
		if member and member.view_attachments
		else None,
	}


#: How many of a project's latest days of time its portal page shows.
SHOWN_DAYS = 15


def time(project: str) -> dict:
	"""The project's submitted time for its portal page: the hours of each
	activity on its latest days, and the hours in all."""
	rows = frappe.db.sql(
		"""select date(from_time) as day, activity_type, sum(hours) as hours
		from `tabTimesheet Detail` where project = %s and docstatus = 1
		group by date(from_time), activity_type order by day desc, activity_type""",
		project,
		as_dict=True,
	)
	days = sorted({row.day for row in rows}, reverse=True)[:SHOWN_DAYS]
	rows = [row for row in rows if row.day in days]
	total = frappe.get_all(
		"Timesheet Detail", filters={"project": project, "docstatus": 1}, fields=[{"SUM": "hours", "as": "hours"}]
	)
	return {"rows": rows, "hours": flt(total[0].hours if total else 0)}


def progress(doc, of: dict | None = None) -> tuple[int, int, int]:
	"""How far along a project is for its customer, as its page and the list
	both say it: the tasks done of all the tasks in it and the sub-projects of
	the same customer; erpnext's own percentage where there are no tasks."""
	of = of if of is not None else tree.parents()
	theirs = [
		one
		for one in tree.below({doc.name}, of)
		if one == doc.name or frappe.db.get_value("Project", one, "customer") == doc.customer
	]
	counted = frappe.get_all(
		"Task", filters={"project": ["in", theirs], "status": ["in", list(SHOWN)]}, pluck="status"
	)
	done = sum(1 for one in counted if one == "Completed")
	share = (
		100
		if doc.status == "Completed"
		else overview.share(done, len(counted))
		if counted
		else round(flt(doc.percent_complete))
	)
	return share, done, len(counted)


#: A project's status, as the portal's Badge themes it.
TONES = {"Completed": "green", "Cancelled": "gray", "On hold": "amber"}

#: A task's colour (SHOWN), as the portal's Badge themes it.
TASK_TONES = {"orange": "amber"}


@frappe.whitelist()
def page(project: str) -> dict:
	"""The portal's page for a project (frontend/portal), from `view`: how far
	along it is and when it ends, its photos, its milestones, sub-projects
	and tasks, the time and files a member is shown, its order and invoices.
	Every value as frappe formats it."""
	from frappe.utils import fmt_money

	said = view(project)
	doc = said["doc"]

	def task(one):
		return {
			"subject": one.subject,
			"tone": TASK_TONES.get(one.colour, one.colour),
			"status": one.shown,
			"due": _date(one.due),
			"late": one.late,
			"under": bool(one.parent_task),
		}

	return {
		"name": doc.name,
		"title": doc.project_name or doc.name,
		"tone": TONES.get(doc.status, "blue"),
		"status": _(doc.status),
		"share": said["share"],
		"done": said["done"],
		"total": said["total"],
		"ends": _date(doc.expected_end_date),
		"when": when(said["days_left"]),
		"late": (said["days_left"] or 0) < 0,
		"parent": {"name": said["parent"].name, "title": said["parent"].project_name}
		if said["parent"]
		else None,
		"media": [{key: one[key] for key in ("title", "url", "thumbnail", "kind")} for one in said["media"]],
		"milestones": [task(one) for one in said["milestones"]],
		"tasks": [task(one) for one in said["tasks"]],
		"projects": [
			{
				"name": one.name,
				"title": one.project_name or one.name,
				"ends": _("Ends {0}").format(_date(one.expected_end_date)) if one.expected_end_date else "",
				"tone": TONES.get(one.status, "blue"),
				"status": _(one.status),
				"share": progress(frappe.get_doc("Project", one.name))[0],
			}
			for one in said["projects"]
		],
		"time": {
			"hours": frappe.format(said["time"]["hours"], {"fieldtype": "Float"}),
			"rows": [
				{
					"what": _(one.activity_type) if one.activity_type else _("Time"),
					"day": _date(one.day),
					"hours": frappe.format(one.hours, {"fieldtype": "Float"}),
				}
				for one in said["time"]["rows"]
			],
		}
		if said["time"]
		else None,
		"files": [{"name": one.file_name, "url": one.file_url} for one in said["files"]]
		if said["files"]
		else [],
		"order": {
			"name": said["order"].name,
			"total": fmt_money(said["order"].grand_total, currency=said["order"].currency),
		}
		if said["order"]
		else None,
		"invoices": [
			{
				"name": one.name,
				"date": _date(one.posting_date),
				"tone": "amber" if one.outstanding_amount > 0 else "green",
				"status": _("Unpaid") if one.outstanding_amount > 0 else _("Paid"),
				"total": fmt_money(one.grand_total, currency=one.currency),
			}
			for one in said["invoices"]
		],
	}


def _date(value) -> str:
	return frappe.format(value, {"fieldtype": "Date"}) if value else ""


def may_see(doc) -> bool:
	"""A customer's portal user sees their customer's projects; anybody else
	whoever may read it in the desk."""
	from frappe.utils.user import is_website_user

	if not is_website_user():
		return bool(frappe.has_permission("Project", "read", doc))
	if not doc.customer:
		return False
	from erpnext.controllers.website_list_for_contact import has_website_permission

	return bool(has_website_permission(doc, "read", frappe.session.user))


def when(days: int | None) -> str | None:
	"""A project's end, said to its customer. Pure but for translation."""
	if days is None:
		return None
	if days < 0:
		return _("{0} days late").format(-days)
	if days == 0:
		return _("Due today")
	return _("In {0} days").format(days)
