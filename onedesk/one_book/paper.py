"""What a printed invoice says that ERPNext keeps nowhere a print format can
read it from: each line's VAT, the account the customer pays into, and whether
it is a tax invoice.

ERPNext keeps each line's tax (Item Wise Tax Detail) in a table of its own,
which frappe's print format builder cannot join to the lines. Written onto
each line as it is saved, it is three fields the builder places like any other.
"""

import re

import frappe
from frappe.utils import flt


def lines(doc, method=None) -> None:
	"""validate: each line's VAT rate, its VAT, and the line with its VAT.
	ERPNext works the tax out as the invoice validates and writes its table
	only once it's saved, so until then it's read from what ERPNext holds."""
	taxes: dict = {}
	pending = doc.get("_item_wise_tax_details")
	for one in pending if pending is not None else doc.get("item_wise_tax_details") or []:
		key = id(one.item) if pending is not None else one.item_row
		rate, amount = taxes.get(key, (0.0, 0.0))
		taxes[key] = (rate + flt(one.get("rate")), amount + flt(one.get("amount")))
	for row in doc.get("items") or []:
		rate, amount = taxes.get(id(row) if pending is not None else row.name, (0.0, 0.0))
		row.one_vat_rate = rate
		row.one_vat_amount = amount
		row.one_line_total = flt(row.net_amount) + amount


def pay_into(doc, method=None) -> None:
	"""validate: the company's own bank account, its default first, unless one was chosen."""
	if doc.get("one_pay_into") or not doc.get("company"):
		return
	doc.one_pay_into = frappe.db.get_value(
		"Bank Account",
		{"company": doc.company, "is_company_account": 1, "disabled": 0},
		"name",
		order_by="is_default desc, creation asc",
	)


def titled(doc, *_args) -> None:
	"""before_print: whether the invoice prints as a tax invoice, which it does
	carrying the company's tax number where the law calls it one
	(one/countries.py). The print formats read `doc.flags.one_tax_invoice`."""
	from onedesk.one import countries

	doc.flags.one_tax_invoice = bool(doc.get("company_tax_id")) and countries.tax_invoice(doc.get("company"))


DIRHAM = ("د.إ", "AED")


def settle() -> None:
	"""after_install and after_migrate: AED said by its code, unless the
	workspace has chosen another symbol for it, and each tax line saying its
	rate once, on the templates and on what was made from them, so every
	document prints it so."""
	shipped, ours = DIRHAM
	if frappe.db.get_value("Currency", "AED", "symbol") == shipped:
		frappe.db.set_value("Currency", "AED", "symbol", ours)
		frappe.clear_cache()
	for doctype in ("Sales Taxes and Charges", "Purchase Taxes and Charges"):
		for row in frappe.get_all(
			doctype,
			filters={"description": ["like", "%@%"]},
			fields=["name", "description", "rate"],
		):
			said = tax_label(row.description, row.rate)
			if said != row.description:
				frappe.db.set_value(doctype, row.name, "description", said, update_modified=False)


def tax_label(description: str | None, rate) -> str:
	"""A tax line as a reader says it: ERPNext writes "VAT 5% @ 5.0", the rate
	twice, the second as a bare number. Pure."""
	said = (description or "").strip()
	found = re.match(r"^(.*?)\s*@\s*([0-9.]+)\s*$", said)
	if not found:
		return said
	head, number = found.group(1), flt(found.group(2))
	if "%" in head:
		return head
	return f"{head} @ {number:g}%"

