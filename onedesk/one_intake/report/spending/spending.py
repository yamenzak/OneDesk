"""Spending: what was bought, read from the receipts and invoices themselves
(docs/INTAKE.md §3.2).

A household keeps no books, and a company's books answer "what did we spend
on fuel this quarter" only through a report somebody builds. The readings
already hold every line with its amount and category, so this adds them up:
by category, by shop, by person or by month, one currency at a time, with
the document behind every row one click away. A reader sees what was read on
their own behalf; an administrator of the workspace sees all of it.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

KINDS = ("Receipt", "Invoice")
GROUPS = {"Category": "category", "Shop": "shop", "Person": "person", "Month": "month"}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	group = GROUPS.get(filters.get("group_by") or "Category", "category")
	rows = lines(filters)
	totals: dict[tuple, dict] = {}
	for one in rows:
		key = (one[group] or _("Other"), one["currency"] or "")
		held = totals.setdefault(key, {"what": key[0], "currency": key[1], "amount": 0.0, "count": 0, "documents": set()})
		held["amount"] += flt(one["amount"])
		held["documents"].add(one["reading"])
	data = [
		{"what": held["what"], "currency": held["currency"], "amount": held["amount"], "documents": len(held["documents"])}
		for held in sorted(totals.values(), key=lambda one: -one["amount"])
	]
	columns = [
		{"fieldname": "what", "label": _(filters.get("group_by") or "Category"), "fieldtype": "Data", "width": 220},
		{"fieldname": "amount", "label": _("Spent"), "fieldtype": "Currency", "options": "currency", "width": 140},
		{"fieldname": "currency", "label": _("Currency"), "fieldtype": "Link", "options": "Currency", "width": 90},
		{"fieldname": "documents", "label": _("Documents"), "fieldtype": "Int", "width": 110},
	]
	return columns, data


def lines(filters) -> list[dict]:
	"""Every spent line in the period the reader may see: a document's lines,
	or its total when it was read without them."""
	from onedesk.one.roles import administers

	conditions = {"state": "Understood", "kind": ["in", KINDS], "issued_on": ["between", [filters.get("from_date"), filters.get("to_date")]]}
	if not administers():
		conditions["on_behalf_of"] = frappe.session.user
	readings = frappe.get_all(
		"Reading",
		filters=conditions,
		fields=["name", "issued_on", "currency", "gross", "on_behalf_of", "paid_how"],
		limit=5000,
	)
	if not readings:
		return []
	names = [one.name for one in readings]
	shops = {
		row.parent: row.party_name
		for row in frappe.get_all("Reading Party", filters={"parent": ["in", names], "role": ["in", ("Sender", "Paid To")]}, fields=["parent", "party_name"])
	}
	by_reading: dict[str, list] = {}
	for row in frappe.get_all("Reading Line", filters={"parent": ["in", names]}, fields=["parent", "amount", "category"]):
		by_reading.setdefault(row.parent, []).append(row)
	out = []
	for one in readings:
		base = {
			"reading": one.name,
			"shop": shops.get(one.name),
			"person": frappe.db.get_value("User", one.on_behalf_of, "full_name") if one.on_behalf_of else None,
			"month": getdate(one.issued_on).strftime("%Y-%m") if one.issued_on else None,
			"currency": one.currency,
		}
		held = [row for row in by_reading.get(one.name, []) if row.amount is not None]
		if held:
			out += [{**base, "amount": row.amount, "category": row.category} for row in held]
		elif one.gross:
			out.append({**base, "amount": one.gross, "category": None})
	return out
