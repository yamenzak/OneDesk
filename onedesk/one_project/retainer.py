"""A Retainer's months: a fee each month for a set number of hours
(one_project/AGENTS.md, kinds.py).
"""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils import add_months, flt, get_first_day, getdate, nowdate

from onedesk.one_book.currency import bill_in, billed_in
from onedesk.one_project import billing, kinds, terms

MONTH = "one_retainer_month"

SHOWN = 6


def over(hours: float, allowance: float) -> float:
	"""Hours beyond the month's allowance. Pure."""
	return max(0.0, flt(hours) - flt(allowance)) if flt(allowance) else 0.0


def rate(rows: list) -> float:
	"""What an hour was billed at on average, over billable rows. Pure."""
	hours = sum(flt(row.get("billing_hours")) for row in rows)
	return sum(flt(row.get("billing_amount")) for row in rows) / hours if hours else 0.0


def month_list(starts, today, count: int = SHOWN) -> list:
	"""The first days of the months from the one a project starts in to this
	one, newest first, at most `count`. Pure."""
	first = get_first_day(getdate(starts or today))
	now = get_first_day(getdate(today))
	found = []
	while now >= first and len(found) < count:
		found.append(now)
		now = add_months(now, -1)
	return found


def _time(project: str, month) -> list:
	"""The month's time on the project, read as the reader reads timesheets."""
	return frappe.get_list(
		"Timesheet Detail",
		parent_doctype="Timesheet",
		filters=[
			["Timesheet Detail", "project", "=", project],
			["Timesheet Detail", "from_time", ">=", str(month)],
			["Timesheet Detail", "from_time", "<", str(add_months(month, 1))],
			["Timesheet", "docstatus", "<", 2],
		],
		fields=[
			"name",
			"parent",
			"hours",
			"billing_hours",
			"billing_amount",
			"is_billable",
			"sales_invoice",
			"docstatus",
			"activity_type",
			"description",
			"from_time",
			"to_time",
			"project_name",
		],
		limit_page_length=0,
	)


def fee_currency(doc) -> str:
	"""The currency a retainer's fee is in: the customer's own."""
	from erpnext import get_company_currency, get_default_company

	if doc.get("customer"):
		return billed_in("Customer", doc.customer, doc.get("company"))
	return get_company_currency(doc.get("company") or get_default_company())


def _priced(rows: list, currency: str) -> list:
	"""Time rows with their billing amount in `currency`."""
	sheets = {row.parent for row in rows}
	found = dict(
		frappe.get_all(
			"Timesheet", filters={"name": ["in", list(sheets)]}, fields=["name", "currency"], as_list=True
		)
		if sheets
		else []
	)
	for row in rows:
		row["currency"] = found.get(row.parent)
	return billing.in_currency(rows, currency)


def _invoices(project: str) -> dict:
	"""Each month's invoice, the latest that isn't cancelled. Whoever reads
	the project is told a month is invoiced and how it stands; the invoice
	itself, its name and its total, only whoever may read invoices."""
	reads = frappe.has_permission("Sales Invoice", "read")
	found = {}
	for one in frappe.get_all(
		"Sales Invoice",
		filters={"project": project, MONTH: ["is", "set"], "docstatus": ["<", 2]},
		fields=["name", MONTH, "status", "docstatus", "grand_total"],
		order_by="creation asc",
	):
		found[str(getdate(one.get(MONTH)))] = {
			"name": one.name if reads else None,
			"status": "Draft" if one.docstatus == 0 else one.status,
			"total": flt(one.grand_total) if reads else None,
		}
	return found


@frappe.whitelist()
@frappe.read_only()
def months(project: Annotated[str, "The project."]) -> dict:
	"""The retainer's months, newest first: hours used of the allowance, hours
	over, and the invoice if there is one."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	doc = frappe.get_cached_doc("Project", project)
	allowance = flt(doc.get("one_monthly_hours"))
	invoices = _invoices(project)
	this = get_first_day(getdate(nowdate()))
	found = []
	for month in month_list(doc.expected_start_date or doc.creation, nowdate()):
		rows = _time(project, month)
		hours = sum(flt(row.hours) for row in rows)
		found.append(
			{
				"month": str(month),
				"hours": round(hours, 2),
				"allowance": allowance,
				"over": round(over(hours, allowance), 2),
				"drafts": round(sum(flt(row.hours) for row in rows if row.docstatus == 0), 2),
				"invoice": invoices.get(str(month)),
				"current": month == this,
			}
		)
	return {
		"fee": flt(doc.get("one_monthly_fee")),
		"currency": fee_currency(doc),
		"allowance": allowance,
		"months": found,
		"renews": str(add_months(this, 1)),
		"can_invoice": bool(doc.customer) and bool(frappe.has_permission("Sales Invoice", "create")),
	}


def logged(project: str, month) -> float:
	"""Everyone's hours on the project in a month, drafts too, whoever reads."""
	found = frappe.db.sql(
		"""select sum(detail.hours) from `tabTimesheet Detail` detail
		join `tabTimesheet` sheet on sheet.name = detail.parent
		where detail.project = %s and detail.from_time >= %s and detail.from_time < %s
		and sheet.docstatus < 2""",
		(project, str(month), str(add_months(month, 1))),
	)
	return flt(found[0][0]) if found else 0.0


