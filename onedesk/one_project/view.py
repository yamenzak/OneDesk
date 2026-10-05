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
from frappe.utils import (
	add_days,
	add_months,
	date_diff,
	flt,
	formatdate,
	get_first_day,
	get_fullname,
	getdate,
	nowdate,
)

from onedesk.one_project import billing, budget, kinds, media, money, overview, retainer, tree

#: How many of each list the Overview shows.
SHOWN = 6


#: The tabs each kind has, in order, as far as they are built.
def views(kind: str, cash: dict, customer: str | None = None) -> list[str]:
	"""The views the page shows beyond Overview, the tasks, Files and
	Activity, each for whoever may see what it shows: Time to whoever may read
	timesheets; Money when the reader may see any of it; Invoices on a project
	with a customer, to whoever may read invoices; Suppliers where there are
	subcontracts or the project is a Fixed Price one, which is where they're
	expected; and Team to everyone."""
	shown = []
	if frappe.has_permission("Timesheet", "read"):
		shown.append("time")
	if cash["customer"] or cash["cost"]:
		shown.append("money")
	if customer and frappe.has_permission("Sales Invoice", "read"):
		shown.append("invoices")
	if cash["suppliers"] or (kind == kinds.FIXED and frappe.has_permission("Purchase Order", "read")):
		shown.append("suppliers")
	shown.append("team")
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
			{
				"user": row.user,
				"name": get_fullname(row.user),
				"image": frappe.db.get_value("User", row.user, "user_image"),
			}
			for row in doc.users
		],
		"contract": contract(doc),
		"quotation": None if contract(doc) else quotation(doc),
		"currency": cash["currency"],
		"can_write": bool(frappe.has_permission("Project", "write", doc=doc)),
		"views": views(kind, cash, doc.customer),
		"money": cash,
		"can_budget": bool(frappe.has_permission("Project", "write", doc=doc)),
		"cards": cards(kind, doc, view, cash),
		"progress": view["share"] if view["tasks"] or doc.percent_complete else None,
		"days_left": view["days_left"],
		"monthly_hours": flt(doc.get("one_monthly_hours")),
		"cover": doc.get("one_cover"),
		"media": media.shown(doc.name),
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


def quotation(doc) -> dict | None:
	"""While nothing is ordered, the customer's quotations for the project
	still open, extra work aside: the newest, and how many there are."""
	from onedesk.one_project.money import OPEN_QUOTE, _route

	filters = {"project": doc.name, "docstatus": 1, "status": ["in", list(OPEN_QUOTE)], "one_extra_work": 0}
	found = frappe.get_all(
		"Quotation",
		filters=filters,
		fields=["name", "base_net_total", "valid_till"],
		order_by="transaction_date desc, creation desc",
	)
	if not found:
		return None
	one = found[0]
	return {
		"name": one.name,
		"value": flt(one.base_net_total),
		"valid_till": one.valid_till,
		"count": len(found),
		"list": _route("Quotation", filters),
		# ERPNext asks which alternative items to take on the quotation itself.
		"alternatives": bool(frappe.db.exists("Quotation Item", {"parent": one.name, "is_alternative": 1})),
	}


@frappe.whitelist()
@frappe.read_only()
def to_quote(customer: Annotated[str, "The customer being quoted."]) -> str | None:
	"""A new quotation's project: the customer's one open Fixed Price project
	with nothing ordered yet, when there is exactly one. Other kinds are never
	ordered as a whole, so they aren't waiting for a quote."""
	if not frappe.has_permission("Customer", "read", doc=customer):
		return None
	found = [
		one.name
		for one in frappe.get_list(
			"Project",
			filters={"customer": customer, "status": "Open", "one_kind": kinds.FIXED},
			fields=["name", "sales_order"],
			limit_page_length=0,
		)
		if not contract(one)
	]
	return found[0] if len(found) == 1 else None


def _first(doc, cash: dict) -> dict:
	"""A Fixed Price project's first figure: its contract once ordered, the
	quote while one is out, or nothing yet with Add Contract."""
	order = contract(doc)
	if order:
		return {"key": "contract", "money": cash["contract"], "route": f"/desk/sales-order/{order}"}
	quote = quotation(doc)
	if quote and quote["count"] > 1:
		# Which of them is ordered is the customer's answer, picked on the list.
		return {
			"key": "quoted",
			"money": quote["value"],
			"note": _("{0} open quotes").format(quote["count"]),
			"route": quote["list"],
			"valid_till": quote["valid_till"],
		}
	if quote:
		return {
			"key": "quoted",
			"money": quote["value"],
			"note": _("Not ordered yet"),
			"route": f"/desk/quotation/{quote['name']}",
			"valid_till": quote["valid_till"],
		}
	return {"key": "contract", "money": 0, "action": "add_contract"}


