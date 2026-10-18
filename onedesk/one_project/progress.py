"""Bill Progress: an order billed as the work gets done, less retention."""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate, strip_html

from onedesk.one_project import retention, terms
from onedesk.one_project.retention import HANDOVER, HELD, RETENTION, parts

SIDES = {
	"Purchase Order": {
		"invoice": "Purchase Invoice",
		"make": "erpnext.buying.doctype.purchase_order.mapper.make_purchase_invoice",
		"detail": "po_detail",
	},
	"Sales Order": {
		"invoice": "Sales Invoice",
		"make": "erpnext.selling.doctype.sales_order.mapper.make_sales_invoice",
		"detail": "so_detail",
	},
}

LUMP_SUM = "Lump Sum"


def to_bill(qty: float, billed: float, share: float) -> float:
	"""How much of a line to bill now: the share of it done, less what's been
	billed. Never below nothing. Pure."""
	return max(0.0, flt(qty) * flt(share) / 100 - flt(billed))


def billed_share(lines: list) -> float:
	"""How far an order has been billed, out of 100, by amount. Pure."""
	total = sum(flt(line.amount) for line in lines)
	return round(100 * sum(flt(line.billed_amt) for line in lines) / total, 1) if total else 0.0


@frappe.whitelist()
@frappe.read_only()
def progress(doctype: str, name: str) -> dict:
	"""What Bill Progress asks with: how far the order is billed already, as
	a whole and line by line."""
	order = _order(doctype, name)
	return {
		"billed": billed_share(order.items),
		"retention": flt(order.get("one_retention")),
		"lines": [
			{
				"line": line.name,
				"item": strip_html(line.description or "").strip() or line.item_name or line.item_code,
				"ordered": f"{flt(line.qty):g} {line.uom or ''}".strip(),
				"billed": round(100 * flt(line.billed_amt) / flt(line.amount), 1)
				if flt(line.amount)
				else 0.0,
			}
			for line in order.items
		],
	}


def overall(lines: list, done: dict) -> float:
	"""How far an order is done as a whole, by amount, when each line has
	its own share done. Pure."""
	total = sum(flt(line.amount) for line in lines)
	worth = sum(flt(line.amount) * flt(done.get(line.name)) / 100 for line in lines)
	return round(100 * worth / total, 2) if total else 0.0


@frappe.whitelist(methods=["POST"])
def bill_progress(
	source_name: Annotated[str, "The order."],
	doctype: Annotated[str | None, "Purchase Order or Sales Order."] = None,
	done: Annotated[float | None, "How far the work has got, out of 100."] = None,
	lines: Annotated[dict | str | None, "How far each order line has got, out of 100, by line."] = None,
):
	"""A draft invoice for the share of the order done and not yet billed, for
	the page to open through frappe.model.open_mapped_doc, which passes the
	doctype and share in its args. Each line may have its own share done
	(`lines`), as work measured against a bill of quantities is: 120 of 400 m²
	of tiling and 80% of the glazing. Nothing is saved."""
	args = frappe.flags.args or {}
	doctype = doctype or args.get("doctype")
	shares = frappe.parse_json(lines if lines is not None else args.get("lines")) or None
	if doctype not in SIDES:
		frappe.throw(_("Bill Progress is for purchase and sales orders."))
	order = _order(doctype, source_name)
	if shares:
		shares = {key: flt(value) for key, value in shares.items()}
		if any(not 0 <= value <= 100 for value in shares.values()) or not any(shares.values()):
			frappe.throw(_("Give each line a share done between 0 and 100, and at least one above 0."))
		done = overall(order.items, shares)
	else:
		done = flt(done if done is not None else args.get("done"))
		if not 0 < done <= 100:
			frappe.throw(_("Give each line a share done between 0 and 100, and at least one above 0."))
	side = SIDES[doctype]
	frappe.has_permission(side["invoice"], "create", throw=True)

	invoice = frappe.get_attr(side["make"])(source_name)
	lines = {line.name: line for line in order.items}
	whole = set(frappe.get_all("UOM", filters={"must_be_whole_number": 1}, pluck="name"))
	kept = []
	for row in invoice.items:
		line = lines.get(row.get(side["detail"]))
		if not line:
			continue
		qty = to_bill(line.qty, flt(line.qty) - flt(row.qty), shares.get(line.name, 0) if shares else done)
		qty = flt(qty, row.precision("qty"))
		if qty <= 0:
			continue
		if row.uom in whole and qty != int(qty):
			frappe.throw(
				_("Bill Progress can't bill part of a {0}. Order {1} in {2} to bill it in parts.").format(
					row.uom, row.item_name or row.item_code, LUMP_SUM
				)
			)
		row.qty = qty
		row.stock_qty = qty * flt(row.conversion_factor or 1)
		kept.append(row)
	if not kept:
		frappe.throw(_("{0} is billed up to {1}% already.").format(order.name, billed_share(order.items)))
	invoice.set("items", kept)
	invoice.one_progress = done
	invoice.allocate_advances_automatically = 1
	terms.give(invoice, order.get("payment_terms_template"), None if invoice.get("tc_name") else order.get("tc_name"))
	invoice.run_method("set_missing_values")
	invoice.run_method("calculate_taxes_and_totals")
	_retain(invoice, order)
	return invoice


