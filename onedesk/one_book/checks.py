"""OneBook's part of the integration suite (one_demo/check.py runs it):
Home's figures, invoices and payments, the bank, tax, closing and other
currencies, as their people read them, and the two abilities."""

import frappe
from frappe.utils import add_days, date_diff, flt, getdate, today

from onedesk.one import story as stories
from onedesk.one.company import company_currency, reader_company
from onedesk.one_demo.base import COMPANY, as_user, on
from onedesk.one_demo.checking import CENTS, _close, _each_way, _refused, check
from onedesk.one_demo.people import OWNER


@check
def the_books_balance():
	off = frappe.db.sql(
		"""select voucher_type, voucher_no, sum(debit) - sum(credit) from `tabGL Entry`
		where is_cancelled = 0 and company = %s group by voucher_type, voucher_no
		having abs(sum(debit) - sum(credit)) > 0.01""",
		COMPANY,
	)
	assert not off, off[:5]


@check
def every_party_is_billed_in_its_own_currency():
	from erpnext.accounts.party import get_party_account_currency

	wrong = []
	for doctype, party_type, party in (("Sales Invoice", "Customer", "customer"), ("Purchase Invoice", "Supplier", "supplier")):
		for doc in frappe.get_all(doctype, filters={"docstatus": 1}, fields=["name", party, "company", "currency", "conversion_rate", "grand_total", "base_grand_total"]):
			if doc.currency != get_party_account_currency(party_type, doc[party], doc.company):
				wrong.append((doc.name, doc.currency))
			if not _close(doc.grand_total * doc.conversion_rate, doc.base_grand_total, 1):
				wrong.append((doc.name, "base"))
	assert not wrong, wrong


@check
def three_currencies_besides_the_companys():
	used = set(frappe.get_all("Sales Invoice", filters={"docstatus": 1}, pluck="currency")) | set(
		frappe.get_all("Purchase Invoice", filters={"docstatus": 1}, pluck="currency")
	)
	assert {"AED", "USD", "EUR", "GBP"} <= used, used


@check
def the_books_home_tells_the_truth():
	"""What is owed to us on the books' home is what the invoices still have
	outstanding, less credit notes not yet set against one."""
	from onedesk.one_book import home as books

	with as_user("huda@one.test"):
		said = books.owed_to_us()
	found = frappe.db.sql(
		"""select sum(outstanding_amount * conversion_rate) from `tabSales Invoice`
		where docstatus = 1 and company = %s and outstanding_amount != 0""",
		COMPANY,
	)[0][0]
	assert _close(said["value"], found, 2), (said["value"], found)


@check
def the_assets_depreciate():
	booked = frappe.db.count("Journal Entry", {"voucher_type": "Depreciation Entry", "docstatus": 1})
	assert booked, "no depreciation booked this year"


@check
def the_books_lock_up_to_today_at_most():
	from onedesk.one_demo.base import ahead

	_refused(_each_way("huda@one.test", "Company", COMPANY, {"accounts_frozen_till_date": str(ahead(30))}), "up to today")


def _abroad(party_type: str, party: str) -> bool:
	"""Whether a customer is billed abroad, or a supplier sells from abroad."""
	from onedesk.one_demo.masters import ABROAD, EXPORTS

	if party_type == "Supplier":
		return party in ABROAD
	from erpnext.accounts.party import get_default_address

	address = get_default_address(party_type, party)
	return bool(address) and frappe.db.get_value("Address", address, "country") in EXPORTS


@check
def onebook_home_and_payments_for_the_accounts_team():
	"""What Huda's home says, every figure, a payment taken against an invoice
	in one step, the books locked and unlocked, and a readiness fix."""
	from onedesk.one_book import closing, home, paid, ready, tell

	with as_user("huda@one.test"):
		said = {
			"cash": home.cash(),
			"owed to us": home.owed_to_us(),
			"overdue": home.overdue(),
			"we owe": home.we_owe(),
			"due this week": home.due_this_week(),
			"profit this month": home.profit_this_month(),
		}
		assert all(one is not None for one in said.values()), said
		invoice = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "outstanding_amount": [">", 0], "currency": "AED", "company": COMPANY}, fields=["name", "outstanding_amount"], limit=1)[0]
		bank = frappe.get_all("Account", filters={"account_type": "Bank", "is_group": 0, "company": COMPANY}, pluck="name", limit=1)[0]
		paid.settle("Sales Invoice", invoice.name, invoice.outstanding_amount, bank, reference="CHK-001", on=today())
		assert not frappe.db.get_value("Sales Invoice", invoice.name, "outstanding_amount")
	with as_user(OWNER):
		closing.lock(str(on(1, 31)))
		assert str(frappe.db.get_value("Company", COMPANY, "accounts_frozen_till_date")) == str(on(1, 31))
		closing.lock(None)
		ready.fix("bills")
		assert frappe.db.get_single_value("Accounts Settings", "check_supplier_invoice_uniqueness")
	with as_user("omar@one.test"):
		customer = frappe.get_all("Customer", pluck="name", limit=1)[0]
		tell.credit_limit(customer, COMPANY)


