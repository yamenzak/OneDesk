"""The figures on OneBook's Home: cash, what customers owe and how much of it
is late, what the company owes and what falls due this week, and this month's
profit.
"""

import frappe
from frappe import _lt
from frappe.utils import add_days, flt, get_first_day, getdate, nowdate

WEEK = 7


def _card(amount, route: list, options: dict | None = None) -> dict:
	card = {"value": amount, "fieldtype": "Currency", "route": route}
	if options:
		card["route_options"] = options
	return card


def _company() -> str:
	from erpnext import get_default_company

	return get_default_company()


def _ledger(sql: str, **values) -> float:
	frappe.has_permission("GL Entry", "read", throw=True)
	found = frappe.db.sql(sql, {"company": _company(), **values})
	return flt(found[0][0]) if found else 0.0


@frappe.whitelist()
@frappe.read_only()
def cash(filters: str | None = None) -> dict:
	"""What is in the bank and cash accounts, by the ledger."""
	amount = _ledger(
		"""select sum(entry.debit - entry.credit) from `tabGL Entry` entry
		join `tabAccount` account on account.name = entry.account
		where entry.company = %(company)s and entry.is_cancelled = 0
		and account.account_type in ('Bank', 'Cash')"""
	)
	return _card(amount, ["query-report", "Cash Flow"])


@frappe.whitelist()
@frappe.read_only()
def profit_this_month(filters: str | None = None) -> dict:
	"""Income less expenses since the first of the month. The entries a period
	closing makes are left out, since they move the profit, not make it."""
	amount = _ledger(
		"""select sum(entry.credit - entry.debit) from `tabGL Entry` entry
		join `tabAccount` account on account.name = entry.account
		where entry.company = %(company)s and entry.is_cancelled = 0
		and account.root_type in ('Income', 'Expense')
		and entry.voucher_type != 'Period Closing Voucher'
		and entry.posting_date between %(start)s and %(today)s""",
		start=get_first_day(nowdate()),
		today=nowdate(),
	)
	return _card(amount, ["query-report", "Profit and Loss Statement"])


def _unpaid(doctype: str, fields: list | None = None) -> list:
	"""What each still owes, in the company's currency. ERPNext keeps it in
	the party's, so an invoice in dollars to a party billed in dollars is
	turned at the invoice's own rate."""
	from erpnext import get_company_currency

	company = _company()
	ours = get_company_currency(company)
	rows = frappe.get_list(
		doctype,
		filters={"docstatus": 1, "outstanding_amount": [">", 0], "company": company},
		fields=[
			"name",
			"outstanding_amount",
			"due_date",
			"conversion_rate",
			"party_account_currency",
			*(fields or []),
		],
		limit=0,
	)
	for row in rows:
		row.own = flt(row.outstanding_amount)
		if row.party_account_currency and row.party_account_currency != ours:
			row.outstanding_amount = flt(row.outstanding_amount) * flt(row.conversion_rate or 1)
	return rows


def _schedule(doctype: str, names: list) -> dict:
	"""Each invoice's payment schedule, the earliest part first."""
	found = {}
	if not names:
		return found
	for row in frappe.get_all(
		"Payment Schedule",
		filters={"parenttype": doctype, "parent": ["in", names]},
		fields=["parent", "due_date", "payment_amount"],
		order_by="due_date asc, idx asc",
	):
		found.setdefault(row.parent, []).append(row)
	return found


def parts(row: dict, schedule: list) -> list[dict]:
	"""What an invoice still owes, part by part as its payment schedule falls
	due. What was paid settles the earliest parts first, as ERPNext's Overdue
	status counts it, so a retention held for a year does not hide a part
	long late. The parts add up to what it owes, in the company's currency.
	Pure over the invoice's outstanding_amount (and `own`, the same in its
	own currency) and due_date, and its schedule's payment_amount and
	due_date."""
	owed = flt(row.get("outstanding_amount"))
	own = flt(row.get("own", owed))
	paid = sum(flt(one.get("payment_amount")) for one in schedule or []) - own
	left = []
	for one in schedule or []:
		part = flt(one.get("payment_amount"))
		settled = min(part, max(paid, 0))
		paid -= settled
		if part - settled > 0:
			left.append((one.get("due_date"), part - settled))
	total = sum(amount for _, amount in left)
	if not total:
		return [{"outstanding_amount": owed, "due_date": row.get("due_date")}]
	return [{"outstanding_amount": owed * amount / total, "due_date": day} for day, amount in left]


