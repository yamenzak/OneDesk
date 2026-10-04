"""The project page: what it shows, in one call, shaped by the project's kind
(kinds.py, docs/PROJECT-PAGE.md).

The page is `page/project_view` (public/js/project_page.js), opened at the
project's own address. `said` gives it the head (the kind, status, health,
the main action), the title line, the kind's four cards and its Overview. Everything is read from the
modules that work it out already: overview.py (tasks, dates, hours), money.py
(both sides), budget.py (cost types), billing.py (time not invoiced) and
tree.py (sub-projects). It reads as the person asking and checks they may
read the project.
"""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils import add_months, flt, get_first_day, get_fullname, getdate, nowdate

from onedesk.one_project import billing, budget, kinds, money, overview, tree

#: How many of each list the Overview shows.
SHOWN = 6

#: The tabs each kind has, in order, as far as they are built.
def views(kind: str, cash: dict) -> list[str]:
	"""The views the page shows beyond Overview and the tasks: Money when the
	reader may see any of it, Suppliers when there are subcontracts or the
	project is a Fixed Price one, which is where they're expected."""
	shown = []
	if cash["customer"] or cash["cost"]:
		shown.append("money")
	if cash["suppliers"] or (kind == kinds.FIXED and frappe.has_permission("Purchase Order", "read")):
		shown.append("suppliers")
	return shown


def share(part: float, whole: float) -> int:
	"""Part of a whole, out of 100, for a bar. Pure."""
	return max(0, min(100, round(100 * flt(part) / flt(whole)))) if flt(whole) else 0


@frappe.whitelist()
@frappe.read_only()
def said(project: Annotated[str, "The project."]) -> dict:
	frappe.has_permission("Project", "read", doc=project, throw=True)
	doc = frappe.get_doc("Project", project)
	kind = doc.get("one_kind") or kinds.guess(bool(doc.sales_order), False, doc.customer)
	view = overview.overview(project)
	cash = money.money(project)
	return {
		"name": doc.name,
		"title": doc.project_name,
		"modified": str(doc.modified),
		"notes": doc.notes,
		"percent_complete": flt(doc.percent_complete),
		"kind": kind,
		"status": doc.status,
		"health": doc.get("one_health"),
		"customer": doc.customer,
		"customer_name": frappe.db.get_value("Customer", doc.customer, "customer_name")
		if doc.customer
		else None,
		"starts": str(doc.expected_start_date) if doc.expected_start_date else None,
		"ends": str(doc.expected_end_date) if doc.expected_end_date else None,
		"manager": doc.get("one_manager"),
		"manager_name": get_fullname(doc.one_manager) if doc.get("one_manager") else None,
		"parent": doc.get("one_parent"),
		"parent_title": frappe.db.get_value("Project", doc.one_parent, "project_name")
		if doc.get("one_parent")
		else None,
		"team": [
			{"user": row.user, "name": get_fullname(row.user), "image": frappe.db.get_value("User", row.user, "user_image")}
			for row in doc.users
		],
		"contract": contract(doc),
		"currency": cash["currency"],
		"can_write": bool(frappe.has_permission("Project", "write", doc=doc)),
		"views": views(kind, cash),
		"money": cash,
		"can_budget": bool(frappe.has_permission("Project", "write", doc=doc)),
		"cards": cards(kind, doc, view, cash),
		"overview": _overview(kind, doc, view, cash),
	}


def contract(doc) -> str | None:
	"""The customer's contract: the project's Sales Order, or the first one
	submitted against it, still open to bill."""
	if doc.sales_order:
		return doc.sales_order
	found = frappe.get_all(
		"Sales Order",
		filters={"project": doc.name, "docstatus": 1, "status": ["not in", ("Closed", "Completed")]},
		order_by="transaction_date asc",
		pluck="name",
		limit=1,
	)
	return found[0] if found else None


