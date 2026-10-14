"""What a journal entry is called. ERPNext titles one by its first account
when nobody types a title, so a month's depreciation, a payroll and the rent
all read as an account's name in the list ("Accumulated Depreciation - SGA").
See the module's README, Under the hood."""

import frappe
from frappe import _
from frappe.utils import formatdate

#: How long a title taken from the remark may be.
LONGEST = 140


def referenced(doc) -> tuple[str, str] | None:
	"""The first document the entry's lines name: an asset, a payroll, an
	invoice."""
	for row in doc.get("accounts") or []:
		if row.get("reference_type") and row.get("reference_name"):
			return row.reference_type, row.reference_name
	return None


def named(doctype: str, name: str) -> str:
	"""A document's title, or its name when it has none."""
	field = frappe.get_meta(doctype).get_title_field()
	return (field and field != "name" and frappe.db.get_value(doctype, name, field)) or name


def title(remark: str | None, voucher_type: str, reference: tuple | None) -> str | None:
	"""What the entry is for: the asset it depreciates or the salaries it
	books, else its remark's first line, else what it references."""
	if reference and reference[0] == "Payroll Entry":
		start, end = frappe.db.get_value("Payroll Entry", reference[1], ["start_date", "end_date"]) or (
			None,
			None,
		)
		if start and end:
			return _("Salaries from {0} to {1}").format(formatdate(start), formatdate(end))
	if reference and reference[0] == "Asset" and voucher_type == "Depreciation Entry":
		return _("Depreciation of {0}").format(named(*reference))
	said = (remark or "").strip().splitlines()[0].strip() if (remark or "").strip() else ""
	if said:
		return said[:LONGEST]
	if not reference:
		return None
	return _("{0}: {1}").format(_(reference[0]), named(*reference))


def untitled(doc) -> bool:
	"""Whether the entry still has a title nobody chose: none, or the name of
	one of its own accounts, as ERPNext and HRMS give it."""
	return not doc.title or doc.title in {row.account for row in doc.get("accounts") or []}


def titled(doc, method=None) -> None:
	"""Titles an entry by what it is for while nobody has chosen its title; a
	title somebody typed is kept."""
	if not untitled(doc):
		return
	doc.title = title(doc.user_remark, doc.voucher_type, referenced(doc)) or doc.title
