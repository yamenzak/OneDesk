"""What was on the shelves when the year began, counted in as ERPNext's own
Stock Reconciliation does, and a bin of each material on the workshop floor."""

import frappe

from onedesk.one_demo.base import dated, on, save, wh

#: code, qty in Stores, rate
OPENING = (
	("ALU-6063", 2200, 27),
	("GLS-DGU", 420, 160),
	("GLS-TMP10", 180, 118),
	("HW-HINGE", 600, 36),
	("HW-HANDLE", 380, 23),
	("HW-LOCK", 120, 92),
	("SEAL-EPDM", 3000, 4.2),
	("SIL-CLR", 240, 30),
	("FIX-ANCH", 1500, 5.5),
)


def run(password=None):
	if frappe.db.exists("Stock Reconciliation", {"purpose": "Opening Stock", "docstatus": 1}):
		return
	doc = frappe.new_doc("Stock Reconciliation")
	doc.purpose = "Opening Stock"
	doc.company = frappe.db.get_single_value("Global Defaults", "default_company")
	dated(doc, on(1, 1))
	doc.posting_time = "08:00:00"
	doc.expense_account = frappe.db.get_value("Account", {"company": doc.company, "account_name": "Temporary Opening"})
	for code, qty, rate in OPENING:
		doc.append("items", {"item_code": code, "warehouse": wh("Stores"), "qty": qty, "valuation_rate": rate})
	save(doc, submit=True)