def cards(kind: str, doc, view: dict, cash: dict) -> list[dict]:
	"""The kind's four figures, each with what it's of and a bar where there's
	something to fill."""
	done = {
		"key": "done",
		"value": f"{view['share']}%",
		"note": _("{0} of {1} tasks").format(view["done"], view["tasks"]) if view["tasks"] else None,
		"bar": view["share"],
	}
	if kind == kinds.FIXED:
		customer = {one["label"]: one["value"] for one in cash["customer"]}
		paid = customer.get(_("Paid"), 0)
		return [
			{
				"key": "contract",
				"money": cash["contract"],
				"note_money": [[_("Invoiced {0}"), [cash["invoiced"]]], [_("paid {0}"), [paid]]],
				"bar": share(cash["invoiced"], cash["contract"]),
			},
			{
				"key": "cost",
				"money": cash["spent"],
				"note_money": [[_("{0} more on order"), [cash["open_orders"]]]]
				if cash["open_orders"]
				else None,
				"bar": share(cash["spent"], cash["spent"] + cash["open_orders"]),
				"tone": "alarm" if cash["budget"] and cash["forecast_cost"] > cash["budget"] else None,
			},
			{
				"key": "forecast",
				"money": cash["forecast_margin"],
				"note": _("{0}% of the contract").format(share(cash["forecast_margin"], cash["contract"]))
				if cash["contract"] and cash["forecast_margin"] > 0
				else None,
				"tone": "alarm" if cash["forecast_margin"] < 0 else None,
			},
			done,
		]
	if kind in (kinds.TIME, kinds.RETAINER):
		hours = _month_hours(doc.name)
		waiting = billing.unbilled(doc.name)
		customer = {one["label"]: one["value"] for one in cash["customer"]}
		first = {
			"key": "hours",
			"hours": hours,
			"note": _("of {0} h a month").format(flt(doc.one_monthly_hours, 1))
			if kind == kinds.RETAINER and doc.one_monthly_hours
			else None,
			"bar": share(hours, doc.one_monthly_hours) if kind == kinds.RETAINER else None,
			"tone": "alarm"
			if kind == kinds.RETAINER and doc.one_monthly_hours and hours > doc.one_monthly_hours
			else None,
		}
		second = {
			"key": "unbilled",
			"money": flt(waiting.get("amount")),
			"note": _("{0} h").format(flt(waiting.get("hours"), 1)) if waiting.get("hours") else None,
		}
		if kind == kinds.RETAINER:
			second = {"key": "fee", "money": flt(doc.one_monthly_fee)}
		third = {
			"key": "invoiced",
			"money": cash["invoiced"],
			"note_money": [[_("Paid {0}"), [customer.get(_("Paid"), 0)]]],
		}
		return [first, second, third, _budget_card(cash) if cash["budget"] else done]
	return [_budget_card(cash), {"key": "spent", "money": cash["spent"]}, done, _due(view)]


def _budget_card(cash: dict) -> dict:
	return {
		"key": "budget",
		"value": f"{share(cash['spent'], cash['budget'])}%",
		"note_money": [[_("{0} of {1}"), [cash["spent"], cash["budget"]]]] if cash["budget"] else None,
		"bar": share(cash["spent"], cash["budget"]),
		"tone": "alarm" if cash["budget"] and cash["spent"] > cash["budget"] else None,
	}


def _due(view: dict) -> dict:
	left = view["days_left"]
	return {
		"key": "due",
		"value": view["end"],
		"date": True,
		"note": None
		if left is None
		else _("{0} days late").format(-left)
		if left < 0
		else _("Today")
		if left == 0
		else _("In {0} days").format(left),
		"tone": "alarm" if left is not None and left < 0 else None,
	}


def _overview(kind: str, doc, view: dict, cash: dict) -> dict:
	said = {
		"needs": needs(doc, view),
		"update": _latest_update(doc.name),
		"sub_projects": _sub_projects(doc.name),
	}
	if kind in (kinds.FIXED, kinds.INTERNAL):
		said["milestones"] = _milestones(view["tree"])
	if kind == kinds.FIXED:
		said["subcontracts"] = cash["suppliers"][:SHOWN]
		order = contract(doc)
		said["retention"] = (
			frappe.db.get_value("Sales Order", order, ["one_retention", "one_retention_due"], as_dict=True)
			if order
			else None
		)
	if kind in (kinds.TIME, kinds.RETAINER):
		said["weekly"] = view["weekly"]
		said["activities"] = _activities(doc.name)
		said["people"] = _people(doc.name)
	return said


