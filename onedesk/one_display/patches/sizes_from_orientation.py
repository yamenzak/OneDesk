"""A channel and a widget collection had an Orientation of Landscape or
Portrait; each now has a Screen Size with its width and height (sizes.py)."""

import frappe

from onedesk.one_display import sizes


def execute():
	for doctype in ("Display Channel", "Widget Collection"):
		has = frappe.db.has_column(doctype, "orientation")
		for row in frappe.get_all(doctype, fields=["name"] + (["orientation"] if has else [])):
			size = "Portrait" if row.get("orientation") == "Portrait" else "Landscape"
			wide, high = sizes.SIZES[size]
			frappe.db.set_value(doctype, row.name, {"screen_size": size, "width": wide, "height": high}, update_modified=False)
