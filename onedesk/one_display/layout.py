"""A widget collection for the channel builder (screen.py, which OneSlide's
editor reaches through its hooks): its widgets, the kinds and sources it may
use, and saving them back. Nothing is written that the collection's own
validation would refuse (doctype/widget_collection)."""

import json
from typing import Annotated

import frappe
from frappe import _, _lt

from onedesk.one_display import widgets as kinds

DOCTYPE = "Widget Collection"
KEPT = ("widget_type", "label", "source", "x", "y", "w", "h", "layer", "mapping", "settings", "shown", "from_time", "to_time")
FEED = {"title": _lt("Title"), "summary": _lt("Summary"), "date": _lt("Date"), "link": _lt("Link"), "image": _lt("Image")}


@frappe.whitelist()
def get(collection: Annotated[str, "The widget collection."]) -> dict:
	"""A collection, what it may hold and where the rows can come from."""
	doc = frappe.get_doc(DOCTYPE, collection)
	doc.check_permission("read")
	return {
		"name": doc.name,
		"orientation": doc.orientation or "Landscape",
		"background": doc.background or "",
		"writable": doc.has_permission("write"),
		"widgets": [{"id": row.name, **{key: row.get(key) for key in KEPT}} for row in doc.widgets],
		"types": kinds.described(),
		"sources": frappe.get_list(
			"Display Source", fields=["name", "kind", "ref_doctype", "report"], order_by="name asc", limit=500
		),
	}


@frappe.whitelist()
def fields(source: Annotated[str, "A source."]) -> list[dict]:
	"""What a source's rows carry, for mapping a widget's slots to."""
	from onedesk.one_display import sources

	row = frappe.get_doc("Display Source", source)
	row.check_permission("read")
	if row.kind in ("Records", "Record"):
		if row.kind == "Records" and row.aggregate:
			return [{"fieldname": "value", "label": _("Value")}]
		return sources.fields_of(row.ref_doctype)
	if row.kind == "Report":
		return sources.report_fields(row.report, row.report_filters)
	if row.kind == "Exchange Rates":
		labels = {"currency": _("Currency"), "rate": _("Rate"), "base": _("In Currency"), "line": _("Line")}
		return [{"fieldname": one, "label": labels[one]} for one in sources.RATE_FIELDS]
	if row.kind == "Feed":
		return [{"fieldname": one, "label": str(label)} for one, label in FEED.items()]
	return []


@frappe.whitelist(methods=["POST"])
def save(
	collection: Annotated[str, "The widget collection."],
	widgets: Annotated[str | list, "Its widgets, in the shape get() gives."],
	orientation: Annotated[str | None, "Landscape or Portrait."] = None,
	background: Annotated[str | None, "A colour, or empty for the brand's."] = None,
) -> dict:
	"""Write the editor's widgets over the collection's, keeping each row
	the editor knows by its id."""
	doc = frappe.get_doc(DOCTYPE, collection)
	doc.check_permission("write")
	given = json.loads(widgets) if isinstance(widgets, str) else widgets
	known = {row.name: row for row in doc.widgets}
	rows = []
	for one in given or []:
		values = {key: one.get(key) for key in KEPT}
		for key in ("mapping", "settings"):
			if isinstance(values[key], dict):
				values[key] = json.dumps(values[key], ensure_ascii=False)
		row = known.get(one.get("id"))
		if row:
			row.update(values)
			rows.append(row)
		else:
			rows.append(doc.append("widgets", values))
	doc.set("widgets", rows)
	if orientation in ("Landscape", "Portrait"):
		doc.orientation = orientation
	if background is not None:
		doc.background = background or None
	doc.save()
	return get(collection)
