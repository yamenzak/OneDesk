"""Every payment, as a Payment Entry into the bank it was paid to, and petty
cash as a purchase paid in cash on its project.

A receipt the old app linked to an invoice pays that invoice. Most were
not linked, so each is matched within its project and the projects above
and below it, which is where Rua billed one and received the other: first
an open invoice of the same amount, nearest in date; then, what is still
open, oldest invoice first. What no invoice takes is an advance on the
project's order, or on the customer's account when it has none. Every
match and every advance is listed for Rua's accountant.
"""

import frappe
from frappe.utils import flt, getdate

from rua.importer.base import clean, money
from rua.importer.parties import customer_of, supplier_of
from rua.importer.projects import PROJECT, order_of, project_of
from rua.setup import SITE_EXPENSE

PAYMENT = "RUA Payment"
INVOICE = "RUA Invoice"
LPO = "RUA LPO"
BANKS = {
	"adcb": "ADCB",
	"adcbn": "ADCB",
	"nbq": "NBQ",
	"fab": "FAB",
	"mashreq": "Mashreq",
	"cbi": "CBI",
	"adib": "ADIB",
	"emirates islamic bank": "Emirates Islamic Bank",
}
UNNAMED = "Bank Not Recorded"
CURRENT = "Current Account"
SAME = 1.0


def run(run_):
	payments = [one for one in run_.docs(PAYMENT) if one.get("status") == "Submitted"]
	plan = matched(run_, [one for one in payments if one.get("type") == "Receive"])
	for old in sorted(payments, key=lambda one: (one.get("date") or "", one["name"])):
		if old.get("type") == "Receive":
			receive(run_, old, plan.get(old["name"], []))
		elif old.get("type") == "Pay":
			pay(run_, old)
		elif old.get("type") == "Pay: Petty Cash":
			petty(run_, old)