def _due(doctype: str, fields: list | None = None) -> list:
	"""What is still owed on each invoice, part by part (`parts`), each part
	carrying the invoice's own fields."""
	rows = _unpaid(doctype, fields)
	schedule = _schedule(doctype, [row.name for row in rows])
	return [{**row, **part} for row in rows for part in parts(row, schedule.get(row.name))]


def yesterday():
	return add_days(nowdate(), -1)


def this_week():
	return add_days(nowdate(), WEEK - 1)


def outstanding(rows: list, until=None) -> float:
	"""What the rows still owe; only what falls due by `until` when given.
	Pure over rows of outstanding_amount and due_date."""
	return sum(
		flt(row.get("outstanding_amount"))
		for row in rows
		if until is None or (row.get("due_date") and getdate(row.get("due_date")) <= getdate(until))
	)


@frappe.whitelist()
@frappe.read_only()
def owed_to_us(filters: str | None = None) -> dict:
	"""What customers still owe on invoices."""
	return _card(outstanding(_unpaid("Sales Invoice")), ["query-report", "Accounts Receivable"], {"based_on_payment_terms": 1})


@frappe.whitelist()
@frappe.read_only()
def overdue(filters: str | None = None) -> dict:
	"""What customers owe on invoices past their due date."""
	amount = outstanding(_due("Sales Invoice"), until=yesterday())
	return _card(amount, ["List", "Sales Invoice"], {"status": "Overdue"})


@frappe.whitelist()
@frappe.read_only()
def we_owe(filters: str | None = None) -> dict:
	"""What the company still owes on bills."""
	return _card(outstanding(_unpaid("Purchase Invoice")), ["query-report", "Accounts Payable"], {"party_type": "Supplier"})


@frappe.whitelist()
@frappe.read_only()
def due_this_week(filters: str | None = None) -> dict:
	"""What falls due on bills in the next seven days, and any already late."""
	amount = outstanding(_due("Purchase Invoice"), until=this_week())
	return _card(amount, ["List", "Purchase Invoice"], DUE_THIS_WEEK())


def DUE_THIS_WEEK() -> dict:
	"""The bills behind Due This Week: unpaid, and due by the week's end."""
	return {"docstatus": 1, "outstanding_amount": [">", 0], "due_date": ["<=", this_week()]}


FEW = 5

