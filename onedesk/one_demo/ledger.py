"""The books' second rank, after `books`: a closed year, the founders' shares,
the dirham's peg, a customer who is also a supplier, the cheque the bank
prints, foreign balances valued again, costs shared between cost centers,
the corrections an accountant keeps to hand, a weekly mail of the figures
and the codes an e-invoice uses, so no OneBook list opens empty. What is left
empty on purpose is in the README."""

import frappe
from frappe.utils import add_days, add_years, get_first_day, getdate

from onedesk.one_demo.base import ABBR, COMPANY, as_user, make, once, today

ACCOUNTS = "huda@one.test"

PARTS = (
	"_closed_year",
	"_shares",
	"_peg",
	"_party_link",
	"_cheque",
	"_revaluation",
	"_allocation",
	"_corrections",
	"_digest",
	"_codes",
)


def run(password=None):
	with as_user("Administrator"):
		for part in PARTS:
			globals()[part]()


def _account(**filters) -> str:
	return frappe.db.get_value("Account", {"company": COMPANY, "is_group": 0, **filters}, "name")


def _closed_year():
	"""Last year, before the books began, closed to every kind of entry."""
	year = getdate(today()).year - 1
	once(
		"Accounting Period",
		{"company": COMPANY, "start_date": f"{year}-01-01"},
		{
			"period_name": str(year),
			"company": COMPANY,
			"start_date": f"{year}-01-01",
			"end_date": f"{year}-12-31",
			"closed_documents": [
				{"document_type": kind, "closed": 1}
				for kind in ("Sales Invoice", "Purchase Invoice", "Journal Entry", "Payment Entry")
			],
		},
	)


def _shares():
	"""The two founders' ordinary shares, issued when the company began."""
	once("Share Type", {"name": "Ordinary"}, {"__newname": "Ordinary", "title": "Ordinary"})
	equity = _account(root_type="Equity", account_type=["in", ["", None]]) or _account(root_type="Equity")
	bank = frappe.db.get_value("Bank Account", {"company": COMPANY}, "account")
	start = 1
	for name, shares in (("Karim Mansour", 6000), ("Samir Aoun", 4000)):
		holder = once("Shareholder", {"title": name}, {"title": name, "company": COMPANY}).name
		if not frappe.db.exists("Share Transfer", {"to_shareholder": holder, "docstatus": 1}):
			make(
				{
					"doctype": "Share Transfer",
					"transfer_type": "Issue",
					"date": get_first_day(f"{getdate(today()).year}-01-01"),
					"company": COMPANY,
					"to_shareholder": holder,
					"share_type": "Ordinary",
					"from_no": start,
					"to_no": start + shares - 1,
					"no_of_shares": shares,
					"rate": 100,
					"equity_or_liability_account": equity,
					"asset_account": bank,
				},
				submit=True,
			)
		start += shares


def _peg():
	"""The dirham, held to the dollar since 1997."""
	pegged = frappe.get_single("Pegged Currencies")
	if not any(one.source_currency == "AED" for one in pegged.get("pegged_currency_item") or []):
		pegged.append("pegged_currency_item", {"source_currency": "AED", "pegged_against": "USD", "pegged_exchange_rate": 3.6725})
		pegged.save(ignore_permissions=True)


