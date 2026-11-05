"""An item's barcodes: ERPNext's own table on Item (Item Barcode). A new item
is given its code as its first barcode, and its page shows the first two and
manages the rest in one dialog (frontend/src/inventory/item/ItemBarcodes.vue)."""

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
