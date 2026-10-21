"""A document's version history: what it said at a moment, named by somebody
or taken while it was being written, and put back from the history panel.
Suite's policy: the editor offers a version every ten minutes of writing,
and one is kept if the last taken was ten minutes ago or more. README,
Version history.
"""

from datetime import datetime, timedelta

import frappe

from onedesk.one_doc import api

VERSION = "Writer Document Version"

#: The least time between two versions taken while writing.
EVERY = timedelta(minutes=10)

#: Versions taken while writing kept per document; named ones are all kept.
KEPT = 100

STAMP = "%Y-%m-%d %H:%M"


@frappe.whitelist(methods=["POST"])
def new_version(name: str, data: str, title: str | None = None) -> dict | None:
	"""A version of the document as `data` (its HTML): named when `title` is
	given, else taken unless one was taken in the last ten minutes."""
	api._may(name, "write")
	if not data or not data.strip() or data.strip() == "<p></p>":
		return None
	title = " ".join((title or "").split())[: api.MOST_TITLE]
	if not title:
		last = frappe.db.get_value(VERSION, {"document": name, "manual": 0}, "creation", order_by="creation desc")
		if last and frappe.utils.now_datetime() - last < EVERY:
			return None
	made = frappe.get_doc(
		{
			"doctype": VERSION,
			"document": name,
			"snapshot": data,
			"manual": 1 if title else 0,
			"title": title or datetime.strftime(frappe.utils.now_datetime(), STAMP),
		}
	)
	made.flags.ignore_permissions = True
	made.insert()
	return {"name": made.name, "title": made.title, "manual": made.manual, "snapshot": made.snapshot, "creation": made.creation}


@frappe.whitelist()
@frappe.read_only()
def listed(id: str) -> list[dict]:
	"""The document's versions, oldest first, as the history panel shows them."""
	api._may(id, "read")
	return frappe.get_all(VERSION, filters={"document": id}, fields=["name", "snapshot", "title", "manual", "creation"], order_by="creation asc")


def forget(name: str) -> None:
	"""A document's history, gone with it."""
	frappe.db.delete(VERSION, {"document": name})


def tidy() -> None:
	"""Daily: each document keeps its newest hundred versions taken while
	writing, and every named one."""
	for row in frappe.db.sql(
		f"select document from `tab{VERSION}` where manual = 0 group by document having count(*) > %s", KEPT, as_dict=True
	):
		old = frappe.get_all(VERSION, filters={"document": row.document, "manual": 0}, order_by="creation desc", pluck="name", start=KEPT, limit=10000)
		if old:
			frappe.db.delete(VERSION, {"name": ["in", old]})
