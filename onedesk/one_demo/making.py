"""The workshop: a bill of materials for each product, and work orders the
way a workshop has them, finished, with materials on the floor, and not yet
started.

No app of One's gives anybody ERPNext's manufacturing roles yet, so these are
made by whoever set the workspace up (docs/PASSOVER.md, Noticed)."""

import frappe
from frappe.utils import add_days

from onedesk.one_demo.base import COMPANY, as_user, dated, make, on, save, today, wh
from onedesk.one_demo.setup import BUILDER as SUPERVISOR

#: product, [(material, qty for one)]
BOMS = (
	("WIN-CS12", (("ALU-6063", 9), ("GLS-DGU", 1.3), ("HW-HINGE", 2), ("HW-HANDLE", 1), ("SEAL-EPDM", 6), ("SIL-CLR", 1))),
	("DR-SL24", (("ALU-6063", 16), ("GLS-DGU", 4.5), ("HW-LOCK", 1), ("HW-HANDLE", 2), ("SEAL-EPDM", 12), ("SIL-CLR", 1))),
	("BAL-GL", (("GLS-TMP10", 1.1), ("FIX-ANCH", 4), ("SIL-CLR", 1))),
)

#: product, qty, started, made (all, part or none)
ORDERS = (
	("WIN-CS12", 40, on(4, 8), 40),
	("DR-SL24", 14, on(4, 20), 14),
	("BAL-GL", 90, on(6, 12), 90),
	("WIN-CS12", 60, on(7, 6), 60),
	("DR-SL24", 10, on(8, 24), 10),
	("WIN-CS12", 30, add_days(today(), -9), 12),
	("BAL-GL", 40, add_days(today(), -2), 0),
	("DR-SL24", 8, add_days(today(), 4), 0),
)


def run(password=None):
	with as_user(SUPERVISOR):
		for product, materials in BOMS:
			if frappe.db.exists("BOM", {"item": product, "is_default": 1}):
				continue
			make(
				{
					"doctype": "BOM",
					"item": product,
					"company": COMPANY,
					"quantity": 1,
					"is_default": 1,
					"is_active": 1,
					"rm_cost_as_per": "Valuation Rate",
					"items": [{"item_code": code, "qty": qty} for code, qty in materials],
				},
				submit=True,
			)
		if frappe.db.exists("Work Order", {"docstatus": 1}):
			return
		for product, qty, started, made in ORDERS:
			_work_order(product, qty, started, made)


def _work_order(product, qty, started, made):
	from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry

	order = frappe.new_doc("Work Order")
	order.update(
		{
			"production_item": product,
			"bom_no": frappe.db.get_value("BOM", {"item": product, "is_default": 1}),
			"qty": qty,
			"company": COMPANY,
			"wip_warehouse": wh("Work In Progress"),
			"fg_warehouse": wh("Finished Goods"),
			"source_warehouse": wh("Stores"),
			"planned_start_date": f"{started} 08:00:00",
			"expected_delivery_date": add_days(started, 10),
		}
	)
	order = save(order, submit=True)
	if started >= today():
		return
	transfer = frappe.get_doc(make_stock_entry(order.name, "Material Transfer for Manufacture", qty))
	dated(transfer, started)
	save(transfer, submit=True)
	if made:
		finish = frappe.get_doc(make_stock_entry(order.name, "Manufacture", made))
		dated(finish, min(add_days(started, 6), today()))
		save(finish, submit=True)
