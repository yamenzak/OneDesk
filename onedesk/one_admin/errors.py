"""Errors, gathered from every workspace: `heard` keeps one row for each
workspace and kind of error, and an operator is told when a kind nobody has
seen before appears (one/errors.py is the workspace's side)."""

import frappe
from frappe.utils import cint, get_datetime

from onedesk.one_admin import tell

DOCTYPE = "Workspace Error"
MOST_ROWS = 200
TITLE_LONG = 140
MOST_TOLD = 3


def _cut(row: dict, field: str, long: int = TITLE_LONG) -> str:
	return str(row.get(field) or "")[:long]


def _when(value):
	return get_datetime(value) if value else None


def heard(tenant: str, rows: list[dict]) -> int:
	"""A workspace's latest summary, kept: new kinds added, known kinds
	counted up, and the operators told of up to `MOST_TOLD` kinds new to
	every workspace."""
	told = 0
	for row in (rows or [])[:MOST_ROWS]:
		fingerprint = _cut(row, "fingerprint", 64)
		if not fingerprint:
			continue
		first, last = _when(row.get("first_seen")), _when(row.get("last_seen"))
		found = frappe.db.get_value(DOCTYPE, {"tenant": tenant, "fingerprint": fingerprint}, ["name", "occurrences", "first_seen"], as_dict=True)
		if found:
			frappe.db.set_value(DOCTYPE, found.name, {"occurrences": cint(found.occurrences) + cint(row.get("count")), "last_seen": last, "status": "Open"}, update_modified=False)
			continue
		new_kind = not frappe.db.exists(DOCTYPE, {"fingerprint": fingerprint})
		doc = frappe.get_doc(
			{
				"doctype": DOCTYPE,
				"tenant": tenant,
				"fingerprint": fingerprint,
				"title": _cut(row, "title"),
				"kind": _cut(row, "kind"),
				"where_in_code": _cut(row, "where"),
				"status": "Open",
				"occurrences": cint(row.get("count")),
				"first_seen": first,
				"last_seen": last,
			}
		).insert(ignore_permissions=True)
		if new_kind and told < MOST_TOLD:
			tell.new_error(doc)
			told += 1
	return len(rows or [])