def _retain(invoice, order) -> None:
	"""The invoice holds its order's retention: the rest now, any part
	released at handover, and the rest at Retention Due (`retained`)."""
	invoice.one_retention = flt(order.get("one_retention"))
	if not invoice.one_retention:
		return
	if retention.when_released():
		withhold(invoice, _terms_of(order), invoice.one_retention)
		return
	invoice.payment_terms_template = None
	invoice.ignore_default_payment_terms_template = 1
	total = flt(invoice.get("rounded_total") or invoice.grand_total)
	due = getdate(invoice.get("due_date") or invoice.get("posting_date") or invoice.get("bill_date"))
	invoice.set("payment_schedule", [])
	invoice.append("payment_schedule", {"due_date": due, "invoice_portion": 100, "payment_amount": total})
	_hold(invoice, _terms_of(order), invoice.one_retention)


def _terms_of(source) -> frappe._dict:
	"""An order's or a project's retention terms, named alike: the handover
	share, Retention Due and when the work ends."""
	return frappe._dict(
		retention=flt(source.get("one_retention")),
		handover=flt(source.get("one_retention_handover")),
		due=source.get("one_retention_due"),
		ends=source.get("delivery_date") or source.get("schedule_date") or source.get("expected_end_date"),
	)


def source(doc) -> frappe._dict | None:
	"""Where an invoice's retention terms come from: the one order it's
	made from, or else the customer's project."""
	link = "purchase_order" if doc.doctype == "Purchase Invoice" else "sales_order"
	orders = {row.get(link) for row in doc.get("items") or [] if row.get(link)}
	if len(orders) == 1:
		order_type = "Purchase Order" if doc.doctype == "Purchase Invoice" else "Sales Order"
		ends = "schedule_date" if order_type == "Purchase Order" else "delivery_date"
		order = frappe.db.get_value(
			order_type,
			orders.pop(),
			["one_retention", "one_retention_handover", "one_retention_due", ends],
			as_dict=True,
		)
		return _terms_of(order) if order else None
	if doc.doctype != "Sales Invoice":
		return None
	project = doc.get("project") or next((row.project for row in doc.get("items") or [] if row.get("project")), None)
	if not project:
		return None
	found = frappe.db.get_value(
		"Project",
		project,
		["one_retention", "one_retention_handover", "one_retention_due", "expected_end_date"],
		as_dict=True,
	)
	return _terms_of(found) if found else None


def _hold(doc, said, share: float) -> None:
	"""Add the retention's payment terms after the invoice's own: released
	at handover when the work ends, and the rest at Retention Due. Two terms
	can't fall on one day, so each comes after the one before."""
	said = said or frappe._dict()
	due = max(getdate(row.due_date) for row in doc.payment_schedule)
	split_at = [term for term, _portion in parts(share, said.handover) if term]
	dates = released_on(due, said, split_at)
	for term in split_at:
		doc.append(
			"payment_schedule",
			{
				"payment_term": term,
				"description": {HANDOVER: _("Retention at Handover"), RETENTION: _("Retention")}[term],
				"due_date": dates[term],
				"invoice_portion": 0,
				"payment_amount": 0,
			},
		)


