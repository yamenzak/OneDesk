"""The Number and List widgets are gone (D4): each becomes words with chips
on its collection's backdrop, read from the same Display Source, and its
row is removed. The other widgets keep the look they were drawn with
before widgets were bare (widgets.FIRST_LOOK)."""

import json

import frappe

from onedesk.one_display import chips
from onedesk.one_display import widgets as kinds


def execute():
	rows = frappe.get_all(
		"Display Widget",
		filters={"parenttype": "Widget Collection"},
		fields=["name", "parent", "widget_type", "source", "settings", "mapping", "x", "y", "w", "h"],
		order_by="idx asc",
	)
	gone = {}
	for row in rows:
		if row.widget_type in ("Number", "List"):
			gone.setdefault(row.parent, []).append(row)
			continue
		settings = json.loads(row.settings or "{}")
		if "look" in settings:
			continue
		look = dict(kinds.LOOKS.get(kinds.FIRST_LOOK.get(row.widget_type, "Plain")) or {})
		# a text's colour was its own setting; it is the element's now
		if settings.get("colour"):
			look["color"] = settings.pop("colour")
		if look:
			frappe.db.set_value("Display Widget", row.name, "settings", json.dumps({**settings, "look": look}), update_modified=False)
	for collection, old in gone.items():
		blocks, sources = chips.widget_blocks(old)
		frappe.db.delete("Display Widget", {"name": ["in", [row.name for row in old]]})
		frappe.clear_document_cache("Widget Collection", collection)
		if blocks:
			chips.onto(collection, blocks, sources)
