"""What Rua bought: its LPOs as Purchase Orders, the goods received against
them, and its requests for quotation.

Rua never recorded a supplier's bill, so an LPO marked Final, which is the
one the supplier accepted, becomes a Purchase Invoice on its own date. That
puts the material cost on the project, and each one is listed for Rua's
accountant to set against the real bill.

Where an old line's total isn't its quantity times its price (the old app
kept a measured quantity as a whole one), the total is what the supplier
billed: the line keeps its quantity and price, and a Line Difference line
carries the rest.
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
DIFFERENCE = "Line Difference"

#: Requests Rua confirmed were tests in the old app, left out by name.
TESTS = {"RC-RFQ-2500004"}


def rest(qty, price, total) -> float:
	"""What an old line's total says beyond its quantity times its price, or
	nothing when they agree to the fils. Pure."""
	over = flt(total) - flt(qty) * flt(price)
	return round(over, 2) if flt(total) and abs(over) >= 0.01 else 0.0


def lines_of(codes, old, project) -> list[dict]:
	"""An old LPO's lines as an order's, each followed by its Line Difference
	where its total says more or less than its quantity times its price."""
	rows = []
	for one in old.get("items") or []:
		if not flt(one.get("qty")):
			continue
		code = item(codes, one.get("item"), old.get("type"), one.get("description"))
		said = clean(one.get("description")) or clean(one.get("item"))
		rows.append(
			{
				"item_code": code,
				"description": said,
				"qty": flt(one.get("qty")),
				"rate": flt(one.get("unit_price"), 2),
				"schedule_date": old.get("date"),
				"project": project,
			}
		)
		over = rest(one.get("qty"), one.get("unit_price"), one.get("total_amount"))
		if over:
			rows.append(
				{
					"item_code": setup.item(DIFFERENCE, "Nos", "Services"),
					"description": f"{code}: {flt(one.get('qty')):,g} x {flt(one.get('unit_price')):,.2f} "
					f"on the old LPO, whose line total is {flt(one.get('total_amount')):,.2f}",
					"qty": 1,
					"rate": over,
					"schedule_date": old.get("date"),
					"project": project,
				}
			)
	return rows


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
			"items": lines_of(codes, old, project),
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
	if old["name"] in TESTS:
		run_.note("Left Out", None, None, f"{old['name']}: a test in the old app (Majd, 20 Oct 2026)")
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
