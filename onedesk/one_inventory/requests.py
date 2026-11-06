"""A material request's title: its first three items' names, which read the
same in every language. ERPNext writes "Purchase Request for …" in the
language of whoever saved it, and the title is stored, so an Arabic reader
saw English (hooks.py, Material Request before_validate)."""


import frappe


def titled(doc, method=None) -> None:
	if not doc.title:
		names = [
			row.item_name or frappe.get_cached_value("Item", row.item_code, "item_name") or row.item_code
			for row in doc.items[:3]
			if row.item_code
		]
		doc.title = ", ".join(names)[:100] or None