def _valid(until) -> dict:
	"""The day an open quote lapses, and how far off it is."""
	left = date_diff(until, nowdate()) if until else None
	return {
		"key": "valid",
		"value": until,
		"date": True,
		"note": None
		if left is None
		else _("Today")
		if left == 0
		else _("In {0} days").format(left)
		if left > 0
		else None,
	}


def cards(kind: str, doc, view: dict, cash: dict) -> list[dict]:
	"""The kind's figures, each with what it's of and a bar where there's
	something to fill (docs/PROJECT-PAGE.md)."""
	customer = {one["label"]: one["value"] for one in cash["customer"]}
	paid = customer.get(_("Paid"), 0)
	invoiced = {
		"key": "invoiced",
		"money": cash["invoiced"],
		"note_money": [[_("Paid {0}"), [paid]]],
	}
	if kind == kinds.FIXED:
		first = _first(doc, cash)
		# While it's only quoted, the margin is measured against the quote.
		worth = first["money"] if first["key"] == "quoted" else cash["contract"]
		margin = worth - cash["forecast_cost"] if first["key"] == "quoted" else cash["forecast_margin"]
		# Billed means nothing until something is ordered: while it's quoted the
		# quote's last day stands in its place, and with nothing yet, nothing.
		valid = first.pop("valid_till", None)
		if first["key"] == "quoted":
			second = [_valid(valid)]
		elif first.get("action") == "add_contract":
			second = []
		else:
			second = [
				{
					"key": "billed",
					"value": f"{percent(cash['invoiced'], cash['contract'])}%",
					"note_money": [[_("{0} invoiced"), [cash["invoiced"]]]],
					"bar": share(cash["invoiced"], cash["contract"]),
				}
			]
		return [
			first,
			*second,
			{
				"key": "cost",
				"money": cash["spent"],
				"note_money": [[_("of {0} budget"), [cash["budget"]]]]
				if cash["budget"]
				else [[_("{0} more on order"), [cash["open_orders"]]]]
				if cash["open_orders"]
				else None,
				"bar": share(cash["spent"], cash["budget"]) if cash["budget"] else None,
				"tone": "alarm" if cash["budget"] and cash["forecast_cost"] > cash["budget"] else None,
			},
			{
				"key": "forecast",
				"money": margin,
				"note": (
					_("{0}% of the quote") if first["key"] == "quoted" else _("{0}% of the contract")
				).format(share(margin, worth))
				if worth and margin > 0
				else None,
				"tone": "alarm" if worth and margin < 0 else None,
			},
		]
	if kind == kinds.TIME:
		waiting = billing.unbilled(doc.name)
		return [
			{
				"key": "unbilled",
				"money": flt(waiting.get("amount")),
				"note": _("{0} h").format(f"{flt(waiting.get('hours'), 1):g}")
				if waiting.get("hours")
				else None,
			},
			{"key": "hours", "hours": _month_hours(view["tree"])},
			invoiced,
			_budget_card(cash) if cash["budget"] else _done(view),
		]
	if kind == kinds.RETAINER:
		hours = _month_hours([doc.name])
		allowance = flt(doc.one_monthly_hours)
		# A retainer's months that have ended without an invoice, at its fee.
		late = retainer.waiting(doc.name) if doc.customer else []
		return [
			{
				"key": "month",
				"hours": hours,
				"note": _("of {0} h").format(f"{allowance:g}") if allowance else None,
				"bar": share(hours, allowance) if allowance else None,
				"tone": "alarm" if allowance and hours > allowance else None,
			},
			{
				"key": "fee",
				"money": flt(doc.one_monthly_fee),
				"currency": retainer.fee_currency(doc),
				"note": _("Renews {0}").format(formatdate(add_months(get_first_day(nowdate()), 1))),
			},
			{
				"key": "months_waiting",
				"money": len(late) * flt(doc.one_monthly_fee),
				"currency": retainer.fee_currency(doc),
				"note": _("{0} months").format(len(late))
				if len(late) > 1
				else _("1 month")
				if late
				else None,
				"tone": "alarm" if late else None,
			},
			invoiced,
		]
	found = [
		_done(view),
		_due(view),
		{
			"key": "overdue",
			"value": view["late"],
			"note": _("of {0} open").format(view["tasks"] - view["done"])
			if view["tasks"] > view["done"]
			else None,
			"tone": "alarm" if view["late"] else None,
		},
	]
	return [*found, _budget_card(cash)] if cash["budget"] else found