@check
def onebook_keeps_the_books_rules():
	"""A bank mode of payment added later is wired by saving the company's
	bank account. Only an invoice or a bill is paid in one step. A bill made
	again drops last month's supplier number and its schedule. The books lock
	only up to today, by the closers alone, however the date is set. A year
	ended with entries is closed into Retained Earnings and locked, and the
	check turns the payment reminder on."""
	from onedesk.one_book import closing, paid, ready

	company = frappe.get_doc("Company", COMPANY)
	with as_user(OWNER):
		frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": "Demo Transfer", "type": "Bank", "enabled": 1}).insert()
		frappe.get_doc("Bank Account", {"is_company_account": 1, "is_default": 1, "company": COMPANY}).save()
		assert [one.default_account for one in frappe.get_doc("Mode of Payment", "Demo Transfer").accounts] == [company.default_bank_account or frappe.db.get_value("Bank Account", {"is_default": 1, "company": COMPANY}, "account")]
	with as_user("huda@one.test"):
		order = frappe.get_all("Sales Order", filters={"docstatus": 1}, pluck="name", limit=1)[0]
		try:
			paid.settle("Sales Order", order, 10, frappe.db.get_value("Bank Account", {"is_default": 1}, "account"))
			raise AssertionError("an order was paid as if it were an invoice")
		except frappe.ValidationError:
			pass
		bill = frappe.get_all("Purchase Invoice", filters={"docstatus": 1, "bill_no": ["is", "set"], "auto_repeat": ["is", "not set"]}, fields=["name", "bill_no"], limit=1)[0]
		repeat = frappe.get_doc({"doctype": "Auto Repeat", "reference_doctype": "Purchase Invoice", "reference_document": bill.name, "frequency": "Monthly", "start_date": today()}).insert()
		copy = repeat.make_new_document()
		assert not copy.bill_no and copy.name != bill.name, "last month's supplier number would be refused"
		assert getdate(copy.due_date) >= getdate(today()) and all(getdate(row.due_date) >= getdate(today()) for row in copy.payment_schedule), "last month's schedule"
	with as_user("rania@one.test"):
		for step in (lambda: closing.lock(today()), lambda: ready.fix("bills")):
			try:
				step()
				raise AssertionError("somebody outside the books closed or fixed them")
			except frappe.PermissionError:
				pass
	with as_user(OWNER):
		try:
			closing.lock(str(add_days(today(), 1)))
			raise AssertionError("the books were locked into the future")
		except frappe.ValidationError:
			pass
		company.reload()
		company.accounts_frozen_till_date = add_days(today(), 1)
		try:
			company.save()
			raise AssertionError("the Company form locked the books into the future")
		except frappe.ValidationError:
			pass
		income = company.default_income_account
		cash = frappe.db.get_value("Account", {"account_type": "Cash", "is_group": 0, "company": COMPANY})
		with as_user("Administrator"):
			for period in frappe.get_all("Accounting Period", filters={"company": COMPANY, "start_date": "2025-01-01"}, pluck="name"):
				frappe.delete_doc("Accounting Period", period, ignore_permissions=True, force=True)
		earned = frappe.get_doc({
			"doctype": "Journal Entry", "company": COMPANY, "posting_date": "2025-06-30", "user_remark": "Last year's sale",
			"accounts": [
				{"account": cash, "debit_in_account_currency": 500, "cost_center": company.cost_center},
				{"account": income, "credit_in_account_currency": 500, "cost_center": company.cost_center},
			],
		}).insert()
		earned.submit()
		assert [one.name for one in closing.unclosed(COMPANY)] == ["2025"]
		ready.fix("close")
		voucher = frappe.get_doc("Period Closing Voucher", {"fiscal_year": "2025", "company": COMPANY, "docstatus": 1})
		assert voucher.closing_account_head == closing.retained_earnings(COMPANY)
		assert str(closing.locked(COMPANY)) == "2025-12-31" and not closing.unclosed(COMPANY)
		ready.fix("reminder")
		assert frappe.db.get_value("Notification", "Payment Reminder", "enabled")


