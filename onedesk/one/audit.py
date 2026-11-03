"""The Audit Log: who changed what, who signed in, and what left the workspace
as a file.

Frappe already writes all three (Version, Activity Log, Access Log); a
workspace administrator reads them as one list in AccessCenter (`log`), each
row opening frappe's own record, with the limits below.
"""

import frappe
from frappe import _
from frappe.permissions import get_doctypes_with_read

from onedesk.one import roles
from onedesk.one_studio.customize import REFUSED_MODULES

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


KINDS = {
	"changes": ("Version", ["name", "ref_doctype", "docname", "owner", "creation"]),
	"signins": ("Activity Log", ["name", "subject", "operation", "status", "user", "full_name", "ip_address", "creation"]),
	"exports": ("Access Log", ["name", "export_from", "reference_document", "file_type", "report_name", "method", "user", "creation"]),
}


def _said(kind: str, row) -> dict:
	"""One row as AccessCenter's Audit Log draws it: what happened, to what,
	by whom and when, and the record it opens."""
	if kind == "changes":
		what, of, who = _("Changed"), f"{_(row.ref_doctype)} {row.docname}", row.owner
	elif kind == "signins":
		# Activity Log's subject already says who did what ("Layla Haddad
		# logged in"); a failure says so after it.
		what, of, who = row.subject or _(row.operation or "Login"), "", row.full_name or row.user
		if row.status and row.status != "Success":
			what = f"{what} ({_(row.status)})"
	else:
		what = _("Printed") if row.method and "print" in row.method.lower() else _("Exported")
		of, who = " ".join(one for one in (_(row.export_from) if row.export_from else "", row.reference_document or row.report_name or "") if one), row.user
	return {
		"kind": kind,
		"doctype": KINDS[kind][0],
		"name": row.name,
		"what": what,
		"of": of,
		"who": who,
		"when": str(row.creation),
		"ip": row.get("ip_address"),
	}


@frappe.whitelist()
@frappe.read_only()
def log(kind: str | None = None, limit: int = 60) -> list[dict]:
	"""The newest of the three logs as one list, or of one kind; each read
	through frappe's own list, so its permission query (above) holds.
	Workspace administrators only."""
	roles.require()
	limit = max(1, min(int(limit or 60), 200))
	rows = []
	for key, (doctype, fields) in KINDS.items():
		if kind and kind != key:
			continue
		for row in frappe.get_list(doctype, fields=fields, order_by="creation desc", limit_page_length=limit):
			rows.append(_said(key, row))
	return sorted(rows, key=lambda one: one["when"], reverse=True)[:limit]