def percent(part: float, whole: float) -> int:
	"""Part of a whole, out of 100, past 100 when it's more. Pure."""
	return max(0, round(100 * flt(part) / flt(whole))) if flt(whole) else 0


def _done(view: dict) -> dict:
	return {
		"key": "done",
		"value": f"{view['share']}%",
		"note": _("{0} of {1} tasks").format(view["done"], view["tasks"]) if view["tasks"] else None,
		"bar": view["share"],
	}


def _budget_card(cash: dict) -> dict:
	return {
		"key": "budget",
		"value": f"{percent(cash['spent'], cash['budget'])}%",
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


def _quotes(doc) -> list[dict]:
	"""The customer's quotations for the project, newest first, drafts too,
	read as the reader reads quotations."""
	if not doc.customer or not frappe.has_permission("Quotation", "read"):
		return []
	return [
		{
			"name": one.name,
			"date": one.transaction_date,
			"status": "Draft" if one.docstatus == 0 else one.status,
			"value": flt(one.net_total),
			"currency": one.currency,
			"extra": bool(one.one_extra_work),
		}
		for one in frappe.get_list(
			"Quotation",
			filters={"project": doc.name, "docstatus": ["<", 2]},
			fields=[
				"name",
				"transaction_date",
				"status",
				"docstatus",
				"net_total",
				"currency",
				"one_extra_work",
			],
			order_by="transaction_date desc, creation desc",
			limit_page_length=SHOWN,
		)
	]


def _overview(kind: str, doc, view: dict, cash: dict) -> dict:
	"""What the kind's Overview shows beyond its figures. Each thing is in
	one place: what is in a section is not in Needs You as well."""
	said = {
		"needs": needs(doc, view, kind),
		"sub_projects": _sub_projects(doc.name),
		"quotes": _quotes(doc),
	}
	if kind in (kinds.FIXED, kinds.INTERNAL):
		said["milestones"] = _milestones(view["tree"])
	if kind == kinds.FIXED:
		# Work against billing means nothing until something is ordered.
		said["billing"] = (
			{
				"done": view["share"],
				"billed": share(cash["invoiced"], cash["contract"]),
				"paid": share(
					{one["label"]: one["value"] for one in cash["customer"]}.get(_("Paid"), 0),
					cash["contract"],
				),
			}
			if contract(doc)
			else None
		)
		said["budget"] = _budget_lines(doc.name)
		said["subcontracts"] = cash["suppliers"][:SHOWN]
		order = contract(doc)
		terms = (
			frappe.db.get_value("Sales Order", order, ["one_retention", "one_retention_due"], as_dict=True)
			if order
			else None
		)
		held = {one["label"]: one["value"] for one in cash["customer"]}.get(_("Retention Held"), 0)
		said["retention"] = (
			{"percent": flt(terms.one_retention), "due": terms.one_retention_due, "held": held}
			if terms and terms.one_retention
			else None
		)
	if kind == kinds.RETAINER:
		said["months"] = retainer.months(doc.name)
		said["people"] = _people(doc.name)
	if kind in (kinds.TIME, kinds.RETAINER):
		said["weekly"] = view["weekly"]
		said["activities"] = _activities(doc.name)
	if kind == kinds.TIME:
		said["unbilled"] = _unbilled_people(doc.name)
	if kind == kinds.INTERNAL:
		said["statuses"] = view["statuses"]
		said["due_soon"] = _due_soon(view["tree"])
		said["on_it"] = _on_it(view["tree"])
	return said


def needs(doc, view: dict, kind: str | None = None) -> list[dict]:
	"""What wants somebody now, worst first: cost types over budget (where the
	page has no budget section of its own), bills to check, and late tasks. A
	retainer's months and the time not invoiced have sections of their own.
	A completed project still owed money says so first."""
	found = []
	if doc.status == "Completed" and frappe.has_permission("Sales Invoice", "read"):
		from onedesk.one_project.status import due

		found += [{"tone": "orange", "text": one["text"], "money": one["money"]} for one in due(doc.name)]
	if kind != kinds.FIXED:
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
	today = nowdate()
	for task in frappe.get_list(
		"Task",
		filters=[
			["project", "in", view["tree"]],
			["status", "not in", overview.DONE],
			# frappe reads a missing date as the earliest one.
			["exp_end_date", "is", "set"],
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


def _budget_lines(project: str) -> list[dict]:
	"""Each cost type's budget and what is spent and ordered against it."""
	return [
		{
			"cost_type": one["cost_type"],
			"budget": one["budget"],
			"used": one["spent"] + one["committed"],
			"left": one["left"],
		}
		for one in budget._lines(project)
	][:SHOWN]


def _due_soon(projects: list[str]) -> list[dict]:
	"""Open tasks due in the next two weeks, soonest first."""
	today = getdate(nowdate())
	rows = frappe.get_list(
		"Task",
		filters=[
			["project", "in", projects],
			["status", "not in", overview.DONE],
			["exp_end_date", ">=", str(today)],
			["exp_end_date", "<=", str(add_days(today, 14))],
		],
		fields=["name", "subject", "exp_end_date", "_assign"],
		order_by="exp_end_date asc",
		limit=SHOWN,
	)
	return [
		{
			"name": one.name,
			"subject": one.subject,
			"due": str(getdate(one.exp_end_date)),
			"who": (lambda people: get_fullname(people[0]) if people else None)(
				frappe.parse_json(one._assign or "[]")
			),
		}
		for one in rows
	]


def _on_it(projects: list[str]) -> list[dict]:
	"""Who has open tasks on the project, most first."""
	found: dict = {}
	for one in frappe.get_list(
		"Task",
		filters=[["project", "in", projects], ["status", "not in", overview.DONE]],
		fields=["_assign"],
		limit_page_length=0,
	):
		for user in frappe.parse_json(one._assign or "[]"):
			found[user] = found.get(user, 0) + 1
	return [
		{"user": user, "name": get_fullname(user), "tasks": n}
		for user, n in sorted(found.items(), key=lambda one: -one[1])[:SHOWN]
	]


def _unbilled_people(project: str) -> list[dict]:
	"""The billable time not invoiced yet, by who logged it."""
	rows = billing._rows(project)
	names = dict(
		frappe.get_all(
			"Timesheet",
			filters={"name": ["in", list({row.time_sheet for row in rows})]},
			fields=["name", "employee_name"],
			as_list=True,
		)
	)
	found: dict = {}
	for row in rows:
		one = found.setdefault(names.get(row.time_sheet) or _("Other"), {"hours": 0.0, "amount": 0.0})
		one["hours"] += flt(row.billing_hours)
		one["amount"] += flt(row.billing_amount)
	return sorted(
		({"name": key, "hours": round(v["hours"], 1), "amount": v["amount"]} for key, v in found.items()),
		key=lambda one: (-one["amount"], -one["hours"]),
	)[:SHOWN]


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
			"share": 100 if one["status"] == "Completed" else round(flt(one["percent_complete"])),
		}
		for one in tree.totals(project)["under"][:SHOWN]
	]


def _month_hours(projects: list[str]) -> float:
	"""This month's hours on the projects, as Hours by Week counts them."""
	rows = frappe.get_list(
		"Timesheet Detail",
		parent_doctype="Timesheet",
		filters=[
			["Timesheet Detail", "project", "in", projects],
			["Timesheet Detail", "from_time", ">=", str(get_first_day(nowdate()))],
			["Timesheet Detail", "from_time", "<", str(get_first_day(add_months(nowdate(), 1)))],
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
	sheets = {
		one.name: one
		for one in frappe.get_all(
			"Timesheet",
			filters={"name": ["in", list({row.parent for row in rows})]},
			fields=["name", "user", "employee", "employee_name"],
		)
	}
	for row in rows:
		sheet = sheets.get(row.parent) or frappe._dict()
		# A timesheet is the employee's; the user is there only when they have one.
		row.user = sheet.user or sheet.employee
		row.who = get_fullname(sheet.user) if sheet.user else sheet.employee_name
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
	names: dict = {}
	for row in _time_rows(project):
		if row.user:
			found[row.user] = found.get(row.user, 0.0) + flt(row.hours)
			names[row.user] = row.who
	return [
		{"user": user, "name": names[user] or user, "hours": round(hours, 1)}
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
		"statuses": [
			one for one in meta.get_field("status").options.split("\n") if one and one != "Template"
		],
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
