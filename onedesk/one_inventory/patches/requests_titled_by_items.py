"""Material requests ERPNext titled "Purchase Request for …" in English are
titled by their items, as new ones are (one_inventory/requests.py)."""

import frappe


def execute():
	for name, title in frappe.get_all("Material Request", filters={"title": ["like", "% Request for %"]}, fields=["name", "title"], as_list=True):
		items = frappe.get_all("Material Request Item", filters={"parent": name}, fields=["item_name", "item_code"], order_by="idx", limit=3)
		new = ", ".join(row.item_name or row.item_code for row in items)[:100]
		if new and new != title:
			frappe.db.set_value("Material Request", name, "title", new, update_modified=False)
