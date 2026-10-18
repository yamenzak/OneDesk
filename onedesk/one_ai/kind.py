"""A kind of record as whatever fills one in needs to know it, and whether a
record of it is ready to be made. One place for OneAI's cards and tools and
for Intake, so each reads a kind the same way.
"""

import frappe
from frappe.utils import strip_html_tags

LAYOUT = {"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Heading", "Image", "Fold"}

NEVER_READ = ("Password",)

TYPED = "__newname"

READY = "one_ai_ready"


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


def ready(doctype: str, changes: dict) -> None:
	"""Refuse a new record now that frappe would refuse when it is made.

	Frappe's own checks on a document that is never saved, inside a savepoint that
	is always rolled back, then what is still `missing`.
	"""
	meta = frappe.get_meta(doctype)
	unknown = [
		key
		for key in changes
		if not meta.has_field(key) and key not in frappe.model.default_fields and key != TYPED
	]
	doc = frappe.new_doc(doctype)
	doc.update(changes)
	rows = [doc, *(row for table in doc.meta.get_table_fields() for row in doc.get(table.fieldname) or [])]

	bad, wrong = [], set()
	for one in rows:
		invalid, _cancelled = one.get_invalid_links()
		bad += [f"Could not find {said}" for _field, _value, said in invalid]
		wrong |= {field for field, _value, _said in invalid}

	muted = frappe.flags.mute_messages
	frappe.db.savepoint(READY)
	frappe.flags.mute_messages = True
	try:
		for one in rows:
			one._fix_numeric_types()
		doc.run_method("before_validate")
		doc.run_method("validate")
	except frappe.ValidationError as refused:
		bad.append(strip_html_tags(str(refused)).strip())
	except Exception:
		pass
	finally:
		frappe.flags.mute_messages = muted
		frappe.db.rollback(save_point=READY)

	needed = [f"{label} ({fieldname})" for fieldname, label in missing(doc) if fieldname not in wrong]
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