def released_on(due, said, split_at: list[str]) -> dict:
	"""When each part of the retention falls due: the handover part when the
	work ends, the rest at Retention Due, each after the invoice's own
	payments and the one before it. Pure."""
	handover = max(getdate(said.ends), add_days(due, 1)) if said.ends else add_days(due, 1)
	after = add_days(handover, 1) if HANDOVER in split_at else add_days(due, 1)
	release = max(getdate(said.due), after) if said.due else after
	return {HANDOVER: handover, RETENTION: release}


def withheld(net: float, share: float, handover: float) -> list[tuple[str, float]]:
	"""Retention taxed when released: what each part holds back of the work
	billed, before tax, to the cent, the last part taking what rounding
	leaves. Pure."""
	kept = flt(flt(net) * flt(share) / 100, 2)
	split_at = [(term, portion) for term, portion in parts(share, handover) if term]
	amounts = spread(kept, [portion for _term, portion in split_at])
	return [(term, amount) for (term, _portion), amount in zip(split_at, amounts, strict=True) if amount > 0]


def withhold(doc, said, share: float) -> None:
	"""Retention taxed when released: the invoice holds it as Retention lines
	below nothing, one for each part, so its tax is on the work less the
	retention and what's held is booked to Retention Receivable (Payable on
	a bill) until the invoice releasing it. Its payment schedule is ERPNext's
	own, for what the invoice asks now."""
	said = said or frappe._dict()
	work = [row for row in doc.items if not row.get("one_held")]
	had = {row.one_held: row for row in doc.items if row.get("one_held")}
	doc.set("payment_schedule", [row for row in doc.get("payment_schedule") or [] if row.payment_term not in HELD])
	sign = -1 if doc.get("is_return") else 1
	if sign < 0:
		had = {}
	held = withheld(sign * sum(flt(row.net_amount or row.amount) for row in work), share, said.handover)
	due = getdate(doc.get("due_date") or doc.get("posting_date") or doc.get("bill_date") or nowdate())
	dates = released_on(due, said, [term for term, _amount in held])
	first = work[0] if work else frappe._dict()
	unit = frappe.get_cached_value("Item", retention.ITEM, "stock_uom")
	lines = []
	for term, amount in held:
		row = had.get(term) or frappe._dict(
			item_code=retention.ITEM if sign > 0 else None,
			item_name=retention.ITEM,
			description=_("Retention at Handover") if term == HANDOVER else _("Retention"),
			qty=sign,
			uom=unit,
			stock_uom=unit,
			conversion_factor=1,
			one_held=term,
			one_release_on=dates[term],
			project=first.get("project") or doc.get("project"),
			cost_center=first.get("cost_center") or doc.get("cost_center"),
		)
		row.update({"qty": sign, "rate": -amount, "price_list_rate": -amount, "discount_percentage": 0, "discount_amount": 0})
		lines.append(row)
	doc.set("items", work + lines)
	for idx, row in enumerate(doc.items, start=1):
		row.idx = idx
	retention.book(doc)
	doc.run_method("calculate_taxes_and_totals")
	_said(doc, work=sum(flt(row.net_amount) for row in work) if lines else 0, held=sign * sum(amount for _term, amount in held))
	if doc.docstatus == 0 and not doc.get("is_pos") and not doc.get("is_return"):
		from erpnext.accounts.services.payment_schedule import PaymentScheduleService

		doc.set("payment_schedule", [])
		PaymentScheduleService(doc).set_payment_schedule()


