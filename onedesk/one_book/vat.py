"""VAT: what the UAE return needs filled in, and what any return reads.

**The UAE's own return** is ERPNext's UAE VAT 201 (regional/report/uae_vat_201),
and on a new company three of its inputs are empty and nothing says so:

- **UAE VAT Settings** names the company's VAT accounts. Without them the
  reverse-charge boxes are nought and a reverse-charge bill will not submit.
  `uae_accounts` fills them from the chart: the Tax accounts called VAT.
- **The VAT on a bill** (box 9) is not read from the bill. It is the sum of a
  field on each, *Recoverable Standard Rated Expenses*, that somebody is meant
  to type; a bill left at nought does not count, so the company reclaims none
  of the VAT it paid and pays it twice. `reclaimed` (Purchase Invoice validate)
  keeps it at the VAT charged on the bill until somebody types their own
  figure, which is then left alone.
- **The emirate and the TRN.** Box 1 is by emirate, read from the company's
  address; a UAE tax invoice must carry the company's TRN. A new company has
  neither. The Books Check asks for both, and `emirate` (Sales Invoice
  validate) copies the emirate onto an invoice made anywhere but its page.

**A return any country can read** is report/vat_return: tax charged on
invoices against tax paid on bills and expense claims, by tax account and
rate, and what is left to pay or reclaim.
"""

import frappe
from frappe import _
from frappe.utils import flt

UAE = "United Arab Emirates"

EMIRATES = ("Abu Dhabi", "Ajman", "Dubai", "Fujairah", "Ras Al Khaimah", "Sharjah", "Umm Al Quwain")


def in_uae(company: str) -> bool:
	return frappe.get_cached_value("Company", company, "country") == UAE


def vat_accounts(company: str) -> list[str]:
	"""The company's VAT accounts: leaf Tax accounts with VAT in the name."""
	return frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "account_type": "Tax", "account_name": ["like", "%VAT%"]},
		pluck="name",
		order_by="lft",
	)


def uae_accounts(company: str) -> None:
	"""UAE VAT Settings for the company, from its chart."""
	found = vat_accounts(company)
	if not found:
		frappe.throw(_("The chart of accounts has no Tax account with VAT in its name."))
	settings = (
		frappe.get_doc("UAE VAT Settings", company)
		if frappe.db.exists("UAE VAT Settings", company)
		else frappe.new_doc("UAE VAT Settings")
	)
	settings.company = company
	have = {row.account for row in settings.uae_vat_accounts}
	for account in found:
		if account not in have:
			settings.append("uae_vat_accounts", {"account": account})
	settings.save()


def settled_accounts(company: str) -> list[str]:
	return frappe.get_all("UAE VAT Account", filters={"parent": company}, pluck="account")


def company_address(company: str) -> str | None:
	found = frappe.get_all(
		"Dynamic Link",
		filters={"link_doctype": "Company", "link_name": company, "parenttype": "Address"},
		pluck="parent",
	)
	return found[0] if found else None


def add_address(company: str, emirate: str, line: str, city: str | None = None) -> str:
	"""The company's own address, which an invoice prints and box 1 reads the
	emirate from."""
	if emirate not in EMIRATES:
		frappe.throw(_("Pick the emirate."))
	if not (line or "").strip():
		frappe.throw(_("Enter the street address."))
	address = frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": company,
			"address_type": "Office",
			"address_line1": line.strip(),
			"city": (city or "").strip() or emirate,
			"country": UAE,
			"emirate": emirate,
			"is_your_company_address": 1,
			"is_primary_address": 1,
			"links": [{"link_doctype": "Company", "link_name": company}],
		}
	).insert()
	return address.name


def recoverable(typed: float, before: float | None, vat_before: float | None, vat: float) -> float:
	"""What a bill says is reclaimable: the VAT on it, unless somebody typed a
	figure of their own. A figure is theirs when it is set and was not simply
	the VAT the bill had before. Pure."""
	if not flt(typed):
		return vat
	if before is not None and flt(typed) == flt(before) and flt(before) == flt(vat_before):
		return vat
	return flt(typed)


def vat_on(doc, accounts: set) -> float:
	"""The reclaimable VAT on a bill: VAT rows added to its total, not to the
	cost of what was bought."""
	return sum(
		flt(row.base_tax_amount_after_discount_amount)
		for row in doc.get("taxes") or []
		if row.account_head in accounts and row.add_deduct_tax == "Add" and row.category == "Total"
	)


def reclaimed(doc, method=None) -> None:
	"""Purchase Invoice validate: keep box 9's figure at the bill's VAT."""
	if not doc.meta.has_field("recoverable_standard_rated_expenses") or doc.get("reverse_charge") == "Y":
		return
	if not in_uae(doc.company):
		return
	accounts = set(settled_accounts(doc.company))
	if not accounts:
		return
	before = doc.get_doc_before_save()
	doc.recoverable_standard_rated_expenses = recoverable(
		doc.recoverable_standard_rated_expenses,
		before.recoverable_standard_rated_expenses if before else None,
		vat_on(before, accounts) if before else None,
		vat_on(doc, accounts),
	)


def emirate(doc, method=None) -> None:
	"""Sales Invoice validate: the emirate a sale is reported under, from the
	company's address. Frappe fetches it only when the address is picked on
	the page, so an invoice made any other way — repeated, from an order, by
	the API — went without."""
	if doc.meta.has_field("vat_emirate") and not doc.get("vat_emirate") and doc.get("company_address"):
		doc.vat_emirate = frappe.db.get_value("Address", doc.company_address, "emirate")
