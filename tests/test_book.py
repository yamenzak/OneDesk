"""OneBook: the money — invoices, bills, payments, the bank and the reports —
on ERPNext's own accounting."""

import ast
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

BOOK = tree.APP / "one_book"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")
READY = BOOK / "ready.py"
RAIL = json.loads((BOOK / "sidebar" / "onebook" / "onebook.json").read_text())


def _items(rail=RAIL):
	return {item["label"]: item for item in rail["items"]}


def test_onebook_is_in_the_dock_instead_of_erpnexts_accounts():
	dock = json.loads((tree.APP / "dock" / "onedesk" / "onedesk.json").read_text())
	links = [row["link_to"] for row in dock["items"]]
	assert "OneBook" in links and "Accounts" not in links


def test_the_money_is_onebooks_and_the_customer_onecrms():
	items = _items()
	owned = {item["link_to"] for item in RAIL["items"] if item.get("is_default_module") and item["type"] == "Link"}
	assert {"Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry", "Supplier"} <= owned
	assert not items["Customer"]["is_default_module"], "customers are OneCRM's"
	assert "is_return" in items["Credit Note"]["filters"] and "is_return" in items["Debit Note"]["filters"]


def test_every_report_row_names_a_report_erpnext_or_onebook_ships():
	reports = [item["link_to"] for item in RAIL["items"] if item.get("link_type") == "Report"]
	erpnext = Path("/home/frappe/bench1/apps/erpnext/erpnext")
	if not erpnext.exists():
		return
	shipped = {
		json.loads(p.read_text())["name"]
		for root in (erpnext, BOOK, BOOK.parent / "one_ai")
		for p in root.glob("**/report/*/*.json")
		if p.parent.name == p.stem
	}
	assert set(reports) <= shipped, set(reports) - shipped