@check
def onebook_home_tells_how_the_money_is_doing():
	"""Huda's Home: its figures agree with the ledger and with what is owed,
	the ageing adds up to Accounts Receivable, Today lists every overdue sales
	invoice, and every row of the directory opens something that exists. An
	overdue invoice's head is red with its Paid step late; a paid one is
	green with every step done."""
	from onedesk.one import head
	from onedesk.one_book import home, story

	with as_user("huda@one.test"):
		told = story.read()
		said = home.read()
		cards = told["cards"]
		assert set(cards) == {"cash", "receivable", "overdue", "payable", "due_this_week", "profit"}, set(cards)
		assert abs(cards["cash"]["value"] - home.cash()["value"]) < 0.01, (cards["cash"], home.cash())
		assert abs(cards["profit"]["value"] - home.profit_this_month()["value"]) < 0.01
		assert abs(cards["receivable"]["value"] - home.owed_to_us()["value"]) < 0.01
		assert len(cards["cash"]["series"]) == stories.MONTHS
		assert abs(sum(cards["overdue"]["series"]) - cards["overdue"]["value"]) < 0.01, cards["overdue"]
		assert len(cards["due_this_week"]["series"]) == home.WEEK, cards["due_this_week"]
		assert abs(sum(cards["due_this_week"]["series"]) - cards["due_this_week"]["value"]) < 0.01, cards["due_this_week"]
		aged = sum(one["owed"] for one in told["receivable"]["ages"])
		assert abs(aged - cards["receivable"]["value"]) < 0.01, (aged, cards["receivable"])
		overdue = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "status": "Overdue", "company": COMPANY}, pluck="name")
		assert overdue and said["needs"]["overdue"]["count"] == len(overdue), (said["needs"]["overdue"], overdue)
		for row in said["everything"]:
			kind = "DocType" if row["kind"] == "List" else row["kind"]
			assert frappe.db.exists(kind, row["target"]), row
		record = frappe.get_doc("Record Head", "Sales Invoice")
		late = head.said(frappe.get_doc("Sales Invoice", overdue[0]), record)
		assert late["sentence"]["colour"] == "red", late["sentence"]
		assert late["band"][0]["steps"][-1]["state"] == "late", late["band"][0]
		paid = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "status": "Paid", "is_return": 0}, pluck="name", limit=1)
		done = head.said(frappe.get_doc("Sales Invoice", paid[0]), record)
		assert done["sentence"]["colour"] == "green" and all(step["state"] == "done" for step in done["band"][0]["steps"]), done


@check
def onebook_oneai_reads_the_money_as_home_does():
	"""What OneAI reads in OneBook agrees with Home: the figures are Home's,
	the overdue invoices are Today's, one invoice says what settled it, the
	bank lines are Today's; and Home offers its three questions."""
	from onedesk.one_ai import chat, suggest
	from onedesk.one_book import agent, home, story

	with as_user("huda@one.test"):
		money = agent.money_now()
		assert money["figures"]["cash"]["now"] == story.read()["cards"]["cash"]["value"], money["figures"]
		late = agent.late_invoices("Sales Invoice")
		assert late["count"] == home.needs_you()["overdue"]["count"] and late["count"], late
		assert agent.late_invoices("Sales Invoice", party=late["invoices"][0]["party"])["count"] >= 1
		paid = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "status": "Paid", "is_return": 0}, pluck="name", limit=1)
		said = agent.invoice_facts(paid[0])
		assert said["still_owed"] == 0 and said["payments"], said
		assert agent.bank_to_match()["lines"] == home.needs_you()["bank"]["count"]
		offered = [one["label"] for one in suggest.for_page({"page": "books"})]
		assert "How is the money doing?" in offered, offered
		assert "OneBook's Home" in chat._page({"page": "books"})
	with as_user("rania@one.test"):
		assert agent.bank_to_match().get("error") and agent.late_invoices().get("error"), "outside the books, nothing is read"


