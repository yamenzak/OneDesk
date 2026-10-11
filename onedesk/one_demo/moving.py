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
	if not frappe.db.exists("Stock Reconciliation", {"docstatus": 1, "purpose": "Stock Reconciliation"}):
		_counted()
	from onedesk.one_demo.build import _reposted

	_reposted()


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
