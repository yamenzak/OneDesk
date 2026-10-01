"""The Audit Log: who changed what, who signed in, and what left the workspace
as a file. docs/DESK-COVERAGE.md, P2.

Frappe already writes all three: a `Version` for every change to a record that
tracks its changes, an `Activity Log` for every sign-in and sign-out (failed
ones too), and an `Access Log` for every export, printed PDF and private file
downloaded. Reading them is its System Manager's, whom no workspace has, so
nobody here could answer "who changed this price?" across the workspace. Now
a workspace administrator reads them, as frappe's own lists, with three
limits:

- only changes to, and exports of, the kinds of record they may read, plus
  people's accounts and what they may do (the `PEOPLE` kinds), so the log
  shows no salary to somebody who cannot open a salary slip;
- never frappe's own machinery or the platform's records;
- never what the system did (`SYSTEM`): a scheduler, a patch or an operator
  signed in as Administrator, which is the platform's, not the workspace's.

Nobody writes to it: frappe writes every row, and nobody here may change or
delete one. Frappe clears sign-ins after 90 days; changes and exports are
kept. Audit Trail, frappe's comparison of a document's amendments, stays
out: every submitted record's own timeline already shows each version.
"""

import frappe
from frappe.permissions import get_doctypes_with_read

from onedesk.one import roles
from onedesk.one.customize import REFUSED_MODULES

GRANTS = {
	"Version": ("read", "report"),
	"Activity Log": ("read", "report"),
	"Access Log": ("read", "report"),
}

#: Who acts as the system rather than as a person.
SYSTEM = ("Administrator", "Guest", "oneai@one.invalid")

#: Core's records that are the workspace's own and worth auditing: who may
#: use the workspace and what they may do. Changes to them are the first
#: thing an audit asks about.
PEOPLE = ("User", "User Permission", "Role Profile", "User Group")

#: A downloaded file is a `File`, which is Core's; who took which one is the
#: point of the log.
DOWNLOADS = ("File",)


def settle() -> None:
	roles.grant(GRANTS)


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