@check
def onebook_chases_what_customers_owe():
	"""Huda's chasing: the customer longest late has a payment reminder that
	prints as One's Payment Reminder with each overdue invoice and the bank to
	pay into; another has a payment request; the statements go monthly; DEWA's
	direct debits match by a rule; and Dunning opens in OneBook's rail."""
	with as_user("huda@one.test"):
		reminder = frappe.get_doc("Dunning", frappe.get_all("Dunning", filters={"docstatus": 1}, pluck="name", limit=1)[0])
		printed = frappe.get_print("Dunning", reminder.name, print_format="One Payment Reminder")
		assert "Payment Reminder" in printed and reminder.overdue_payments[0].sales_invoice in printed
		iban = frappe.db.get_value("Bank Account", reminder.one_pay_into, "iban")
		assert iban and iban in printed, "it says where to pay"
		assert frappe.db.get_value("Property Setter", {"doc_type": "Dunning", "property": "default_print_format"}, "value") == "One Payment Reminder"
		assert frappe.get_all("Payment Request", filters={"reference_doctype": "Sales Invoice", "docstatus": 1})
		assert frappe.db.get_value("Process Statement Of Accounts", "Monthly Statements", "frequency") == "Monthly"
		assert frappe.db.exists("Bank Transaction Rule", "DEWA direct debit")
	assert frappe.get_hooks("one_module_heirs").get("Accounts") == ["OneBook"], "Dunning opens in OneBook"


@check
def onebook_a_late_invoice_ages_into_its_column():
	"""The invoice longest late sits in the same column of what is owed on
	Huda's Home as in ERPNext's Accounts Receivable, and that column is the
	one its days past due fall in."""
	from erpnext.accounts.report.accounts_receivable.accounts_receivable import execute

	from onedesk.one_book import home, story

	with as_user("huda@one.test"):
		late = frappe.get_all(
			"Sales Invoice",
			filters={"docstatus": 1, "status": "Overdue", "company": COMPANY},
			fields=["name", "due_date", "outstanding_amount"],
			order_by="due_date asc",
			limit=1,
		)
		assert late, "the demo leaves an invoice late"
		one = late[0]
		days = date_diff(today(), one.due_date)
		bands = [row["band"] for row in story.ageing([])]
		ours = next(row["band"] for row in story.ageing([one]) if row["owed"])
		low, _, high = ours.partition("-")
		assert int(low) <= days and (high == "Above" or days <= int(high)), (ours, days)
		told = {row["band"]: row["owed"] for row in story.read()["receivable"]["ages"]}
		assert told[ours] >= flt(one.outstanding_amount) - 0.01, (told, one)
		_, rows, *_ = execute(
			frappe._dict(company=reader_company(), report_date=today(), range="30, 60, 90, 120", ageing_based_on="Due Date")
		)
		row = next(row for row in rows if row.get("voucher_no") == one.name)
		theirs = next(n for n in range(1, 6) if abs(flt(row.get(f"range{n}")) - flt(one.outstanding_amount)) < 0.01)
		assert bands[theirs] == ours, (bands[theirs], ours, days)


@check
def onebook_profit_and_loss_shows_each_month_in_its_month():
	"""ERPNext's Profit and Loss by month, as Huda runs it: the workshop and
	office rent, 38,000 on the first of each month, sits in each month this
	year, and nowhere twice."""
	from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute

	from onedesk.one_book import home

	with as_user("huda@one.test"):
		year = frappe.db.get_value(
			"Fiscal Year", {"year_start_date": ["<=", today()], "year_end_date": [">=", today()]}, "name"
		)
		_, rows, *_ = execute(
			frappe._dict(
				company=reader_company(),
				filter_based_on="Fiscal Year",
				from_fiscal_year=year,
				to_fiscal_year=year,
				period_start_date=getdate(f"{getdate(today()).year}-01-01"),
				period_end_date=getdate(f"{getdate(today()).year}-12-31"),
				periodicity="Monthly",
				accumulated_values=0,
				presentation_currency=None,
			)
		)
		rent = next(row for row in rows if (row.get("account_name") or "").startswith("Rent Expense"))
		months = [key for key in rent if key[:3].lower() in {
			"jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"
		} and key[-4:].isdigit()]
		assert len(months) == 12, months
		for n, key in enumerate(months, start=1):
			want = 38000 if n <= getdate(today()).month else 0
			assert abs(flt(rent[key]) - want) < 0.01, (key, rent[key])


