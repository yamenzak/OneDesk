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
	"""validate: each line's VAT rate, its VAT, and the line with its VAT."""
	taxes: dict = {}
	for one in doc.get("item_wise_tax_details") or []:
		rate, amount = taxes.get(one.item_row, (0.0, 0.0))
		taxes[one.item_row] = (rate + flt(one.rate), amount + flt(one.amount))
	for row in doc.get("items") or []:
		rate, amount = taxes.get(row.name, (0.0, 0.0))
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
