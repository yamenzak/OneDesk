"""Rua's claims, as submitted Sales Invoices against the project's contract,
each keeping its old number and its claim number in the project. A proforma
asked for money without booking it: it is a Payment Request on the order.

The old invoice had no lines, only an amount: it becomes one line of the
contract item. VAT is 5%, in the amount or on top as the old one said, so
the total is the old total to the fils.
"""

import frappe
from frappe.utils import cint, flt

from rua.importer.base import money
from rua.importer.parties import customer_of
from rua.importer.projects import order_of, project_of, taxes

INVOICE = "RUA Invoice"


def run(run_):
	from onedesk.one_project.kinds import CONTRACT_ITEM

	for old in sorted(run_.docs(INVOICE), key=lambda one: (one.get("date") or "", one["name"])):
		if old.get("status") in ("Draft", "Cancelled"):
			continue
		if old.get("type") == "Tax Invoice":
			invoice(run_, old, CONTRACT_ITEM)
		elif old.get("type") == "Proforma":
			proforma(run_, old)


def customer(run_, old):
	project = project_of(run_, old.get("project"))
	return customer_of(run_, old.get("party")) or (
		frappe.db.get_value("Project", project, "customer") if project else None
	)


def invoice(run_, old, item):
	if run_.made(INVOICE, old["name"], "Sales Invoice"):
		return
	party = customer(run_, old)
	if not party:
		run_.note("Left Out", None, None, f"{old['name']}: an invoice with no client")
		return
	project = project_of(run_, old.get("project"))
	order = order_of(run_, old.get("project"))
	share = held(old)
	inclusive = cint(old.get("is_vat_inclusive")) and not share
	template, rows = taxes(run_, inclusive=inclusive)
	line = {
		"item_code": item,
		"qty": 1,
		"rate": money(old.get("grand_total") if inclusive else old.get("amount")),
		"description": (old.get("print_remarks") or old.get("remarks") or "").strip() or None,
		"project": project,
	}
	if order:
		line["sales_order"] = order
		line["so_detail"] = frappe.db.get_value("Sales Order Item", {"parent": order}, "name")
	doc = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": party,
			"company": run_.company,
			"set_posting_time": 1,
			"posting_date": old.get("date"),
			"due_date": old.get("date"),
			"project": project,
			"taxes_and_charges": template,
			"taxes": rows,
			"disable_rounded_total": 1,
			"one_claim": cint(old.get("serial_number")) or None,
			"one_retention": share,
			"remarks": (old.get("remarks") or "").strip() or None,
			"items": [line],
		}
	)
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True, set_name=old["name"])
	if old.get("status") == "Final":
		doc.submit()
	else:
		run_.note(
			"To Check",
			"Sales Invoice",
			doc.name,
			f"{old['name']} was never made final in the old app: it is a draft here",
		)
	run_.remember(INVOICE, old["name"], "Sales Invoice", doc.name)


def held(old) -> float:
	"""The share of the work the old invoice held back, in percent: its
	retention field was never filled, but its amounts say it. Pure."""
	amount, after = flt(old.get("amount")), flt(old.get("amount_after_retention"))
	if amount <= 0 or after <= 0 or after >= amount - 0.01:
		return flt(old.get("retention_percentage"))
	return flt(100 * (amount - after) / amount, 4)


def proforma(run_, old):
	if run_.made(INVOICE, old["name"], "Payment Request"):
		return
	order = order_of(run_, old.get("project"))
	party = customer(run_, old)
	if not order or not party:
		run_.note("Left Out", None, None, f"{old['name']}: a proforma on a project with no contract")
		return
	doc = frappe.get_doc(
		{
			"doctype": "Payment Request",
			"payment_request_type": "Inward",
			"transaction_date": old.get("date"),
			"company": run_.company,
			"party_type": "Customer",
			"party": party,
			"reference_doctype": "Sales Order",
			"reference_name": order,
			"grand_total": money(old.get("grand_total")),
			"currency": run_.currency,
			"mute_email": 1,
			"subject": old["name"],
			"message": (old.get("print_remarks") or old.get("remarks") or "").strip() or None,
		}
	)
	doc.flags.mute_email = True
	frappe.db.savepoint("rua_proforma")
	try:
		doc.insert(ignore_permissions=True, set_name=old["name"])
		doc.submit()
	except frappe.ValidationError as error:
		frappe.db.rollback(save_point="rua_proforma")
		run_.note(
			"Left Out", "Sales Order", order, f"{old['name']}: {frappe.utils.strip_html(str(error))[:300]}"
		)
		return
	run_.remember(INVOICE, old["name"], "Payment Request", doc.name)


def total(name):
	return flt(frappe.db.get_value("Sales Invoice", name, "grand_total"))
