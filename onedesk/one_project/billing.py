"""What a project costs and what it is billed, on ERPNext's own records.

**Time is priced by ERPNext.** A timesheet row takes its costing and billing
rate from the person's **Activity Cost** for its activity, or the **Activity
Type**'s own rates when they have none (`TimesheetDetail.update_cost`), and a
submitted timesheet adds its cost and billable amount to the project. The timer
(one_task/timer.py) writes those rows; nothing here prices anything.

**Invoice Time** (`invoice_time`) is ERPNext's Sales Invoice with its Time
Sheets table filled: every billable hour on the project not yet invoiced, as
lines by activity — Design 12 h, Site visits 4 h — at what the hours come to.
It opens as a draft for somebody to read before it is submitted, and
submitting it is what marks the hours billed and adds to the project's Billed,
which is ERPNext's (TimesheetBillingService). On a project with sub-projects
it takes the whole tree's billable time for the same customer, each line of
the invoice's Time Sheets naming its project, so the villa's page invoices
the windows' hours too (`_rows`). A retainer's hours are billed with its
month, never here.

**What was bought for it** (`costs`). A Time and Materials job bills the
materials and outside work bought for it as well as its hours: supplier
bills' lines on the project, stock issued to it, and approved expense claims
for it, each at what it cost the company plus the project's **Markup on
Costs** (`one_markup`). Invoice Time adds them as lines under the time, one
per cost, and each line names the cost it bills (`one_rebills`), so a cost is
never billed twice and is billable again if its invoice is cancelled. Only a
Time and Materials project's costs are billed this way; a fixed price covers
its own.

**A quotation for extra work becomes a sub-project** (`ordered`). A quotation
names its project like any other (chain.py), and **Extra Work** says it is
more than the job was ordered for. Both are carried to its Sales Order (the
same fields on both, so ERPNext's mapping carries them), and when the order is
submitted a project is made for it under that one, ERPNext's own "Create >
Project" from an order with the order's total as its estimate. The order and
its lines then name the sub-project, so the handrails a customer asked for
halfway through the windows have their own order, time, costs and invoices,
and add up into the villa's.
"""

import frappe
from frappe import _
from frappe.utils import flt

from onedesk.one_book.currency import bill_in, billed_in
from onedesk.one_book.currency import rate as currency_rate

#: The tick on Quotation and Sales Order saying the order is extra work, to
#: become a sub-project of the project it names.
EXTRA = "one_extra_work"


@frappe.whitelist()
@frappe.read_only()
def unbilled(project: str) -> dict:
	"""What Invoice Time would bill: the hours, their amount, and the item used
	for time last time."""
	frappe.has_permission("Project", "read", project, throw=True)
	customer = frappe.db.get_value("Project", project, "customer")
	rows = _rows(project)
	# Each timesheet's amount in the currency the customer is billed in.
	currency = (billed_in("Customer", customer) if customer else None) or (rows[0].currency if rows else None)
	if rows and currency:
		rows = in_currency(rows, currency)
	found = costs(project) if frappe.has_permission("Sales Invoice", "create") else []
	rate = currency_rate(_company_currency(project), currency) if found and currency else 1
	return {
		"hours": sum(flt(row.billing_hours) for row in rows),
		"amount": sum(flt(row.billing_amount) for row in rows),
		"currency": currency,
		"customer": customer,
		"item": _last_item(),
		"projects": sorted({row.project_name for row in rows if row.get("project_name")}),
		"costs": {
			"count": len(found),
			"amount": round(sum(one["charge"] for one in found) * flt(rate), 2),
			"item": _last_item(costs=True),
		},
	}


