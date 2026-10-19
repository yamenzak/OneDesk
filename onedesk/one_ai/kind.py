"""A kind of record as whatever fills one in needs to know it, and whether a
record of it is ready to be made. One place for OneAI's cards and tools and
for Intake, so each reads a kind the same way.
"""

import re

import frappe
from frappe.utils import strip_html_tags

LAYOUT = {"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Heading", "Image", "Fold"}

NEVER_READ = ("Password",)

TYPED = "__newname"

READY = "one_ai_ready"

# A value that points at another card's record, which does not exist until
# that card is approved: "@PROP-26-000042".
REF = re.compile(r"^@(PROP-[\w-]+)$")


def refs(changes) -> list[str]:
	"""The cards a card's values point at, in the order they appear."""
	found = []
	for value in (changes or {}).values():
		rows = value if isinstance(value, list) else [value]
		for one in rows:
			if isinstance(one, dict):
				found += refs(one)
			elif isinstance(one, str) and REF.match(one):
				found.append(REF.match(one).group(1))
	return list(dict.fromkeys(found))


def resolved(changes: dict, made: dict) -> dict:
	"""The values with every pointer at a card replaced by the record it made."""

	def one(value):
		if isinstance(value, dict):
			return resolved(value, made)
		if isinstance(value, list):
			return [one(row) for row in value]
		if isinstance(value, str) and REF.match(value):
			return made.get(REF.match(value).group(1), value)
		return value

	return {key: one(value) for key, value in (changes or {}).items()}


def naming(doctype: str) -> dict:
	"""How a new record of a kind gets its name, as frappe's set_new_name
	decides it: `by` is series, field, expression, typed, random or code, with
	the field when it is named by one."""
	from frappe.model.base_document import get_controller

	meta = frappe.get_meta(doctype)
	autoname = (meta.autoname or "").strip()
	lowered = autoname.lower()
	try:
		coded = hasattr(get_controller(doctype), "autoname")
	except Exception:
		coded = False
	if coded:
		return {"by": "code"}
	if lowered.startswith("naming_series:"):
		return {"by": "series", "field": "naming_series"}
	if lowered.startswith("field:"):
		return {"by": "field", "field": autoname[6:]}
	if lowered == "prompt":
		return {"by": "typed", "field": TYPED}
	if lowered in ("", "hash", "uuid", "autoincrement"):
		return {"by": "random"}
	return {"by": "expression", "pattern": autoname}


def fields(meta, depth: int = 0, printing: bool = False) -> list:
	"""A kind's fields as a model needs them to fill a form in, or, printing,
	to lay a page out. Hidden fields and what the reader may not see are left
	out, and a field the system fills is said to be.
	"""
	said = []
	for f in meta.fields:
		if f.fieldtype in LAYOUT or f.fieldtype in NEVER_READ or f.hidden:
			continue
		if printing:
			kind = f"Link to {f.options}" if f.fieldtype == "Link" and f.options else f.fieldtype
			line = f"{f.fieldname} ({f.label or f.fieldname}, {kind}{', not printed' if f.print_hide else ''})"
			if f.fieldtype in frappe.model.table_fields and depth == 0:
				said.append({"table": line, "rows": fields(frappe.get_meta(f.options), depth + 1, printing=True)})
			else:
				said.append(line)
			continue
		one = {"fieldname": f.fieldname, "label": f.label, "fieldtype": f.fieldtype}
		if f.reqd:
			one["required"] = True
		if f.mandatory_depends_on:
			one["required_when"] = f.mandatory_depends_on
		if f.depends_on:
			one["shown_when"] = f.depends_on
		if f.read_only or f.fetch_from:
			one["filled_by_the_system"] = True
		if f.unique:
			one["unique"] = True
		if f.default not in (None, ""):
			one["default"] = f.default
		if f.fieldtype == "Select":
			one["options"] = [o for o in (f.options or "").split("\n") if o]
		elif f.fieldtype in ("Link", "Dynamic Link"):
			one["links_to"] = f.options
		elif f.fieldtype in frappe.model.table_fields and depth == 0:
			one["rows"] = fields(frappe.get_meta(f.options), depth + 1)
		if f.description:
			one["description"] = strip_html_tags(f.description)[:200]
		said.append(one)
	return said