GROUPS = (
	("receivables", _lt("Receivables")),
	("payables", _lt("Payables")),
	("payments", _lt("Payments")),
	("banking", _lt("Banking")),
	("reports", _lt("Reports")),
	("setup", _lt("Setup")),
)
REPORT_SECTIONS = (
	("statements", _lt("Financial Reports")),
	("ledgers", _lt("Ledgers")),
	("registers", _lt("Registers")),
	("profit", _lt("Profitability")),
	("tax", _lt("Taxes")),
)
REPORT_TOPICS = {
	"Consolidated Trial Balance": "statements",
	"Trial Balance (Simple)": "statements",
	"Custom Financial Statement": "statements",
	"Deferred Revenue and Expense": "statements",
	"Dimension-wise Accounts Balance Report": "ledgers",
	"Voucher-wise Balance": "ledgers",
	"Payment Ledger": "ledgers",
	"Share Balance": "ledgers",
	"Share Ledger": "ledgers",
	"Gross and Net Profit Report": "profit",
	"VAT Audit Report": "tax",
	"Profit and Loss Statement": "statements",
	"Balance Sheet": "statements",
	"Cash Flow": "statements",
	"Trial Balance": "statements",
	"Consolidated Financial Statement": "statements",
	"Budget Variance Report": "statements",
	"General Ledger": "ledgers",
	"Customer Ledger Summary": "ledgers",
	"Supplier Ledger Summary": "ledgers",
	"Trial Balance for Party": "ledgers",
	"Bank Reconciliation Statement": "ledgers",
	"Accounts Receivable": "registers",
	"Accounts Receivable Summary": "registers",
	"Accounts Payable": "registers",
	"Accounts Payable Summary": "registers",
	"Sales Register": "registers",
	"Purchase Register": "registers",
	"Item-wise Sales Register": "registers",
	"Item-wise Purchase Register": "registers",
	"Payment Period Based On Invoice Date": "registers",
	"Customer Credit Balance": "registers",
	"Gross Profit": "profit",
	"Profitability Analysis": "profit",
	"Sales Invoice Trends": "profit",
	"Purchase Invoice Trends": "profit",
	"Tax Return": "tax",
	"UAE VAT 201": "tax",
	"Tax Withholding Details": "tax",
}
SETUP_SECTIONS = (
	("settings", _lt("Settings")),
	("accounts", _lt("Accounts")),
	("tax", _lt("Taxes")),
	("payments", _lt("Payments")),
	("currency", _lt("Currencies")),
	("shares", _lt("Shares")),
	("corrections", _lt("Corrections")),
)
SETUP_TOPICS = {
	"Accounting Dimension": "accounts",
	"Accounting Dimension Filter": "accounts",
	"Accounting Period": "accounts",
	"Cost Center Allocation": "accounts",
	"Party Link": "accounts",
	"Chart of Accounts Importer": "accounts",
	"Financial Report Template": "accounts",
	"Process Deferred Accounting": "accounts",
	"Lower Deduction Certificate": "tax",
	"South Africa VAT Settings": "tax",
	"Cheque Print Template": "payments",
	"Plaid Settings": "payments",
	"Email Digest": "settings",
	"Code List": "tax",
	"Common Code": "tax",
	"Subscription Settings": "payments",
	"Currency Exchange": "currency",
	"Currency Exchange Settings": "currency",
	"Pegged Currencies": "currency",
	"Exchange Rate Revaluation": "currency",
	"Shareholder": "shares",
	"Share Type": "shares",
	"Share Transfer": "shares",
	"Repost Accounting Ledger": "corrections",
	"Repost Payment Ledger": "corrections",
	"Ledger Merge": "corrections",
	"Ledger Health Monitor": "corrections",
	"Invalid Ledger Entries": "corrections",
	"General and Payment Ledger Comparison": "corrections",
	"Books Check": "settings",
	"Accounts Settings": "settings",
	"UAE VAT Settings": "settings",
	"Account": "accounts",
	"Cost Center": "accounts",
	"Fiscal Year": "accounts",
	"Finance Book": "accounts",
	"Period Closing Voucher": "accounts",
	"Opening Invoice Creation Tool": "accounts",
	"Sales Taxes and Charges Template": "tax",
	"Purchase Taxes and Charges Template": "tax",
	"Item Tax Template": "tax",
	"Tax Rule": "tax",
	"Tax Category": "tax",
	"Tax Withholding Category": "tax",
	"Payment Terms Template": "payments",
	"Payment Term": "payments",
	"Mode of Payment": "payments",
	"Bank Transaction Rule": "payments",
}

