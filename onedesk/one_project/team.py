"""A project's team, for the page's Team view (docs/PROJECT-PAGE.md).

The team is ERPNext's **Members** on the project (Project User), and with
them everyone the work names: the manager, whoever a task on the project or a
project under it is assigned to, and whoever logged time on it. Each says how
much is on them (open tasks, and how many are late) and how much they have
put in (hours this month and in all), read as the reader reads tasks and
timesheets.

Adding or removing a member is a change to the project, made by whoever may
change it, and saved as the form saves it, so ERPNext's own rules on members
(the welcome mail, who sees the project in the portal) run as they do there.
"""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils import flt, get_first_day, getdate, nowdate

from onedesk.one_project import hours, tree

#: Task statuses that are no longer work to do.
DONE = ("Completed", "Cancelled", "Template")


@frappe.whitelist()
@frappe.read_only()
def team(project: Annotated[str, "The project."]) -> dict:
	"""Everyone on the project, members first, with their load and hours."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	doc = frappe.get_doc("Project", project)
	projects = sorted(tree.below({project}, tree.parents()))
	people: dict[str, dict] = {}

	def person(user: str) -> dict:
		return people.setdefault(
			user,
			{
				"user": user,
				"member": False,
				"manager": False,
				"open": 0,
				"late": 0,
				"month": 0.0,
				"hours": 0.0,
			},
		)

	for row in doc.users:
		if row.user:
			person(row.user)["member"] = True
	if doc.get("one_manager"):
		person(doc.one_manager)["manager"] = True

	today = getdate(nowdate())
	for task in frappe.get_list(
		"Task",
		filters=[["project", "in", projects], ["status", "not in", DONE]],
		fields=["_assign", "exp_end_date"],
		limit_page_length=0,
	):
		for user in frappe.parse_json(task._assign or "[]"):
			one = person(user)
			one["open"] += 1
			if task.exp_end_date and getdate(task.exp_end_date) < today:
				one["late"] += 1

	month = getdate(get_first_day(nowdate()))
	rows = frappe.get_list(
		"Timesheet Detail",
		parent_doctype="Timesheet",
		filters=[["Timesheet Detail", "project", "in", projects], ["Timesheet", "docstatus", "<", 2]],
		fields=["parent", "hours", "from_time"],
		limit_page_length=0,
	)
	sheets = hours.whose({row.parent for row in rows})
	for row in rows:
		sheet = sheets.get(row.parent)
		if not sheet:
			continue
		one = person(sheet["key"])
		one.setdefault("shown", sheet["name"])
		one["hours"] += flt(row.hours)
		if row.from_time and getdate(row.from_time) >= month:
			one["month"] += flt(row.hours)

	found = {
		one.name: one
		for one in frappe.get_all(
			"User",
			filters={"name": ["in", list(people)]},
			fields=["name", "full_name", "user_image", "enabled"],
		)
	}
	for user, one in people.items():
		known = found.get(user)
		one["name"] = (known.full_name if known else None) or one.pop("shown", None) or user
		one.pop("shown", None)
		one["image"] = known.user_image if known else None
		# Only a user who can sign in can be made a member.
		one["can_join"] = bool(known and known.enabled) and not one["member"]
		one["hours"] = round(one["hours"], 1)
		one["month"] = round(one["month"], 1)
	return {
		"people": sorted(
			people.values(),
			key=lambda one: (not one["manager"], not one["member"], -one["open"], one["name"]),
		),
		"can_change": bool(frappe.has_permission("Project", "write", doc=doc)),
	}


@frappe.whitelist(methods=["POST"])
def add(project: Annotated[str, "The project."], user: Annotated[str, "Who joins it."]) -> dict:
	"""Make somebody a member of the project."""
	doc = frappe.get_doc("Project", project)
	doc.check_permission("write")
	if not frappe.db.exists("User", {"name": user, "enabled": 1}):
		frappe.throw(_("{0} is not a user here.").format(user))
	if not any(row.user == user for row in doc.users):
		doc.append("users", {"user": user})
		doc.save()
	return team(project)


@frappe.whitelist(methods=["POST"])
def remove(project: Annotated[str, "The project."], user: Annotated[str, "Who leaves it."]) -> dict:
	"""Take somebody off the project's members. Their tasks and time stay."""
	doc = frappe.get_doc("Project", project)
	doc.check_permission("write")
	kept = [row for row in doc.users if row.user != user]
	if len(kept) != len(doc.users):
		doc.users = kept
		doc.save()
	return team(project)
