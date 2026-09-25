"""Fields of another record, edited on this one and saved with it.

"Put the employee's mobile on this form" means a field of a different record.
Frappe's `fetch_from` copies it, which gives two values that drift apart and
cannot be edited here. A **Linked Section** on a record's head
(one/head.py) names a Link field of the record and fields of the record it
points at; they draw as a section of the form with frappe's own controls, and
are saved like this (docs/SHELL.md, decision 5):

- **One save, one transaction.** The form sends what changed in the linked
  record, and the `modified` it loaded, with its own document
  (`__one_linked`; frappe keeps a key it does not know on the document it
  saves). `save`, on the record's on_update, saves the linked record in the
  same request, so if either fails both roll back and there is never half a
  save.
- **A clash is frappe's.** The linked record is saved against the `modified`
  the form loaded, so a change somebody made meanwhile is refused with the
  record named, and nothing is overwritten. The form hears the linked
  record's `doc_update` too, and says so before Save is pressed.
- **Permissions are the linked record's**, down to the field. Its fields are
  read-only for a reader who may not write it, and the section is not drawn
  for one who may not read it. A field above permission level nought is
  hidden from a reader without read at that level and read-only without
  write, as it is on the record's own form. On a submitted record only
  fields it allows on submit are editable; on a cancelled one none are.
- **A child table is the linked record's table**, drawn as frappe's own grid:
  rows are added, edited, moved and deleted there, and the whole table is
  sent and set on the linked record, so frappe updates, inserts and deletes
  the rows as it would from that record's form. The rows on this form are
  copies under names of their own, so a form of the linked record open
  elsewhere keeps its own.
- **Not** computed or fetched fields, or a second link onward: those are a
  Connection, or a report.
"""

import json
import re

import frappe
from frappe import _
from frappe.utils import cstr

#: The form's own name for a linked field, which no field of a record has.
PREFIX = "one_linked__"

#: What a linked section may not show: layout, and what is computed.
REFUSED = {
	"Section Break",
	"Column Break",
	"Tab Break",
	"HTML",
	"Button",
	"Image",
	"Fold",
	"Heading",
	"Read Only",
}

#: A linked record's child tables, drawn as frappe's grid.
TABLES = ("Table", "Table MultiSelect")

#: The docfield properties the form draws a linked field with.
DRAWN = ("fieldtype", "label", "options", "description", "precision", "length", "non_negative")


def fieldname(link_field: str, field: str) -> str:
	"""The form's name for a linked record's field. Pure."""
	return f"{PREFIX}{link_field}__{field}"


def names(text: str | None) -> list[str]:
	"""A section's fields, one to a line or split by commas, once each. Pure."""
	seen = []
	for name in re.split(r"[\s,]+", text or ""):
		if name and name not in seen:
			seen.append(name)
	return seen


def refused(df) -> str | None:
	"""Why a field of the linked record cannot be edited here, if it cannot.
	Pure over the docfield."""
	label = _(df.get("label") or df.get("fieldname") or "")
	if df.fieldtype in REFUSED:
		return _("{0} is not a field to edit.").format(label)
	if df.get("is_virtual") or df.get("fetch_from") or df.get("read_only"):
		return _("{0} is worked out, not typed.").format(label)
	return None


def placing(source: list[tuple[str, str]], chosen: list[str]) -> list[str]:
	"""The chosen fields laid out as the linked record's own form lays them:
	a field in a later column of the same section of that form goes into a
	new column here, one in another section, or any table, starts a section
	of its own. `source` is the linked form's fields in order, as (fieldname,
	fieldtype). Returns fieldnames with "|" for a column break and "-" for a
	section break. Pure."""
	where, section, column = {}, 0, 0
	for name, fieldtype in source:
		if fieldtype in ("Section Break", "Tab Break"):
			section, column = section + 1, 0
		elif fieldtype == "Column Break":
			column += 1
		else:
			where[name] = (section, column, fieldtype in TABLES)
	out, last = [], None
	for name in chosen:
		now = where.get(name, (0, 0, False))
		if last is not None:
			if now[2] or last[2] or now[0] != last[0] or now[1] < last[1]:
				out.append("-")
			elif now[1] > last[1]:
				out.append("|")
		out.append(name)
		last = now
	return out


