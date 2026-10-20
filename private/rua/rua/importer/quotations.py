"""The old quotations, each line under the product its description names,
its mark (CW01) as the line's name and its size in millimetres. The old app
wrote sizes in centimetres ("200.0 cm"); a size with no unit over 1000 is
taken as millimetres already. The written sections become the quotation's
terms under their headings."""

import re

import frappe
from frappe.utils import flt

from rua import setup
from rua.importer.base import clean
from rua.importer.parties import customer_of
from rua.importer.projects import project_of, taxes
from rua.setup import TERMS

QUOTATION = "RUA Quotation"
SECTIONS = (
	("specifications", "Specification"),
	("qualifications", "Standard Qualifications"),
	("scopes", "Scope of Work"),
	("scope_of_work", "Scope of Work"),
	("exclusions", "Exclusions"),
	("maintenance_and_warranty", "Maintenance and Warranty"),
	("duration_and_payment", "Duration and Payment"),
	("terms_and_conditions", "Terms and Conditions"),
	("proposal_basis", "Proposal Basis"),
	("notes", "Notes"),
)
def run(run_):
	for old in run_.docs(QUOTATION):
		if run_.made(QUOTATION, old["name"], "Quotation"):
			continue
		customer = customer_of(run_, old.get("party"))
		if not customer or not old.get("items"):
			run_.note("Left Out", None, None, f"{old['name']}: a quotation with no client or no lines")
			continue
		template, rows = taxes(run_, inclusive=False)
		doc = frappe.get_doc(
			{
				"doctype": "Quotation",
				"quotation_to": "Customer",
				"party_name": customer,
				"company": run_.company,
				"transaction_date": old.get("date"),
				"valid_till": old.get("date"),
				"project": project_of(run_, old.get("project")),
				"taxes_and_charges": template,
				"taxes": rows,
				"tc_name": TERMS,
				"terms": terms(old),
				"items": [line(one) for one in old["items"]],
			}
		)
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True, set_name=old["name"])
		if old.get("status") in ("Submitted", "Rejected"):
			doc.submit()
		run_.remember(QUOTATION, old["name"], "Quotation", doc.name)


def product(description):
	"""The product a line is, by its description (setup.KINDS, which Rua's
	costing template reads the same way)."""
	return setup.kind(description)


def millimetres(value) -> float:
	"""A size as the old app wrote it, in millimetres. Pure."""
	text = str(value or "").strip().lower()
	number = re.search(r"[\d.]+", text)
	if not number:
		return 0.0
	size = flt(number.group())
	if "mm" in text:
		return size
	if "cm" in text:
		return size * 10
	if text.endswith("m") or " m" in text:
		return size * 1000
	return size


def line(one):
	length, width = millimetres(one.get("width")), millimetres(one.get("height"))
	qty = flt(one.get("qty")) or 1
	rate = flt(one.get("total")) / qty if flt(one.get("total")) else flt(one.get("amount"))
	row = {
		"item_code": product(one.get("description")),
		"item_name": clean(one.get("item_name"))[:140] or None,
		"description": clean(one.get("description")) or clean(one.get("item_name")),
		"qty": qty,
		"rate": flt(rate, 2),
	}
	if length and width:
		row.update({"one_measured_by": "Piece", "one_length": length, "one_width": width})
	return row


def terms(old):
	parts, seen = [], set()
	for field, heading in SECTIONS:
		text = (old.get(field) or "").strip()
		if not text or text in seen:
			continue
		seen.add(text)
		parts.append(
			f"<h4>{heading}</h4>{text if text.startswith('<') else '<p>' + frappe.utils.escape_html(text) + '</p>'}"
		)
	return "".join(parts) or None