@frappe.whitelist(methods=["POST"])
def invoice_time(source_name: str, item: str | None = None, cost_item: str | None = None):
	"""A draft Sales Invoice for the project's billable time not yet invoiced,
	and its costs not yet billed when `cost_item` is given, for the page to
	open through frappe.model.open_mapped_doc, which passes the items in its
	args. Nothing is saved."""
	project = source_name
	args = frappe.flags.args or {}
	item = item or args.get("item")
	cost_item = cost_item or args.get("cost_item")
	if not item:
		frappe.throw(_("Pick the item to invoice the time as."))
	frappe.has_permission("Project", "read", project, throw=True)
	frappe.has_permission("Sales Invoice", "create", throw=True)
	source = frappe.db.get_value("Project", project, ["project_name", "customer", "one_kind"], as_dict=True)
	if source.one_kind == "Retainer":
		# Its hours are covered by the fee and billed with the month
		# (retainer.py); billing them here would bill them twice.
		frappe.throw(_("{0} is a retainer. Invoice it by the month.").format(source.project_name))
	if not source.customer:
		frappe.throw(_("Give {0} a customer to bill its time to.").format(source.project_name))
	rows = _rows(project)
	found = costs(project) if cost_item else []
	if not rows and not found:
		frappe.throw(_("{0} has no billable time that is not invoiced yet.").format(source.project_name))
	invoice = frappe.new_doc("Sales Invoice")
	invoice.customer = source.customer
	invoice.project = project
	# The customer is billed in their currency, and each timesheet's amount is
	# turned into it, as ERPNext's own Fetch Timesheet does.
	bill_in(invoice, "Customer", source.customer)
	rows = in_currency(rows, invoice.currency)
	for line in lines(rows):
		invoice.append(
			"items",
			{
				"item_code": item,
				"qty": line["hours"],
				"rate": line["rate"],
				"description": line["activity"] or _("Time"),
			},
		)
	# What was bought for it, at cost plus the project's markup, in the
	# currency the customer is billed in.
	rate = currency_rate(_company_currency(project), invoice.currency) if found else 1
	for one in found:
		invoice.append(
			"items",
			{
				"item_code": cost_item,
				"qty": 1,
				"rate": flt(one["charge"] * flt(rate), 2),
				"description": one["title"],
				"one_rebills": one["key"],
			},
		)
	for row in rows:
		invoice.append(
			"timesheets",
			{
				"time_sheet": row.time_sheet,
				"timesheet_detail": row.name,
				"billing_hours": row.billing_hours,
				"billing_amount": row.billing_amount,
				"activity_type": row.activity_type,
				"description": row.description,
				"from_time": row.from_time,
				"to_time": row.to_time,
				"project_name": row.project_name,
			},
		)
	invoice.run_method("set_missing_values")
	invoice.run_method("calculate_taxes_and_totals")
	return invoice


@frappe.whitelist()
@frappe.read_only()
def invoices(project: str) -> dict:
	"""The customer's invoices for the project and those under it, newest
	first, read as the reader reads invoices: an invoice names the project, or
	one of its lines does. Drafts and returns included, cancelled ones not."""
	from onedesk.one_project import tree

	frappe.has_permission("Project", "read", project, throw=True)
	if not frappe.has_permission("Sales Invoice", "read"):
		return {"invoices": [], "totals": {}, "can_create": False}
	projects = sorted(tree.below({project}, tree.parents()))
	named = set(
		frappe.get_list(
			"Sales Invoice",
			filters={"project": ["in", projects], "docstatus": ["<", 2]},
			pluck="name",
			limit_page_length=0,
		)
	)
	named |= {
		row.parent
		for row in frappe.get_list(
			"Sales Invoice Item",
			parent_doctype="Sales Invoice",
			filters=[
				["Sales Invoice Item", "project", "in", projects],
				["Sales Invoice", "docstatus", "<", 2],
			],
			fields=["parent"],
			limit_page_length=0,
		)
	}
	rows = (
		frappe.get_list(
			"Sales Invoice",
			filters={"name": ["in", list(named)]},
			fields=[
				"name",
				"customer_name",
				"posting_date",
				"due_date",
				"status",
				"docstatus",
				"is_return",
				"currency",
				"grand_total",
				"base_grand_total",
				"outstanding_amount",
				"conversion_rate",
			],
			order_by="posting_date desc, creation desc",
			limit_page_length=0,
		)
		if named
		else []
	)
	totals = {"invoiced": 0.0, "paid": 0.0, "outstanding": 0.0, "overdue": 0.0, "drafts": 0}
	for row in rows:
		if row.docstatus == 0:
			totals["drafts"] += 1
			continue
		owed = flt(row.outstanding_amount) * flt(row.conversion_rate or 1)
		totals["invoiced"] += flt(row.base_grand_total)
		totals["paid"] += flt(row.base_grand_total) - owed
		totals["outstanding"] += owed
		if row.status == "Overdue":
			totals["overdue"] += owed
	return {
		"invoices": [
			{
				"name": row.name,
				"customer": row.customer_name,
				"date": str(row.posting_date) if row.posting_date else None,
				"due": str(row.due_date) if row.due_date else None,
				"status": "Draft" if row.docstatus == 0 else row.status,
				"currency": row.currency,
				"total": flt(row.grand_total),
				"outstanding": flt(row.outstanding_amount),
			}
			for row in rows
		],
		"totals": totals,
		"can_create": bool(frappe.has_permission("Sales Invoice", "create")),
	}