def columns(doctype: str) -> list[str]:
	"""The fields a child row holds a value in."""
	return [
		df.fieldname
		for df in frappe.get_meta(doctype).fields
		if df.fieldtype not in frappe.model.no_value_fields
	]


def rows(doc, fieldname: str) -> list[dict]:
	"""A child table as the form is sent it: each row's values, by the row's
	own name."""
	table = doc.meta.get_field(fieldname).options
	return [
		{"name": row.name, **{name: row.get(name) for name in columns(table)}} for row in doc.get(fieldname)
	]


def as_rows(doc, fieldname: str, sent: list) -> list[dict]:
	"""A table the form sent, as rows to set on the linked record: a row that
	was the record's keeps its name, so frappe updates it; any other is new;
	one left out is deleted."""
	table = doc.meta.get_field(fieldname).options
	own = {row.name for row in doc.get(fieldname)}
	out = []
	for row in sent or []:
		kept = {name: row.get(name) for name in columns(table) if name in row}
		if row.get("name") in own:
			kept["name"] = row["name"]
		out.append(kept)
	return out


def validate(head) -> None:
	"""Each section goes through a link of the record, to fields the linked
	record has and a person may type. Called by head.validate."""
	meta = frappe.get_meta(head.record_doctype)
	for row in head.get("linked") or []:
		where = _("Linked section {0}").format(row.idx)
		link = meta.get_field(row.link_field)
		if not link or link.fieldtype != "Link":
			frappe.throw(_("{0} goes through {1}, which is not a link.").format(where, row.link_field))
		if row.placed_in and not meta.get_field(row.placed_in):
			frappe.throw(
				_("{0} names {1}, which {2} does not have.").format(
					where, row.placed_in, _(head.record_doctype)
				)
			)
		linked = frappe.get_meta(link.options)
		if not names(row.fields):
			frappe.throw(_("{0} shows nothing.").format(where))
		for name in names(row.fields):
			df = linked.get_field(name)
			if not df:
				frappe.throw(
					_("{0} names {1}, which {2} does not have.").format(where, name, _(link.options))
				)
			if reason := refused(df):
				frappe.throw(f"{where}: {reason}")


# ------------------------------------------------------------------ what the form is given


def for_boot(bootinfo=None) -> dict:
	"""The sections each doctype's form draws, for this person: none through a
	doctype they may not read. The form builds its layout from these once. A
	child table's own doctype goes into the boot's docs, as a form's tables'
	do into its meta, so frappe's grid has it before the form is drawn."""
	from frappe.desk.form.meta import get_meta

	from onedesk.one import head

	found = {}
	tables = set()
	for doctype in sorted(head.headed()):
		rows = frappe.get_cached_doc("Record Head", doctype).get("linked") or []
		meta = frappe.get_meta(doctype)
		for row in rows:
			link = meta.get_field(row.link_field)
			if not link or not frappe.has_permission(link.options, "read"):
				continue
			linked = frappe.get_meta(link.options)
			fields, layout = [], []
			chosen = [
				name
				for name in names(row.fields)
				if linked.get_field(name) and not refused(linked.get_field(name))
			]
			source = [(df.fieldname, df.fieldtype) for df in linked.fields]
			for i, name in enumerate(placing(source, chosen)):
				if name in ("|", "-"):
					layout.append(
						{"fieldtype": "Column Break", "fieldname": f"{fieldname(row.link_field, '')}c{i}"}
						if name == "|"
						else {
							"fieldtype": "Section Break",
							"fieldname": f"{fieldname(row.link_field, '')}s{i}",
							"hide_border": 1,
						}
					)
					continue
				df = linked.get_field(name)
				if df.fieldtype in TABLES:
					tables.add(df.options)
				drawn = {
					**{key: df.get(key) for key in DRAWN if df.get(key)},
					"label": _(df.label),
					"fieldname": fieldname(row.link_field, name),
					"one_linked": name,
				}
				fields.append(drawn)
				layout.append(drawn)
			found.setdefault(doctype, []).append(
				{
					"label": _(row.label),
					"link_field": row.link_field,
					"doctype": link.options,
					"placed_in": row.placed_in or None,
					"fields": fields,
					"layout": layout,
				}
			)
	if bootinfo is not None:
		bootinfo.setdefault("docs", []).extend(get_meta(table) for table in sorted(tables))
	return found