EVERYTHING = (
	("receivables", _lt("Sales Invoice"), "DocType", "Sales Invoice", _lt("What you have billed customers."), {"is_return": 0}),
	("receivables", _lt("Credit Note"), "DocType", "Sales Invoice", _lt("Money given back to a customer, against an invoice."), {"is_return": 1}),
	("receivables", _lt("Customer"), "DocType", "Customer", _lt("Who you sell to, and what each owes.")),
	("receivables", _lt("Dunning"), "DocType", "Dunning", _lt("A reminder to a customer who is late paying, with any fee.")),
	("receivables", _lt("Process Statement Of Accounts"), "DocType", "Process Statement Of Accounts", _lt("Each customer's statement, mailed on a schedule.")),
	("receivables", _lt("Auto Repeat"), "DocType", "Auto Repeat", _lt("Invoices and bills made again every month, quarter or year."), {"reference_doctype": ["in", ["Sales Invoice", "Purchase Invoice"]]}),
	("payables", _lt("Purchase Invoice"), "DocType", "Purchase Invoice", _lt("What suppliers have billed you."), {"is_return": 0}),
	("payables", _lt("Debit Note"), "DocType", "Purchase Invoice", _lt("Money a supplier gives back, against their invoice."), {"is_return": 1}),
	("payables", _lt("Supplier"), "DocType", "Supplier", _lt("Who you buy from, and what you owe each.")),
	("payables", _lt("Ready to Submit"), "Report", "Ready to Submit", _lt("Drafts OneAI read from mail and scans, bills most of all, waiting to be submitted.")),
	("payables", _lt("Import Supplier Invoice"), "DocType", "Import Supplier Invoice", _lt("Suppliers' electronic invoices read in from a zip file.")),
	("payments", _lt("Payment Entry"), "DocType", "Payment Entry", _lt("Money received from customers and paid to suppliers.")),
	("payments", _lt("Journal Entry"), "DocType", "Journal Entry", _lt("Anything that is not an invoice or a payment: corrections, accruals, opening balances.")),
	("payments", _lt("Payment Request"), "DocType", "Payment Request", _lt("A link sent to a customer to pay online.")),
	("payments", _lt("Payment Reconciliation"), "DocType", "Payment Reconciliation", _lt("Payments matched to the invoices they settle.")),
	("payments", _lt("Process Payment Reconciliation"), "DocType", "Process Payment Reconciliation", _lt("Payments matched to invoices for many parties at once.")),
	("banking", _lt("Bank Reconciliation Tool"), "DocType", "Bank Reconciliation Tool", _lt("Your bank statement matched to what is in the books.")),
	("banking", _lt("Bank Transaction"), "DocType", "Bank Transaction", _lt("Each line of the bank statement.")),
	("banking", _lt("Bank Statement Import"), "DocType", "Bank Statement Import", _lt("A bank statement read in from a file.")),
	("banking", _lt("Bank Account"), "DocType", "Bank Account", _lt("The company's bank accounts.")),
	("banking", _lt("Bank Clearance"), "DocType", "Bank Clearance", _lt("The dates payments cleared the bank, set in one go.")),
	("reports", _lt("Profit and Loss"), "Report", "Profit and Loss Statement", _lt("Income less expenses, month by month or year by year.")),
	("reports", _lt("Balance Sheet"), "Report", "Balance Sheet", _lt("What the company owns and owes on a day.")),
	("reports", _lt("Cash Flow"), "Report", "Cash Flow", _lt("Where the cash came from and went.")),
	("reports", _lt("Trial Balance"), "Report", "Trial Balance", _lt("Every account's balance, debits against credits.")),
	("reports", _lt("Consolidated Financial Statement"), "Report", "Consolidated Financial Statement", _lt("The statements of several companies as one.")),
	("reports", _lt("Budget Variance Report"), "Report", "Budget Variance Report", _lt("What was spent against the budget.")),
	("reports", _lt("General Ledger"), "Report", "General Ledger", _lt("Every entry in the books, one line each.")),
	("reports", _lt("Customer Ledger Summary"), "Report", "Customer Ledger Summary", _lt("Each customer's invoices, payments and balance.")),
	("reports", _lt("Supplier Ledger Summary"), "Report", "Supplier Ledger Summary", _lt("Each supplier's bills, payments and balance.")),
	("reports", _lt("Trial Balance for Party"), "Report", "Trial Balance for Party", _lt("Each customer's or supplier's opening, movement and closing.")),
	("reports", _lt("Bank Reconciliation Statement"), "Report", "Bank Reconciliation Statement", _lt("The books' bank balance against the statement's.")),
	("reports", _lt("Accounts Receivable"), "Report", "Accounts Receivable", _lt("Who owes you, and how late."), {"based_on_payment_terms": 1}),
	("reports", _lt("Accounts Receivable Summary"), "Report", "Accounts Receivable Summary", _lt("What each customer owes, by how late."), {"based_on_payment_terms": 1}),
	("reports", _lt("Accounts Payable"), "Report", "Accounts Payable", _lt("Whom you owe, and when it falls due."), {"party_type": "Supplier"}),
	("reports", _lt("Accounts Payable Summary"), "Report", "Accounts Payable Summary", _lt("What you owe each supplier, by how late."), {"party_type": "Supplier"}),
	("reports", _lt("Sales Register"), "Report", "Sales Register", _lt("Every sales invoice with its taxes, one line each.")),
	("reports", _lt("Purchase Register"), "Report", "Purchase Register", _lt("Every purchase invoice with its taxes, one line each.")),
	("reports", _lt("Item-wise Sales Register"), "Report", "Item-wise Sales Register", _lt("Every line of every sales invoice.")),
	("reports", _lt("Item-wise Purchase Register"), "Report", "Item-wise Purchase Register", _lt("Every line of every purchase invoice.")),
	("reports", _lt("Payment Period Based On Invoice Date"), "Report", "Payment Period Based On Invoice Date", _lt("How long each invoice took to be paid.")),
	("reports", _lt("Customer Credit Balance"), "Report", "Customer Credit Balance", _lt("Each customer's credit limit, and what is left of it.")),
	("reports", _lt("Gross Profit"), "Report", "Gross Profit", _lt("What each sale made over what it cost.")),
	("reports", _lt("Profitability Analysis"), "Report", "Profitability Analysis", _lt("Income and expenses by cost center or project.")),
	("reports", _lt("Sales Invoice Trends"), "Report", "Sales Invoice Trends", _lt("What was invoiced, period against period.")),
	("reports", _lt("Purchase Invoice Trends"), "Report", "Purchase Invoice Trends", _lt("What was billed, period against period.")),
	("reports", _lt("Tax Return"), "Report", "Tax Return", _lt("The tax owed for a period, ready for the tax office.")),
	("reports", _lt("UAE VAT 201"), "Report", "UAE VAT 201", _lt("The UAE's VAT return, box by box.")),
	("reports", _lt("Tax Withholding Details"), "Report", "Tax Withholding Details", _lt("Tax withheld from suppliers, payment by payment.")),
	("reports", _lt("Consolidated Trial Balance"), "Report", "Consolidated Trial Balance", _lt("The trial balances of several companies as one.")),
	("reports", _lt("Trial Balance (Simple)"), "Report", "Trial Balance (Simple)", _lt("Each account's debits and credits, day by day.")),
	("reports", _lt("Custom Financial Statement"), "Report", "Custom Financial Statement", _lt("A statement laid out by a financial report template.")),
	("reports", _lt("Deferred Revenue and Expense"), "Report", "Deferred Revenue and Expense", _lt("Income and costs spread over the months they belong to.")),
	("reports", _lt("Dimension-wise Accounts Balance Report"), "Report", "Dimension-wise Accounts Balance Report", _lt("Each account's balance by accounting dimension.")),
	("reports", _lt("Voucher-wise Balance"), "Report", "Voucher-wise Balance", _lt("Vouchers whose debits and credits do not agree.")),
	("reports", _lt("Payment Ledger"), "Report", "Payment Ledger", _lt("Every payment and what it settled.")),
	("reports", _lt("Share Balance"), "Report", "Share Balance", _lt("Each shareholder's shares on a day.")),
	("reports", _lt("Share Ledger"), "Report", "Share Ledger", _lt("Every share issued, moved and bought back.")),
	("reports", _lt("Gross and Net Profit Report"), "Report", "Gross and Net Profit Report", _lt("Gross and net profit, period by period.")),
	("reports", _lt("VAT Audit Report"), "Report", "VAT Audit Report", _lt("Every taxed invoice, for a VAT audit.")),
	("setup", _lt("Books Check"), "Report", "Books Check", _lt("What is not set up yet, with the fix.")),
	("setup", _lt("Accounts Settings"), "DocType", "Accounts Settings", _lt("How invoices, payments and the books work.")),
	("setup", _lt("Email Digest"), "DocType", "Email Digest", _lt("A mail each day, week or month of how the business is doing.")),
	("setup", _lt("UAE VAT Settings"), "DocType", "UAE VAT Settings", _lt("The accounts the UAE VAT 201 reads.")),
	("setup", _lt("Chart of Accounts"), "DocType", "Account", _lt("The accounts the books are kept in.")),
	("setup", _lt("Cost Center"), "DocType", "Cost Center", _lt("The parts of the business costs and income are kept by.")),
	("setup", _lt("Fiscal Year"), "DocType", "Fiscal Year", _lt("The years the books are kept and closed in.")),
	("setup", _lt("Finance Book"), "List", "Finance Book", _lt("A second set of books, such as for tax depreciation.")),
	("setup", _lt("Period Closing Voucher"), "DocType", "Period Closing Voucher", _lt("A year closed, its profit carried into equity.")),
	("setup", _lt("Opening Invoice Creation Tool"), "DocType", "Opening Invoice Creation Tool", _lt("What customers and suppliers owed when you started.")),
	("setup", _lt("Sales Taxes and Charges Template"), "DocType", "Sales Taxes and Charges Template", _lt("The taxes a sale carries.")),
	("setup", _lt("Purchase Taxes and Charges Template"), "DocType", "Purchase Taxes and Charges Template", _lt("The taxes a purchase carries.")),
	("setup", _lt("Item Tax Template"), "DocType", "Item Tax Template", _lt("A rate for items taxed differently.")),
	("setup", _lt("Tax Rule"), "DocType", "Tax Rule", _lt("Which tax template a sale or purchase takes, by party and place.")),
	("setup", _lt("Tax Category"), "List", "Tax Category", _lt("Groups of customers and suppliers taxed alike.")),
	("setup", _lt("Code List"), "DocType", "Code List", _lt("A published list of codes an electronic invoice uses, such as units.")),
	("setup", _lt("Common Code"), "DocType", "Common Code", _lt("One code of a code list, and what it stands for here.")),
	("setup", _lt("Tax Withholding Category"), "DocType", "Tax Withholding Category", _lt("Tax held back from what is paid to suppliers.")),
	("setup", _lt("Payment Terms Template"), "DocType", "Payment Terms Template", _lt("When an invoice falls due, in one part or several.")),
	("setup", _lt("Payment Term"), "DocType", "Payment Term", _lt("One part of a payment terms template.")),
	("setup", _lt("Mode of Payment"), "DocType", "Mode of Payment", _lt("Cash, card, transfer, and the account each goes to.")),
	("setup", _lt("Bank Transaction Rule"), "DocType", "Bank Transaction Rule", _lt("How a bank line is matched without asking.")),
	("setup", _lt("Plaid Settings"), "DocType", "Plaid Settings", _lt("Bank transactions brought in from Plaid, where Plaid reaches your bank.")),
	("setup", _lt("Accounting Dimension"), "DocType", "Accounting Dimension", _lt("A way to split the books beyond cost centers, such as by branch.")),
	("setup", _lt("Accounting Dimension Filter"), "DocType", "Accounting Dimension Filter", _lt("Which values of a dimension an account may take.")),
	("setup", _lt("Accounting Period"), "DocType", "Accounting Period", _lt("A period closed to new entries.")),
	("setup", _lt("Cost Center Allocation"), "DocType", "Cost Center Allocation", _lt("One cost center's costs shared among others.")),
	("setup", _lt("Party Link"), "DocType", "Party Link", _lt("A customer and a supplier that are the same business.")),
	("setup", _lt("Chart of Accounts Importer"), "DocType", "Chart of Accounts Importer", _lt("Your chart of accounts read in from a spreadsheet.")),
	("setup", _lt("Financial Report Template"), "DocType", "Financial Report Template", _lt("The rows and formulas of a custom financial statement.")),
	("setup", _lt("Process Deferred Accounting"), "DocType", "Process Deferred Accounting", _lt("Deferred income and costs booked for a period.")),
	("setup", _lt("Lower Deduction Certificate"), "DocType", "Lower Deduction Certificate", _lt("A supplier's certificate for tax withheld at a lower rate.")),
	("setup", _lt("South Africa VAT Settings"), "DocType", "South Africa VAT Settings", _lt("The accounts South Africa's VAT reports read.")),
	("setup", _lt("Cheque Print Template"), "DocType", "Cheque Print Template", _lt("How a cheque is printed for each bank.")),
	("setup", _lt("Subscription Settings"), "DocType", "Subscription Settings", _lt("How subscriptions are billed and cancelled.")),
	("setup", _lt("Currency Exchange"), "DocType", "Currency Exchange", _lt("The rate between two currencies on a day.")),
	("setup", _lt("Currency Exchange Settings"), "DocType", "Currency Exchange Settings", _lt("Where exchange rates are fetched from.")),
	("setup", _lt("Pegged Currencies"), "DocType", "Pegged Currencies", _lt("Currencies fixed to another at a set rate.")),
	("setup", _lt("Exchange Rate Revaluation"), "DocType", "Exchange Rate Revaluation", _lt("Foreign currency balances valued again at today's rate.")),
	("setup", _lt("Shareholder"), "DocType", "Shareholder", _lt("Who owns shares in the company.")),
	("setup", _lt("Share Type"), "DocType", "Share Type", _lt("A class of shares.")),
	("setup", _lt("Share Transfer"), "DocType", "Share Transfer", _lt("Shares issued, moved or bought back.")),
	("setup", _lt("Repost Accounting Ledger"), "DocType", "Repost Accounting Ledger", _lt("Chosen transactions posted to the books again.")),
	("setup", _lt("Repost Payment Ledger"), "DocType", "Repost Payment Ledger", _lt("The payment ledger rebuilt, so what is owed is right again.")),
	("setup", _lt("Ledger Merge"), "DocType", "Ledger Merge", _lt("Two or more accounts combined into one.")),
	("setup", _lt("Ledger Health Monitor"), "DocType", "Ledger Health Monitor", _lt("Checks the books for entries that don't add up.")),
	("setup", _lt("Invalid Ledger Entries"), "Report", "Invalid Ledger Entries", _lt("Entries that don't match their documents.")),
	("setup", _lt("General and Payment Ledger Comparison"), "Report", "General and Payment Ledger Comparison", _lt("Where the general and payment ledgers disagree.")),
)