def describe(doctype: str) -> dict:
	"""A kind of record: its fields and how a new one is named."""
	named = naming(doctype)
	said = {"doctype": doctype, "fields": fields(frappe.get_meta(doctype)), "naming": named}
	if named["by"] == "typed":
		said["naming"]["say"] = f"Whoever makes one types its name: give it as {TYPED}."
	elif named["by"] == "field":
		said["naming"]["say"] = f"A new one is named by its {named['field']}, which must be new each time."
	return said


def fields_of(meta, most: int = 80) -> list[str]:
	"""A kind's fields as a line each for a message to a model: "fieldname
	(Label, Link to Customer, required)", hidden and layout ones left out."""
	lines = []
	for f in meta.fields:
		if f.fieldtype in LAYOUT or f.fieldtype in NEVER_READ or f.hidden:
			continue
		said = [f.label or f.fieldname]
		if f.fieldtype in ("Link", "Dynamic Link") and f.options:
			said.append(f"Link to {f.options}")
		elif f.fieldtype == "Select" and f.options:
			said.append("one of " + " | ".join(o for o in f.options.split("\n") if o)[:120])
		if f.reqd:
			said.append("required")
		lines.append(f"{f.fieldname} ({', '.join(said)})")
	return lines[:most]


def missing(doc) -> list[tuple[str, str]]:
	"""What a record, and each of its rows, still needs before frappe saves
	it, as (fieldname, label): frappe's own required fields, and the name
	where the kind is named by a field or typed. A row's parent is set on save
	and is never missing."""
	out = []
	rows = [doc, *(row for table in doc.meta.get_table_fields() for row in doc.get(table.fieldname) or [])]
	for one in rows:
		for fieldname, _msg in one._get_missing_mandatory_fields():
			if fieldname not in ("parent", "parenttype"):
				out.append((fieldname, one.meta.get_label(fieldname)))
	named = naming(doc.doctype)
	if named["by"] == "typed" and not (doc.get(TYPED) or doc.get("name")):
		out.append((TYPED, "Name"))
	elif named["by"] == "field" and not doc.get(named["field"]):
		out.append((named["field"], doc.meta.get_label(named["field"])))
	return list(dict.fromkeys(out))


def ready(doctype: str, changes: dict, before: list | tuple = ()) -> None:
	"""Refuse a new record now that frappe would refuse when it is made.

	It is inserted as Approve will insert it, in a savepoint always rolled
	back, after the cards it points at (`before`: card, kind, values, in
	order). README, kind.py."""
	meta = frappe.get_meta(doctype)
	unknown = [
		key
		for key in changes
		if not meta.has_field(key) and key not in frappe.model.default_fields and key != TYPED
	]
	bad, short = [], False
	muted = frappe.flags.mute_messages
	frappe.db.savepoint(READY)
	frappe.flags.mute_messages = True
	try:
		made = {}
		for card, kind, values in before:
			try:
				first = frappe.get_doc({"doctype": kind, **resolved(values, made)})
				first.insert()
				made[card] = first.name
			except Exception as refused:
				bad.append(f"The card {card} it points at would not be made: {strip_html_tags(str(refused)).strip()}")
		doc = frappe.new_doc(doctype)
		doc.update(resolved(changes, made))
		try:
			doc.insert()
		except frappe.MandatoryError:
			short = True
		except frappe.ValidationError as refused:
			bad.append(strip_html_tags(str(refused)).strip())
		except Exception:
			pass
	finally:
		frappe.flags.mute_messages = muted
		frappe.local.message_log = []
		frappe.db.rollback(save_point=READY)

	needed = [f"{label} ({fieldname})" for fieldname, label in missing(doc)] if short or not bad else []
	if needed:
		bad.insert(0, "Still needed: " + ", ".join(needed))
	if unknown:
		bad.insert(
			0, f"{doctype} has no field {', '.join(unknown)}. Its fields: {', '.join(fields_of(meta))}"
		)
	if bad:
		frappe.throw(
			". ".join(one.rstrip(".") for one in dict.fromkeys(bad))
			+ ". "
			+ "Correct what you can from what the person already said and suggest it again; ask them only for what they have not said.",
			frappe.MandatoryError,
		)
