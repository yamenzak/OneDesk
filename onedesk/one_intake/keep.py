"""How long a document must be kept, and nothing deleted before (docs/INTAKE.md §16.10).

A business must keep its books' papers for years, and which papers and how
many years is the law of its country:

- **Germany** (§ 147 AO, § 257 HGB, since 2025): invoices, receipts, bank
  statements and other vouchers eight years; business letters, orders,
  delivery notes and contracts six; the payroll account six (§ 41 EStG);
- **the United Arab Emirates** (Federal Decree-Law 50 of 2022, and the VAT
  law): the books and their papers five years.

The time runs from the end of the year the document is dated in. A reading
carries the day it may go (Keep Until), and a file whose only copy holds such
a reading cannot be deleted for good before that day: it may go to the
Recycle Bin, where it stays. A household keeps no books and has no keeping
periods, and neither has a country not listed here.
"""

from datetime import date

#: Years to keep, by country and kind, and the law that says so.
PERIODS = {
	"DE": {
		**dict.fromkeys(("Invoice", "Credit Note", "Receipt", "Bank Statement", "Payment Advice"), (8, "§ 147 AO")),
		**dict.fromkeys(("Offer", "Order", "Order Confirmation", "Delivery Note", "Contract", "Reminder", "Letter"), (6, "§ 257 HGB")),
		"Payslip": (6, "§ 41 EStG"),
	},
	"AE": dict.fromkeys(
		("Invoice", "Credit Note", "Receipt", "Bank Statement", "Payment Advice", "Offer", "Order", "Order Confirmation", "Delivery Note", "Contract", "Payslip"),
		(5, "Federal Decree-Law 50/2022"),
	),
}


def period(kind: str | None, country: str | None) -> tuple[int, str] | None:
	"""Years to keep a kind of document in a country, and the law. Pure."""
	return PERIODS.get((country or "").upper(), {}).get(kind or "")


def until(kind: str | None, country: str | None, dated: date | None) -> date | None:
	"""The last day a document must be kept: the end of the year it is dated
	in, plus the years its kind is kept. Pure."""
	found = period(kind, country)
	if not found or not dated:
		return None
	return date(dated.year + found[0], 12, 31)


def guard(doc, method=None) -> None:
	"""File on_trash: not a file whose only copy holds a document still kept
	by law."""
	import frappe
	from frappe import _
	from frappe.utils import getdate

	if doc.is_folder or frappe.flags.in_install or frappe.flags.in_migrate:
		return
	kept = held(doc)
	if kept:
		frappe.throw(
			_("{0} must be kept until {1} by law, and cannot be deleted before then.").format(doc.file_name, frappe.format(getdate(kept), "Date")),
			title=_("Kept by law"),
		)


def held(doc) -> str | None:
	"""The day a file's document may go, when this file is its only copy and
	that day has not come."""
	import frappe
	from frappe.utils import today

	readings = [doc.one_reading] if doc.get("one_reading") else []
	if doc.content_hash:
		readings += frappe.get_all("Reading", filters={"key": doc.content_hash}, pluck="name")
	if not readings:
		return None
	kept = frappe.get_all("Reading", filters={"name": ["in", readings], "keep_until": [">", today()], "copy_of": ["is", "not set"]}, pluck="keep_until")
	if not kept:
		return None
	if doc.content_hash and frappe.db.exists("File", {"content_hash": doc.content_hash, "name": ["!=", doc.name], "is_folder": 0, "one_deleted": 0}):
		return None
	return str(max(kept))
