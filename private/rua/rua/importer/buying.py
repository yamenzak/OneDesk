"""What Rua bought: its LPOs as Purchase Orders, the goods received against
them, and its requests for quotation.

Rua never recorded a supplier's bill, so an LPO marked Final, which is the
one the supplier accepted, becomes a Purchase Invoice on its own date. That
puts the material cost on the project, and each one is listed for Rua's
accountant to set against the real bill.
"""

import frappe
from frappe.utils import flt

from rua import setup
from rua.importer.base import clean
from rua.importer.parties import supplier_of
from rua.importer.projects import project_of, taxes
from rua.importer.quotations import millimetres

LPO = "RUA LPO"
RFQ = "RUA RFQ"
RECEIPT = "RUA Purchase Receipt"
GROUPS = {"Aluminum": "Aluminium", "Glass": "Glass", "Material": "Materials", "Cladding": "Cladding"}


def run(run_):
	codes = {}
	for old in run_.docs(LPO):
		order(run_, old, codes)
	for old in run_.docs(RECEIPT):
		received(run_, old)
	for old in run_.docs(RFQ):
		requested(run_, old, codes)


def item(codes, name, kind=None, description=None):
	"""The item a line names, made the first time it's named, one per name
	whatever its capitals."""
	name = clean(name)[:140] or "Material"
	key = name.lower()
	if key not in codes:
		found = frappe.db.get_value("Item", {"item_code": name}) or frappe.db.get_value(
			"Item", {"item_name": name}
		)
		codes[key] = found or setup.item(
			name, "Nos", GROUPS.get(kind or "", "Materials"), description=clean(description) or name
		)
	return codes[key]


def order(run_, old, codes):
	if run_.made(LPO, old["name"], "Purchase Order") or old.get("status") == "Cancelled":
		return
	supplier = supplier_of(run_, old.get("party"))
	lines = [one for one in old.get("items") or [] if flt(one.get("qty"))]
	if not supplier or not lines:
		run_.note("Left Out", None, None, f"{old['name']}: an LPO with no supplier or no lines")
		return
	template, rows = taxes(run_, inclusive=False, doctype="Purchase Taxes and Charges Template")
	project = project_of(run_, old.get("project"))
	doc = frappe.get_doc(
		{
			"doctype": "Purchase Order",
			"supplier": supplier,
			"company": run_.company,
			"transaction_date": old.get("date"),
			"schedule_date": old.get("date"),
			"project": project,
			"taxes_and_charges": template,
			"taxes": rows,
			"items": [
				{
					"item_code": item(codes, one.get("item"), old.get("type"), one.get("description")),
					"description": clean(one.get("description")) or clean(one.get("item")),
					"qty": flt(one.get("qty")),
					"rate": flt(one.get("unit_price"), 2),
					"schedule_date": old.get("date"),
					"project": project,
				}
				for one in lines
			],
		}
	)
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True, set_name=old["name"])
	if old.get("status") in ("Submitted", "Final"):
		doc.submit()
	run_.remember(LPO, old["name"], "Purchase Order", doc.name)
	if old.get("status") == "Final":
		bill(run_, old, doc)


def bill(run_, old, po):
	"""The supplier's bill, as the accepted LPO says it will be."""
	from erpnext.buying.doctype.purchase_order.mapper import make_purchase_invoice

	if run_.made(LPO, old["name"], "Purchase Invoice"):
		return
	doc = make_purchase_invoice(po.name)
	doc.update(
		{
			"set_posting_time": 1,
			"posting_date": old.get("date"),
			"bill_date": old.get("date"),
			"due_date": old.get("date"),
			"bill_no": clean(old.get("supplier_reference_number")) or None,
		}
	)
	doc.payment_schedule = []
	doc.insert(ignore_permissions=True)
	doc.submit()
	run_.remember(LPO, old["name"], "Purchase Invoice", doc.name)
	run_.note(
		"Bill From Order",
		"Purchase Invoice",
		doc.name,
		f"Made from {old['name']} for {flt(doc.grand_total, 2)}. Set it against the supplier's real bill.",
	)


def received(run_, old):
	from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt

	if run_.made(RECEIPT, old["name"], "Purchase Receipt") or old.get("status") != "Received":
		return
	po = run_.made(LPO, old.get("purchase_order"), "Purchase Order")
	if not po or frappe.db.get_value("Purchase Order", po, "docstatus") != 1:
		run_.note("Left Out", None, None, f"{old['name']}: a receipt against an LPO that isn't ordered")
		return
	doc = make_purchase_receipt(po)
	got = {
		clean(one.get("item")).lower(): flt(one.get("received_quantity")) for one in old.get("items") or []
	}
	for row in doc.items:
		row.qty = got.get((row.item_code or "").lower(), row.qty)
		row.received_qty = row.qty
	doc.items = [row for row in doc.items if row.qty]
	doc.update(
		{
			"set_posting_time": 1,
			"posting_date": old.get("date"),
			"supplier_delivery_note": clean(old.get("supplier_delivery_note")) or None,
		}
	)
	frappe.db.savepoint("rua_receipt")
	try:
		doc.insert(ignore_permissions=True, set_name=old["name"])
		doc.submit()
	except frappe.ValidationError as error:
		frappe.db.rollback(save_point="rua_receipt")
		run_.note(
			"Left Out", "Purchase Order", po, f"{old['name']}: {frappe.utils.strip_html(str(error))[:300]}"
		)
		return
	run_.remember(RECEIPT, old["name"], "Purchase Receipt", doc.name)


def requested(run_, old, codes):
	if run_.made(RFQ, old["name"], "Request for Quotation"):
		return
	supplier = supplier_of(run_, old.get("party"))
	lines = [one for one in old.get("items") or [] if flt(one.get("qty"))]
	if not supplier or not lines:
		run_.note(
			"Left Out", None, None, f"{old['name']}: a request for quotation with no supplier or no lines"
		)
		return
	rows = []
	for one in lines:
		row = {
			"item_code": item(codes, one.get("item"), old.get("type"), one.get("description")),
			"description": clean(one.get("description")) or clean(one.get("item")),
			"qty": flt(one.get("qty")),
			"conversion_factor": 1,
			"schedule_date": old.get("date"),
			"project_name": project_of(run_, old.get("project")),
		}
		length = millimetres(f"{one.get('length') or ''} {unit(one.get('measurement_unit'))}")
		if length:
			row.update(
				{
					"one_measured_by": "Piece",
					"one_length": length,
					"one_width": millimetres(f"{one.get('width') or ''} {unit(one.get('measurement_unit'))}"),
				}
			)
		rows.append(row)
	doc = frappe.get_doc(
		{
			"doctype": "Request for Quotation",
			"company": run_.company,
			"transaction_date": old.get("date"),
			"schedule_date": old.get("date"),
			"suppliers": [{"supplier": supplier, "send_email": 0}],
			"items": rows,
		}
	)
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True, set_name=old["name"])
	if old.get("status") != "Draft":
		doc.submit()
	run_.remember(RFQ, old["name"], "Request for Quotation", doc.name)


def unit(said):
	return {"meters": "m", "meter": "m", "cm": "cm", "mm": "mm"}.get(clean(said).lower(), "m" if said else "")
