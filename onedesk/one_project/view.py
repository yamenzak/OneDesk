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

from onedesk.one_project import (
	billing,
	budget,
	kinds,
	media,
	milestones,
	money,
	overview,
	retainer,
	retention,
	tree,
)
from onedesk.one_project import updates as asking

#: The most late tasks Needs You reads, to count and to show some of.
LISTED = 200

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
		"above": _above(doc.name),
		"priority": doc.priority,
		"progress_method": doc.percent_complete_method,
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
		"orders": orders(doc, view["tree"]),
		"orders_route": _orders_route(doc),
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
		"update_due": asking.asked(doc.name),
		"asking": asking.asking(doc.as_dict()),
	}


def _above(project: str) -> list[dict]:
	"""The projects a sub-project sits under, top first, for the breadcrumb."""
	chain = tree.above(project, tree.parents())[1:]
	if not chain:
		return []
	titles = dict(
		frappe.get_all(
			"Project", filters={"name": ["in", chain]}, fields=["name", "project_name"], as_list=True
		)
	)
	return [{"name": one, "title": titles.get(one) or one} for one in reversed(chain)]


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


#: An order Bill Progress can't bill: closed, held or done.
UNBILLABLE = ("Closed", "On Hold", "Completed")


def orders(doc, projects: list[str] | None = None) -> list[dict]:
	"""The customer's submitted orders on the project and those under it,
	oldest first: where each is, what it's for, whether it's extra work, and
	what's left to bill. `own` is one on the page's project itself."""
	if not frappe.has_permission("Sales Order", "read"):
		return []
	of = tree.parents()
	projects = projects or sorted(tree.below({doc.name}, of))
	found = frappe.get_list(
		"Sales Order",
		filters={"project": ["in", projects], "docstatus": 1},
		fields=[
			"name",
			"project",
			"base_net_total",
			"per_billed",
			"status",
			"one_extra_work",
			"one_retention",
			"one_retention_due",
		],
		order_by="transaction_date asc, creation asc",
	)
	if not found:
		return []
	lines = {}
	for line in frappe.get_all(
		"Sales Order Item",
		filters={"parent": ["in", [one.name for one in found]]},
		fields=["parent", "item_name"],
		order_by="idx asc",
	):
		lines.setdefault(line.parent, []).append(line)
	titles = dict(
		frappe.get_all(
			"Project", filters={"name": ["in", projects]}, fields=["name", "project_name"], as_list=True
		)
	)
	return [
		{
			"name": one.name,
			"project": one.project,
			"own": one.project == doc.name,
			"where": milestones.where(one.project, doc.name, of, titles),
			"for": money.bought(lines.get(one.name, [])),
			"extra": bool(one.one_extra_work),
			"value": flt(one.base_net_total),
			"left": flt(one.base_net_total) * max(0.0, 100 - flt(one.per_billed)) / 100,
			"billed": round(flt(one.per_billed)),
			"status": one.status,
			"billable": one.status not in UNBILLABLE,
			"retention": flt(one.one_retention),
			"retention_due": one.one_retention_due,
		}
		for one in found
	]