def needs(doc, view: dict) -> list[dict]:
	"""What wants somebody now, worst first: cost types over budget, bills to
	check, time not invoiced from before this month, and late tasks."""
	found = []
	for one in budget._lines(doc.name):
		if one["left"] < 0:
			found.append(
				{
					"tone": "red",
					"text": _("{0} is over budget").format(one["cost_type"]),
					"money": one["left"],
				}
			)
	for doctype in ("Purchase Invoice", "Sales Invoice"):
		if not frappe.has_permission(doctype, "read"):
			continue
		for bill in frappe.get_all(
			doctype,
			filters={"docstatus": 0, "one_progress": [">", 0], "project": ["in", view["tree"]]},
			fields=[
				"name",
				"one_progress",
				"grand_total",
				"supplier_name" if doctype == "Purchase Invoice" else "customer_name",
			],
			limit=SHOWN,
		):
			party = bill.get("supplier_name") or bill.get("customer_name")
			found.append(
				{
					"tone": "orange",
					"text": _("Bill from {0} to check").format(party)
					if doctype == "Purchase Invoice"
					else _("Invoice to {0} to check").format(party),
					"dim": _("{0}% done").format(f"{flt(bill.one_progress):g}"),
					"money": bill.grand_total,
					"route": f"/desk/{frappe.scrub(doctype).replace('_', '-')}/{bill.name}",
				}
			)
	before = billing.unbilled(doc.name)
	if flt(before.get("hours")) and doc.get("one_kind") in (kinds.TIME, kinds.RETAINER):
		found.append(
			{
				"tone": "orange",
				"text": _("Time not invoiced yet"),
				"dim": _("{0} h").format(flt(before.get("hours"), 1)),
				"money": flt(before.get("amount")),
				"action": "invoice_time",
			}
		)
	today = nowdate()
	for task in frappe.get_list(
		"Task",
		filters=[
			["project", "in", view["tree"]],
			["status", "not in", overview.DONE],
			["exp_end_date", "<", today],
		],
		fields=["name", "subject", "exp_end_date", "_assign"],
		order_by="exp_end_date asc",
		limit=SHOWN,
	):
		people = frappe.parse_json(task._assign or "[]")
		found.append(
			{
				"tone": "red",
				"text": task.subject,
				"dim": get_fullname(people[0]) if people else None,
				"late": (getdate(today) - getdate(task.exp_end_date)).days,
				"route": f"/desk/task/{task.name}",
			}
		)
	return found[: SHOWN + 2]


def _milestones(projects: list[str]) -> list[dict]:
	rows = frappe.get_list(
		"Task",
		filters=[
			["project", "in", projects],
			["is_milestone", "=", 1],
			["status", "not in", ("Cancelled", "Template")],
		],
		fields=["name", "subject", "status", "exp_end_date"],
		order_by="exp_end_date asc",
		limit=8,
	)
	return [
		{
			"name": one.name,
			"subject": one.subject,
			"done": one.status == "Completed",
			"due": str(one.exp_end_date).split(" ")[0] if one.exp_end_date else None,
		}
		for one in rows
	]


def _latest_update(project: str) -> dict | None:
	from onedesk.one_project.ai import _updates

	found = _updates(project)
	return found[0] if found else None


def _sub_projects(project: str) -> list[dict]:
	return [
		{
			"name": one["name"],
			"title": one["title"],
			"status": one["status"],
			"share": round(flt(one["percent_complete"])),
		}
		for one in tree.totals(project)["under"][:SHOWN]
	]


def _month_hours(project: str) -> float:
	rows = frappe.get_list(
		"Timesheet Detail",
		parent_doctype="Timesheet",
		filters=[
			["Timesheet Detail", "project", "=", project],
			["Timesheet Detail", "from_time", ">=", str(get_first_day(nowdate()))],
			["Timesheet", "docstatus", "<", 2],
		],
		fields=["hours"],
		limit_page_length=0,
	)
	return round(sum(flt(one.hours) for one in rows), 1)


def _time_rows(project: str) -> list:
	"""This month's time on the project, each with who logged it."""
	rows = frappe.get_list(
		"Timesheet Detail",
		parent_doctype="Timesheet",
		filters=[
			["Timesheet Detail", "project", "=", project],
			["Timesheet Detail", "from_time", ">=", str(get_first_day(nowdate()))],
			["Timesheet Detail", "from_time", "<", str(get_first_day(add_months(nowdate(), 1)))],
			["Timesheet", "docstatus", "<", 2],
		],
		fields=["parent", "activity_type", "hours", "billing_amount"],
		limit_page_length=0,
	)
	users = dict(
		frappe.get_all(
			"Timesheet",
			filters={"name": ["in", list({row.parent for row in rows})]},
			fields=["name", "user"],
			as_list=True,
		)
	)
	for row in rows:
		row.user = users.get(row.parent)
	return rows


def _activities(project: str) -> list[dict]:
	found: dict = {}
	for row in _time_rows(project):
		one = found.setdefault(row.activity_type or _("Other"), {"hours": 0.0, "amount": 0.0})
		one["hours"] += flt(row.hours)
		one["amount"] += flt(row.billing_amount)
	return sorted(
		({"activity": key, "hours": round(v["hours"], 1), "amount": v["amount"]} for key, v in found.items()),
		key=lambda one: -one["hours"],
	)[:SHOWN]


