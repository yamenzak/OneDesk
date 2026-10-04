"""Bill Progress: an order billed as the work gets done, less retention.

A **subcontract** is a Purchase Order on the project, one per supplier per
package of work. The customer's contract is their Sales Order. Both are
billed the same way, a share at a time:

- **Bill Progress** (`bill_progress`) asks how far the work has got, as a
  share of the order, and drafts the invoice for what that share comes to
  less what's been billed already. It's ERPNext's own "Create > Invoice" from
  the order with each line's quantity cut to that share, so the order's
  billed amount, its status and the project's figures are ERPNext's. ERPNext
  keeps an invoice at the order's rate, so a share is a part of the quantity:
  a package of work is ordered as 1 **Lump Sum** (`settle`), a unit that can
  be split. A line in a unit that can't is refused in plain words.
- **Retention** is a share of each invoice held back (often 5 to 10%), set
  on the order with the date it's due (`one_retention`, `one_retention_due`).
  The invoice's payment schedule splits in two: the rest, due as usual, and
  **Retention**, a Payment Term of that name due on that date, the share of
  the work billed before tax, whatever advance is set off (`retained`). What's still
  held on an invoice is the retention or what's left to pay on it, whichever
  is smaller, since retention is paid last. Changing the date on the order
  moves it on every invoice made from it (`release`).
- **Advances** paid against the order are set off by ERPNext on each
  invoice (`allocate_advances_automatically`).
- The invoice says the share it's for (**Work Done**, `one_progress`), and
  saving it tells the project's manager to check it (`drafted`).
"""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate

#: How an order is billed: the invoice it makes, ERPNext's own mapper, and the
#: field on an invoice line naming the order line it came from.
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

#: The Payment Term retention is held under, and the unit a package of work
#: is ordered in.
RETENTION = "Retention"
LUMP_SUM = "Lump Sum"


def to_bill(qty: float, billed: float, share: float) -> float:
	"""How much of a line to bill now: the share of it done, less what's been
	billed. Never below nothing. Pure."""
	return max(0.0, flt(qty) * flt(share) / 100 - flt(billed))


def billed_share(lines: list) -> float:
	"""How far an order has been billed, out of 100, by amount. Pure."""
	total = sum(flt(line.amount) for line in lines)
	return round(100 * sum(flt(line.billed_amt) for line in lines) / total, 1) if total else 0.0


def held(retention: float, outstanding: float) -> float:
	"""What's still held on one invoice: retention is paid last, so it's the
	retention or what's left to pay, whichever is smaller. Pure."""
	return max(0.0, min(flt(retention), flt(outstanding)))


@frappe.whitelist()
@frappe.read_only()
def progress(doctype: str, name: str) -> dict:
	"""What Bill Progress asks with: how far the order is billed already."""
	order = _order(doctype, name)
	return {"billed": billed_share(order.items), "retention": flt(order.get("one_retention"))}


@frappe.whitelist(methods=["POST"])
def bill_progress(
	source_name: Annotated[str, "The order."],
	doctype: Annotated[str | None, "Purchase Order or Sales Order."] = None,
	done: Annotated[float | None, "How far the work has got, out of 100."] = None,
):
	"""A draft invoice for the share of the order done and not yet billed, for
	the page to open through frappe.model.open_mapped_doc, which passes the
	doctype and share in its args. Nothing is saved."""
	args = frappe.flags.args or {}
	doctype = doctype or args.get("doctype")
	done = flt(done if done is not None else args.get("done"))
	if doctype not in SIDES:
		frappe.throw(_("Bill Progress is for purchase and sales orders."))
	if not 0 < done <= 100:
		frappe.throw(_("How far the work has got is a share between 1 and 100."))
	order = _order(doctype, source_name)
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
		# The mapper leaves what's not billed yet; the rest is billed.
		qty = to_bill(line.qty, flt(line.qty) - flt(row.qty), done)
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
	invoice.run_method("set_missing_values")
	invoice.run_method("calculate_taxes_and_totals")
	_retain(invoice, order)
	return invoice