def returned(doc) -> None:
	"""A credit note against an invoice holding Retention lines gives back
	the retention on the work it takes back, at the invoice's rate, so what's
	still held, and what Retention Receivable says, come down with it. One
	against an invoice holding retention in its payment terms needs nothing:
	ERPNext sets it against what the invoice owes."""
	against = doc.get("return_against")
	if not against or not frappe.db.exists(f"{doc.doctype} Item", {"parent": against, "one_held": ["is", "set"]}):
		return
	share = flt(frappe.db.get_value(doc.doctype, against, "one_retention"))
	doc.one_retention = share
	withhold(doc, source(doc), share)


def _said(doc, work: float = 0, held: float = 0, now: float = 0) -> None:
	"""What the printed totals say of the retention: taxed when released, the
	work billed and the retention taken off it before tax; with the invoice,
	the retention held and what's due now."""
	doc.one_work_billed = work
	doc.one_retention_held = held
	doc.one_due_now = now


def split(payable: float, net: float, share: float) -> tuple[float, float]:
	"""What's due now and what's retained: the share of the work billed,
	before tax, whatever the advance set off. Pure."""
	retained = max(0.0, min(flt(payable), flt(flt(net) * flt(share) / 100, 2)))
	return flt(payable) - retained, retained


def spread(amount: float, weights: list[float]) -> list[float]:
	"""An amount over parts in the proportions given, to the cent, the last
	part taking what rounding leaves. Pure."""
	whole = sum(weights)
	if not weights:
		return []
	found = [flt(amount * (weight / whole if whole else 1 / len(weights)), 2) for weight in weights[:-1]]
	return [*found, flt(amount - sum(found), 2)]


def retained(doc, method=None) -> None:
	"""Purchase/Sales Invoice validate, after ERPNext's own: the invoice
	holds its own Retention, which starts as its order's (or its project's)
	and may be changed, or set to 0, before it's submitted. The retention is
	the share of the work billed (`split`), held as payment terms after the
	invoice's own, and divided between handover and the rest as the order
	says. ERPNext keeps the invoice in Debtors or Creditors whole, so what's
	held stays owed, and a payment for it is matched to its terms."""
	if doc.get("is_pos") or doc.get("is_opening") == "Yes":
		return
	if any(row.get("one_retention_of") for row in doc.get("items") or []):
		return
	if doc.get("is_return"):
		returned(doc)
		return
	rows = doc.get("payment_schedule") or []
	lines = [row for row in doc.get("items") or [] if row.get("one_held")]
	if not rows and not lines:
		return
	said = source(doc)
	if doc.get("one_retention") is None:
		doc.one_retention = said.retention if said else 0
	share = flt(doc.one_retention)
	if lines or (share and retention.when_released()):
		withhold(doc, said, share)
		return
	held_rows = [row for row in rows if row.payment_term in HELD]
	if not share and not held_rows:
		_said(doc)
		return
	if share and not held_rows:
		_hold(doc, said, share)
	elif not share:
		for row in held_rows:
			doc.remove(row)
	payable = (
		flt(doc.get("rounded_total") or doc.grand_total)
		- flt(doc.get("write_off_amount"))
		- flt(doc.get("total_advance"))
	)
	now, kept = split(payable, doc.net_total, share)
	_said(doc, held=kept, now=now)
	rows = doc.payment_schedule
	own = [row for row in rows if row.payment_term not in HELD]
	held_rows = [row for row in rows if row.payment_term in HELD]
	first = (
		flt(kept * min(100.0, flt(said.handover if said else 0)) / 100, 2)
		if len(held_rows) == 2
		else 0
	)
	if not own:
		own = [doc.append("payment_schedule", {"due_date": doc.get("posting_date") or doc.get("bill_date"), "payment_amount": 0})]
		rows = doc.payment_schedule
	amounts = {id(row): amount for row, amount in zip(own, spread(now, [flt(row.payment_amount) for row in own]), strict=True)}
	for row in held_rows:
		amounts[id(row)] = {HANDOVER: first, RETENTION: kept - first}[row.payment_term] if len(held_rows) == 2 else kept
	for row in rows:
		amount = amounts[id(row)]
		row.payment_amount = amount
		row.invoice_portion = 100 * amount / payable if payable else 0
		row.base_payment_amount = flt(amount * flt(doc.conversion_rate or 1), 2)
		row.outstanding = amount
		row.base_outstanding = row.base_payment_amount
	rows.sort(key=lambda row: getdate(row.due_date))
	for idx, row in enumerate(rows, start=1):
		row.idx = idx
	doc.due_date = max(getdate(row.due_date) for row in rows)


