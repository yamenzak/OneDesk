"""A material request's title: its first three items' names, which read the
same in every language. ERPNext writes "Purchase Request for …" in the
language of whoever saved it, and the title is stored, so an Arabic reader
saw English (hooks.py, Material Request before_validate)."""


def titled(doc, method=None) -> None:
	if not doc.title:
		doc.title = ", ".join(row.item_name or row.item_code for row in doc.items[:3] if row.item_code)[:100] or None