@check
def onebook_a_payment_says_where_it_stands():
	"""Every payment Huda opens says in a sentence what moved, to or from
	whom, and a payment through the bank says whether the statement has it
	yet. A payment to an employee is titled by their name, not HR-EMP."""
	from onedesk.one import head

	record = frappe.get_doc("Record Head", "Payment Entry")
	with as_user("huda@one.test"):
		for name in frappe.get_all("Payment Entry", filters={"docstatus": ["<", 2]}, pluck="name"):
			doc = frappe.get_doc("Payment Entry", name)
			said = head.said(doc, record)
			assert said["sentence"] and said["sentence"]["text"], name
			if doc.docstatus == 1 and frappe.get_cached_value("Account", doc.paid_from if doc.payment_type == "Pay" else doc.paid_to, "account_type") == "Bank":
				steps = said["band"][0]["steps"]
				assert steps[-1]["state"] == ("done" if doc.clearance_date else "now"), (name, steps)
	named = frappe.get_all("Payment Entry", filters={"party_type": "Employee"}, fields=["title", "party", "party_name"])
	assert named and all(one.title == one.party_name for one in named), named


@check
def onebook_a_journal_entry_says_what_it_is_for():
	"""No journal entry is titled by one of its own accounts: a month's
	depreciation names its asset, a payroll its period, the rent its remark.
	Each says in a sentence what it moved, and names what it is for."""
	from onedesk.one import head
	from onedesk.one_book import journal

	record = frappe.get_doc("Record Head", "Journal Entry")
	with as_user("huda@one.test"):
		for name in frappe.get_all("Journal Entry", filters={"docstatus": 1}, pluck="name"):
			doc = frappe.get_doc("Journal Entry", name)
			if journal.referenced(doc) or doc.user_remark:
				assert not journal.untitled(doc), (name, doc.title)
			said = head.said(doc, record)
			assert said["sentence"] and said["sentence"]["text"], name
		asset = frappe.get_all("Journal Entry", filters={"voucher_type": "Depreciation Entry", "docstatus": 1}, pluck="name", limit=1)
		said = head.said(frappe.get_doc("Journal Entry", asset[0]), record)
		assert any(one.get("route", "").startswith("/desk/asset/") for one in said["band"]), said["band"]


@check
def onebook_the_bank_says_what_is_left_to_match():
	"""Huda's bank account says what the books hold and how many statement
	lines are unmatched; a line says what came in or went out and points at
	the payment with its reference, the draft OneAI made for Marina Hotels;
	the reconciliation tool opens on that account, back to its oldest line."""
	from onedesk.one import head

	with as_user("huda@one.test"):
		from onedesk.one.company import reader_company

		account = frappe.get_all("Bank Account", filters={"is_company_account": 1, "is_default": 1, "company": reader_company()}, pluck="name")[0]
		said = head.said(frappe.get_doc("Bank Account", account), frappe.get_doc("Record Head", "Bank Account"))
		unmatched = frappe.db.count("Bank Transaction", {"bank_account": account, "docstatus": 1, "status": "Unreconciled"})
		assert unmatched and any(one.get("value") == str(unmatched) for one in said["band"]), said["band"]
		record = frappe.get_doc("Record Head", "Bank Transaction")
		lines = frappe.get_all("Bank Transaction", filters={"docstatus": 1, "status": "Unreconciled"}, fields=["name", "reference_number"])
		for one in lines:
			said = head.said(frappe.get_doc("Bank Transaction", one.name), record)
			assert said["sentence"]["colour"] == "orange", said["sentence"]
		paid = [one for one in lines if one.reference_number and frappe.db.exists("Payment Entry", {"reference_no": one.reference_number})]
		assert paid, lines
		said = head.said(frappe.get_doc("Bank Transaction", paid[0].name), record)
		assert any((one.get("route") or "").startswith("/desk/payment-entry/") for one in said["band"]), said["band"]
		from onedesk.one_book import bank

		opens = bank.reconciling()
		oldest = min(frappe.get_all("Bank Transaction", filters={"bank_account": opens["bank_account"], "docstatus": 1, "status": "Unreconciled"}, pluck="date"))
		assert opens["bank_account"] == account and opens["from_date"] == str(oldest), (opens, account, oldest)


