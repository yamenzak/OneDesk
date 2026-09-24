"""Ready to submit: every draft OneAI made that a person can post in one go
(docs/INTAKE.md §3.2).

A draft is ready when its document's facts all passed the check, its party
is known, its total is the document's total, and, for an invoice billed from
an order, what it bills is what was ordered and received: ERPNext's three-way
match, read here rather than redone. A supplier whose IBAN on the document is
not one we have for them is red, and so is anything that fails another
check. Red drafts are listed apart and stay out of Submit all until somebody
opens them. Submitting is the person's own act, under their own permission.

An e-invoice from a known supplier, billed from an order and ready, may be
submitted by OneAI itself when a workspace switches that on (Intake
Settings); it is off by default.
"""


import frappe
from frappe import _
from frappe.utils import flt

DOCTYPES = ("Purchase Invoice", "Purchase Receipt", "Sales Order", "Supplier Quotation", "Payment Entry")

#: How far a draft's total may be from the document's before it is red.
TOLERANCE = 0.01

PARTY = {"Purchase Invoice": "supplier", "Purchase Receipt": "supplier", "Supplier Quotation": "supplier", "Sales Order": "customer", "Payment Entry": "party"}
TOTAL = {"Purchase Invoice": "grand_total", "Purchase Receipt": "grand_total", "Sales Order": "grand_total", "Supplier Quotation": "grand_total", "Payment Entry": "paid_amount"}


def red(doc, reading) -> list[str]:
	"""Why a draft is not ready, in the reader's words; empty when it is."""
	why = []
	if reading and reading.unsure:
		why.append(_("Some of what OneAI read is not in the document."))
	if not doc.get(PARTY[doc.doctype]):
		why.append(_("The party is not known."))
	if reading and reading.gross and doc.doctype in ("Purchase Invoice", "Sales Order") and abs(flt(doc.get(TOTAL[doc.doctype])) - flt(reading.gross)) > TOLERANCE:
		why.append(_("The total is {0}, the document says {1}.").format(frappe.format_value(doc.get(TOTAL[doc.doctype]), {"fieldtype": "Currency"}, doc), frappe.format_value(reading.gross, {"fieldtype": "Currency"}, doc)))
	if doc.doctype == "Purchase Invoice":
		why += _three_way(doc)
		why += _iban(doc, reading)
	return why


def _three_way(doc) -> list[str]:
	"""A billed row that differs from its order row in quantity or rate."""
	why = []
	for row in doc.items:
		if not row.po_detail:
			continue
		ordered = frappe.db.get_value("Purchase Order Item", row.po_detail, ["qty", "rate", "received_qty"], as_dict=True)
		if not ordered:
			continue
		if abs(flt(row.rate) - flt(ordered.rate)) > TOLERANCE:
			why.append(_("{0} is billed at {1}, ordered at {2}.").format(row.item_name, row.rate, ordered.rate))
		if flt(row.qty) > flt(ordered.qty):
			why.append(_("{0} is billed {1} times, ordered {2}.").format(row.item_name, row.qty, ordered.qty))
	return why


def _iban(doc, reading) -> list[str]:
	"""An IBAN on the invoice that is not one we have for the supplier: the
	commonest fraud there is, so always red."""
	if not reading or not reading.iban:
		return []
	known = frappe.get_all("Bank Account", filters={"party_type": "Supplier", "party": doc.supplier}, pluck="iban")
	known = [one.replace(" ", "").upper() for one in known if one]
	if known and reading.iban.replace(" ", "").upper() not in known:
		return [_("The invoice asks to be paid to an IBAN we do not have for {0}.").format(doc.supplier)]
	return []


def _drafts() -> list[dict]:
	rows = frappe.get_all(
		"Intake Action",
		filters={"kind": "Create", "level": "Done", "target_doctype": ["in", DOCTYPES]},
		fields=["name", "target_doctype", "target_name", "reading"],
		order_by="creation desc",
		limit=500,
	)
	return [row for row in rows if row.target_name and frappe.db.get_value(row.target_doctype, row.target_name, "docstatus") == 0]


@frappe.whitelist()
def listed() -> dict:
	"""Every OneAI draft the reader may submit, ready or red."""
	from onedesk.one_intake import panel

	ready, held = [], []
	for row in _drafts():
		if not frappe.has_permission(row.target_doctype, "submit", row.target_name):
			continue
		doc = frappe.get_doc(row.target_doctype, row.target_name)
		reading = frappe.get_doc("Reading", row.reading) if row.reading and frappe.db.exists("Reading", row.reading) else None
		why = red(doc, reading)
		said = {
			"doctype": doc.doctype,
			"name": doc.name,
			"party": doc.get(PARTY[doc.doctype]),
			"total": doc.get(TOTAL[doc.doctype]),
			"currency": doc.get("currency") or doc.get("paid_from_account_currency"),
			"date": doc.get("posting_date") or doc.get("transaction_date"),
			"title": reading.title if reading else None,
			"document": panel.document_of(reading.name) if reading else None,
			"red": why,
		}
		(held if why else ready).append(said)
	return {"ready": ready, "red": held}


@frappe.whitelist(methods=["POST"])
def submit_all(names) -> dict:
	"""Submit the listed drafts that are still ready, each as the person
	pressing the button, under their own permission."""
	names = frappe.parse_json(names) if isinstance(names, str) else names
	done, failed = [], []
	for doctype, name in names or []:
		if doctype not in DOCTYPES:
			continue
		doc = frappe.get_doc(doctype, name)
		if doc.docstatus != 0:
			continue
		reading = frappe.db.get_value("Intake Action", {"target_doctype": doctype, "target_name": name, "kind": "Create"}, "reading")
		if red(doc, frappe.get_doc("Reading", reading) if reading and frappe.db.exists("Reading", reading) else None):
			failed.append({"name": name, "why": _("It is not ready any more.")})
			continue
		try:
			doc.check_permission("submit")
			doc.submit()
			frappe.db.commit()
			done.append(name)
		except Exception as raised:
			frappe.db.rollback()
			frappe.clear_messages()
			failed.append({"name": name, "why": frappe.utils.strip_html_tags(str(raised))[:300]})
	return {"done": done, "failed": failed}


def maybe_submit(reading) -> None:
	"""The optional e-invoice submit: from a known supplier, billed from an
	order, and ready. Off unless the workspace switched it on."""
	if not frappe.db.get_single_value("Intake Settings", "submit_einvoices") or reading.how != "E-invoice":
		return
	made = frappe.db.get_value("Intake Action", {"reading": reading.name, "kind": "Create", "target_doctype": "Purchase Invoice", "level": "Done"}, "target_name")
	if not made:
		return
	doc = frappe.get_doc("Purchase Invoice", made)
	if doc.docstatus != 0 or not any(row.po_detail for row in doc.items) or red(doc, reading):
		return
	from onedesk.one_intake import act

	with act.as_oneai(reading.on_behalf_of):
		if frappe.has_permission("Purchase Invoice", "submit", doc.name):
			doc.submit()
			frappe.db.commit()
