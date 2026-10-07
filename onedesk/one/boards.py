"""One's boards on frappe's Kanban, the one every new board opens in."""

import frappe


def cards(board, fields: dict[str, str]) -> bool:
	"""Put `board` on the new Kanban, its cards showing `fields` under the
	title, each by its icon as erpnext's own boards do. Whether anything
	changed."""
	meta = frappe.get_meta(board.reference_doctype)
	wanted = list(fields.items())
	before = (board.use_kanban_v2, [(row.fieldname, row.icon) for row in board.get("card_fields") or []])
	if before == (1, wanted):
		return False
	board.use_kanban_v2 = 1
	board.set("card_fields", [])
	for fieldname, icon in wanted:
		df = meta.get_field(fieldname)
		board.append("card_fields", {"fieldname": fieldname, "icon": icon, "label": df.label if df else fieldname})
	return True