@check
def onebook_the_statement_is_matched_to_what_it_shows():
	"""The transport debit on the bank statement is matched to the bank entry
	Huda made from it in the reconciliation tool: the line is Reconciled with
	nothing left over, the entry carries the bank's reference and is cleared
	on the statement's date, and the bank account counts it no more."""
	from onedesk.one_demo.books import TRANSPORT

	with as_user("huda@one.test"):
		line = frappe.get_all(
			"Bank Transaction",
			filters={"docstatus": 1, "withdrawal": [">", 0], "description": ["like", "%transport%"]},
			fields=["name", "status", "unallocated_amount", "reference_number", "date", "withdrawal"],
		)
		assert line, "the statement has its transport debit"
		line = line[0]
		assert line.status == "Reconciled" and not flt(line.unallocated_amount), line
		paid = frappe.get_doc("Bank Transaction", line.name).payment_entries
		assert len(paid) == 1 and paid[0].payment_document == "Journal Entry", paid
		entry = frappe.get_doc("Journal Entry", paid[0].payment_entry)
		assert entry.docstatus == 1 and entry.cheque_no == line.reference_number, entry.cheque_no
		assert str(entry.clearance_date) == str(line.date), (entry.clearance_date, line.date)
		booked = {row.account.rsplit(" - ", 1)[0]: flt(row.debit) for row in entry.accounts}
		assert booked.get(TRANSPORT) == flt(line.withdrawal), booked
		still = frappe.db.count("Bank Transaction", {"docstatus": 1, "status": "Unreconciled"})
		assert still and still == frappe.db.count("Bank Transaction", {"docstatus": 1}) - 1


@check
def onebook_the_books_check_has_nothing_left_to_do():
	"""The demo company is set up as its accountant would leave it: nothing
	on the Books Check is To Do, Temporary Opening is at nought, and the UAE
	VAT 201 reports the sales made in Dubai, the company's emirate."""
	from frappe.desk.query_report import run as run_report

	from onedesk.one_book import ready

	with as_user("huda@one.test"):
		todo = [row["key"] for row in ready.checks() if row["state"] == ready.TO_DO]
		assert not todo, todo
		assert not ready.temporary(COMPANY)
		said = run_report("UAE VAT 201", filters={"company": COMPANY, "from_date": add_days(today(), -365), "to_date": today()})
		dubai = next(row for row in said["result"] if isinstance(row, dict) and row.get("no") == "1b")
		assert flt(dubai.get("raw_amount", dubai.get("amount"))) > 0, dubai


@check
def onebook_a_uae_invoice_prints_as_a_tax_invoice():
	"""In the UAE a sales invoice prints as a Tax Invoice and a credit note as
	a Tax Credit Note, each with the company's TRN, and the VAT line says its
	rate once."""
	trn = frappe.get_cached_value("Company", COMPANY, "tax_id")
	invoice = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "is_return": 0, "company": COMPANY}, pluck="name", limit=1)[0]
	printed = frappe.get_print("Sales Invoice", invoice, print_format="One Sales Invoice")
	assert "Tax Invoice" in printed and trn in printed
	note = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "is_return": 1}, pluck="name", limit=1)
	assert "Tax Credit Note" in frappe.get_print("Sales Invoice", note[0], print_format="One Sales Invoice")
	assert "% @" not in printed, "the VAT says its rate once"


@check
def onebook_vat_is_charged_and_returned():
	"""A sale in the UAE carries 5% VAT and one abroad none, a bill the VAT
	its supplier charged, and the Tax Return is what they carry, as Huda reads
	it for the year."""
	from onedesk.one_book.report.tax_return import tax_return

	wrong, output, input_ = [], 0.0, 0.0
	for doctype, party_type, party in (("Sales Invoice", "Customer", "customer"), ("Purchase Invoice", "Supplier", "supplier")):
		for doc in frappe.get_all(doctype, filters={"docstatus": 1, "company": COMPANY}, fields=["name", party, "base_net_total", "base_total_taxes_and_charges", "taxes_and_charges"]):
			rate = 0 if _abroad(party_type, doc[party]) else 5
			if not doc.taxes_and_charges or abs(flt(doc.base_total_taxes_and_charges) - flt(doc.base_net_total) * rate / 100) > CENTS:
				wrong.append((doc.name, doc[party], doc.taxes_and_charges, doc.base_net_total, doc.base_total_taxes_and_charges))
			if doctype == "Sales Invoice":
				output += flt(doc.base_total_taxes_and_charges)
			else:
				input_ += flt(doc.base_total_taxes_and_charges)
	assert not wrong, wrong[:5]
	assert output > 0 and input_ > 0, (output, input_)
	claims = frappe.db.sql("select ifnull(sum(tax.base_tax_amount), 0) from `tabExpense Taxes and Charges` tax join `tabExpense Claim` claim on claim.name = tax.parent where claim.docstatus = 1")[0][0]
	with as_user("huda@one.test"):
		_columns, lines = tax_return.execute({"from_date": f"{getdate(today()).year - 1}-01-01", "to_date": today()})
	said = {line["line"]: flt(line.get("tax")) for line in lines if line.get("bold")}
	assert abs(said["Total charged"] - output) <= 1, (said, output)
	assert abs(said["Total paid"] - (input_ + flt(claims))) <= 1, (said, input_, claims)
	from onedesk.one_book import vat

	assert not vat.unreclaimed(COMPANY), ("box 9 claims nothing back on", vat.unreclaimed(COMPANY)[:5])


