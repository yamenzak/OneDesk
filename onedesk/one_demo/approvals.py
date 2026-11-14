"""Demo step: one of each thing waiting for a second person (one/second.py).
Karim drafts a large payment to the supplier with the most still owed,
which waits for Huda or Layla; Huda changes Gulf Office Supplies' bank
account, which waits for Layla, and the supplier is told; and Omar asks to
export more customers than the workspace allows at once, which waits for
Layla. Made the way a person's own save makes each."""

import frappe
from frappe import _

from onedesk.one_demo.base import COMPANY, as_user, today

SUPPLIER = "Gulf Office Supplies"

IBAN, NEW_IBAN = "AE070331234567890123456", "AE580260001015333439201"


def run(password=None):
	was = frappe.flags.in_demo
	frappe.flags.in_demo = False
	try:
		_bank_details()
		_payment()
		_export()
	finally:
		frappe.flags.in_demo = was


def _bank_details() -> None:
	if frappe.db.exists("Second Approval", {"kind": "Bank Details", "party": SUPPLIER}):
		return
	bank = frappe.db.get_value("Bank Account", {"is_company_account": 1, "company": COMPANY}, "bank")
	with as_user("huda@one.test"):
		account = frappe.db.get_value("Bank Account", {"party_type": "Supplier", "party": SUPPLIER}, "name")
		if not account:
			made = frappe.get_doc(
				{
					"doctype": "Bank Account",
					"account_name": SUPPLIER,
					"bank": bank,
					"party_type": "Supplier",
					"party": SUPPLIER,
					"iban": IBAN,
				}
			).insert()
			account = made.name
		doc = frappe.get_doc("Bank Account", account)
		doc.iban = NEW_IBAN
		doc.save()


def _payment() -> None:
	if frappe.db.exists("Second Approval", {"kind": "Payment"}):
		return
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	bill = frappe.get_all(
		"Purchase Invoice",
		filters={"company": COMPANY, "docstatus": 1, "outstanding_amount": [">", 10000], "supplier": ["!=", SUPPLIER], "currency": "AED"},
		order_by="outstanding_amount desc",
		pluck="name",
		limit=1,
	)
	if not bill:
		return
	with as_user("karim@one.test"):
		payment = get_payment_entry("Purchase Invoice", bill[0])
		payment.reference_no = f"TRF-{bill[0][-5:]}"
		payment.reference_date = today()
		payment.insert()


def _export() -> None:
	if frappe.db.exists("Second Approval", {"kind": "Export"}):
		return
	from onedesk.one import exports

	with as_user("omar@one.test"):
		exports.asked("Customer", max(exports.limit(), 1) + 250, _("Report View"))
