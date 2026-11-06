"""Add from a List: a parts list pasted or uploaded in New Item's Made From step
(public/js/item_new.js), read into rows matched to the workspace's items by
code, supplier's part number or name, and the missing ones added as stock
items once the person says so."""

import csv
import io

import frappe
from frappe import _
from frappe.utils import cstr, flt

from onedesk.one_inventory.kinds import code_from

MOST = 1000

HEADS = {
	"code": ("code", "item", "item code", "part", "part no", "part number", "article", "article no", "sku", "ref"),
	"name": ("name", "item name", "description", "part name", "title"),
	"qty": ("qty", "quantity", "count", "pcs", "amount"),
	"unit": ("unit", "uom", "units"),
}

ORDER = {"code": 0, "name": 1, "qty": 2, "unit": 3}


def rows_from(text: str) -> list[list[str]]:
	"""The rows of a pasted or saved list, split by tab, semicolon or comma,
	whichever it uses. Pure."""
	text = cstr(text).strip()
	if not text:
		return []
	sample = text.splitlines()[0]
	split = "\t" if "\t" in sample else ";" if sample.count(";") > sample.count(",") else ","
	return [[cstr(cell).strip() for cell in row] for row in csv.reader(io.StringIO(text), delimiter=split) if any(cell.strip() for cell in row)]


def number(value) -> float:
	"""A quantity as a list writes it: 1.5, 1,5 or 1,200.5. Pure."""
	said = cstr(value).strip().replace(" ", "")
	if "," in said and "." in said:
		said = said.replace(",", "")
	elif "," in said:
		said = said.replace(",", ".")
	try:
		return float(said)
	except ValueError:
		return 0.0


def columns(head: list[str]) -> dict | None:
	"""Which column is which, read from a heading row, or None when the first
	row is a part. Pure."""
	found = {}
	for index, cell in enumerate(head):
		cell = cell.strip().lower().rstrip(".:")
		for key, names in HEADS.items():
			if key not in found and cell in names:
				found[key] = index
	return found if ("code" in found or "name" in found) and "qty" in found else None


def parse(table: list[list[str]]) -> list[dict]:
	"""The parts in a list, one per code or name, the same part listed twice
	added up. A part with no quantity counts one. Pure."""
	if not table:
		return []
	found = columns(table[0])
	body = table[1:] if found else table
	found = found or ORDER
	cell = lambda row, key: row[found[key]].strip() if key in found and found[key] < len(row) else ""  # noqa: E731
	parts = {}
	for row in body:
		code, name = cell(row, "code"), cell(row, "name")
		if not (code or name):
			continue
		qty = number(cell(row, "qty")) if cell(row, "qty") else 1.0
		key = (code or name).lower()
		if key in parts:
			parts[key]["qty"] += qty
		else:
			parts[key] = {"code": code, "name": name, "qty": qty, "unit": cell(row, "unit")}
	return [one for one in parts.values() if one["qty"] > 0]


def _table(text: str | None, file_url: str | None) -> list[list[str]]:
	if not file_url:
		return rows_from(text)
	file = frappe.get_doc("File", {"file_url": file_url})
	file.check_permission("read")
	content = file.get_content()
	if cstr(file.file_name).lower().endswith((".xlsx", ".xls")):
		from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

		return [[cstr(cell).strip() for cell in row] for row in read_xlsx_file_from_attached_file(fcontent=content) if any(cstr(cell).strip() for cell in row)]
	return rows_from(content.decode("utf-8-sig") if isinstance(content, bytes) else content)


@frappe.whitelist(methods=["POST"])
def read(text: str | None = None, file_url: str | None = None) -> dict:
	"""The parts in a list, each matched to an item by its code, a supplier's
	part number or its name, or marked new."""
	frappe.has_permission("Item", "read", throw=True)
	parts = parse(_table(text, file_url))[:MOST]
	if not parts:
		frappe.throw(_("No parts found. Each row needs a code or a name."))
	codes = [one["code"] for one in parts if one["code"]]
	names = [one["name"] for one in parts if one["name"]]
	fields = ["name", "item_name", "stock_uom"]
	by_code = {one.name.lower(): one for one in frappe.get_list("Item", filters={"name": ["in", codes or [""]], "disabled": 0}, fields=fields, limit_page_length=0)}
	by_name = {one.item_name.lower(): one for one in frappe.get_list("Item", filters={"item_name": ["in", names or [""]], "disabled": 0}, fields=fields, limit_page_length=0)}
	by_supplier = {
		one.supplier_part_no.lower(): one.parent
		for one in frappe.get_all("Item Supplier", filters={"supplier_part_no": ["in", codes or [""]], "parenttype": "Item"}, fields=["parent", "supplier_part_no"])
	}
	units = {one.lower(): one for one in frappe.get_all("UOM", filters={"enabled": 1}, pluck="name")}
	for one in parts:
		item = by_code.get(one["code"].lower()) or (
			by_supplier.get(one["code"].lower()) and next(iter(frappe.get_list("Item", filters={"name": by_supplier[one["code"].lower()]}, fields=fields)), None)
		) or by_name.get(one["name"].lower())
		unit = units.get(one["unit"].lower()) if one["unit"] else None
		if item:
			one.update(item=item.name, item_name=item.item_name, uom=item.stock_uom, new=False)
			if unit and unit != item.stock_uom:
				one["note"] = _("Listed in {0}, stocked in {1}").format(unit, item.stock_uom)
		else:
			one.update(item=None, item_name=one["name"] or one["code"], uom=unit, new=True)
			if one["unit"] and not unit:
				one["note"] = _("Unit {0} not found").format(one["unit"])
	return {"parts": parts, "new": sum(1 for one in parts if one["new"])}


@frappe.whitelist(methods=["POST"])
def add(parts: list | str) -> list[dict]:
	"""The listed parts as rows for the Made From table, the new ones first
	added as stock items bought from suppliers."""
	parts = [one for one in frappe.parse_json(parts) or [] if isinstance(one, dict)][:MOST]
	new = [one for one in parts if not one.get("item")]
	if new:
		frappe.has_permission("Item", "create", throw=True)
	group = "Raw Material" if frappe.db.exists("Item Group", "Raw Material") else frappe.db.get_single_value("Stock Settings", "item_group")
	fallback = frappe.db.get_single_value("Stock Settings", "stock_uom") or "Nos"
	rows = []
	for one in parts:
		name = one.get("item")
		if not name:
			code = cstr(one.get("code")).strip() or code_from(one.get("name"))
			name = code if frappe.db.exists("Item", code) else None
		if not name:
			item = frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": code,
					"item_name": cstr(one.get("name")).strip() or code,
					"item_group": group,
					"stock_uom": one.get("uom") or fallback,
					"is_stock_item": 1,
					"is_purchase_item": 1,
					"is_sales_item": 0,
				}
			).insert()
			name = item.name
		frappe.has_permission("Item", "read", doc=name, throw=True)
		said = frappe.db.get_value("Item", name, ["item_name", "stock_uom"], as_dict=True)
		rows.append({"item_code": name, "item_name": said.item_name, "qty": flt(one.get("qty")), "uom": said.stock_uom})
	return rows