def _people(project: str) -> list[dict]:
	found: dict = {}
	for row in _time_rows(project):
		if row.user:
			found[row.user] = found.get(row.user, 0.0) + flt(row.hours)
	return [
		{"user": user, "name": get_fullname(user), "hours": round(hours, 1)}
		for user, hours in sorted(found.items(), key=lambda one: -one[1])[:SHOWN]
	]


#: A task's fields as the workspace's views show them.
TASK_FIELDS = (
	"name",
	"subject",
	"project",
	"status",
	"priority",
	"parent_task",
	"is_group",
	"is_milestone",
	"exp_start_date",
	"exp_end_date",
	"progress",
	"expected_time",
	"actual_time",
	"_assign",
	"modified",
)


@frappe.whitelist()
@frappe.read_only()
def work(project: Annotated[str, "The project."]) -> dict:
	"""The project's tasks and its sub-projects', for the Tasks, Board and
	Timeline views: one group per project in the tree, this one first. Read as
	the reader, so a task they may not see is not here."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	tree_ = tree.totals(project)
	groups = [{"key": project, "title": frappe.db.get_value("Project", project, "project_name"), "own": True}]
	groups += [{"key": one["name"], "title": one["title"] or one["name"]} for one in tree_["under"]]
	rows = frappe.get_list(
		"Task",
		filters=[["project", "in", [one["key"] for one in groups]], ["status", "!=", "Template"]],
		fields=list(TASK_FIELDS),
		order_by="exp_end_date asc, creation asc",
		limit_page_length=0,
	)
	people: set[str] = set()
	tasks = []
	for row in rows:
		assigned = frappe.parse_json(row._assign or "[]")
		people.update(assigned)
		tasks.append(
			{
				**{key: row.get(key) for key in TASK_FIELDS if key != "_assign"},
				"assigned": assigned,
				"exp_start_date": str(row.exp_start_date).split(" ")[0] if row.exp_start_date else None,
				"exp_end_date": str(row.exp_end_date).split(" ")[0] if row.exp_end_date else None,
				"modified": str(row.modified),
			}
		)
	meta = frappe.get_meta("Task")
	return {
		"groups": groups,
		"tasks": tasks,
		"people": _people_of(people),
		"statuses": [one for one in meta.get_field("status").options.split("\n") if one and one != "Template"],
		"priorities": [one for one in meta.get_field("priority").options.split("\n") if one],
		"can_create": bool(frappe.has_permission("Task", "create")),
		"can_write": bool(frappe.has_permission("Task", "write")),
		"today": nowdate(),
	}


def _people_of(users) -> dict:
	"""Each user's name and picture, for avatars."""
	users = [one for one in users if one]
	if not users:
		return {}
	return {
		one.name: {"name": one.full_name or one.name, "image": one.user_image}
		for one in frappe.get_all(
			"User", filters={"name": ["in", users]}, fields=["name", "full_name", "user_image"]
		)
	}


@frappe.whitelist()
@frappe.read_only()
def files(project: Annotated[str, "The project."]) -> list[dict]:
	"""What is attached to the project, its sub-projects and their tasks, newest
	first, each saying where it is attached."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	projects = [project] + [one["name"] for one in tree.totals(project)["under"]]
	tasks = frappe.get_list("Task", filters={"project": ["in", projects]}, pluck="name", limit_page_length=0)
	found = []
	for doctype, names in (("Project", projects), ("Task", tasks)):
		if not names:
			continue
		found += frappe.get_all(
			"File",
			filters={"attached_to_doctype": doctype, "attached_to_name": ["in", names], "is_folder": 0},
			fields=[
				"name",
				"file_name",
				"file_url",
				"file_size",
				"is_private",
				"owner",
				"creation",
				"attached_to_doctype",
				"attached_to_name",
			],
			order_by="creation desc",
			limit=200,
		)
	found.sort(key=lambda one: one.creation, reverse=True)
	people = _people_of({one.owner for one in found})
	return [
		{
			**one,
			"creation": str(one.creation),
			"by": people.get(one.owner, {}).get("name", one.owner),
		}
		for one in found
	]


@frappe.whitelist()
@frappe.read_only()
def updates(project: Annotated[str, "The project."]) -> list[dict]:
	"""The team's updates on the project, newest first: who, when, what."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	from onedesk.one_project.ai import _updates

	return _updates(project)
