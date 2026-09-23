"""What to order: open purchase requests not yet ordered, and items low with
no request yet. See one_inventory/order.py."""

from frappe import _

from onedesk.one_inventory import order


def execute(filters=None):
	return columns(), order.rows()


def columns() -> list[dict]:
	return [
		{"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 200},
		{"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Link", "options": "Warehouse", "width": 160},
		{"fieldname": "qty", "label": _("To Order"), "fieldtype": "Float", "width": 100},
		{"fieldname": "uom", "label": _("Unit"), "fieldtype": "Data", "width": 70},
		{"fieldname": "supplier", "label": _("Supplier"), "fieldtype": "Link", "options": "Supplier", "width": 200},
		{"fieldname": "rate", "label": _("Last Rate"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "why", "label": _("Why"), "fieldtype": "Data", "width": 100},
		{"fieldname": "material_request", "label": _("Request"), "fieldtype": "Link", "options": "Material Request", "width": 170},
	]
