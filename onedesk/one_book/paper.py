"""What a printed invoice says that ERPNext keeps nowhere a print format can
read it from: each line's VAT, and the account the customer pays into.

ERPNext works out each line's tax (Item Wise Tax Detail) but keeps it in a
table of its own, by row id, which frappe's print format builder cannot join
to the lines. Written onto each line as it is saved, it is three fields the
builder places like any other.
"""

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


#: The dirham's symbol as frappe ships it, and as One prints and shows it: the
#: code, which every printer and every reader reads the same.
DIRHAM = ("د.إ", "AED")


def settle() -> None:
	"""after_install and after_migrate: AED said by its code, unless the
	workspace has chosen another symbol for it."""
	shipped, ours = DIRHAM
	if frappe.db.get_value("Currency", "AED", "symbol") == shipped:
		frappe.db.set_value("Currency", "AED", "symbol", ours)
		frappe.clear_cache()
