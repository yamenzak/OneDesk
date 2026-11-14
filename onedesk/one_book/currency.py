"""Billing a customer or supplier in their own currency: `bill_in` sets what
the form would, and `rate` turns an amount from one currency into another.
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate


def billed_in(party_type: str, party: str, company: str | None = None) -> str:
	"""The currency ERPNext bills the party in, for the company: what it was
	billed in already, else its own account's, its group's, then the
	company's default, ERPNext's order (party.get_party_account). Read
	without ERPNext's question whether the reader may open that ledger
	account, which a project's team may not: the currency is no secret."""
	from erpnext import get_company_currency
	from onedesk.one.company import reader_company
	from erpnext.accounts.party import get_party_gle_currency

	company = company or reader_company()
	found = get_party_gle_currency(party_type, party, company)
	if found:
		return found
	account = frappe.db.get_value("Party Account", {"parenttype": party_type, "parent": party, "company": company}, "account")
	group = {"Customer": "Customer Group", "Supplier": "Supplier Group"}.get(party_type)
	if not account and group:
		account = frappe.db.get_value(
			"Party Account",
			{"parenttype": group, "parent": frappe.db.get_value(party_type, party, frappe.scrub(group)), "company": company},
			"account",
		)
	if not account:
		kind = frappe.get_cached_value("Party Type", party_type, "account_type")
		account = kind and frappe.get_cached_value("Company", company, f"default_{kind.lower()}_account")
	return (account and frappe.get_cached_value("Account", account, "account_currency")) or get_company_currency(company)


def rate(source: str | None, target: str, date=None) -> float:
	"""What one of `source` is worth in `target`; refused when ERPNext has no
	rate for the pair."""
	if not source or source == target:
		return 1.0
	from erpnext.setup.utils import get_exchange_rate

	date = date or nowdate()
	found = flt(get_exchange_rate(source, target, date))
	if not found:
		back = flt(get_exchange_rate(target, source, date))
		found = 1 / back if back else 0.0
	if not found:
		frappe.throw(
			_("There's no exchange rate from {0} to {1}. Add one in Currency Exchange.").format(
				source, target
			)
		)
	return found


def bill_in(doc, party_type: str, party: str) -> str:
	"""Puts a new sales or buying document in the party's currency, with its
	rate to the company's, and returns the currency."""
	from erpnext import get_company_currency
	from onedesk.one.company import reader_company

	doc.company = doc.get("company") or reader_company()
	doc.currency = billed_in(party_type, party, doc.company)
	date = doc.get("transaction_date") or doc.get("posting_date")
	doc.conversion_rate = rate(doc.currency, get_company_currency(doc.company), date)
	return doc.currency


def payable_in(company: str, currency: str) -> str:
	"""The company's payable in `currency`, Creditors USD and the like, made
	once. In a group it is made at the group's root company, which ERPNext
	then makes in every company under it, as it refuses an account a
	company's root does not have."""
	from erpnext.accounts.doctype.account.account import get_root_company

	name = frappe.db.get_value("Account", {"company": company, "account_name": f"Creditors {currency}"})
	if name:
		return name
	at = (get_root_company(company) or [company])[0]
	parent = frappe.db.get_value("Account", {"company": at, "account_type": "Payable", "is_group": 0}, "parent_account")
	account = frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": f"Creditors {currency}",
			"parent_account": parent,
			"company": at,
			"account_type": "Payable",
			"account_currency": currency,
		}
	)
	account.flags.ignore_permissions = True
	account.insert()
	return frappe.db.get_value("Account", {"company": company, "account_name": f"Creditors {currency}"})
