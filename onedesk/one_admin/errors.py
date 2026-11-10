"""Errors, gathered from every workspace: `heard` keeps one row for each
workspace and kind of error, and an operator is told when a kind nobody has
seen before appears (one/errors.py is the workspace's side)."""

import frappe
from frappe.utils import add_days, cint, get_datetime, now_datetime

from onedesk.one import ready
from onedesk.one_admin import tell

DOCTYPE = "Workspace Error"
MOST_ROWS = 200
TITLE_LONG = 140
MOST_TOLD = 3
MOST_LISTED = 20
APPS = {"frappe": "Frappe", "erpnext": "ERPNext", "hrms": "Frappe HR"}
FOLDERS = {one["folder"]: name for name, one in ready.MODULES.items()}


def part_of(where: str, title: str = "") -> str:
	"""Which part of One an error happened in, from where in the code it
	was: `onedesk/onedesk/one_mail/x.py:send` is OneMail. Pure."""
	pieces = (where or "").split("/")
	if pieces[0] == "onedesk" and len(pieces) > 3:
		folder = pieces[2]
	elif (title or "").startswith("onedesk.") and title.count(".") > 1:
		folder = title.split(".")[1]
	elif pieces[0] in APPS:
		return APPS[pieces[0]]
	else:
		return "One"
	if folder in FOLDERS:
		return FOLDERS[folder]
	return "One" + "".join(word.title() for word in folder.split("_")[1:]) if folder.startswith("one_") else "One"


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


def new_kinds(since) -> list[dict]:
	"""The kinds of error no workspace had before `since`, first made since:
	one row each, oldest first."""
	fields = ["name", "tenant", "title", "kind", "where_in_code", "occurrences", "fingerprint"]
	made = frappe.get_all(DOCTYPE, filters={"creation": [">=", since]}, fields=fields, order_by="creation asc")
	if not made:
		return []
	older = set(frappe.get_all(DOCTYPE, filters={"creation": ["<", since], "fingerprint": ["in", list({one.fingerprint for one in made})]}, pluck="fingerprint"))
	seen, kept = set(), []
	for one in made:
		if one.fingerprint in older or one.fingerprint in seen:
			continue
		seen.add(one.fingerprint)
		kept.append(one)
	return kept


def today() -> None:
	"""Daily: the operators mailed the kinds of error new since yesterday,
	in one notification, or nothing when there were none."""
	from onedesk.one_admin import site

	if site.is_admin():
		tell.errors_today(new_kinds(add_days(now_datetime(), -1)))
