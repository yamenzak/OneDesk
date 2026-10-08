"""A project's team, for the page's Team view (docs/PROJECT-PAGE.md)."""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils import flt, get_first_day, getdate, nowdate

from onedesk.one_project import hours, tree

#: Task statuses that are no longer work to do.
DONE = ("Completed", "Cancelled", "Template")


@frappe.whitelist()
@frappe.read_only()
def team(
	project: Annotated[str, "The project."],
	only: Annotated[bool | None, "Only the project's own work, not what is under it."] = None,
) -> dict:
	"""Everyone on the project, members first, with their load and hours."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	doc = frappe.get_doc("Project", project)
	tree.narrow(project, only)
	projects = sorted(tree.scope(project))
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
	# Each person's job, from their Employee record: by their user, or the
	# employee a timesheet was for when they have no sign-in.
	jobs = {}
	for employee in frappe.get_all(
		"Employee",
		filters=[["user_id", "in", list(people) or [""]]],
		fields=["user_id", "designation"],
	) + frappe.get_all(
		"Employee",
		filters=[["name", "in", list(people) or [""]]],
		fields=["name as user_id", "designation"],
	):
		if employee.designation:
			jobs[employee.user_id] = employee.designation
	for user, one in people.items():
		known = found.get(user)
		one["job"] = jobs.get(user)
		one["signs_in"] = bool(known)
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