def _party_link():
	"""Harbour Logistics buys glass and also moves it: one business, a
	customer and a supplier, netted against each other."""
	if not frappe.db.exists("Supplier", "Harbour Logistics"):
		make({"doctype": "Supplier", "supplier_name": "Harbour Logistics", "supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0})})
	once(
		"Party Link",
		{"primary_party": "Harbour Logistics", "secondary_role": "Supplier"},
		{"primary_role": "Customer", "primary_party": "Harbour Logistics", "secondary_role": "Supplier", "secondary_party": "Harbour Logistics"},
	)


def _cheque():
	"""How Emirates NBD's cheques are printed."""
	once("Cheque Print Template", {"name": "Emirates NBD"}, {"bank_name": "Emirates NBD"})


def _revaluation():
	"""What customers abroad owe, valued again at this month's rates."""
	if frappe.db.exists("Exchange Rate Revaluation", {"company": COMPANY}):
		return
	doc = frappe.new_doc("Exchange Rate Revaluation")
	doc.update({"company": COMPANY, "posting_date": today()})
	doc.fetch_and_calculate_accounts_data()
	if doc.get("accounts"):
		doc.insert(ignore_permissions=True)


def _allocation():
	"""From next year the head office's costs are shared between the
	workshop and the showroom, sixty to forty."""
	parent = f"{COMPANY} - {ABBR}"
	for name in ("Workshop", "Showroom"):
		once("Cost Center", {"cost_center_name": name}, {"cost_center_name": name, "parent_cost_center": parent, "company": COMPANY})
	once(
		"Cost Center Allocation",
		{"main_cost_center": f"Main - {ABBR}"},
		{
			"main_cost_center": f"Main - {ABBR}",
			"company": COMPANY,
			"valid_from": get_first_day(add_years(today(), 1).replace(month=1)),
			"allocation_percentages": [
				{"cost_center": f"Workshop - {ABBR}", "percentage": 60},
				{"cost_center": f"Showroom - {ABBR}", "percentage": 40},
			],
		},
	)


def _corrections():
	"""What an accountant keeps to hand, each made but not run: the payment
	ledger rebuilt for a quarter, an invoice posted again, a customer's
	payments matched in the background, deferred income booked, and two
	expense accounts to be merged."""
	with as_user(ACCOUNTS):
		quarter = add_days(today(), -90)
		once("Repost Payment Ledger", {"company": COMPANY}, {"company": COMPANY, "posting_date": quarter})
		invoice = frappe.db.get_value("Sales Invoice", {"company": COMPANY, "docstatus": 1}, "name")
		if invoice:
			once(
				"Repost Accounting Ledger",
				{"company": COMPANY},
				{"company": COMPANY, "vouchers": [{"voucher_type": "Sales Invoice", "voucher_no": invoice}]},
			)
		once(
			"Process Payment Reconciliation",
			{"company": COMPANY},
			{
				"company": COMPANY,
				"party_type": "Customer",
				"party": "Osei Builders",
				"receivable_payable_account": _account(account_type="Receivable", account_currency="AED")
				or _account(account_type="Receivable"),
			},
		)
		once(
			"Process Deferred Accounting",
			{"company": COMPANY},
			{"company": COMPANY, "type": "Income", "start_date": get_first_day(today()), "end_date": today(), "posting_date": today()},
		)
	into = _account(root_type="Expense", account_name="Office Maintenance Expenses")
	merged = _account(root_type="Expense", account_name="Miscellaneous Expenses")
	if into and merged:
		once(
			"Ledger Merge",
			{"company": COMPANY},
			{
				"company": COMPANY,
				"account": into,
				"account_name": frappe.db.get_value("Account", into, "account_name"),
				"root_type": "Expense",
				"merge_accounts": [{"account": merged, "account_name": frappe.db.get_value("Account", merged, "account_name")}],
			},
		)


def _digest():
	"""Monday's mail to the owner and the accountant: last week's income,
	spending, bank balance and what is owed both ways."""
	once(
		"Email Digest",
		{"name": "Weekly Figures"},
		{
			"__newname": "Weekly Figures",
			"enabled": 1,
			"company": COMPANY,
			"frequency": "Weekly",
			**{
				one: 1
				for one in (
					"income",
					"expenses_booked",
					"bank_balance",
					"credit_balance",
					"invoiced_amount",
					"payables",
					"sales_orders_to_bill",
					"purchase_orders_to_bill",
				)
			},
			"recipients": [{"recipient": "wsadmin@one.test"}, {"recipient": ACCOUNTS}],
		},
	)


UNITS = (("H87", "Piece", "Nos"), ("MTR", "Metre", "Meter"), ("KGM", "Kilogram", "Kg"))


def _codes():
	"""The units an electronic invoice names, from the list every e-invoice uses."""
	codes = once(
		"Code List",
		{"name": "UNECE Rec 20"},
		{
			"__newname": "UNECE Rec 20",
			"title": "Codes for Units of Measure Used in International Trade",
			"publisher": "UNECE",
			"version": "17",
		},
	)
	for code, title, unit in UNITS:
		if frappe.db.exists("Common Code", {"code_list": codes.name, "common_code": code}):
			continue
		applies = [{"link_doctype": "UOM", "link_name": unit}] if frappe.db.exists("UOM", unit) else []
		make({"doctype": "Common Code", "code_list": codes.name, "common_code": code, "title": title, "applies_to": applies})
