"""Retention a client held on an invoice made before One.

Rua held retention on invoices made in Excel and typed only what the client
paid into the old app, so what each client still holds was written nowhere.
Submitting one of these makes the invoice One would have made: the work, all
of it held, nothing billed now and no VAT, the held amount in Retention
Receivable until Release Retention on the project bills it back with VAT.

Where the old app has the invoice for the full work, retention included
(`taken_from`), the retention also comes off that invoice: a credit note for
it and its VAT, so the work is billed once and the VAT is charged when the
retention is released, as One would have done it.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate, today

HELD_BEFORE = "Retention held before One, on an invoice made outside it"


class RetentionBeforeOne(Document):
	def validate(self):
		from onedesk.one_project import retention

		if not retention.on():
			frappe.throw(_("Turn retention on in Projects Settings first."))
		if flt(self.amount) <= 0:
			frappe.throw(_("Say how much retention the client holds, before VAT."))
		self.customer = frappe.db.get_value("Project", self.project, "customer")
		if not self.customer:
			frappe.throw(_("{0} has no customer to hold the retention.").format(self.project))
		if self.taken_from:
			taken = frappe.db.get_value(
				"Sales Invoice",
				self.taken_from,
				["customer", "docstatus", "is_return", "net_total"],
				as_dict=True,
			)
			if not taken or taken.docstatus != 1 or taken.is_return or taken.customer != self.customer:
				frappe.throw(
					_("{0} is not an invoice to {1} on this project.").format(self.taken_from, self.customer)
				)
			if flt(self.amount) > flt(taken.net_total):
				frappe.throw(_("{0} is for less than the retention, before VAT.").format(self.taken_from))

	def on_submit(self):
		invoice = frappe.get_doc(held_invoice(self))
		invoice.flags.ignore_permissions = True
		invoice.insert()
		invoice.submit()
		self.db_set("sales_invoice", invoice.name)
		if self.taken_from:
			credit = frappe.get_doc(credit_note(self))
			credit.flags.ignore_permissions = True
			credit.insert()
			credit.submit()
			self.db_set("credit_note", credit.name)

	def on_cancel(self):
		for name in (self.credit_note, self.sales_invoice):
			if name and frappe.db.get_value("Sales Invoice", name, "docstatus") == 1:
				invoice = frappe.get_doc("Sales Invoice", name)
				invoice.flags.ignore_permissions = True
				invoice.cancel()


def held_invoice(doc) -> dict:
	"""The invoice for retention held outside One: one line of the work, all
	of it held. Due back on `due_back`, which One's retention reads as the day
	after the invoice falls due."""
	from onedesk.one_project.kinds import CONTRACT_ITEM

	company = frappe.db.get_value("Project", doc.project, "company") or frappe.db.get_default("company")
	back = getdate(doc.due_back) if doc.due_back else None
	return {
		"doctype": "Sales Invoice",
		"customer": doc.customer,
		"company": company,
		"set_posting_time": 1,
		"posting_date": today(),
		"due_date": str(add_days(back, -1)) if back and back > getdate(today()) else today(),
		"one_retention": 100,
		"remarks": "\n".join(filter(None, [HELD_BEFORE, doc.note])),
		"items": [
			{
				"item_code": CONTRACT_ITEM,
				"qty": 1,
				"rate": flt(doc.amount, 2),
				"project": doc.project,
				"description": HELD_BEFORE,
			}
		],
	}


TAKEN_OFF = "Retention held on this invoice, held until it is released"


def credit_note(doc) -> dict:
	"""The retention off the invoice for the full work: one line of the work
	for the held amount, and the invoice's VAT on it, which Release Retention
	charges again when it bills the retention."""
	from onedesk.one_project.kinds import CONTRACT_ITEM

	taken = frappe.get_doc("Sales Invoice", doc.taken_from)
	return {
		"doctype": "Sales Invoice",
		"is_return": 1,
		"return_against": taken.name,
		"customer": taken.customer,
		"company": taken.company,
		"set_posting_time": 1,
		"posting_date": today(),
		"remarks": "\n".join(filter(None, [TAKEN_OFF, doc.note])),
		"items": [
			{
				"item_code": CONTRACT_ITEM,
				"qty": -1,
				"rate": flt(doc.amount, 2),
				"project": doc.project,
				"description": TAKEN_OFF,
			}
		],
		"taxes": [
			{
				"charge_type": "On Net Total",
				"account_head": tax.account_head,
				"description": tax.description,
				"rate": tax.rate,
				"cost_center": tax.cost_center,
				"included_in_print_rate": 0,
			}
			for tax in taken.taxes
			if tax.charge_type == "On Net Total"
		],
	}