@check
def onebook_a_foreign_payment_gains_or_loses_at_its_rate():
	"""The euro rose in July, so what Nordlicht paid after it brought in more
	dirhams than its invoice was booked at. Every payment in another currency
	settles its invoice in full, and the difference from the invoice's rate
	is a gain or a loss in the books, to the dirham."""
	gain_loss = tuple(filter(None, frappe.db.get_value("Company", COMPANY, ["exchange_gain_loss_account", "exchange_gain_account", "exchange_loss_account"])))
	seen, wrong = 0, []
	for ref in frappe.db.sql(
		"""select ref.parent as payment, ref.reference_doctype as doctype, ref.reference_name as invoice,
			ref.allocated_amount, ref.exchange_rate as booked, pe.payment_type,
			pe.source_exchange_rate, pe.target_exchange_rate, pe.paid_amount, pe.received_amount
		from `tabPayment Entry Reference` ref join `tabPayment Entry` pe on pe.name = ref.parent
		where pe.docstatus = 1 and ref.reference_doctype in ('Sales Invoice', 'Purchase Invoice')
			and (pe.paid_from_account_currency != pe.paid_to_account_currency)""",
		as_dict=True,
	):
		booked = flt(frappe.db.get_value(ref.doctype, ref.invoice, "conversion_rate"))
		if ref.payment_type == "Receive":
			paid_at = flt(ref.received_amount) / flt(ref.paid_amount)
			difference = flt(ref.allocated_amount) * (paid_at - booked)
		else:
			paid_at = flt(ref.paid_amount) / flt(ref.received_amount)
			difference = flt(ref.allocated_amount) * (booked - paid_at)
		if abs(difference) < 1:
			continue
		seen += 1
		posted = frappe.db.sql(
			"""select ifnull(sum(gl.credit - gl.debit), 0) from `tabGL Entry` gl
			where gl.voucher_type = 'Journal Entry' and gl.account in %s and gl.is_cancelled = 0
				and gl.voucher_no in (select parent from `tabJournal Entry Account` where reference_name = %s)""",
			(gain_loss, ref.invoice),
		)[0][0]
		if abs(flt(posted) - difference) > 1:
			wrong.append((ref.payment, ref.invoice, round(difference, 2), flt(posted)))
	assert seen, "no payment was made at a rate other than its invoice's"
	assert not wrong, wrong
	nordlicht = frappe.get_all("Sales Invoice", filters={"customer": "Nordlicht GmbH", "docstatus": 1, "status": "Paid"}, pluck="name")
	assert nordlicht, "Nordlicht's invoice is not paid"


@check
def onebook_what_is_outstanding_is_what_is_left():
	"""What every invoice and bill still has outstanding is its total less
	what was paid, credited or debited against it, as its ledger says."""
	wrong = []
	for doctype in ("Sales Invoice", "Purchase Invoice"):
		for doc in frappe.get_all(doctype, filters={"docstatus": 1, "is_return": 0}, fields=["name", "outstanding_amount"]):
			left = frappe.db.sql(
				"""select ifnull(sum(amount_in_account_currency), 0) from `tabPayment Ledger Entry`
				where against_voucher_type = %s and against_voucher_no = %s and delinked = 0""",
				(doctype, doc.name),
			)[0][0]
			if abs(abs(flt(left)) - flt(doc.outstanding_amount)) > CENTS:
				wrong.append((doc.name, doc.outstanding_amount, left))
	assert not wrong, wrong[:5]


@check
def onebook_locking_and_fixing_are_abilities():
	"""Lock the Books and Fix What the Check Finds start with the Accounts
	Manager alone: an Accounts User may do neither."""
	from onedesk.one_book import closing, ready

	assert closing.locks("huda@one.test") and ready.fixes("huda@one.test")
	assert not closing.locks("omar@one.test") and not ready.fixes("omar@one.test")
	assert not closing.locks("karim@one.test")
	with as_user("omar@one.test"):
		for refused in (lambda: closing.lock(today()), lambda: ready.fix("year")):
			try:
				refused()
			except frappe.PermissionError:
				pass
			else:
				raise AssertionError("an Accounts User locked or fixed the books")


