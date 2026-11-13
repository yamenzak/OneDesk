"""One is sold to any country, in any currency, under any tax. Nothing generic
names the UAE, its dirham or its VAT: a label says "Tax" and "Tax ID", a money
figure carries its own currency rather than a heading that names one, and the
parts that really are one country's are in the files below, each shown only
where the workspace's country is that one. docs/STANDARD.md, Money and tax."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
SRC = ROOT / "frontend" / "src"

COUNTRY = re.compile(r"\bAED\b|\bUAE\b|United Arab Emirates|\bVAT\b|Emirat|\bTRN\b|\bFTA\b|dirham", re.I)

# Each is one country's, or the EU's, and is shown only there.
REGIONAL = {
	"hooks.py": "UAE VAT Settings, homed in OneBook",
	"one_book/manifest.py": "OneBook's step that keeps the emirate to UAE companies",
	"one/countries.py": "which regional doctypes and reports each country sees",
	"one/shown.json": "what the rails show, generated, and the rails gate them by country",
	"one_hr/holidays.py": "the holiday names a country's calendar ships",
	"one/patches/holiday_names.py": "the same, renamed once",
	"one_studio/letter_heads.py": "a UAE company's tax number is called TRN",
	"one_studio/print_blocks.py": "the UAE tax-invoice block and the dirham's symbol",
	"one_book/home.py": "the regional reports, shown by country",
	"one_book/sidebar/onebook/onebook.json": "UAE VAT 201, shown by country",
	"one_book/paper.py": "the dirham's printed symbol",
	"one_book/vat.py": "the UAE VAT return",
	"one_book/ready.py": "what the UAE return needs, asked only in the UAE",
	"one_book/report/books_check/books_check.js": "the UAE company's TRN and emirate",
	"one_book/patches/invoices_say_their_vat.py": "an old patch, by its name",
	"one_book/patches/tax_return.py": "removes the old VAT Return report",
	"one_book/patches/bills_reclaim_their_vat.py": "box 9 of the UAE return, filled on old bills",
	"one_hr/papers.py": "the employee documents each country asks for",
	"one_project/retention.py": "the countries where retention is taxed when released",
	"one_ai/reading/identifiers.py": "the EU VAT number on a supplier's invoice",
	"one_ai/reading/identity.py": "the same",
	"one_ai/reading/panel.py": "the same",
	"one_ai/reading/planning.py": "the same",
	"one_ai/reading/understand.py": "the same",
	"one_ai/reading/readers/einvoice.py": "the same, in an e-invoice",
	"one_ai/doctype/reading_party/reading_party.json": "the same",
	"public/js/one_crm/crm_record.js": "the EU VAT ID on a customer",
	"trust_center/documents.py": "the operator's own address and law",
	"one_admin/costs.py": "what the operator pays, in its own currency, and its Stripe account's country",
	"one_admin/price_list.py": "the operator's own currency and tax registration",
	"trust_center/trust.py": "the operator's own law",
	"trust_center/laws.py": "the laws the agreements answer, the UAE's among them",
	"one_portal/checks.py": "the demo company's own customers and suppliers, which its checks sign in as",
	"one_project/checks.py": "the demo company is in the UAE, where tax on retention falls due as it's released",
	"one_book/checks.py": "the demo company is in the UAE: its VAT 201, its TRN on a Tax Invoice, its dirhams",
	"one_inventory/checks.py": "the demo company keeps its stock in dirhams, and buys in other currencies",
	"one_hr/checks.py": "the demo company is in the UAE: its papers, its end of service, its dirhams",
	"one/checks.py": "the demo company is in the UAE: its suppliers, its holidays, its VAT settings",
	"one_ai/checks.py": "the demo company is in the UAE: the VAT on its bills, its dirhams",
	"account_center/checks.py": "the operator's own address on the demo's bill",
}

SKIP = ("locale", "one_demo", "fixtures", "dist", "tests")


def _ours():
	for path in [*APP.rglob("*"), *SRC.rglob("*")]:
		if path.suffix not in (".py", ".js", ".vue", ".json", ".html") or set(path.parts) & set(SKIP):
			continue
		yield path


def test_nothing_generic_names_one_country():
	found = []
	for path in _ours():
		where = str(path.relative_to(APP if APP in path.parents else ROOT))
		if where in REGIONAL:
			continue
		for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
			if COUNTRY.search(line):
				found.append(f"{where}:{n}: {line.strip()[:120]}")
	assert not found, "say Tax, Tax ID and the record's own currency, or gate it by country:\n" + "\n".join(
		found
	)


def test_every_regional_file_still_needs_it():
	for where in REGIONAL:
		assert COUNTRY.search((APP / where).read_text(encoding="utf-8")), (
			f"{where} names no country now; drop it from REGIONAL"
		)


def test_a_money_figure_carries_its_currency():
	"""A heading that names the currency so the figures under it need not was
	how a page said AED once; every amount says its own now."""
	for path in SRC.rglob("*.vue"):
		source = path.read_text(encoding="utf-8")
		assert not re.search(r"""__\(\s*["']Amounts? in\b""", source), (
			f"{path.relative_to(SRC)} names the currency above its figures"
		)
	assert "export const plain" not in (SRC / "kit" / "desk.js").read_text(encoding="utf-8"), (
		"an amount without its currency"
	)


def test_a_taxed_figure_says_the_other_side_on_hover():
	figures = (SRC / "kit" / "Figures.vue").read_text(encoding="utf-8")
	assert "<Tooltip" in figures and "one.other" in figures and "decoration-dashed" in figures
	band = (APP / "public" / "js" / "band.js").read_text(encoding="utf-8")
	assert "one-taxed" in band and '.attr("title", other)' in band
	css = (APP / "public" / "css" / "desk.css").read_text(encoding="utf-8")
	assert re.search(r"\.one-taxed \{[^}]*underline dashed", css)
	head = (APP / "one" / "head.py").read_text(encoding="utf-8")
	assert "def taxed(" in head
