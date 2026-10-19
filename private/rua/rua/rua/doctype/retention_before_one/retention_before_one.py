"""Retention a client held on an invoice made before One.

Rua held retention on invoices made in Excel and typed only what the client
paid into the old app, so what each client still holds was written nowhere.
Submitting one of these makes the invoice One would have made: the work, all
of it held, nothing billed now and no VAT, the held amount in Retention
Receivable until Release Retention on the project bills it back with VAT.
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

	def on_submit(self):
		invoice = frappe.get_doc(held_invoice(self))
		invoice.flags.ignore_permissions = True
		invoice.insert()
		invoice.submit()
		self.db_set("sales_invoice", invoice.name)

	def on_cancel(self):
		if self.sales_invoice and frappe.db.get_value("Sales Invoice", self.sales_invoice, "docstatus") == 1:
			invoice = frappe.get_doc("Sales Invoice", self.sales_invoice)
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