@check
def onebook_riyadh_keeps_its_own_books():
	"""Sahara Glass Saudi's invoice, payment and bill, in riyals, stay out of
	Sahara's Home and a party's figures; with Riyadh as Huda's company Home
	is Riyadh's, in riyals, what is owed being what is left on each; and
	Huda, limited to Sahara, never lists them."""
	from erpnext import get_company_currency

	from onedesk.one_book import heads, home
	from onedesk.one_demo.branch import BRANCH

	invoice = frappe.db.get_value("Sales Invoice", {"company": BRANCH, "docstatus": 1}, ["name", "customer", "outstanding_amount"], as_dict=True)
	bill = frappe.db.get_value("Purchase Invoice", {"company": BRANCH, "docstatus": 1}, ["name", "outstanding_amount"], as_dict=True)
	assert invoice and bill, "the demo's second company has its books (one_demo/branch.py)"
	with as_user("huda@one.test"):
		ours = home.owed_to_us()["value"]
		assert invoice.name not in {one["name"] for one in home.needs_you()["overdue"].get("rows", [])}
		customer = frappe.get_doc("Customer", invoice.customer)
		last = heads.party_last_bill(customer)
		assert last.get("value") == frappe._("None yet"), "Sahara read Riyadh's invoice as its customer's last"
	frappe.defaults.set_user_default("company", BRANCH, "huda@one.test")
	try:
		with as_user("huda@one.test"):
			theirs = home.owed_to_us()["value"]
			assert abs(theirs - flt(invoice.outstanding_amount)) < 0.01, (theirs, invoice)
			assert abs(home.we_owe()["value"] - flt(bill.outstanding_amount)) < 0.01
			assert theirs != ours
			assert company_currency() == get_company_currency(BRANCH)
	finally:
		frappe.defaults.set_user_default("company", COMPANY, "huda@one.test")
	frappe.get_doc({"doctype": "User Permission", "user": "huda@one.test", "allow": "Company", "for_value": COMPANY}).insert(ignore_permissions=True)
	with as_user("huda@one.test"):
		assert invoice.name not in frappe.get_list("Sales Invoice", pluck="name", limit_page_length=0)
		assert bill.name not in frappe.get_list("Purchase Invoice", pluck="name", limit_page_length=0)


@check
def onebook_oneai_reads_the_tax_return_of_one_company():
	"""OneAI's tax_now is Tax Return for the reader's company: with Riyadh
	worked in, Dubai's VAT is not in it."""
	from onedesk.one_book import agent

	with as_user("huda@one.test"):
		dubai = agent.tax_now(from_date="2026-01-01")
		frappe.defaults.set_user_default("company", "Sahara Glass Saudi")
		try:
			riyadh = agent.tax_now(from_date="2026-01-01")
		finally:
			frappe.defaults.set_user_default("company", "Sahara Glass & Aluminium")
	charged = lambda said: next(one["tax"] for one in said["lines"] if one["line"] == "Total charged")
	assert dubai["currency"] == "AED" and riyadh["currency"] == "SAR", (dubai["currency"], riyadh["currency"])
	assert charged(dubai) > 0 and charged(riyadh) != charged(dubai), (charged(dubai), charged(riyadh))


@check
def onebook_its_accountant_drafts_what_mail_and_files_bring():
	"""OneBook's accountant's work on what OneAI read (planner.py): a
	payment advice as a draft Payment Entry and a bank statement's lines as
	Bank Transactions, each under its own name and action; the supplier a
	new bill came from is OneAI's own, made before the accountant works."""
	from onedesk.one.registry import agents
	from onedesk.one_demo import samples

	paid = [one for one in samples.done_by("payment-advice", "one_book") if one.target_doctype == "Payment Entry"]
	assert paid and paid[0].agent_action == "draft_payment_entry" and paid[0].level == "Done", paid
	assert frappe.db.get_value("Payment Entry", paid[0].target_name, "docstatus") == 0, "a person submits it"
	lines = [one for one in samples.done_by("bank-statement", "one_book") if one.target_doctype == "Bank Transaction"]
	assert len(lines) >= 2 and {one.agent_action for one in lines} == {"add_bank_transactions"}, lines
	made = frappe.get_all("Reading Action", filters={"target_doctype": "Supplier", "kind": "Create", "key": ["like", "%party|supplier"]}, fields=["agent"])
	assert made and not {one.agent for one in made} & {one.email for one in agents.listed()}, made
