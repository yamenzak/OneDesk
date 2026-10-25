"""Ready to Submit: every draft OneAI made that the reader may submit, ready
ones first (onedesk/one_ai/reading/README.md §3.2). The checks are drafts.py's;
this only lays them out as a report, so the list, its checkboxes and its
export are frappe's.
"""

from frappe import _

from onedesk.one_ai.reading import drafts


def execute(filters=None):
	said = drafts.listed()
	data = [_row(one, True) for one in said["ready"]] + [_row(one, False) for one in said["red"]]
	columns = [
		{"fieldname": "doctype", "label": _("Type"), "fieldtype": "Link", "options": "DocType", "width": 140},
		{"fieldname": "name", "label": _("Draft"), "fieldtype": "Dynamic Link", "options": "doctype", "width": 180},
		{"fieldname": "state", "label": _("Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "party", "label": _("Party"), "fieldtype": "Data", "width": 180},
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "total", "label": _("Total"), "fieldtype": "Currency", "options": "currency", "width": 130},
		{"fieldname": "document", "label": _("Document"), "fieldtype": "Data", "width": 200},
		{"fieldname": "why", "label": _("Needs Review"), "fieldtype": "Data", "width": 320},
		{"fieldname": "currency", "label": _("Currency"), "fieldtype": "Link", "options": "Currency", "hidden": 1},
	]
	return columns, data


def _row(one: dict, ready: bool) -> dict:
	document = one.get("document") or {}
	return {
		"doctype": one["doctype"],
		"name": one["name"],
		"state": _("Ready") if ready else _("Needs Review"),
		"ready": int(ready),
		"party": one.get("party"),
		"date": one.get("date"),
		"total": one.get("total"),
		"currency": one.get("currency"),
		"document": document.get("label") or one.get("title"),
		"route": document.get("route"),
		"why": " ".join(one.get("red") or []),
	}
