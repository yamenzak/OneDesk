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
which is ERPNext's (TimesheetBillingService). A sub-project's time is its own
and is invoiced from it.

**A quotation for extra work becomes a sub-project** (`ordered`). **Sub-project
Of** on a Quotation is carried to its Sales Order (the same field on both, so
ERPNext's mapping carries it), and when the order is submitted a project is
made for it under that one — ERPNext's own "Create > Project" from an order,
with the order's total as its estimate — so the handrails a customer asked for
halfway through the windows have their own order, time, costs and invoices,
and add up into the villa's.
"""

import frappe
from frappe import _
from frappe.utils import flt

#: The field on Quotation and Sales Order naming the project an order goes under.
UNDER = "one_project"


@frappe.whitelist()
@frappe.read_only()
def unbilled(project: str) -> dict:
	"""What Invoice Time would bill: the hours, their amount, and the item used
	for time last time."""
	frappe.has_permission("Project", "read", project, throw=True)
	rows = _rows(project)
	return {
		"hours": sum(flt(row.billing_hours) for row in rows),
		"amount": sum(flt(row.billing_amount) for row in rows),
		"currency": rows[0].currency if rows else None,
		"customer": frappe.db.get_value("Project", project, "customer"),
		"item": _last_item(),
	}


@frappe.whitelist(methods=["POST"])
def invoice_time(source_name: str, item: str | None = None):
	"""A draft Sales Invoice for the project's billable time not yet invoiced,
	for the page to open through frappe.model.open_mapped_doc, which passes the
	item in its args. Nothing is saved."""
	project = source_name
	item = item or (frappe.flags.args or {}).get("item")
	if not item:
		frappe.throw(_("Pick the item to invoice the time as."))
	frappe.has_permission("Project", "read", project, throw=True)
	frappe.has_permission("Sales Invoice", "create", throw=True)
	source = frappe.db.get_value("Project", project, ["project_name", "customer"], as_dict=True)
	if not source.customer:
		frappe.throw(_("Give {0} a customer to bill its time to.").format(source.project_name))
	rows = _rows(project)
	if not rows:
		frappe.throw(_("{0} has no billable time that is not invoiced yet.").format(source.project_name))
	invoice = frappe.new_doc("Sales Invoice")
	invoice.customer = source.customer
	invoice.project = project
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


def lines(rows: list) -> list[dict]:
	"""Time by activity, in the order each activity first appears: its hours
	and the rate that gives its amount. Pure."""
	found: dict = {}
	for row in rows:
		one = found.setdefault(row.get("activity_type"), {"activity": row.get("activity_type"), "hours": 0.0, "amount": 0.0})
		one["hours"] += flt(row.get("billing_hours"))
		one["amount"] += flt(row.get("billing_amount"))
	return [
		{**one, "rate": one["amount"] / one["hours"] if one["hours"] else 0.0}
		for one in found.values()
		if one["hours"] or one["amount"]
	]


def _rows(project: str) -> list:
	from erpnext.projects.doctype.timesheet.timesheet import get_projectwise_timesheet_data

	return get_projectwise_timesheet_data(project=project)


def _last_item() -> str | None:
	"""The item the last invoice for time was made out in."""
	found = frappe.db.sql(
		"""select item.item_code from `tabSales Invoice Item` item
		where exists (select 1 from `tabSales Invoice Timesheet` time where time.parent = item.parent)
		order by item.creation desc limit 1"""
	)
	return found[0][0] if found else None


def ordered(doc, method=None) -> None:
	"""Sales Order on_submit: an order for extra work on a project becomes a
	sub-project of it."""
	parent = doc.get(UNDER)
	if not parent or doc.project or frappe.db.exists("Project", {"sales_order": doc.name}):
		return
	from erpnext.selling.doctype.sales_order.mapper import make_project

	project = make_project(doc.name)
	project.project_name = title(doc)
	project.set("one_parent", parent)
	project.flags.ignore_permissions = True
	project.insert()
	# The order is linked to it in its after_insert, after its sales were added up.
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
