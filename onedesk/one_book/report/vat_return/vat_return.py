"""Tax charged on invoices against tax paid on bills and expense claims, by
tax account and rate, for a period, and what is left to pay or reclaim.

It reads the tax rows of submitted documents, so a credit note lowers what was
charged and a debit note what was paid. A bill's tax counts only when it was
added to the bill's total: tax added to the cost of what was bought (Valuation)
cannot be reclaimed. Journal entries to a tax account are not in it; they are
in the General Ledger.
"""

import frappe
from frappe import _
from frappe.utils import flt, get_quarter_start, getdate, nowdate

#: (section, parent doctype, tax row doctype, taxable field on the parent, extra condition)
SOURCES = (
	("output", "Sales Invoice", "Sales Taxes and Charges", "base_net_total", ""),
	(
		"input",
		"Purchase Invoice",
		"Purchase Taxes and Charges",
		"base_net_total",
		"and tax.add_deduct_tax = 'Add' and tax.category = 'Total'",
	),
	("input", "Expense Claim", "Expense Taxes and Charges", "total_sanctioned_amount", ""),
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	start = getdate(filters.from_date or get_quarter_start(nowdate()))
	end = getdate(filters.to_date or nowdate())
	rows = []
	for section, parent, child, taxable, extra in SOURCES:
		if frappe.db.table_exists(child) and frappe.has_permission(parent, "read"):
			rows += _rows(section, parent, child, taxable, extra, start, end)
	return columns(), lines(rows)


def columns() -> list[dict]:
	return [
		{"fieldname": "line", "label": _("Line"), "fieldtype": "Data", "width": 300},
		{"fieldname": "rate", "label": _("Rate (%)"), "fieldtype": "Percent", "width": 90},
		{"fieldname": "taxable", "label": _("Taxable Amount"), "fieldtype": "Currency", "width": 160},
		{"fieldname": "tax", "label": _("Tax"), "fieldtype": "Currency", "width": 140},
	]


def _rows(section, parent, child, taxable, extra, start, end) -> list[dict]:
	amount = "tax.base_tax_amount" if child == "Expense Taxes and Charges" else "tax.base_tax_amount_after_discount_amount"
	found = frappe.db.sql(
		f"""select tax.account_head as account, tax.rate as rate,
			sum({amount}) as tax, sum(doc.{taxable}) as taxable, '{parent}' as source
		from `tab{child}` tax join `tab{parent}` doc on doc.name = tax.parent
		where tax.parenttype = %(parent)s and doc.docstatus = 1
			and doc.posting_date between %(start)s and %(end)s {extra}
		group by tax.account_head, tax.rate""",
		{"parent": parent, "start": start, "end": end},
		as_dict=True,
	)
	return [dict(one, section=section) for one in found]


def lines(rows: list[dict]) -> list[dict]:
	"""The report's lines: what was charged, what was paid, each by account and
	rate with a total, and the difference. Pure over rows of section, account,
	rate, taxable and tax."""
	out = []
	totals = {}
	for section, heading, total in (
		("output", _("Tax charged on sales"), _("Total charged")),
		("input", _("Tax paid on purchases and expenses"), _("Total paid")),
	):
		mine = sorted((one for one in rows if one["section"] == section), key=lambda one: (one["account"], -flt(one["rate"])))
		out.append({"line": heading, "bold": 1})
		for one in mine:
			out.append({"line": one["account"], "rate": flt(one["rate"]), "taxable": flt(one["taxable"]), "tax": flt(one["tax"]), "sub": 1})
		totals[section] = sum(flt(one["tax"]) for one in mine)
		out.append({"line": total, "tax": totals[section], "bold": 1})
	due = totals["output"] - totals["input"]
	out.append({"line": _("To pay") if due >= 0 else _("To reclaim"), "tax": abs(due), "bold": 1})
	return out
