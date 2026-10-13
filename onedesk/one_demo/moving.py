"""Stock moved and counted: the villa's materials sent from the stores to its
site with a transfer note, used there on the project, and a count of the
stores that finds hinges short, posted to the books as a loss."""

import frappe
from erpnext.stock.utils import get_stock_balance
from frappe.utils import flt

from onedesk.one_demo.base import COMPANY, ago, as_user, dated, once, save, wh

STORES = "karim@one.test"
SITE = "tariq@one.test"
VILLA = "Mansour Villa Windows and Doors"

#: What the villa's site needs from the stores: code, quantity.
SENT = (("ALU-6063", 120), ("HW-LOCK", 12), ("SIL-CLR", 20))
#: What was used on site from it.
USED = (("ALU-6063", 80), ("SIL-CLR", 14))
#: The hinges the count found short.
SHORT = ("HW-HINGE", 3)


def run(password=None):
	project = frappe.db.get_value("Project", {"project_name": VILLA})
	site = _site()
	if not frappe.db.exists("Stock Entry", {"docstatus": 1, "purpose": "Material Transfer", "to_warehouse": site}):
		_sent(project, site)
		_used(project, site)
	from onedesk.one_demo.build import _reposted

	# The count reads each item's value, so the back-dated entries are worked out first.
	_reposted()
	if not frappe.db.exists("Stock Reconciliation", {"docstatus": 1, "purpose": "Stock Reconciliation"}):
		_counted()
	_reposted()
	_given()
	_on_the_road()


def _site() -> str:
	"""The villa's site as a warehouse, with the address its transfer note
	takes the goods to. Set up as whoever set up the warehouses."""
	return once(
		"Warehouse",
		{"warehouse_name": "Mansour Villa Site", "company": COMPANY},
		{
			"warehouse_name": "Mansour Villa Site",
			"company": COMPANY,
			"parent_warehouse": wh("All Warehouses"),
			"address_line_1": "Villa 14, Al Wasl Road",
			"city": "Dubai",
			"phone_no": "+971 50 412 7731",
		},
	).name


def _sent(project, site):
	"""Karim sends the villa's materials to its site."""
	with as_user(STORES):
		doc = frappe.new_doc("Stock Entry")
		doc.stock_entry_type = "Material Transfer"
		doc.purpose = "Material Transfer"
		doc.company = COMPANY
		doc.project = project
		doc.from_warehouse = wh("Stores")
		doc.to_warehouse = site
		dated(doc, ago(6))
		for code, qty in SENT:
			doc.append("items", {"item_code": code, "qty": qty, "s_warehouse": wh("Stores"), "t_warehouse": site, "project": project})
		save(doc, submit=True)


def _used(project, site):
	"""Tariq uses some of it on site, for the villa."""
	with as_user(SITE):
		doc = frappe.new_doc("Stock Entry")
		doc.stock_entry_type = "Material Issue"
		doc.purpose = "Material Issue"
		doc.company = COMPANY
		doc.project = project
		doc.from_warehouse = site
		dated(doc, ago(3))
		for code, qty in USED:
			doc.append("items", {"item_code": code, "qty": qty, "s_warehouse": site, "project": project})
		save(doc, submit=True)


def _counted():
	"""Karim counts the stores' hardware and finds three hinges short. The
	difference is posted to the company's stock adjustment account."""
	code, short = SHORT
	day = ago(2)
	with as_user(STORES):
		doc = frappe.new_doc("Stock Reconciliation")
		doc.company = COMPANY
		doc.purpose = "Stock Reconciliation"
		dated(doc, day)
		doc.posting_time = "17:00:00"
		doc.expense_account = frappe.get_cached_value("Company", COMPANY, "stock_adjustment_account")
		for one in ("HW-HINGE", "HW-HANDLE", "HW-LOCK"):
			have, rate = get_stock_balance(one, wh("Stores"), day, "17:00:00", with_valuation_rate=True)[:2]
			counted = flt(have) - (short if one == code else 0)
			doc.append("items", {"item_code": one, "warehouse": wh("Stores"), "qty": counted, "valuation_rate": rate})
		save(doc, submit=True)


def _given():
	"""Gaskets the seal supplier threw in with an order, taken into the
	Stores with no receipt to go with them: a Material Receipt."""
	if frappe.db.exists("Stock Entry", {"docstatus": 1, "purpose": "Material Receipt"}):
		return
	with as_user(STORES):
		doc = frappe.new_doc("Stock Entry")
		doc.stock_entry_type = "Material Receipt"
		doc.purpose = "Material Receipt"
		doc.company = COMPANY
		dated(doc, ago(5))
		doc.remarks = "Spare gaskets the seal supplier added to the order, free of charge."
		doc.to_warehouse = wh("Stores")
		doc.append("items", {"item_code": "SEAL-EPDM", "qty": 50, "t_warehouse": wh("Stores"), "basic_rate": 4.2})
		save(doc, submit=True)


def _on_the_road():
	"""Double-glazed units on their way to the tower's site: sent through Goods
	In Transit, not arrived yet, so the move's head says how much has."""
	if frappe.db.exists("Stock Entry", {"docstatus": 1, "add_to_transit": 1}):
		return
	project = frappe.db.get_value("Project", {"project_name": "Bayview Tower Curtain Wall"})
	with as_user(STORES):
		doc = frappe.new_doc("Stock Entry")
		doc.stock_entry_type = "Material Transfer"
		doc.purpose = "Material Transfer"
		doc.company = COMPANY
		doc.add_to_transit = 1
		doc.project = project
		dated(doc, ago(1))
		doc.from_warehouse, doc.to_warehouse = wh("Stores"), wh("Goods In Transit")
		doc.append("items", {"item_code": "GLS-DGU", "qty": 12, "s_warehouse": wh("Stores"), "t_warehouse": wh("Goods In Transit"), "project": project})
		save(doc, submit=True)
