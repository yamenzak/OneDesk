"""VAT: what the UAE return needs filled in, and what any return reads.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

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


def unreclaimed(company: str) -> list[str]:
	"""Submitted bills that carry VAT on the return's accounts but claim none
	of it back in box 9: bills from before `reclaimed` filled the figure."""
	accounts = settled_accounts(company)
	if not accounts or not frappe.get_meta("Purchase Invoice").has_field("recoverable_standard_rated_expenses"):
		return []
	return frappe.get_all(
		"Purchase Invoice",
		filters={
			"company": company,
			"docstatus": 1,
			"reverse_charge": ["!=", "Y"],
			"recoverable_standard_rated_expenses": 0,
			"name": ["in", frappe.get_all(
				"Purchase Taxes and Charges",
				filters={"parenttype": "Purchase Invoice", "account_head": ["in", accounts], "base_tax_amount_after_discount_amount": ["!=", 0]},
				pluck="parent",
				distinct=True,
			) or [""]],
		},
		pluck="name",
	)


def reclaim(company: str) -> int:
	"""Box 9's figure on every bill `unreclaimed` finds, from its own VAT,
	each saying so on its timeline; never on a bill in a period the books
	are closed for, whose return is filed."""
	from frappe import _

	accounts = set(settled_accounts(company))
	closed = frappe.get_cached_value("Company", company, "accounts_frozen_till_date")
	done = 0
	for name in unreclaimed(company):
		doc = frappe.get_doc("Purchase Invoice", name)
		if closed and doc.posting_date and getdate(doc.posting_date) <= getdate(closed):
			continue
		doc.db_set("recoverable_standard_rated_expenses", vat_on(doc, accounts), update_modified=False)
		doc.add_comment("Info", _("Recoverable VAT for the return set from its own VAT."))
		done += 1
	return done


def emirate(doc, method=None) -> None:
	"""Sales Invoice validate: the emirate a sale is reported under, from the
	company's address. Frappe fetches it only when the address is picked on
	the page, so an invoice made any other way — repeated, from an order, by
	the API — went without."""
	if doc.meta.has_field("vat_emirate") and not doc.get("vat_emirate") and doc.get("company_address"):
		doc.vat_emirate = frappe.db.get_value("Address", doc.company_address, "emirate")


def emirate_only_in_the_uae() -> None:
	"""after_migrate: ERPNext's UAE setup adds an Emirate to every address;
	it is shown only on an address in the UAE. Nothing where the field was
	never added."""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	if not frappe.get_meta("Address").has_field("emirate"):
		return
	wanted = f"eval:doc.country == '{UAE}'"
	if frappe.db.get_value("Property Setter", {"doc_type": "Address", "field_name": "emirate", "property": "depends_on"}, "value") == wanted:
		return
	make_property_setter("Address", "emirate", "depends_on", wanted, "Data", validate_fields_for_doctype=False)