@frappe.whitelist()
def read() -> dict:
	"""What needs somebody, and the directory, as the reader may see them."""
	return {
		"needs": needs_you(),
		"groups": [{"key": key, "label": str(label)} for key, label in GROUPS],
		"sections": {
			"reports": [{"key": key, "label": str(label)} for key, label in REPORT_SECTIONS],
			"setup": [{"key": key, "label": str(label)} for key, label in SETUP_SECTIONS],
		},
		"everything": directory(),
	}


def _kept(rows: list) -> dict:
	return {"rows": rows[:FEW], "count": len(rows)}


def needs_you() -> dict:
	"""Invoices overdue, bills due this week or late, bank lines to match and
	drafts left more than a day, each as the reader may see them."""
	day = getdate(nowdate())
	return {
		"overdue": _kept(_late("Sales Invoice", "customer", yesterday(), day)),
		"bills": {**_kept(_late("Purchase Invoice", "supplier", this_week(), day)), "until": str(this_week())},
		"bank": _bank(),
		"drafts": drafts(),
	}


def _late(doctype: str, party: str, until, day) -> list[dict]:
	"""What has a part still owed falling due by `until`, the latest first:
	ERPNext's Overdue, read from the payment schedule as its status is."""
	if not frappe.has_permission(doctype, "read"):
		return []
	rows = frappe.get_list(
		doctype,
		filters={"docstatus": 1, "outstanding_amount": [">", 0], "company": _company()},
		fields=["name", party, f"{party}_name as party_name", "due_date", "outstanding_amount", "currency"],
		limit_page_length=0,
	)
	schedule = _schedule(doctype, [one.name for one in rows])
	out = []
	for one in rows:
		first = min(getdate(part["due_date"]) for part in parts(one, schedule.get(one.name)) if part["due_date"])
		if first > getdate(until):
			continue
		out.append(
			{
				"name": one.name,
				"party": one.party_name or one.get(party),
				"due_date": str(first),
				"late": (day - first).days,
				"outstanding": flt(one.outstanding_amount),
				"currency": one.currency,
			}
		)
	return sorted(out, key=lambda one: one["due_date"])