def lines(rows: list) -> list[dict]:
	"""Time by activity, in the order each activity first appears: its hours
	and the rate that gives its amount. Pure."""
	found: dict = {}
	for row in rows:
		one = found.setdefault(
			row.get("activity_type"), {"activity": row.get("activity_type"), "hours": 0.0, "amount": 0.0}
		)
		one["hours"] += flt(row.get("billing_hours"))
		one["amount"] += flt(row.get("billing_amount"))
	return [
		{**one, "rate": one["amount"] / one["hours"] if one["hours"] else 0.0}
		for one in found.values()
		if one["hours"] or one["amount"]
	]


def in_currency(rows: list, currency: str) -> list:
	"""Timesheet rows with their billing amount in `currency`, each from its
	timesheet's own."""
	rates: dict = {}
	for row in rows:
		source = row.get("currency")
		if source not in rates:
			rates[source] = currency_rate(source, currency)
		row["billing_amount"] = flt(row.get("billing_amount")) * rates[source]
	return rows


def _rows(project: str) -> list:
	"""The billable time not yet invoiced on the project and those under it
	billed to the same customer, a retainer's left out, by ERPNext's own
	Fetch Timesheet read."""
	from erpnext.projects.doctype.timesheet.timesheet import get_projectwise_timesheet_data

	from onedesk.one_project import kinds, tree

	customer = frappe.db.get_value("Project", project, "customer")
	found = []
	for one in sorted(tree.below({project}, tree.parents())):
		head = frappe.db.get_value("Project", one, ["customer", "one_kind"], as_dict=True)
		if not head or head.one_kind == kinds.RETAINER or (one != project and head.customer != customer):
			continue
		found.extend(get_projectwise_timesheet_data(project=one))
	return found


def _last_item(costs: bool = False) -> str | None:
	"""The item the last invoice for time, or for costs, was made out in."""
	found = frappe.db.sql(
		"""select item.item_code from `tabSales Invoice Item` item
		where ifnull(item.one_rebills, '') != '' order by item.creation desc limit 1"""
		if costs
		else """select item.item_code from `tabSales Invoice Item` item
		where ifnull(item.one_rebills, '') = ''
		and exists (select 1 from `tabSales Invoice Timesheet` time where time.parent = item.parent)
		order by item.creation desc limit 1"""
	)
	return found[0][0] if found else None


def _company_currency(project: str) -> str | None:
	company = frappe.db.get_value("Project", project, "company")
	return frappe.get_cached_value("Company", company, "default_currency") if company else None


def charge(cost: float, markup: float) -> float:
	"""What a cost is billed at: the cost plus the markup, a share of it. Pure."""
	return round(flt(cost) * (1 + flt(markup) / 100), 2)


