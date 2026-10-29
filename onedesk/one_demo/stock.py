"""What was on the shelves when the year began, counted in as ERPNext's own
Stock Reconciliation does, and a bin of each material on the workshop floor."""

import frappe

from onedesk.one_demo.base import COMPANY, dated, on, once, save, wh

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
	_opening()
	_cleared()
	_kept()


def _opening():
	if frappe.db.exists("Stock Reconciliation", {"purpose": "Opening Stock", "docstatus": 1}):
		return
	doc = frappe.new_doc("Stock Reconciliation")
	doc.purpose = "Opening Stock"
	doc.set_warehouse = wh("Stores")
	doc.company = frappe.db.get_single_value("Global Defaults", "default_company")
	dated(doc, on(1, 1))
	doc.posting_time = "08:00:00"
	doc.expense_account = frappe.db.get_value("Account", {"company": doc.company, "account_name": "Temporary Opening"})
	for code, qty, rate in OPENING:
		doc.append("items", {"item_code": code, "warehouse": wh("Stores"), "qty": qty, "valuation_rate": rate})
	save(doc, submit=True)


def _cleared():
	"""The other side of the opening stock: what it was worth moves from
	Temporary Opening to the owners' capital, as an accountant posts it, so
	Temporary Opening ends at nought (the Books Check's opening balances)."""
	from onedesk.one_book import ready

	held = ready.temporary(COMPANY)
	if not held:
		return
	from onedesk.one_demo.books import _entry, _equity

	account, balance = held
	amount = abs(balance)
	cleared = ((account, amount, 0), (_equity(), 0, amount)) if balance < 0 else ((account, 0, amount), (_equity(), amount, 0))
	_entry(on(1, 1), "Opening Entry", "Opening stock, against capital", cleared)


def _kept():
	"""What Setup and the stores keep beside the stock: hinges put away in the
	Stores up to a thousand, how long profile takes to come, and the shims'
	standard cost. The two silicones stand in for each other once the
	weatherproof one is made (lots.py)."""
	once("Putaway Rule", {"item_code": "HW-HINGE"}, {"item_code": "HW-HINGE", "warehouse": wh("Stores"), "capacity": 1000, "stock_capacity": 1000, "uom": "Nos", "conversion_factor": 1, "priority": 1, "company": COMPANY})
	once("Item Lead Time", {"item_code": "ALU-6063"}, {"item_code": "ALU-6063", "purchase_time": 14, "buffer_time": 2})
	once(
		"Item",
		{"item_code": "HW-SHIM"},
		{
			"item_code": "HW-SHIM",
			"item_name": "Packing Shim",
			"item_group": frappe.db.get_value("Item", "HW-HINGE", "item_group"),
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"valuation_method": "Standard Cost",
		},
	)
	once(
		"Item Standard Cost",
		{"item_code": "HW-SHIM"},
		{"item_code": "HW-SHIM", "company": COMPANY, "standard_rate": 0.4, "effective_date": on(1, 1)},
		submit=True,
	)