def bank(run_, said):
	"""The ledger for a bank the old app named in free text, one per bank
	however it was spelled, made as OneBook's Add Bank makes one."""
	from onedesk.one_book import ready

	name = BANKS.get(clean(said).lower())
	ledger = f"{name} {CURRENT}" if name else UNNAMED
	found = run_.account(ledger, account_type="Bank")
	if found:
		return found
	if name:
		made = ready.add_bank(name, CURRENT)
		return frappe.db.get_value("Bank Account", made, "account")
	return (
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": UNNAMED,
				"company": run_.company,
				"parent_account": ready.bank_group(run_.company),
				"account_type": "Bank",
				"account_currency": run_.currency,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def family(run_):
	"""Each old project's top project: a job and its parts are one family."""
	parents = {one["name"]: one.get("parent1") for one in run_.docs(PROJECT)}

	def top(name):
		seen = set()
		while parents.get(name) and name not in seen:
			seen.add(name)
			name = parents[name]
		return name

	if not getattr(run_, "family", None):
		run_.family = {name: top(name) for name in parents}
	return run_.family


def matched(run_, receipts):
	"""Which invoices each receipt pays, worked out before anything is made.
	Pure over the old records and the invoices already made."""
	top = family(run_)
	open_ = {}
	for old in run_.docs(INVOICE):
		made = run_.made(INVOICE, old["name"], "Sales Invoice")
		if not made or frappe.db.get_value("Sales Invoice", made, "docstatus") != 1:
			continue
		open_[made] = {
			"family": top.get(old.get("project")),
			"date": getdate(old.get("date")),
			"left": flt(frappe.db.get_value("Sales Invoice", made, "grand_total"), 2),
		}
	plan = {}

	def take(receipt, invoice, amount, how):
		amount = flt(min(amount, open_[invoice]["left"]), 2)
		if amount <= 0:
			return 0
		open_[invoice]["left"] = flt(open_[invoice]["left"] - amount, 2)
		plan.setdefault(receipt["name"], []).append((invoice, amount, how))
		return amount

	left = {}
	for receipt in receipts:
		amount = flt(receipt.get("amount"), 2)
		linked = (
			run_.made(INVOICE, receipt.get("related_docname"), "Sales Invoice")
			if receipt.get("related_docname")
			else None
		)
		if linked in open_:
			amount -= take(receipt, linked, amount, "linked")
		left[receipt["name"]] = amount
	order = sorted(receipts, key=lambda one: (one.get("date") or "", one["name"]))
	for receipt in order:
		if left[receipt["name"]] <= 0:
			continue
		home, when = top.get(receipt.get("project")), getdate(receipt.get("date"))
		same = [
			name
			for name, one in open_.items()
			if one["family"] == home and abs(one["left"] - left[receipt["name"]]) <= SAME and one["left"] > 0
		]
		if same:
			best = min(same, key=lambda name: abs((open_[name]["date"] - when).days))
			left[receipt["name"]] -= take(receipt, best, left[receipt["name"]], "same amount")
	for receipt in order:
		home = top.get(receipt.get("project"))
		for name in sorted(
			(n for n, one in open_.items() if one["family"] == home), key=lambda n: open_[n]["date"]
		):
			if left[receipt["name"]] <= 0:
				break
			left[receipt["name"]] -= take(receipt, name, left[receipt["name"]], "date order")
	return plan


def receive(run_, old, takes):
	if run_.made(PAYMENT, old["name"], "Payment Entry"):
		return
	project = project_of(run_, old.get("project"))
	party = customer_of(run_, old.get("party")) or (
		frappe.db.get_value("Project", project, "customer") if project else None
	)
	if not party:
		run_.note("Left Out", None, None, f"{old['name']}: a receipt with no client")
		return
	amount = money(old.get("amount"))
	references = [
		{"reference_doctype": "Sales Invoice", "reference_name": name, "allocated_amount": part}
		for name, part, _how in takes
	]
	rest = flt(amount - sum(part for _name, part, _how in takes), 2)
	order = order_of(run_, old.get("project")) or order_of(run_, family(run_).get(old.get("project")))
	if rest > 0 and order:
		room = flt(room_on(order), 2)
		if room > 0:
			references.append(
				{
					"reference_doctype": "Sales Order",
					"reference_name": order,
					"allocated_amount": min(rest, room),
				}
			)
	doc = entry(run_, old, "Receive", "Customer", party, amount, project, references)
	run_.remember(PAYMENT, old["name"], "Payment Entry", doc.name)
	for name, part, how in takes:
		if how != "linked":
			run_.note(
				"Receipt Matched",
				"Payment Entry",
				doc.name,
				f"{old['name']} pays {part} of {name}, matched by {how}",
			)
	advance = sum(
		flt(row["allocated_amount"]) for row in references if row["reference_doctype"] == "Sales Order"
	)
	if flt(doc.unallocated_amount) > 0 or advance:
		where = f"on {order}" if advance else "on the customer's account"
		run_.note(
			"Advance Left Open",
			"Payment Entry",
			doc.name,
			f"{old['name']}: {flt(advance or doc.unallocated_amount, 2)} matches no invoice and is an advance {where}",
		)


def room_on(order):
	"""What an order can still take in advance: its total less what has been
	invoiced or paid against it."""
	grand_total, advance = frappe.db.get_value("Sales Order", order, ["grand_total", "advance_paid"])
	billed = flt(
		frappe.db.sql(
			"""select sum(si.grand_total) from `tabSales Invoice` si where si.docstatus = 1 and exists
			(select 1 from `tabSales Invoice Item` i where i.parent = si.name and i.sales_order = %s)""",
			order,
		)[0][0]
	)
	return flt(grand_total) - flt(advance) - billed


def entry(run_, old, kind, party_type, party, amount, project, references):
	account = bank(run_, old.get("bank"))
	doc = frappe.new_doc("Payment Entry")
	doc.update(
		{
			"payment_type": kind,
			"company": run_.company,
			"posting_date": old.get("date"),
			"party_type": party_type,
			"party": party,
			"paid_amount": amount,
			"received_amount": amount,
			"reference_no": clean(old.get("ref_number")) or old["name"],
			"reference_date": old.get("claim_date") or old.get("date"),
			"project": project,
			"remarks": clean(old.get("remarks")) or None,
		}
	)
	if kind == "Receive":
		doc.paid_to = account
	else:
		doc.paid_from = account
	doc.setup_party_account_field()
	doc.set_missing_values()
	doc.paid_amount = doc.received_amount = amount
	for row in references:
		doc.append("references", row)
	doc.set_amounts()
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True, set_name=old["name"])
	doc.submit()
	return doc