def _load(path: Path, names: tuple, **extra) -> dict:
	space = {
		"getdate": lambda day: day,
		"add_days": lambda day, n: day + timedelta(days=n),
		"add_years": lambda day, n: day.replace(year=day.year + n),
		**extra,
	}
	for node in ast.parse(path.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return space


def _body(path: Path, name: str) -> str:
	for node in ast.parse(path.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return ast.unparse(node)
	raise AssertionError(f"{name} not in {path.name}")


def test_a_missing_fiscal_year_follows_the_last_and_covers_today():
	covering = _load(READY, ("covering",))["covering"]
	assert covering(None, date(2026, 9, 23)) == (date(2026, 1, 1), date(2026, 12, 31))
	assert covering(date(2025, 12, 31), date(2026, 9, 23)) == (date(2026, 1, 1), date(2026, 12, 31))
	assert covering(date(2025, 3, 31), date(2026, 9, 23)) == (date(2026, 4, 1), date(2027, 3, 31))
	assert covering(date(2023, 12, 31), date(2026, 9, 23)) == (date(2026, 1, 1), date(2026, 12, 31))
	assert covering(None, date(2026, 9, 23), (4, 1)) == (date(2026, 4, 1), date(2027, 3, 31))
	assert covering(None, date(2026, 2, 23), (4, 1)) == (date(2025, 4, 1), date(2026, 3, 31))


def test_a_first_fiscal_year_begins_when_the_countrys_does():
	"""As ERPNext's setup wizard proposes it, read from its own map."""
	import re

	begins = _load(READY, ("begins",), re=re)["begins"]
	wizard = 'erpnext.setup.fiscal_years = {\n\tAustralia: ["07-01", "06-30"],\n\t"New Zealand": ["04-01", "03-31"],\n};'
	assert begins(wizard, "Australia") == (7, 1)
	assert begins(wizard, "New Zealand") == (4, 1)
	assert begins(wizard, "Germany") == (1, 1)
	theirs = Path("/home/frappe/bench1/apps/erpnext/erpnext/public/js/setup_wizard.js")
	if theirs.exists():
		assert begins(theirs.read_text(encoding="utf-8"), "India") == (4, 1)


def test_a_company_bank_account_wires_the_bank_modes_of_payment():
	assert '"Bank Account": {"on_update": "onedesk.one_book.ready.wired"}' in HOOKS


def test_the_books_check_opens_setup():
	assert _items()["Setup"]["link_to"] == "books" and _items()["Setup"]["route"] == "setup"
	source = (BOOK / "home.py").read_text(encoding="utf-8")
	rows = [line for line in source.splitlines() if line.strip().startswith('("setup", _lt("') and '"Setup"' not in line]
	assert '"Books Check"' in rows[0]


def test_what_is_outstanding_counts_only_what_falls_due_by_the_day():
	outstanding = _load(BOOK / "home.py", ("outstanding",), flt=float)["outstanding"]
	rows = [
		{"outstanding_amount": 100, "due_date": date(2026, 9, 1)},
		{"outstanding_amount": 50, "due_date": date(2026, 9, 25)},
		{"outstanding_amount": 20, "due_date": None},
	]
	assert outstanding(rows) == 170
	assert outstanding(rows, until=date(2026, 9, 22)) == 100
	assert outstanding(rows, until=date(2026, 9, 29)) == 150


def test_home_is_onebooks_page_with_its_six_figures():
	assert RAIL["items"][0]["link_to"] == "books" and RAIL["items"][0]["link_type"] == "Page"
	source = (BOOK / "story.py").read_text(encoding="utf-8")
	for card in ("cash", "receivable", "overdue", "payable", "due_this_week", "profit"):
		assert f'cards["{card}"]' in source, card
	assert not (BOOK / "workspace").exists() and not (BOOK / "number_card").exists()


def test_what_is_owed_is_aged_in_erpnexts_ranges():
	ageing = _load(BOOK / "story.py", ("ageing",), flt=float, date_diff=lambda a, b: (a - b).days, today=lambda: date(2026, 10, 14), RANGES=(30, 60, 90, 120))["ageing"]
	rows = [
		{"outstanding_amount": 10, "due_date": date(2026, 10, 20)},
		{"outstanding_amount": 20, "due_date": date(2026, 10, 14)},
		{"outstanding_amount": 30, "due_date": date(2026, 9, 1)},
		{"outstanding_amount": 40, "due_date": date(2026, 1, 1)},
	]
	got = {one["band"]: one["owed"] for one in ageing(rows, date(2026, 10, 14))}
	assert list(got) == ["not_due", "0-30", "31-60", "61-90", "91-120", "121-Above"]
	assert got["not_due"] == 30 and got["31-60"] == 30 and got["121-Above"] == 40


def test_a_closing_entry_does_not_count_as_this_months_profit():
	assert "Period Closing Voucher" in _body(BOOK / "home.py", "profit_this_month")


def test_a_payment_is_allocated_first_to_last_and_never_beyond_what_is_owed():
	allocate = _load(BOOK / "paid.py", ("allocate",), flt=float)["allocate"]
	assert allocate(100, [60, 60]) == [60, 40]
	assert allocate(50, [60, 60]) == [50, 0]
	assert allocate(120, [60, 60]) == [60, 60]


def test_record_payment_is_on_invoices_and_bills_only():
	heads = (BOOK / "heads.py").read_text(encoding="utf-8")
	assert '"doctypes": list(paid.SETTLED)' in heads and "for doctype in paid.SETTLED" in heads


def test_the_payment_reminder_ships_off_and_the_books_check_turns_it_on():
	reminder = json.loads((BOOK / "notification" / "payment_reminder" / "payment_reminder.json").read_text())
	assert reminder["enabled"] == 0, "it writes to customers, so nobody gets it until somebody says so"
	assert reminder["document_type"] == "Sales Invoice" and reminder["event"] == "Days After"
	assert "outstanding_amount > 0" in reminder["condition"]


def test_a_repeated_invoice_keeps_its_days_to_pay():
	terms = _load(BOOK / "repeat.py", ("terms",), date_diff=lambda a, b: (a - b).days)["terms"]
	original = {"posting_date": date(2026, 9, 10), "due_date": date(2026, 10, 10)}
	assert terms(original, date(2026, 11, 10)) == date(2026, 12, 10)
	assert terms({**original, "payment_terms_template": "Net 30"}, date(2026, 11, 10)) is None, "terms set it themselves"
	assert terms({"posting_date": date(2026, 9, 10), "due_date": None}, date(2026, 11, 10)) is None


def test_invoices_and_bills_can_repeat_and_the_copy_is_corrected():
	for name in ("sales_invoice", "purchase_invoice"):
		custom = json.loads((BOOK / "custom" / f"{name}.json").read_text())
		assert {"property": "allow_auto_repeat", "value": "1"}.items() <= custom["property_setters"][0].items()
	assert HOOKS.count('"on_recurring": "onedesk.one_book.repeat.repeated"') == 2


def test_a_bills_reclaimable_vat_follows_the_bill_until_somebody_types_their_own():
	recoverable = _load(BOOK / "vat.py", ("recoverable",), flt=lambda v: float(v or 0))["recoverable"]
	assert recoverable(0, None, None, 100) == 100, "a new bill reclaims the VAT on it"
	assert recoverable(100, 100, 100, 150) == 150, "ours, and the bill changed: it follows"
	assert recoverable(20, 100, 100, 150) == 20, "typed just now: kept"
	assert recoverable(20, 20, 100, 150) == 20, "typed before: kept"
	assert recoverable(30, None, None, 100) == 30, "typed on a new bill: kept"


def test_the_tax_return_nets_what_was_charged_against_what_was_paid():
	space = _load(BOOK / "report" / "tax_return" / "tax_return.py", ("lines",), flt=lambda v: float(v or 0), _=lambda s: s)
	rows = [
		{"section": "output", "account": "VAT 5%", "rate": 5, "taxable": 20000, "tax": 1000},
		{"section": "input", "account": "VAT 5%", "rate": 5, "taxable": 4000, "tax": 200},
	]
	out = space["lines"](rows)
	assert out[-1] == {"line": "To pay", "tax": 800, "bold": 1}
	assert space["lines"]([{**rows[1], "tax": 1200}])[-1]["line"] == "To reclaim"


def test_the_uae_checks_only_run_in_the_uae_and_the_bill_hook_is_wired():
	assert "if not vat.in_uae(one.name):" in _body(READY, "_uae")
	assert '"onedesk.one_book.vat.reclaimed"' in HOOKS
	assert '"onedesk.one_book.vat.emirate"' in HOOKS


def test_locking_is_for_the_closers_and_never_into_the_future():
	assert '"validate": "onedesk.one_book.closing.kept_to_today"' in HOOKS


def test_the_year_is_closed_into_retained_earnings_and_then_locked():
	assert '"Period Closing Voucher": {"on_submit": "onedesk.one_book.closing.year_closed"}' in HOOKS


def test_an_accounts_manager_can_add_a_bank():
	"""Add Bank makes the bank first, and ERPNext lets only a System Manager
	add one, which nobody in a workspace is."""
	ready = READY.read_text(encoding="utf-8")
	assert '"doctype": "Bank", "bank_name"' in ready
	access = (BOOK / "access.py").read_text(encoding="utf-8")
	given = access[access.index("GIVEN = {") :].split("\n}\n")[0]
	bank = next(line for line in given.splitlines() if line.strip().startswith('"Bank":'))
	assert "MANAGER" in bank and '"create"' in bank


def test_what_is_owed_is_in_the_companys_currency():
	"""ERPNext keeps what is outstanding in the party's currency, so the home
	turns a party billed in dollars into the company's at the invoice's rate."""
	home = (BOOK / "home.py").read_text(encoding="utf-8")
	unpaid = home[home.index("def _unpaid") :].split("\n\n\n")[0]
	assert "party_account_currency" in unpaid and "conversion_rate" in unpaid


def test_what_is_owed_falls_due_part_by_part():
	parts = _load(BOOK / "home.py", ("parts",), flt=float)["parts"]
	invoice = {"outstanding_amount": 300, "due_date": date(2027, 2, 10)}
	assert parts(invoice, []) == [{"outstanding_amount": 300, "due_date": date(2027, 2, 10)}]
	schedule = [
		{"due_date": date(2026, 5, 30), "payment_amount": 300},
		{"due_date": date(2026, 9, 1), "payment_amount": 200},
		{"due_date": date(2027, 2, 10), "payment_amount": 200},
	]
	assert parts(invoice, schedule) == [
		{"outstanding_amount": 100, "due_date": date(2026, 9, 1)},
		{"outstanding_amount": 200, "due_date": date(2027, 2, 10)},
	]
	assert sum(one["outstanding_amount"] for one in parts({**invoice, "outstanding_amount": 600, "own": 300}, schedule)) == 600


def test_a_tax_line_says_its_rate_once():
	import re

	tax_label = _load(tree.APP / "one_book" / "paper.py", ("tax_label",), flt=float, re=re)["tax_label"]
	assert tax_label("VAT 5% @ 5.0", 5) == "VAT 5%"
	assert tax_label("VAT @ 5.0", 5) == "VAT @ 5%"
	assert tax_label("Customs Duty", 0) == "Customs Duty"


def test_an_invoice_is_a_tax_invoice_only_where_the_law_calls_it_one():
	"""Not wherever the company has a tax ID: by its country (one/countries.py),
	which paper.titled tells the builder's formats before printing."""
	assert '"before_print": "onedesk.one_book.paper.titled"' in HOOKS
	assert '"onedesk.one.print_blocks.offered"' in HOOKS, "a company saved in the UAE is offered its simplified invoice"
	countries = (tree.APP / "one" / "countries.py").read_text(encoding="utf-8")
	listed = countries.split("TAX_INVOICE = (", 1)[1].split(")", 1)[0]
	assert '"United Arab Emirates"' in listed and '"Germany"' not in listed and '"United States"' not in listed
	assert '"One Simplified Tax Invoice": "United Arab Emirates"' in countries
	for name in ("one_sales_invoice", "one_sales_invoice_classic", "one_sales_invoice_bordered", "one_sales_invoice_with_images", "one_detailed_tax_invoice"):
		shown = json.loads((BOOK / "print_format" / name / f"{name}.json").read_text())["format_data"]
		assert "doc.flags.one_tax_invoice and not doc.is_return" in shown and "doc.company_tax_id and" not in shown, name