def loaded(doc, head) -> dict:
	"""Each linked record as the reader may see it: its values, the
	`modified` a save is checked against, and which fields they may change."""
	out = {}
	meta = doc.meta
	for row in head.get("linked") or []:
		target = doc.get(row.link_field)
		link = meta.get_field(row.link_field)
		if not target or not link or not frappe.has_permission(link.options, "read", target):
			continue
		linked = frappe.get_doc(link.options, target)
		writable = linked.docstatus < 2 and bool(linked.has_permission("write"))
		fields = [name for name in names(row.fields) if linked.meta.get_field(name)]
		# What the reader's permission levels keep from them, as frappe's own
		# form would.
		hidden = [name for name in fields if not linked.has_permlevel_access_to(name, permission_type="read")]
		shown = [name for name in fields if name not in hidden]
		out[row.link_field] = {
			"doctype": link.options,
			"name": target,
			"title": linked.get_title() or target,
			"modified": cstr(linked.modified),
			"values": {
				name: rows(linked, name)
				if linked.meta.get_field(name).fieldtype in TABLES
				else linked.get(name)
				for name in shown
			},
			"hidden": hidden,
			"locked": [
				name
				for name in shown
				if not writable
				or not linked.has_permlevel_access_to(name, permission_type="write")
				or (linked.docstatus == 1 and not linked.meta.get_field(name).allow_on_submit)
			],
		}
	return out


# ------------------------------------------------------------------ saved with the record


def save(doc, method=None) -> None:
	"""The linked records' changes the form sent with this one, saved in the
	same transaction, each against the `modified` it was loaded at."""
	sent = doc.get("__one_linked")
	if not sent:
		return
	if isinstance(sent, str):
		sent = json.loads(sent)
	from onedesk.one import head

	sections = (
		{row.link_field: row for row in frappe.get_cached_doc("Record Head", doc.doctype).get("linked") or []}
		if doc.doctype in head.headed()
		else {}
	)
	for link_field, change in sent.items():
		row = sections.get(link_field)
		if not row:
			frappe.throw(_("{0} has no section through {1}.").format(_(doc.doctype), link_field))
		if change.get("name") != doc.get(link_field):
			frappe.throw(
				_("{0} changed in this save. Save it first, then edit what it links to.").format(
					_(doc.meta.get_label(link_field))
				)
			)
		values = change.get("values") or {}
		strange = set(values) - set(names(row.fields))
		if strange:
			frappe.throw(_("{0} are not in this section.").format(", ".join(sorted(strange))))
		if not values:
			continue
		doctype = doc.meta.get_field(link_field).options
		linked = frappe.get_doc(doctype, change["name"])
		linked.check_permission("write")
		if cstr(linked.modified) != cstr(change.get("modified")):
			frappe.throw(
				_(
					"{0} {1} was changed by somebody else after you opened this. Refresh to see it; nothing was saved."
				).format(_(doctype), linked.get_title() or linked.name),
				frappe.TimestampMismatchError,
			)
		if linked.docstatus == 2 or (
			linked.docstatus == 1 and any(not linked.meta.get_field(name).allow_on_submit for name in values)
		):
			frappe.throw(
				_("{0} {1} is submitted, and these cannot change now.").format(_(doctype), linked.name)
			)
		kept = [name for name in values if not linked.has_permlevel_access_to(name, permission_type="write")]
		if kept:
			frappe.throw(
				_("{0} cannot be changed by you.").format(
					", ".join(_(linked.meta.get_label(name)) for name in kept)
				),
				frappe.PermissionError,
			)
		for name, value in values.items():
			if linked.meta.get_field(name).fieldtype in TABLES:
				linked.set(name, as_rows(linked, name, value))
			else:
				linked.set(name, value)
		linked.save()
	doc.__one_linked = None
