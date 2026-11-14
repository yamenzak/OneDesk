"""What OneFactory's production planner does on its own (agent.py WATCH):
a sales order for what the company makes and does not hold enough of, as
draft work orders. It answers actions, which the agents' door takes
(one_ai/agents/work.py)."""

import frappe
from frappe import _
from frappe.utils import flt

from onedesk.one_ai.reading.act import Action


def ordered(order) -> list[Action]:
	"""Each line of a submitted Sales Order whose item has a default bill of
	materials and is short in the line's warehouse, as a draft Work Order
	for what is short, wanted by the line's delivery date. A line that has
	a work order already is left alone."""
	if order.docstatus != 1:
		return []
	out = []
	for row in order.items:
		bom = frappe.db.get_value("BOM", {"item": row.item_code, "is_default": 1, "is_active": 1, "docstatus": 1})
		if not bom or frappe.db.exists("Work Order", {"sales_order": order.name, "production_item": row.item_code, "docstatus": ["<", 2]}):
			continue
		projected = flt(frappe.db.get_value("Bin", {"item_code": row.item_code, "warehouse": row.warehouse}, "projected_qty"))
		short = min(flt(row.stock_qty), max(0.0, -projected))
		if short <= 0:
			continue
		values = {
			"production_item": row.item_code,
			"bom_no": bom,
			"qty": short,
			"sales_order": order.name,
			"company": order.company,
			"expected_delivery_date": str(row.delivery_date or order.delivery_date or "") or None,
			"project": row.get("project") or order.get("project"),
		}
		why = _("Sales Order {0} needs {1} {2} of {3} more than the stores hold.").format(order.name, f"{short:g}", _(row.stock_uom), row.item_name or row.item_code)
		out.append(Action("Create", "Work Order", values={key: value for key, value in values.items() if value}, key=f"one_factory|ordered|{order.name}|{row.item_code}", why=why, propose_on_error=True))
	return out