def invoiced(project: str, month) -> bool:
	"""Whether a month has an invoice that isn't cancelled, whoever reads."""
	return bool(
		frappe.db.exists("Sales Invoice", {"project": project, MONTH: str(month), "docstatus": ["<", 2]})
	)


def waiting(project: str) -> list[str]:
	"""Months that have ended and aren't invoiced, oldest first."""
	said = months(project)
	return [one["month"] for one in reversed(said["months"]) if not one["current"] and not one["invoice"]]


@frappe.whitelist()
@frappe.read_only()
def asked(project: Annotated[str, "The project."], month: Annotated[str, "The month's first day."]) -> dict:
	"""What Invoice Month would bill for a month: the fee, the hours, the hours
	over and what they come to, and the item used for it last time."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	doc = frappe.get_cached_doc("Project", project)
	month = get_first_day(getdate(month))
	rows = _time(project, month)
	hours = sum(flt(row.hours) for row in rows)
	extra = over(hours, doc.get("one_monthly_hours"))
	currency = fee_currency(doc)
	billable = _priced(
		[row for row in rows if row.is_billable and row.docstatus == 1 and not row.sales_invoice], currency
	)
	return {
		"month": str(month),
		"currency": currency,
		"fee": flt(doc.get("one_monthly_fee")),
		"hours": round(hours, 2),
		"over": round(extra, 2),
		"over_amount": round(extra * rate(billable), 2),
		"drafts": round(sum(flt(row.hours) for row in rows if row.docstatus == 0), 2),
		"invoiced": _invoices(project).get(str(month)),
		"item": _last_item(),
	}


@frappe.whitelist(methods=["POST"])
def invoice_month(source_name: str, month: str | None = None, item: str | None = None, overage: int = 1):
	"""A draft Sales Invoice for a retainer's month, for the page to open
	through frappe.model.open_mapped_doc, which passes the month, the item and
	whether to bill the hours over in its args. Nothing is saved."""
	project = source_name
	args = frappe.flags.args or {}
	month = month or args.get("month")
	item = item or args.get("item")
	overage = int(args.get("overage", overage) or 0)
	if not month or not item:
		frappe.throw(_("Pick the month and the item to invoice it as."))
	frappe.has_permission("Project", "read", project, throw=True)
	frappe.has_permission("Sales Invoice", "create", throw=True)
	doc = frappe.get_doc("Project", project)
	if doc.get("one_kind") != kinds.RETAINER:
		frappe.throw(_("{0} is not a retainer.").format(doc.project_name))
	if not doc.customer:
		frappe.throw(_("Give {0} a customer to invoice.").format(doc.project_name))
	month = get_first_day(getdate(month))
	if _invoices(project).get(str(month)):
		frappe.throw(_("{0} is invoiced already.").format(_(month.strftime("%B")) + month.strftime(" %Y")))
	rows = _time(project, month)
	hours = sum(flt(row.hours) for row in rows)
	billable = [row for row in rows if row.is_billable and row.docstatus == 1 and not row.sales_invoice]
	named = _("{0}, {1}").format(doc.project_name, _(month.strftime("%B")) + month.strftime(" %Y"))

	invoice = frappe.new_doc("Sales Invoice")
	invoice.customer = doc.customer
	invoice.project = project
	invoice.set(MONTH, month)
	bill_in(invoice, "Customer", doc.customer)
	terms.give(invoice, *terms.of(project)[:2])
	billable = _priced(billable, invoice.currency)
	invoice.append(
		"items", {"item_code": item, "qty": 1, "rate": flt(doc.get("one_monthly_fee")), "description": named}
	)
	extra = over(hours, doc.get("one_monthly_hours"))
	if overage and extra and rate(billable):
		invoice.append(
			"items",
			billing.hours_line(
				item,
				extra,
				rate(billable),
				_("Hours over the {0} h a month").format(f"{flt(doc.get('one_monthly_hours'), 1):g}"),
			),
		)
	for row in billable:
		invoice.append(
			"timesheets",
			{
				"time_sheet": row.parent,
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


def _last_item() -> str | None:
	"""The item the last retainer month was invoiced as, or the last time."""
	found = frappe.db.sql(
		f"""select item.item_code from `tabSales Invoice Item` item
		join `tabSales Invoice` invoice on invoice.name = item.parent
		where invoice.`{MONTH}` is not null order by item.creation desc limit 1"""
	)
	return found[0][0] if found else billing._last_item()


def billed_by_month(doc, method=None) -> None:
	"""Sales Invoice validate: a retainer's hours are billed with its month
	(Invoice Month), never on their own, as ERPNext's Fetch Timesheet would,
	or they'd be billed twice."""
	if doc.get(MONTH):
		return
	details = [row.timesheet_detail for row in doc.get("timesheets") or [] if row.get("timesheet_detail")]
	if not details:
		return
	projects = set(frappe.get_all("Timesheet Detail", filters={"name": ["in", details]}, pluck="project"))
	found = frappe.get_all(
		"Project", filters={"name": ["in", list(projects - {None})], "one_kind": kinds.RETAINER}, pluck="project_name"
	)
	if found:
		frappe.throw(_("{0} is a retainer. Its hours are billed with its month.").format(found[0]))
