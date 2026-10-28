"""Where a requested file goes on a record (file_requests.py): a file field
on the record itself (`image`), or one in a row of one of its tables
(`one_documents.attachment`), read from the record's own fields. How a row is
picked and what is asked with it is in the README, under Under the hood."""

import frappe
from frappe import _

ATTACH = ("Attach", "Attach Image")

ASKED = ("Data", "Date", "Datetime", "Int", "Float", "Currency", "Percent", "Small Text", "Text", "Select", "Check", "Phone")

KINDS = ("Link", "Select")

MOST_KINDS = 200


def of(doctype: str) -> list[dict]:
	"""Every place on a record of this kind a requested file can go."""
	meta = frappe.get_meta(doctype)
	out = [
		{"value": one.fieldname, "label": _(one.label or one.fieldname)}
		for one in meta.fields
		if one.fieldtype in ATTACH and (not one.hidden or one.fieldtype == "Attach Image")
	]
	for table in meta.get_table_fields():
		child = frappe.get_meta(table.options)
		key = _key(child)
		if not _fillable(child, key):
			continue
		for one in child.fields:
			if one.fieldtype in ATTACH and not one.hidden:
				out.append(
					{
						"value": f"{table.fieldname}.{one.fieldname}",
						"label": f"{_(table.label or table.options)} › {_(one.label or one.fieldname)}",
						"kind": {"label": _(key.label), "options": _options(key)} if key else None,
					}
				)
	return out


def choices(doctype: str) -> list[dict]:
	"""The places as one list to pick from, a table's once per kind: "Image",
	"Employee Document › Passport". Each says its target and its kind."""
	out = []
	for one in of(doctype):
		if not one.get("kind"):
			out.append({"label": one["label"], "fieldname": one["value"], "row_key": None})
			continue
		table = one["label"].rsplit(" › ", 1)[0] if _one_file(doctype, one["value"]) else one["label"]
		out += [{"label": f"{table} › {_(kind)}", "fieldname": one["value"], "row_key": kind} for kind in one["kind"]["options"]]
	return out


def _one_file(doctype: str, target: str) -> bool:
	"""Whether the target's table has only this one file column, so its name
	need not be said."""
	table, _field = split(target)
	child = frappe.get_meta(frappe.get_meta(doctype).get_field(table).options)
	return sum(1 for one in child.fields if one.fieldtype in ATTACH and not one.hidden) == 1


def _key(child):
	"""The column that says which row a file is for, if the table has one."""
	return next((one for one in child.fields if one.reqd and one.fieldtype in KINDS and not one.hidden), None)


def _fillable(child, key) -> bool:
	"""Whether a sender could complete a new row: no required Link but the kind."""
	return not any(one.reqd and one.fieldtype in ("Link", "Dynamic Link") and one is not key for one in child.fields)


def _options(key) -> list[str]:
	if key.fieldtype == "Select":
		return [one for one in (key.options or "").split("\n") if one]
	return frappe.get_all(key.options, pluck="name", order_by="name asc", limit=MOST_KINDS)


def split(target: str) -> tuple[str | None, str]:
	"""("one_documents", "attachment") for a table's field, (None, "image")
	for the record's own. Pure."""
	table, _dot, field = (target or "").rpartition(".")
	return (table or None), field


def check(doctype: str, target: str, kind: str | None) -> None:
	"""Refuse a target the record does not have, or a kind its table does not."""
	found = next((one for one in of(doctype) if one["value"] == target), None)
	if not found:
		frappe.throw(_("{0} has no file field called {1}.").format(_(doctype), target))
	if kind and not found.get("kind"):
		frappe.throw(_("{0} has no kinds to pick from.").format(found["label"]))
	if kind and kind not in found["kind"]["options"]:
		frappe.throw(_("{0} is not one of {1}.").format(kind, found["kind"]["label"]))


def asked(doctype: str, target: str) -> list[dict]:
	"""The columns of a target's row asked of the sender with the file: its
	plain ones, as a frappe field each. None for the record's own field."""
	table, field = split(target)
	if not table:
		return []
	child = frappe.get_meta(frappe.get_meta(doctype).get_field(table).options)
	key = _key(child)
	return [
		{"fieldname": one.fieldname, "label": _(one.label or one.fieldname), "fieldtype": one.fieldtype, "options": one.options if one.fieldtype == "Select" else None, "reqd": one.reqd}
		for one in child.fields
		if one.fieldtype in ASKED and one is not key and one.fieldname != field and not one.hidden and not one.read_only and not one.fetch_from
	]


def clean(fields: list[dict], values: dict | None) -> dict:
	"""What the sender gave for the asked columns, and nothing else; refused
	when a required one is empty."""
	values = values or {}
	out = {}
	for one in fields:
		value = values.get(one["fieldname"])
		if one["fieldtype"] == "Check":
			value = 1 if value in (1, "1", True, "on", "true") else 0
		elif isinstance(value, str):
			value = value.strip()
		if one["reqd"] and value in (None, ""):
			frappe.throw(_("{0} is needed.").format(one["label"]))
		if value not in (None, ""):
			out[one["fieldname"]] = value
	return out


def put(doctype: str, name: str, target: str, kind: str | None, url: str, values: dict) -> None:
	"""The file on its place: the record's own field, or the row of its kind
	(changed in place, so a renewal takes the old one's place) or a new row."""
	table, field = split(target)
	if not table:
		frappe.db.set_value(doctype, name, field, url)
		return
	doc = frappe.get_doc(doctype, name)
	key = _key(frappe.get_meta(doc.meta.get_field(table).options))
	row = next((one for one in doc.get(table) or [] if key and kind and one.get(key.fieldname) == kind), None)
	if not row:
		row = doc.append(table, {key.fieldname: kind} if key and kind else {})
	row.update({**values, field: url})
	doc.save(ignore_permissions=True)