def pay(run_, old):
	if run_.made(PAYMENT, old["name"], "Payment Entry"):
		return
	party = supplier_of(run_, old.get("party"))
	if not party:
		run_.note("Left Out", None, None, f"{old['name']}: a payment to a party that isn't a supplier")
		return
	amount = money(old.get("amount"))
	references = []
	lpo = old.get("related_docname") if old.get("related_doctype") == LPO else None
	bill = run_.made(LPO, lpo, "Purchase Invoice") if lpo else None
	order = run_.made(LPO, lpo, "Purchase Order") if lpo else None
	if bill:
		owed = flt(frappe.db.get_value("Purchase Invoice", bill, "outstanding_amount"))
		if owed > 0:
			references.append(
				{
					"reference_doctype": "Purchase Invoice",
					"reference_name": bill,
					"allocated_amount": min(amount, owed),
				}
			)
	elif order and frappe.db.get_value("Purchase Order", order, "docstatus") == 1:
		grand_total, advance = frappe.db.get_value("Purchase Order", order, ["grand_total", "advance_paid"])
		room = flt(grand_total) - flt(advance)
		if room > 0:
			references.append(
				{
					"reference_doctype": "Purchase Order",
					"reference_name": order,
					"allocated_amount": min(amount, room),
				}
			)
	doc = entry(run_, old, "Pay", "Supplier", party, amount, project_of(run_, old.get("project")), references)
	run_.remember(PAYMENT, old["name"], "Payment Entry", doc.name)
	if flt(doc.unallocated_amount) > 0:
		run_.note(
			"Advance Left Open",
			"Payment Entry",
			doc.name,
			f"{old['name']}: {flt(doc.unallocated_amount, 2)} paid beyond the order's bill",
		)


def petty(run_, old):
	"""Cash spent on a site: a purchase paid in cash on the spot, for what was
	paid. The old app kept no tax invoice for it, so no VAT is reclaimed."""
	if run_.made(PAYMENT, old["name"], "Purchase Invoice"):
		return
	party = supplier_of(run_, old.get("party"))
	if not party:
		run_.note("Left Out", None, None, f"{old['name']}: petty cash paid to a party that isn't a supplier")
		return
	cash = frappe.db.get_value("Company", run_.company, "default_cash_account") or run_.account(
		"Cash", account_type="Cash"
	)
	project = project_of(run_, old.get("project"))
	doc = frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"supplier": party,
			"company": run_.company,
			"set_posting_time": 1,
			"posting_date": old.get("date"),
			"due_date": old.get("date"),
			"bill_no": clean(old.get("ref_number")) or None,
			"project": project,
			"is_paid": 1,
			"cash_bank_account": cash,
			"mode_of_payment": "Cash" if frappe.db.exists("Mode of Payment", "Cash") else None,
			"paid_amount": money(old.get("amount")),
			"remarks": clean(old.get("remarks")) or None,
			"items": [
				{
					"item_code": SITE_EXPENSE,
					"qty": 1,
					"rate": money(old.get("amount")),
					"description": clean(old.get("remarks")) or SITE_EXPENSE,
					"project": project,
				}
			],
		}
	)
	doc.flags.dont_auto_add_taxes = True
	doc.insert(ignore_permissions=True, set_name=old["name"])
	doc.submit()
	frappe.db.set_value("Purchase Invoice", doc.name, "taxes_and_charges", None, update_modified=False)
	run_.remember(PAYMENT, old["name"], "Purchase Invoice", doc.name)
