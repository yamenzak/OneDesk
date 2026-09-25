"""What ERPNext mailed from OneInventory, told through the hub instead
(docs/NOTIFICATIONS.md, stage 6)."""

from onedesk.one import notify


def raised(doc, method=None) -> None:
	"""Material Request on_submit: one raised by reordering (its rows carry
	the level they were raised at) is told to Purchasing, as ERPNext mailed
	them when Stock Settings said to. That switch is off now; Send This on
	the type decides."""
	rows = [row for row in doc.items if row.get("reorder_level")]
	if not rows:
		return
	from erpnext.stock.reorder_item import get_email_list

	notify.notify(
		"Material Request Raised",
		get_email_list(doc.company),
		record=("Material Request", doc.name),
		request=doc.name,
		items=", ".join(row.item_name or row.item_code for row in rows),
	)
