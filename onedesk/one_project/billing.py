"""What a project costs and what it is billed, on ERPNext's own records."""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from onedesk.one_book.currency import bill_in, billed_in
from onedesk.one_book.currency import rate as currency_rate
from onedesk.one_project import terms

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
	terms.give(invoice, *frappe.db.get_value("Project", project, ["one_payment_terms", "one_terms"]))
	rows = in_currency(rows, invoice.currency)
	for line in lines(rows):
		invoice.append("items", hours_line(item, line["hours"], line["rate"], line["activity"] or _("Time")))
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
def invoices(
	project: str, only: Annotated[bool | None, "Only the project's own work, not what is under it."] = None
) -> dict:
	"""The customer's invoices for the project and those under it, newest
	first, read as the reader reads invoices: an invoice names the project, or
	one of its lines does. Drafts and returns included, cancelled ones not.

	Each says what it's for (`for_what`) and which sub-project it's on. The
	figures count the project's share of an invoice that's partly another's,
	tax included, as it's paid; retention still held is apart from what's
	owed now; and an advance not yet set against an invoice is said."""
	from onedesk.one_project import tree

	tree.narrow(project, only)
	said = _listed(project, "Sales Invoice")
	return {**said, "invoices": said.pop("rows")}


@frappe.whitelist()
@frappe.read_only()
def bills(
	project: str, only: Annotated[bool | None, "Only the project's own work, not what is under it."] = None
) -> dict:
	"""The suppliers' bills for the project and those under it, as
	`invoices` lists the customer's: what each is for, from whom, what's
	owed now and when, the retention held apart. A draft from Bill Progress
	is there to check."""
	from onedesk.one_project import tree

	tree.narrow(project, only)
	said = _listed(project, "Purchase Invoice")
	return {**said, "bills": said.pop("rows")}


#: What each kind of document is read with: its party, and what it says
#: it's for that the other doesn't keep.
LISTED = {
	"Sales Invoice": {
		"party": "customer_name",
		"party_id": ("customer", "Customer"),
		"extra": ["one_retainer_month", "total_billing_hours"],
		"lines": ["one_rebills"],
	},
	"Purchase Invoice": {
		"party": "supplier_name",
		"party_id": ("supplier", "Supplier"),
		"extra": [],
		"lines": ["purchase_order"],
	},
}


def _listed(project: str, doctype: str) -> dict:
	from onedesk.one_project import money, retention, tree

	frappe.has_permission("Project", "read", project, throw=True)
	if not frappe.has_permission(doctype, "read"):
		return {"rows": [], "totals": {}, "can_create": False}
	how = LISTED[doctype]
	child = f"{doctype} Item"
	projects = sorted(tree.scope(project))
	named = set(
		frappe.get_list(
			doctype,
			filters={"project": ["in", projects], "docstatus": ["<", 2]},
			pluck="name",
			limit_page_length=0,
		)
	)
	named |= {
		row.parent
		for row in frappe.get_list(
			child,
			parent_doctype=doctype,
			filters=[
				[child, "project", "in", projects],
				[doctype, "docstatus", "<", 2],
			],
			fields=["parent"],
			limit_page_length=0,
		)
	}
	rows = (
		frappe.get_list(
			doctype,
			filters={"name": ["in", list(named)]},
			fields=[
				"name",
				f"{how['party']} as party",
				f"{how['party_id'][0]} as party_id",
				"posting_date",
				"due_date",
				"status",
				"docstatus",
				"is_return",
				"currency",
				"grand_total",
				"base_grand_total",
				"base_net_total",
				"outstanding_amount",
				"conversion_rate",
				"project",
				"one_progress",
				*how["extra"],
			],
			order_by="posting_date desc, creation desc",
			limit_page_length=0,
		)
		if named
		else []
	)
	names = [row.name for row in rows] or [""]
	lines = frappe.get_all(
		child,
		filters={"parent": ["in", names]},
		fields=["parent", "project", "base_net_amount", "item_name", *how["lines"]],
		order_by="idx asc",
	)
	held = retention.held_on(doctype, [row.name for row in rows if row.docstatus == 1])
	# When each is due, retention left out: the last of its other payments.
	due = {}
	for one in frappe.get_all(
		"Payment Schedule",
		filters={"parenttype": doctype, "parent": ["in", names], "payment_term": ["not in", retention.HELD]},
		fields=["parent", "due_date"],
	):
		due[one.parent] = max(due.get(one.parent) or one.due_date, one.due_date)
	titles = dict(
		frappe.get_all(
			"Project", filters={"name": ["in", projects]}, fields=["name", "project_name"], as_list=True
		)
	)
	# Each party's logo (one_mail/faces.py dresses a party without one).
	logos = dict(
		frappe.get_all(
			how["party_id"][1],
			filters={"name": ["in", list({row.party_id for row in rows}) or [""]]},
			fields=["name", "image"],
			as_list=True,
		)
	)
	totals = {"invoiced": 0.0, "paid": 0.0, "outstanding": 0.0, "overdue": 0.0, "retention": 0.0, "drafts": 0, "late": 0}
	# Late by the dates, not the status: ERPNext marks Overdue overnight.
	terms = money._terms(doctype, [row.name for row in rows if row.docstatus == 1])
	today = getdate(nowdate())
	found = []
	for row in rows:
		own = [one for one in lines if one.parent == row.name]
		mine = sum(flt(one.base_net_amount) for one in own if one.project in titles)
		share = mine / flt(row.base_net_total) if flt(row.base_net_total) else 1.0
		owed = flt(row.outstanding_amount) * flt(row.conversion_rate or 1)
		kept = held.get(row.name) or []
		holding = sum(amount for _due, amount in kept)
		now = max(0.0, owed - holding)
		held_own = flt(holding / flt(row.conversion_rate or 1), 2)
		late = (
			money.past_due(terms.get(row.name, []), row.outstanding_amount, today)
			if row.docstatus == 1 and not row.is_return
			else None
		)
		if row.docstatus == 0:
			totals["drafts"] += 1
		else:
			totals["invoiced"] += flt(row.base_grand_total) * share
			totals["paid"] += (flt(row.base_grand_total) - owed) * share
			totals["outstanding"] += now * share
			totals["retention"] += holding * share
			if late:
				totals["overdue"] += late["due"] * flt(row.conversion_rate or 1) * share
				totals["late"] += 1
		on = sorted({one.project for one in own if one.project in titles} | ({row.project} & set(titles)))
		elsewhere = [titles[one] for one in on if one != project]
		found.append(
			{
				"name": row.name,
				"party": row.party,
				"party_image": logos.get(row.party_id),
				"date": str(row.posting_date) if row.posting_date else None,
				# What's held back falls due later: the date is when the rest is
				# due, and the retention held says its own.
				"due": str(due.get(row.name) or row.due_date or "") or None,
				"owed": max(0.0, flt(row.outstanding_amount) - held_own),
				"held": held_own,
				"held_due": str(kept[0][0]) if kept else None,
				"retention_due": str(kept[0][0]) if kept and now < 0.005 else None,
				"status": "Draft"
				if row.docstatus == 0
				else ("Overdue" if late and not late["held"] else row.status),
				"late": (today - getdate(late["since"])).days if late else None,
				"currency": row.currency,
				"total": flt(row.grand_total),
				"outstanding": flt(row.outstanding_amount),
				"for": for_what(row, own),
				"where": money.bought([frappe._dict(item_name=one) for one in elsewhere]),
				"order": next((one.get("purchase_order") for one in own if one.get("purchase_order")), None),
				"can_pay": row.docstatus == 1 and not row.is_return and flt(row.outstanding_amount) > 0,
			}
		)
	cash = money._paid_on(projects, doctype) or {}
	totals["advance"] = flt(cash.get("advance"))
	return {
		"rows": found,
		"totals": totals,
		# One party needs no column of its own.
		"parties": len({row.party_id for row in rows}),
		"can_create": bool(frappe.has_permission(doctype, "create")),
		"can_pay": bool(frappe.has_permission("Payment Entry", "create")),
	}


