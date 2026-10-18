"""Items sold by size: an item sold by length or area (Item's Sold by Size),
and a line that gives its pieces, length and width in millimetres. The
line's quantity is worked out from them, in the line's unit, so ERPNext prices,
taxes, stocks and costs it as it would any other line. Every table that lines
up items carries the size (custom fields one_measured_by, one_pieces,
one_length, one_width and one_size)."""

import frappe
from frappe import _
from frappe.utils import cint, flt

BASE = {"Length": "Meter", "Area": "Square Meter"}

LINES = (
	"Quotation Item",
	"Sales Order Item",
	"Delivery Note Item",
	"Sales Invoice Item",
	"POS Invoice Item",
	"Opportunity Item",
	"Proforma Invoice Item",
	"Blanket Order Item",
	"Packing Slip Item",
	"Pick List Item",
	"Installation Note Item",
	"Product Bundle Item",
	"Material Request Item",
	"Request for Quotation Item",
	"Supplier Quotation Item",
	"Purchase Order Item",
	"Purchase Receipt Item",
	"Purchase Invoice Item",
	"Stock Entry Detail",
	"Stock Reconciliation Item",
	"BOM Item",
	"BOM Creator Item",
	"BOM Secondary Item",
	"Work Order Additional Item",
	"Subcontracting Order Item",
	"Subcontracting Order Service Item",
	"Subcontracting Receipt Item",
	"Subcontracting Inward Order Item",
	"Subcontracting Inward Order Service Item",
	"Asset Capitalization Service Item",
)

