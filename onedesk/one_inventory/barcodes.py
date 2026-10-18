"""An item's barcodes: ERPNext's own table on Item (Item Barcode). A new item
is given its code as its first barcode, and its page shows the first two and
manages the rest in one dialog (frontend/src/item/ItemBarcodes.vue)."""

import frappe

FEATURED = 2


def coded(doc, method=None) -> None:
	"""before_insert: an item without a barcode gets its code as one, on every
	path an item is made by, unless another item already has it."""
	if doc.get("barcodes") or not doc.get("item_code"):
		return
	if frappe.db.exists("Item Barcode", {"barcode": doc.item_code}):
		return
	doc.append("barcodes", {"barcode": doc.item_code})


def listed(doc) -> list[dict]:
	"""An item's barcodes in their order, each as the page draws it. One with
	none shows its code, as a new item is given."""
	rows = [
		{"name": row.name, "barcode": row.barcode, "barcode_type": row.barcode_type or "", "uom": row.uom}
		for row in sorted(doc.get("barcodes") or [], key=lambda row: row.idx)
		if row.barcode
	]
	return rows or [{"name": None, "barcode": doc.item_code, "barcode_type": "", "uom": None}]


@frappe.whitelist(methods=["POST"])
def save(item: str, rows: list | str) -> list[dict]:
	"""The item's barcodes, as the dialog leaves them: their order is their
	place, so the first two are the ones its page shows. ERPNext checks each
	one is the item's alone and fits its type."""
	doc = frappe.get_doc("Item", item)
	doc.check_permission("write")
	rows = [
		one
		for one in frappe.parse_json(rows) or []
		if isinstance(one, dict) and (one.get("barcode") or "").strip()
	]
	doc.set(
		"barcodes",
		[
			{
				"barcode": one["barcode"].strip(),
				"barcode_type": one.get("barcode_type") or "",
				"uom": one.get("uom") or None,
			}
			for one in rows
		],
	)
	doc.save()
	return listed(doc)