def _bank() -> dict:
	"""Bank lines not yet matched, by bank account."""
	if not frappe.has_permission("Bank Transaction", "read"):
		return {"rows": [], "count": 0}
	rows = frappe.get_list(
		"Bank Transaction",
		filters={"docstatus": 1, "status": "Unreconciled", "company": _company()},
		fields=["bank_account", {"COUNT": "*", "as": "lines"}, {"SUM": "unallocated_amount", "as": "amount"}],
		group_by="bank_account",
		limit_page_length=0,
	)
	return {
		"rows": [{"bank_account": one.bank_account, "lines": one.lines, "amount": flt(one.amount)} for one in rows],
		"count": sum(one.lines for one in rows),
	}


DRAFTS = (
	("Sales Invoice", _lt("Sales Invoice")),
	("Purchase Invoice", _lt("Purchase Invoice")),
	("Payment Entry", _lt("Payment Entry")),
	("Journal Entry", _lt("Journal Entry")),
)


def drafts() -> list[dict]:
	"""For each kind of paper, how many drafts were left more than a day ago."""
	out = []
	for doctype, label in DRAFTS:
		if not frappe.has_permission(doctype, "read"):
			continue
		count = len(
			frappe.get_list(
				doctype,
				filters={"docstatus": 0, "modified": ["<", add_days(nowdate(), -1)]},
				pluck="name",
			)
		)
		if count:
			out.append({"doctype": doctype, "label": str(label), "count": count})
	return out