BUYING = {
	"Supplier Quotation",
	"Purchase Order",
	"Purchase Receipt",
	"Purchase Invoice",
}
SELLING = {"Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "POS Invoice", "Opportunity"}


def unit_kind(uom: str | None) -> str | None:
	"""Length or Area when ERPNext's table of units counts `uom` as one."""
	if not uom:
		return None
	for side in ("from_uom", "to_uom"):
		category = frappe.db.get_value("UOM Conversion Factor", {side: uom}, "category")
		if category in BASE:
			return category
	return None


@frappe.whitelist()
def unit_is(uom: str) -> str | None:
	"""What New Item sets Sold by Size to when its unit is picked."""
	return unit_kind(uom)


def follows_unit(doc, method=None) -> None:
	"""Item before_validate: an item counted in a length or an area is sold by
	it, once it is made or its unit changes, on every path an item is saved
	by. One already sold by size keeps what it says (a sheet kept by the
	piece and sold by the square metre)."""
	if doc.get("one_measured_by") in BASE:
		return
	before = doc.get_doc_before_save() if not doc.is_new() else None
	if before and before.stock_uom == doc.stock_uom:
		return
	doc.one_measured_by = unit_kind(doc.stock_uom) or "No"


def amount(measured_by: str, pieces, length, width) -> float:
	"""How many metres or square metres the pieces come to. Pure."""
	pieces = cint(pieces) or 1
	if measured_by == "Length":
		return pieces * flt(length) / 1000
	if measured_by == "Area":
		return pieces * flt(length) * flt(width) / 1_000_000
	return 0.0


def factor(item_code: str, measured_by: str, uom: str) -> float:
	"""How many of the line's unit one metre or square metre is: the item's own
	conversion first (a sheet of 3.125 m²), then ERPNext's table of units."""
	base = BASE[measured_by]
	if uom == base:
		return 1.0
	own = {
		row.uom: flt(row.conversion_factor)
		for row in frappe.get_all(
			"UOM Conversion Detail",
			filters={"parent": item_code, "parenttype": "Item"},
			fields=["uom", "conversion_factor"],
		)
	}
	stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
	own.setdefault(stock_uom, 1.0)
	if own.get(base) and own.get(uom):
		return own[base] / own[uom]
	value = frappe.db.get_value("UOM Conversion Factor", {"from_uom": base, "to_uom": uom}, "value")
	if value:
		return flt(value)
	value = frappe.db.get_value("UOM Conversion Factor", {"from_uom": uom, "to_uom": base}, "value")
	if value:
		return 1 / flt(value)
	frappe.throw(
		_(
			"Unit {0} can't be counted in {1}. Pick a unit that converts, or add it to the item's units."
		).format(_(uom), _(base))
	)


def unit(row, parent) -> str:
	"""The unit a line counts in: its own, or the one ERPNext will give it.
	`parent` is the record, or its doctype."""
	if row.get("uom"):
		return row.uom
	doctype = parent if isinstance(parent, str) else parent.doctype
	buying = doctype in BUYING or (
		doctype == "Material Request" and not isinstance(parent, str) and parent.get("material_request_type") == "Purchase"
	)
	field = "purchase_uom" if buying else "sales_uom" if doctype in SELLING else None
	said = frappe.db.get_value("Item", row.item_code, [field or "stock_uom", "stock_uom"])
	return said[0] or said[1] if field else said[0]


def size(measured_by: str, pieces, length, width) -> str:
	"""A line's size as it is read and printed: 4 × 1200 × 800 mm. Pure."""
	parts = [f"{flt(length):g}"] + ([f"{flt(width):g}"] if measured_by == "Area" else [])
	pieces = cint(pieces) or 1
	return " × ".join(([str(pieces)] if pieces > 1 else []) + parts) + " mm"


def quantity(row, parent) -> float | None:
	"""A line's quantity from its size, or None when it has none."""
	measured_by = row.get("one_measured_by")
	if measured_by not in BASE or not flt(row.get("one_length")):
		return None
	if measured_by == "Area" and not flt(row.get("one_width")):
		return None
	measured = amount(measured_by, row.get("one_pieces"), row.get("one_length"), row.get("one_width"))
	return flt(measured * factor(row.item_code, measured_by, unit(row, parent)), row.precision("qty"))


def tables(doctype: str) -> list[str]:
	"""A record's tables that line up items with a size."""
	return [df.fieldname for df in frappe.get_meta(doctype).get_table_fields() if df.options in LINES]


def sized(doc, method=None) -> None:
	"""before_validate, on every record: each line with a size takes its
	quantity from it, on every path a line is saved by (the form, bulk edit,
	Data Import, a mapper), and says its size for print."""
	if doc.meta.istable:
		return
	for fieldname in tables(doc.doctype):
		for row in doc.get(fieldname) or []:
			if not row.get("item_code"):
				continue
			if row.get("one_measured_by") not in BASE:
				row.one_measured_by = frappe.db.get_value("Item", row.item_code, "one_measured_by")
			qty = quantity(row, doc)
			if qty is None:
				row.one_size = None
				continue
			row.qty = qty
			row.one_size = size(row.one_measured_by, row.one_pieces, row.one_length, row.one_width)


@frappe.whitelist()
def line_quantity(item_code: str, measured_by: str, uom: str, pieces=None, length=None, width=None) -> float:
	"""The quantity a form shows as a line's size is typed."""
	frappe.has_permission("Item", "read", doc=item_code, throw=True)
	if measured_by not in BASE:
		return 0.0
	return amount(measured_by, pieces, length, width) * factor(item_code, measured_by, uom)


def for_boot() -> dict:
	"""Which tables of which records carry a size, for the forms
	(public/js/measure.js)."""
	found = {}
	for doctype in ("DocField", "Custom Field"):
		parent = "parent" if doctype == "DocField" else "dt"
		for row in frappe.get_all(
			doctype, filters={"fieldtype": "Table", "options": ["in", LINES]}, fields=[parent, "fieldname"]
		):
			found.setdefault(row[parent], []).append(row.fieldname)
	symbols = dict(
		frappe.get_all(
			"UOM", filters={"symbol": ["is", "set"], "enabled": 1}, fields=["name", "symbol"], as_list=True
		)
	)
	return {"lines": list(LINES), "records": found, "symbols": symbols}