def _retain(invoice, order) -> None:
	"""Split the invoice's payment in two when the order holds retention."""
	share = flt(order.get("one_retention"))
	if not share:
		return
	posting = getdate(invoice.get("posting_date") or invoice.get("bill_date"))
	due = getdate(invoice.get("due_date") or posting)
	# Two terms can't fall on one day, and retention comes after the rest.
	release = max(getdate(order.get("one_retention_due") or due), add_days(due, 1))
	total = flt(invoice.get("rounded_total") or invoice.grand_total)
	invoice.payment_terms_template = None
	invoice.ignore_default_payment_terms_template = 1
	invoice.set("payment_schedule", [])
	for term, portion, when in ((None, 100 - share, due), (RETENTION, share, release)):
		invoice.append(
			"payment_schedule",
			{
				"payment_term": term,
				"description": _("Retention") if term else None,
				"due_date": when,
				"invoice_portion": portion,
				"payment_amount": flt(total * portion / 100, 2),
			},
		)


def split(payable: float, net: float, share: float) -> tuple[float, float]:
	"""What's due now and what's retained: the share of the work billed,
	before tax, whatever the advance set off. Pure."""
	retained = max(0.0, min(flt(payable), flt(flt(net) * flt(share) / 100, 2)))
	return flt(payable) - retained, retained


def retained(doc, method=None) -> None:
	"""Purchase/Sales Invoice validate, after ERPNext's own: ERPNext splits
	the payment by share of what's left after advances, so the retention is
	set again as the share of the work billed (`split`)."""
	rows = doc.get("payment_schedule") or []
	held_row = [row for row in rows if row.payment_term == RETENTION]
	if len(rows) != 2 or len(held_row) != 1:
		return
	link = "purchase_order" if doc.doctype == "Purchase Invoice" else "sales_order"
	orders = {row.get(link) for row in doc.items if row.get(link)}
	if len(orders) != 1:
		return
	order_type = "Purchase Order" if doc.doctype == "Purchase Invoice" else "Sales Order"
	share = flt(frappe.db.get_value(order_type, orders.pop(), "one_retention"))
	if not share:
		return
	payable = (
		flt(doc.get("rounded_total") or doc.grand_total)
		- flt(doc.get("write_off_amount"))
		- flt(doc.get("total_advance"))
	)
	now, kept = split(payable, doc.net_total, share)
	rest = rows[0] if rows[1] is held_row[0] else rows[1]
	for row, amount in ((rest, now), (held_row[0], kept)):
		row.payment_amount = amount
		row.invoice_portion = 100 * amount / payable if payable else 0
		row.base_payment_amount = flt(amount * flt(doc.conversion_rate or 1), 2)
		row.outstanding = amount
		row.base_outstanding = row.base_payment_amount


def drafted(doc, method=None) -> None:
	"""Purchase/Sales Invoice after_insert: a bill for a share of the work is
	the project manager's to check (Progress Bill Drafted)."""
	if not doc.get("one_progress"):
		return
	from frappe.utils import fmt_money, get_fullname

	from onedesk.one import notify

	link = "purchase_order" if doc.doctype == "Purchase Invoice" else "sales_order"
	order = next((row.get(link) for row in doc.items if row.get(link)), None)
	project = doc.get("project") or next((row.project for row in doc.items if row.get("project")), None)
	if not project:
		return
	head = frappe.db.get_value("Project", project, ["project_name", "one_manager"], as_dict=True)
	if not head or not head.one_manager:
		return
	notify.notify(
		"Progress Bill Drafted",
		head.one_manager,
		record=(doc.doctype, doc.name),
		who=get_fullname(frappe.session.user),
		share=f"{flt(doc.one_progress):g}",
		order=order or doc.name,
		project=head.project_name,
		party=doc.get("supplier_name") or doc.get("customer_name") or "",
		amount=fmt_money(doc.grand_total, currency=doc.currency),
	)


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
		if rows:
			dates = frappe.get_all(
				"Payment Schedule",
				filters={"parent": invoice, "parenttype": side["invoice"]},
				pluck="due_date",
			)
			frappe.db.set_value(side["invoice"], invoice, "due_date", max(dates))


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
	if not frappe.db.exists("Payment Term", RETENTION):
		frappe.get_doc(
			{
				"doctype": "Payment Term",
				"payment_term_name": RETENTION,
				"description": "Held back until the work is handed over.",
				"due_date_based_on": "Day(s) after invoice date",
				"credit_days": 0,
			}
		).insert(ignore_permissions=True)