def for_what(row, lines: list) -> dict:
	"""What an invoice is for, for the page to say: a credit note, a share
	of the work, a retainer's month, time and costs, or its first item and
	how many more. Pure."""
	if row.get("is_return"):
		return {"kind": "credit"}
	if flt(row.get("one_progress")):
		return {"kind": "progress", "value": flt(row.get("one_progress"))}
	if row.get("one_retainer_month"):
		return {"kind": "month", "value": str(row.get("one_retainer_month"))}
	hours = flt(row.get("total_billing_hours"))
	costs = any(one.get("one_rebills") for one in lines)
	if hours:
		return {"kind": "time_costs" if costs else "time", "value": hours}
	if costs:
		return {"kind": "costs"}
	names = [one.get("item_name") for one in lines if one.get("item_name")]
	if not names:
		return {"kind": None}
	return {"kind": "items", "value": names[0], "more": len(names) - 1}


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
	for one in sorted(tree.scope(project)):
		head = frappe.db.get_value("Project", one, ["customer", "one_kind"], as_dict=True)
		if not head or head.one_kind == kinds.RETAINER or (one != project and head.customer != customer):
			continue
		found.extend(get_projectwise_timesheet_data(project=one))
	return found


def hours_line(item: str, hours: float, rate: float, description: str) -> dict:
	"""An invoice line for hours. An item counted in whole units, such as a
	visit in Nos, takes them as one line priced in full, the hours said in
	its description, as ERPNext refuses part of a whole unit."""
	uom = frappe.get_cached_value("Item", item, "stock_uom")
	if flt(hours) % 1 and frappe.get_cached_value("UOM", uom, "must_be_whole_number"):
		hours_said = _("{0} h").format(f"{flt(hours, 2):g}")
		return {"item_code": item, "qty": 1, "rate": flt(flt(hours, 2) * flt(rate), 2), "description": f"{description} ({hours_said})"}
	return {"item_code": item, "qty": flt(hours, 2), "rate": rate, "description": description}


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
			filters={"name": ["in", sorted(tree.scope(project))]},
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
	"""What an order's sub-project is called: what its quotation was called,
	or else what it orders."""
	quotes = {row.get("prevdoc_docname") for row in doc.get("items") or []} - {None, ""}
	for quote in sorted(quotes):
		said = frappe.db.get_value("Quotation", quote, ["title", "customer_name", "party_name"], as_dict=True)
		# ERPNext titles a quotation with the party's name unless somebody wrote one.
		if said and said.title and said.title not in (said.customer_name, said.party_name):
			return said.title
	return ordered_title(doc)


def ordered_title(doc) -> str:
	"""Its one item, or its first item and how many more. Pure over the
	order's rows."""
	names = [row.item_name or row.item_code for row in doc.get("items") or []]
	if not names:
		return doc.name
	if len(names) == 1:
		return names[0]
	return _("{0} and {1} more").format(names[0], len(names) - 1)