def drafted(doc, method=None) -> None:
	"""Purchase/Sales Invoice after_insert: a bill for a share of the work is
	the project manager's to check (Progress Bill Drafted)."""
	if not doc.get("one_progress"):
		return
	from onedesk.one_project import tell

	link = "purchase_order" if doc.doctype == "Purchase Invoice" else "sales_order"
	order = next((row.get(link) for row in doc.items if row.get(link)), None)
	project = doc.get("project") or next((row.project for row in doc.items if row.get("project")), None)
	if not project:
		return
	tell.progress_drafted(doc, project, order)


def release(doc, method=None) -> None:
	"""Purchase/Sales Order on_update_after_submit: a new Retention Due moves
	the retention on every invoice made from the order."""
	if (
		doc.doctype not in SIDES
		or not doc.get("one_retention_due")
		or not doc.has_value_changed("one_retention_due")
	):
		return
	side = SIDES[doc.doctype]
	link = "purchase_order" if doc.doctype == "Purchase Order" else "sales_order"
	invoices = set(
		frappe.get_all(f"{side['invoice']} Item", filters={link: doc.name, "docstatus": 1}, pluck="parent")
	)
	for invoice in invoices:
		rows = frappe.get_all(
			"Payment Schedule",
			filters={"parent": invoice, "parenttype": side["invoice"], "payment_term": RETENTION},
			pluck="name",
		)
		for row in rows:
			frappe.db.set_value("Payment Schedule", row, "due_date", doc.one_retention_due)
		frappe.db.set_value(
			f"{side['invoice']} Item",
			{"parent": invoice, "one_held": RETENTION},
			"one_release_on",
			doc.one_retention_due,
		)
		if rows:
			dates = frappe.get_all(
				"Payment Schedule",
				filters={"parent": invoice, "parenttype": side["invoice"]},
				pluck="due_date",
			)
			_due(side["invoice"], invoice, max(dates))


def _due(doctype: str, invoice: str, due) -> None:
	"""A submitted invoice's due date, moved everywhere ERPNext keeps it: the
	invoice, and its own lines in the payment and general ledgers, which the
	receivables and payables reports age by."""
	frappe.db.set_value(doctype, invoice, "due_date", due)
	for ledger in ("Payment Ledger Entry", "GL Entry"):
		frappe.db.set_value(
			ledger,
			{"voucher_type": doctype, "voucher_no": invoice, "due_date": ["is", "set"]},
			"due_date",
			due,
			update_modified=False,
		)


def _order(doctype: str, name: str):
	if doctype not in SIDES:
		frappe.throw(_("Bill Progress is for purchase and sales orders."))
	order = frappe.get_doc(doctype, name)
	order.check_permission("read")
	if order.docstatus != 1 or order.status in ("Closed", "On Hold", "Completed"):
		frappe.throw(_("Only a submitted order still open can be billed."))
	return order


def settle() -> None:
	"""The unit a package of work is ordered in, and the term retention is
	held under. Made once; the workspace may change them after."""
	if not frappe.db.exists("UOM", LUMP_SUM):
		frappe.get_doc({"doctype": "UOM", "uom_name": LUMP_SUM, "must_be_whole_number": 0}).insert(
			ignore_permissions=True
		)
	for term, said in (
		(RETENTION, "Held back until the work has proved sound."),
		(HANDOVER, "Held back until the work is handed over."),
	):
		if not frappe.db.exists("Payment Term", term):
			frappe.get_doc(
				{
					"doctype": "Payment Term",
					"payment_term_name": term,
					"description": said,
					"due_date_based_on": "Day(s) after invoice date",
					"credit_days": 0,
				}
			).insert(ignore_permissions=True)