def _may(kind: str, target: str) -> bool:
	if kind in ("DocType", "List"):
		return bool(frappe.has_permission(target, "read"))
	if not frappe.db.exists(kind, target):
		return False
	doc = frappe.get_cached_doc(kind, target)
	if kind == "Report":
		if doc.disabled or (doc.ref_doctype and not frappe.has_permission(doc.ref_doctype, "read")):
			return False
	return bool(doc.is_permitted())


def _companies() -> bool:
	return frappe.db.count("Company") > 1


def _template() -> str | None:
	"""The financial report template a Custom Financial Statement opens on:
	one made for it, or else the first there is."""
	for filters in ({"report_type": "Custom Financial Statement", "disabled": 0}, {"disabled": 0}):
		if name := frappe.db.get_value("Financial Report Template", filters, "name", order_by="name asc"):
			return name
	return None


#: Reports that can show nothing until the workspace has what they read, and
#: are left out until then: several companies, a withholding category, an
#: account counted in gross profit, an item billed over months, a credit limit.
WHEN = {
	"Consolidated Financial Statement": _companies,
	"Consolidated Trial Balance": _companies,
	"Tax Withholding Details": lambda: bool(frappe.db.exists("Tax Withholding Category")),
	"Gross and Net Profit Report": lambda: bool(frappe.db.exists("Account", {"include_in_gross": 1})),
	"Deferred Revenue and Expense": lambda: bool(
		frappe.db.exists("Item", {"enable_deferred_revenue": 1}) or frappe.db.exists("Item", {"enable_deferred_expense": 1})
	),
	"Customer Credit Balance": lambda: bool(frappe.db.exists("Customer Credit Limit")),
	"Custom Financial Statement": lambda: bool(_template()),
}

#: Filters worked out when Home is read, for a report that needs one to show anything.
OPENS_WITH = {
	"Custom Financial Statement": lambda: {"report_template": _template()},
}


def directory() -> list[dict]:
	"""Everything in OneBook the reader may open, with what it is for: a
	country's own only where a company is in it (one/countries.py), and a
	report only once there is something for it to show (WHEN)."""
	from onedesk.one import countries

	here = countries.ours()
	return [
		{
			"group": group,
			"label": str(label),
			"kind": kind,
			"target": target,
			"filters": OPENS_WITH[target]() if target in OPENS_WITH else (filters[0] if filters else None),
			"about": str(about),
			"topic": {"reports": REPORT_TOPICS, "setup": SETUP_TOPICS}.get(group, {}).get(target),
		}
		for group, label, kind, target, about, *filters in EVERYTHING
		if _may(kind, target) and countries.shown(target, here) and (kind != "Report" or target not in WHEN or WHEN[target]())
	]