def costs(project: str) -> list[dict]:
	"""What was bought for the project and those under it, on Time and
	Materials projects billed to the same customer, not billed yet: supplier
	bills' lines, stock issued to it and approved expense claims, each with
	what it cost the company and what it's billed at."""
	from onedesk.one_project import kinds, tree

	customer = frappe.db.get_value("Project", project, "customer")
	heads = {
		one.name: one
		for one in frappe.get_all(
			"Project",
			filters={"name": ["in", sorted(tree.below({project}, tree.parents()))]},
			fields=["name", "project_name", "customer", "one_kind", "one_markup"],
		)
		if one.one_kind == kinds.TIME and one.customer == customer
	}
	if not heads:
		return []
	found = []
	for row in frappe.get_all(
		"Purchase Invoice Item",
		filters={"project": ["in", list(heads)], "docstatus": 1, "parenttype": "Purchase Invoice"},
		fields=["name", "parent", "project", "item_name", "base_net_amount as cost"],
	):
		supplier = frappe.db.get_value("Purchase Invoice", row.parent, "supplier_name")
		found.append(_cost("Purchase Invoice Item", row, heads, f"{row.item_name} · {supplier}"))
	for row in frappe.get_all(
		"Stock Entry Detail",
		filters={
			"project": ["in", list(heads)],
			"docstatus": 1,
			"s_warehouse": ["is", "set"],
			"t_warehouse": ["is", "not set"],
		},
		fields=["name", "parent", "project", "item_name", "amount as cost"],
	):
		found.append(_cost("Stock Entry Detail", row, heads, row.item_name))
	for row in frappe.get_all(
		"Expense Claim",
		filters={"project": ["in", list(heads)], "docstatus": 1, "approval_status": "Approved"},
		fields=["name", "name as parent", "project", "employee_name", "total_sanctioned_amount as cost"],
	):
		found.append(_cost("Expense Claim", row, heads, _("Expenses · {0}").format(row.employee_name)))
	found = [one for one in found if one["cost"] > 0]
	billed = set(
		frappe.get_all(
			"Sales Invoice Item",
			filters={"one_rebills": ["in", [one["key"] for one in found] or [""]], "docstatus": ["<", 2]},
			pluck="one_rebills",
		)
	)
	return [one for one in found if one["key"] not in billed]


def _cost(doctype: str, row, heads: dict, title: str) -> dict:
	head = heads[row.project]
	return {
		"key": f"{doctype}:{row.name}",
		"parent": row.parent,
		"project": row.project,
		"title": title if len(heads) == 1 else f"{title} · {head.project_name}",
		"cost": flt(row.cost),
		"charge": charge(row.cost, head.one_markup),
	}


def ordered(doc, method=None) -> None:
	"""Sales Order on_submit: an order for extra work on a project becomes a
	sub-project of it."""
	parent = doc.get("project")
	if not doc.get(EXTRA) or not parent or frappe.db.exists("Project", {"sales_order": doc.name}):
		return
	from erpnext.selling.doctype.sales_order.mapper import make_project

	project = make_project(doc.name)
	project.project_name = title(doc)
	project.set("one_parent", parent)
	project.flags.ignore_permissions = True
	project.insert()
	# The order and its lines are the sub-project's now. ERPNext links an order
	# to its project only when it names none, and this one named the parent.
	doc.db_set("project", project.name)
	frappe.db.set_value("Sales Order Item", {"parent": doc.name}, "project", project.name)
	project.update_sales_amount()
	project.db_set("total_sales_amount", project.total_sales_amount)
	frappe.msgprint(
		_("{0} is a sub-project of {1}.").format(
			frappe.bold(project.project_name), frappe.db.get_value("Project", parent, "project_name")
		),
		alert=True,
	)


def title(doc) -> str:
	"""What an order's sub-project is called: its one item, or its first item
	and how many more. Pure over the order's rows."""
	names = [row.item_name or row.item_code for row in doc.get("items") or []]
	if not names:
		return doc.name
	if len(names) == 1:
		return names[0]
	return _("{0} and {1} more").format(names[0], len(names) - 1)