def _orders_route(doc) -> str:
	from onedesk.one_project.money import _route

	projects = sorted(tree.below({doc.name}, tree.parents()))
	return _route("Sales Order", {"project": ["in", projects], "docstatus": 1})


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
					"view": "invoices",
				}
			]
		return [
			first,
			*second,
			{
				"key": "cost",
				"money": cash["spent"],
				"note_money": cost_note(cash) or None,
				"bar": share(cash["spent"], cash["budget"]) if cash["budget"] else None,
				"tone": "alarm" if cash["budget"] and cash["forecast_cost"] > cash["budget"] else None,
				"view": "money",
			},
			{
				"view": "money",
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


def cost_note(cash: dict) -> list:
	"""Under Cost: the budget, or by how much the forecast passes it, which is
	why the figure is red; then what suppliers still have to bill on their
	orders, which the forecast counts and Cost doesn't yet."""
	said = []
	if cash["budget"]:
		over = cash["forecast_cost"] - cash["budget"]
		said.append(
			[_("Forecast over by {0}"), [over]] if over > 0 else [_("of {0} budget"), [cash["budget"]]]
		)
	if cash["open_orders"]:
		said.append([_("{0} on order"), [cash["open_orders"]]])
	return said


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


def work_and_billing(
	done: int, cash: dict, overdue: float, last: dict | None = None, billable: dict | None = None
) -> dict:
	"""The work done beside what's billed and paid, as amounts: the work done
	not invoiced yet (or invoiced ahead of it), what the customer owes and how
	much of that is overdue or retention, anything paid in advance, and when
	the customer was last billed, at what share of the contract. A project
	billed by milestones measures what's not invoiced against the milestones
	done instead (milestones.billable)."""
	customer = {one["label"]: one["value"] for one in cash["customer"]}
	paid = flt(customer.get(_("Paid")))
	earned = billable["share"] if billable else done
	gap = cash["contract"] * earned / 100 - cash["invoiced"]
	return {
		"done": done,
		"billable": billable,
		"unbilled": round(gap) if gap >= 1 else 0,
		"ahead": round(-gap) if gap <= -1 else 0,
		"owed": max(0.0, cash["invoiced"] - paid),
		"overdue": overdue,
		"retention": flt(customer.get(_("Retention Held"))),
		"advance": max(0.0, paid - cash["invoiced"]),
		"last": last
		and {
			"date": last["posting_date"],
			"share": round(flt(last.get("one_progress")))
			or (round(cash["invoiced"] * 100 / cash["contract"]) if cash["contract"] else None),
		},
	}


def _last_billed(projects: list[str]) -> dict | None:
	"""The newest invoice to the customer on the project, for whoever reads
	invoices. A return isn't a billing."""
	if not frappe.has_permission("Sales Invoice", "read"):
		return None
	found = frappe.get_list(
		"Sales Invoice",
		filters={"docstatus": 1, "is_return": 0, "project": ["in", projects]},
		fields=["posting_date", "one_progress"],
		order_by="posting_date desc, creation desc",
		limit=1,
	)
	return found[0] if found else None


def _overdue(projects: list[str]) -> float:
	"""What the customer owes on invoices past their due date, in the
	company's currency, for whoever reads invoices."""
	if not frappe.has_permission("Sales Invoice", "read"):
		return 0.0
	return flt(
		frappe.db.sql(
			"""select sum(outstanding_amount * conversion_rate) from `tabSales Invoice`
			where docstatus = 1 and status = 'Overdue' and project in %s""",
			(projects,),
		)[0][0]
	)


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
	needed = needs(doc, view, kind)
	said = {
		"needs": needed[: SHOWN + 2],
		"needs_count": len(needed),
		"needs_all": _late_route(view["tree"]) if len(needed) > SHOWN + 2 else None,
		"sub_projects": _sub_projects(doc.name),
		"quotes": _quotes(doc),
	}
	if kind in (kinds.FIXED, kinds.INTERNAL):
		said["milestones"] = milestones.read(doc.name, view["tree"])
	if kind == kinds.FIXED:
		# Work against billing means nothing until something is ordered.
		said["billing"] = (
			work_and_billing(
				view["share"],
				cash,
				_overdue(view["tree"]),
				_last_billed(view["tree"]),
				said["milestones"]["billable"],
			)
			if contract(doc)
			else None
		)
		said["budget"] = _budget_lines(view["tree"], cash)
		said["subcontracts"] = _subcontracts(doc.name, view, cash["suppliers"][:SHOWN])
		said["subcontracts_count"] = len(cash["suppliers"])
		said["retention"] = (
			retention.sides(view["tree"], orders(doc, view["tree"]), cash["suppliers"])
			if retention.on()
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
	"""What wants somebody now, the reader's own first, then worst first:
	cost types over budget over the project and those under it (where the
	page has no budget section of its own), bills to check, supplier bills
	past due, late tasks and tasks due today. A retainer's months and the time not invoiced have
	sections of their own. A completed project still owed money says so
	first. Every row there is, for the Overview to show some and count all."""
	user = frappe.session.user
	found = []
	if doc.status == "Completed" and frappe.has_permission("Sales Invoice", "read"):
		from onedesk.one_project.status import due

		found += [{"tone": "orange", "text": one["text"], "money": one["money"]} for one in due(doc.name)]
	if kind != kinds.FIXED:
		for one in budget.across(view["tree"]):
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
				"owner",
				"one_progress",
				"grand_total",
				"supplier_name" if doctype == "Purchase Invoice" else "customer_name",
			],
		):
			party = bill.get("supplier_name") or bill.get("customer_name")
			mine = bill.owner == user
			found.append(
				{
					"tone": "orange",
					"text": _("Check bill from {0}").format(party)
					if doctype == "Purchase Invoice"
					else _("Check invoice to {0}").format(party),
					"dim": " · ".join(
						filter(
							None,
							[
								_("{0}% done").format(f"{flt(bill.one_progress):g}"),
								_("You") if mine else None,
							],
						)
					),
					"money": bill.grand_total,
					"route": f"/desk/{frappe.scrub(doctype).replace('_', '-')}/{bill.name}",
					"mine": mine,
				}
			)
	found += _overdue_bills(view["tree"], user)
	found += retention.asks(view["tree"], user)
	today = getdate(nowdate())
	titles = dict(
		frappe.get_all(
			"Project", filters={"name": ["in", view["tree"]]}, fields=["name", "project_name"], as_list=True
		)
	)
	of = tree.parents()
	for task in frappe.get_list(
		"Task",
		filters=[
			["project", "in", view["tree"]],
			["status", "not in", overview.DONE],
			# frappe reads a missing date as the earliest one.
			["exp_end_date", "is", "set"],
			# Before tomorrow: the due date is kept with a time.
			["exp_end_date", "<", str(add_days(today, 1))],
		],
		fields=["name", "subject", "exp_end_date", "_assign", "project"],
		order_by="exp_end_date asc",
		limit=LISTED,
	):
		people = frappe.parse_json(task._assign or "[]")
		mine = user in people
		late = (today - getdate(task.exp_end_date)).days
		found.append(
			{
				"tone": "red" if late else "orange",
				"text": task.subject,
				"dim": " · ".join(
					filter(
						None,
						[
							milestones.where(task.project, doc.name, of, titles),
							_("You") if mine else (get_fullname(people[0]) if people else None),
						],
					)
				),
				"late": late,
				"today": not late,
				"route": f"/desk/task/{task.name}",
				"mine": mine,
			}
		)
	# The reader's own first; the rest keep their order, worst first.
	return sorted(found, key=lambda one: not one.get("mine"))


def _subcontracts(project: str, view: dict, orders: list[dict]) -> list[dict]:
	"""The orders as the Overview shows them: where each is, and how far the
	work on its project has got, to set beside what's billed."""
	if not orders:
		return []
	titles = dict(
		frappe.get_all(
			"Project", filters={"name": ["in", view["tree"]]}, fields=["name", "project_name"], as_list=True
		)
	)
	done = {
		one.name: 100 if one.status == "Completed" else round(flt(one.percent_complete))
		for one in frappe.get_all(
			"Project", filters={"name": ["in", view["tree"]]}, fields=["name", "status", "percent_complete"]
		)
	}
	# The page's own project is as far along as its Work Done.
	done[project] = view["share"]
	of = tree.parents()
	return [
		{
			**one,
			"where": milestones.where(one["project"], project, of, titles) if one.get("project") else None,
			"done": done.get(one.get("project") or project),
		}
		for one in orders
	]


def late(days: int) -> str:
	"""How late, in plain words."""
	return _("1 day late") if days == 1 else _("{0} days late").format(days)


def _overdue_bills(projects: list[str], user: str) -> list[dict]:
	"""Supplier bills on the project with a payment past its due date, by
	their payment schedule (ERPNext marks a bill Overdue overnight): what's
	due and how late, retention not yet due left out."""
	if not frappe.has_permission("Purchase Invoice", "read"):
		return []
	rows = frappe.db.sql(
		"""select pi.name, pi.supplier_name, pi.owner, pi.conversion_rate,
			sum(ps.outstanding) as due, min(ps.due_date) as since,
			sum(case when ps.payment_term in %(held)s then 0 else 1 end) = 0 as held
		from `tabPurchase Invoice` pi
		join `tabPayment Schedule` ps on ps.parent = pi.name and ps.parenttype = 'Purchase Invoice'
		where pi.docstatus = 1 and pi.outstanding_amount > 0 and ps.outstanding > 0 and ps.due_date < %(today)s
			and pi.name in (select parent from `tabPurchase Invoice Item` where project in %(projects)s)
		group by pi.name
		order by since asc""",
		{"today": nowdate(), "projects": tuple(projects), "held": retention.HELD},
		as_dict=True,
	)
	today = getdate(nowdate())
	return [
		{
			"tone": "red",
			"text": (_("Pay retention to {0}") if one.held else _("Pay {0}")).format(one.supplier_name),
			"dim": " · ".join(
				filter(
					None,
					[
						late((today - getdate(one.since)).days),
						_("You") if one.owner == user else None,
					],
				)
			),
			"money": flt(one.due) * flt(one.conversion_rate or 1),
			"route": f"/desk/purchase-invoice/{one.name}",
			"mine": one.owner == user,
		}
		for one in rows
	]


def _late_route(projects: list[str]) -> str:
	"""Every late task on the project and those under it, as the desk lists them."""
	return money._route(
		"Task",
		{
			"project": ["in", projects],
			"status": ["not in", list(overview.DONE)],
			"exp_end_date": ["<", nowdate()],
		},
	)


def _budget_lines(projects: list[str], cash: dict) -> dict:
	"""Each cost type over the project and those under it, and Other for
	what they leave out, so the rows add up to the project's Budget and
	Cost."""
	lines = budget.across(projects)
	rest = budget.other(lines, cash["budget"], cash["spent"], cash["open_orders"]) if lines else None
	return {
		"lines": lines[:SHOWN],
		"count": len(lines),
		"other": rest,
	}


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


def _latest_update(project: str) -> dict | None:
	from onedesk.one_project.ai import _updates

	found = _updates(project)
	return found[0] if found else None


def _sub_projects(project: str) -> dict:
	"""The sub-projects directly under the project, each with how it's going
	(kind, when it's due, who runs it, health), its money for its whole
	branch (what's ordered and billed, or spent against its budget), whether
	it's extra work and how many are under it; the first few, and how many."""
	under = tree.totals(project)["under"]
	if not under:
		return {"list": [], "count": 0, "all": None}
	names = [one["name"] for one in under]
	heads = {
		one.name: one
		for one in frappe.get_all(
			"Project",
			filters={"name": ["in", names]},
			fields=["name", "one_kind", "one_manager", "expected_end_date", "one_health"],
		)
	}
	extra = set(
		frappe.get_all(
			"Sales Order",
			filters={"project": ["in", names], "docstatus": 1, billing.EXTRA: 1},
			pluck="project",
		)
	)
	today = getdate(nowdate())
	found = []
	for one in under[:SHOWN]:
		head = heads.get(one["name"]) or frappe._dict()
		finished = one["status"] in ("Completed", "Cancelled")
		found.append(
			{
				"name": one["name"],
				"title": one["title"],
				"status": one["status"],
				"share": 100 if one["status"] == "Completed" else round(flt(one["percent_complete"])),
				"kind": head.one_kind,
				"manager": get_fullname(head.one_manager) if head.one_manager else None,
				"days_left": overview.days_left(head.expected_end_date, today, finished),
				"health": None if finished else head.one_health,
				"below": one["below"],
				"extra": one["name"] in extra,
				**branch_money(one),
			}
		)
	return {
		"list": found,
		"count": len(under),
		"all": money._route("Project", {"one_parent": project}) if len(under) > SHOWN else None,
	}


def branch_money(figures: dict) -> dict:
	"""A branch's money as a sub-project's row says it: what's ordered and
	billed, and what's spent against its budget. Pure."""
	spent = sum(
		flt(figures.get(field))
		for field in (
			"total_costing_amount",
			"total_purchase_cost",
			"total_consumed_material_cost",
			"total_expense_claim",
		)
	)
	budget = flt(figures.get("estimated_costing"))
	return {
		"ordered": flt(figures.get("total_sales_amount")),
		"billed": flt(figures.get("total_billed_amount")),
		"spent": spent,
		"budget": budget,
		"over": bool(budget) and spent > budget,
	}


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
	"one_bill_share",
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
	of = tree.parents()
	below = tree.below({project}, of)
	titles = dict(
		frappe.get_all(
			"Project", filters={"name": ["in", list(below)]}, fields=["name", "project_name"], as_list=True
		)
	)
	# Every project under it, at any depth, the reader may see, by path:
	# Handrails, then Glass for handrails under it (milestones.where).
	under = sorted(
		(
			{"key": one, "title": milestones.where(one, project, of, titles) or titles.get(one) or one}
			for one in below - {project}
			if frappe.has_permission("Project", "read", doc=one)
		),
		key=lambda one: one["title"],
	)
	groups = [{"key": project, "title": titles.get(project) or project, "own": True}, *under]
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
	waiting = _waiting([one["name"] for one in tasks if one["status"] not in overview.DONE])
	for one in tasks:
		one["waiting"] = waiting.get(one["name"], [])
	teams = _user_groups()
	people.update(user for one in teams for user in one["users"])
	meta = frappe.get_meta("Task")
	return {
		"groups": groups,
		"tasks": tasks,
		"user_groups": teams,
		"people": _people_of(people),
		"statuses": [
			one for one in meta.get_field("status").options.split("\n") if one and one != "Template"
		],
		"priorities": [one for one in meta.get_field("priority").options.split("\n") if one],
		"can_create": bool(frappe.has_permission("Task", "create")),
		"can_write": bool(frappe.has_permission("Task", "write")),
		"today": nowdate(),
	}


def _user_groups() -> list[dict]:
	"""The workspace's User Groups and their enabled members, to give a task to
	a whole group as frappe's Assign To does: each member gets it."""
	members: dict[str, list[str]] = {}
	for row in frappe.get_all(
		"User Group Member", filters={"parenttype": "User Group"}, fields=["parent", "user"], order_by="idx"
	):
		members.setdefault(row.parent, []).append(row.user)
	if not members:
		return []
	enabled = set(
		frappe.get_all(
			"User",
			filters={
				"name": ["in", list({user for users in members.values() for user in users})],
				"enabled": 1,
			},
			pluck="name",
		)
	)
	return [
		{"name": name, "users": [user for user in users if user in enabled]}
		for name, users in sorted(members.items())
		if any(user in enabled for user in users)
	]


def _waiting(names: list[str]) -> dict[str, list[str]]:
	"""What each task still waits on: the tasks under its ERPNext Depends On
	not yet completed or cancelled, by subject."""
	if not names:
		return {}
	rows = frappe.get_all(
		"Task Depends On",
		filters={"parent": ["in", names], "parenttype": "Task"},
		fields=["parent", "task"],
	)
	if not rows:
		return {}
	open_ = {
		one.name: one.subject
		for one in frappe.get_all(
			"Task",
			filters={"name": ["in", list({row.task for row in rows})], "status": ["not in", overview.DONE]},
			fields=["name", "subject"],
		)
	}
	found: dict[str, list[str]] = {}
	for row in rows:
		if row.task in open_:
			found.setdefault(row.parent, []).append(open_[row.task])
	return found


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
