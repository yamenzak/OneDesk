"""The Audit Log: who changed what, who signed in, and what left the workspace
as a file.

Frappe already writes all three (Version, Activity Log, Access Log); a
workspace administrator reads them here, as frappe's own lists, with limits.
"""

import frappe
from frappe.permissions import get_doctypes_with_read

from onedesk.one import roles
from onedesk.one.customize import REFUSED_MODULES

SYSTEM = ("Administrator", "Guest", "oneai@one.invalid")

PEOPLE = ("User", "User Permission", "Role Profile", "User Group")

DOWNLOADS = ("File",)


def _trusted(user: str) -> bool:
	return user == "Administrator"


def kinds(extra: tuple = ()) -> list[str]:
	"""The kinds of record whose changes and exports the reader sees."""
	readable = set(get_doctypes_with_read())
	left_out = set(
		frappe.get_all("DocType", filters={"module": ["in", list(REFUSED_MODULES)]}, pluck="name")
	) | set(frappe.get_all("DocType", filters={"istable": 1}, pluck="name"))
	return sorted((readable - left_out) | (readable & set(PEOPLE + extra)))


def _in(column: str, values) -> str:
	listed = ", ".join(frappe.db.escape(one) for one in values) or "''"
	return f"{column} in ({listed})"


def _not_system(column: str) -> str:
	return f"{column} not in ({', '.join(frappe.db.escape(one) for one in SYSTEM)})"


def version_query(user: str | None = None) -> str | None:
	user = user or frappe.session.user
	if _trusted(user):
		return None
	if not roles.administers(user):
		return "1=0"
	return f"({_in('`tabVersion`.`ref_doctype`', kinds())} and {_not_system('`tabVersion`.`owner`')})"


def activity_query(user: str | None = None) -> str | None:
	user = user or frappe.session.user
	if _trusted(user):
		return None
	if not roles.administers(user):
		return "1=0"
	table = "`tabActivity Log`"
	return (
		f"({_not_system(f'{table}.`user`')} and ({table}.`reference_doctype` is null"
		f" or {table}.`reference_doctype` = '' or {_in(f'{table}.`reference_doctype`', kinds())}))"
	)


def access_query(user: str | None = None) -> str | None:
	user = user or frappe.session.user
	if _trusted(user):
		return None
	if not roles.administers(user):
		return "1=0"
	table = "`tabAccess Log`"
	return f"({_in(f'{table}.`export_from`', kinds(DOWNLOADS))} and {_not_system(f'{table}.`user`')})"


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	"""has_permission for all three: read only, by an administrator, of what
	the lists show."""
	user = user or frappe.session.user
	if _trusted(user):
		return True
	if ptype not in ("read", "report", None) or not roles.administers(user):
		return False
	if doc.doctype == "Version":
		return doc.owner not in SYSTEM and doc.ref_doctype in kinds()
	if doc.doctype == "Activity Log":
		return doc.user not in SYSTEM and (not doc.reference_doctype or doc.reference_doctype in kinds())
	return doc.user not in SYSTEM and doc.export_from in kinds(DOWNLOADS)


def _unseen(doctype: str, user: str | None = None) -> set:
	"""Fields of a kind the reader may not read: those at a level their roles
	do not reach (a salary above the people officer's, say)."""
	meta = frappe.get_meta(doctype)
	levels = meta.get_permlevel_access("read", user=user) | {0}
	return {df.fieldname for df in meta.fields if df.permlevel not in levels}


def seen(data: str | dict, doctype: str, user: str | None = None) -> dict:
	"""A change as the reader may see it: without the fields, or the rows of
	tables, they may not read."""
	data = frappe.parse_json(data) or {}
	if _trusted(user or frappe.session.user):
		return data
	unseen = _unseen(doctype, user)
	rows_unseen = {}

	def row_hidden(table: str) -> set:
		if table not in rows_unseen:
			df = frappe.get_meta(doctype).get_field(table)
			rows_unseen[table] = _unseen(df.options, user) if df and df.options else set()
		return rows_unseen[table]

	said = dict(data)
	said["changed"] = [one for one in data.get("changed") or [] if one[0] not in unseen]
	for key in ("added", "removed"):
		said[key] = [
			[table, {k: v for k, v in (row or {}).items() if k not in row_hidden(table)}]
			for table, row in data.get(key) or []
			if table not in unseen
		]
	said["row_changed"] = [
		[table, idx, name, [one for one in changes if one[0] not in row_hidden(table)]]
		for table, idx, name, changes in data.get("row_changed") or []
		if table not in unseen
	]
	return said


def onload(doc, method=None) -> None:
	"""doc_events: a Version opened shows only what its reader may read."""
	if not _trusted(frappe.session.user):
		doc.data = frappe.as_json(seen(doc.data, doc.ref_doctype))
