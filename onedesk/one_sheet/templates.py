"""Workbook templates: a workbook kept in OneCloud's Workbook Templates folder
to start others from. Anyone in the company opens them; whoever made one, or
an administrator, changes it, as with any company file. A template made from
a record's table workbook is for that table: it carries the sheets beside
the table and the formulas typed under the table's header. README,
Templates.
"""

import json

import frappe
from frappe import _

from onedesk.one_sheet import api, storage

FOLDER_NAME = "Workbook Templates"


def folder() -> str:
	"""The Workbook Templates folder in the company's files, made the first
	time it's needed."""
	from onedesk.one_storage import namespace as ns

	found = frappe.db.get_value("File", {"is_folder": 1, "folder": ns.HOME, "file_name": FOLDER_NAME})
	if found:
		return found
	made = frappe.get_doc({"doctype": "File", "is_folder": 1, "folder": ns.HOME, "file_name": FOLDER_NAME})
	made.flags.ignore_permissions = True
	made.insert()
	return made.name


@frappe.whitelist()
@frappe.read_only()
def listed(doctype: str | None = None, field: str | None = None, name: str | None = None, every: int = 0) -> list[dict]:
	"""The templates the reader may use: for a record's table when one is
	named, else those that are workbooks of their own, or, with `every`,
	all of them, whose sheets beside a table any workbook can take. None
	for a record whose table already has its workbook: that one opens."""
	from onedesk.one_storage import namespace as ns

	if name and frappe.db.exists(api.WORKBOOK, {"bound_doctype": doctype, "bound_name": name, "bound_field": field}):
		return []
	filters = {"is_template": 1}
	if doctype:
		filters.update({"template_for": doctype, "template_field": field})
	elif not frappe.utils.cint(every):
		filters["template_for"] = ["is", "not set"]
	out = []
	for one in frappe.get_all(api.WORKBOOK, filters=filters, fields=["name", "title", "file"], order_by="title asc"):
		item = ns.row(one.file) if one.file else None
		if item and not item.get("one_deleted_on") and ns.may(item, "read"):
			out.append({"name": one.name, "title": item["file_name"]})
	return out


@frappe.whitelist()
@frappe.read_only()
def sheets_of(template: str) -> list[dict]:
	"""A template's sheets to add to a workbook already open, each by name
	with its cells, formats, merges, view, link cells and the formulas each
	line gets; a table's own sheet stays out, since a workbook has one."""
	from onedesk.one_sheet import table
	from onedesk.one_sheet.assist import letters

	held = frappe.db.get_value(api.WORKBOOK, template, ["is_template", "bound_sheet", "sheets_data"], as_dict=True)
	if not held or not held.is_template:
		frappe.throw(_("This workbook is not a template."))
	api._may(template, "read")
	data = json.loads(storage.decode_sheets_data(held.sheets_data) or "{}")
	out = []
	for name in ((data.get("sheet") or {}).get("sheets") or {}):
		if name == held.bound_sheet:
			continue
		cells = {
			f"{letters(col)}{int(line) + 1}": value
			for line, values in table.stored(data, name).items()
			for col, value in enumerate(values or [])
			if value not in (None, "")
		}
		one = {"name": name, "cells": cells}
		for part in ("formats", "merge", "view", "validation", "lines"):
			found = (data.get(part) or {}).get(name)
			if found:
				one[part] = found
		out.append(one)
	return out


def data_of(template: str, doctype: str | None = None, field: str | None = None, sheet: str | None = None) -> tuple[dict, str | None, dict]:
	"""A template's sheets for a new workbook, the name its table's sheet
	goes by, and the formulas under that table's header by line and field.
	A template for a table starts only that table's workbook."""
	from onedesk.one_sheet import table

	held = frappe.db.get_value(
		api.WORKBOOK, template, ["is_template", "template_for", "template_field", "bound_sheet", "bound_columns", "sheets_data"], as_dict=True
	)
	if not held or not held.is_template:
		frappe.throw(_("This workbook is not a template."))
	api._may(template, "read")
	if held.template_for and (held.template_for, held.template_field) != (doctype, field):
		frappe.throw(_("This template belongs to a different table."))
	data = json.loads(storage.decode_sheets_data(held.sheets_data) or "{}")
	if not held.bound_sheet:
		return data, sheet, {}
	formulas = table.kept(table.stored(data, held.bound_sheet), json.loads(held.bound_columns or "[]"))
	return data, held.bound_sheet, formulas


def make(title: str, data: dict, template_for: str | None = None, template_field: str | None = None, sheet: str | None = None, cols: list | None = None) -> str:
	"""A template in the Workbook Templates folder; its name."""
	from onedesk.one_storage import api as cloud
	from onedesk.one_storage import namespace as ns

	where = folder()
	title = api._titled(title) or _("Untitled Template")
	book = frappe.get_doc(
		{
			"doctype": api.WORKBOOK,
			"title": title,
			"sheets_data": storage.encode_sheets_data(json.dumps(data, default=str)),
			"is_template": 1,
			"template_for": template_for,
			"template_field": template_field,
			"bound_sheet": sheet,
			"bound_columns": json.dumps(cols) if cols else None,
		}
	)
	book.flags.ignore_permissions = True
	book.insert()
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_url": api.URL + book.name,
			"is_private": 0,
			"folder": where,
			"file_name": ns.unique_name(title, cloud._taken(where)),
		}
	)
	file.flags.ignore_permissions = True
	file.insert()
	book.db_set("file", file.name)
	return book.name


@frappe.whitelist(methods=["POST"])
def save_as(name: str, title: str) -> dict:
	"""This workbook as a template. A record's table workbook gives one for
	that table: the table's sheet keeps its header and the formulas typed in
	it, not the rows, which each record fills."""
	from onedesk.one_sheet import table

	api._may(name, "read")
	held = frappe.db.get_value(
		api.WORKBOOK, name, ["sheets_data", "bound_doctype", "bound_field", "bound_sheet", "bound_columns"], as_dict=True
	)
	data = json.loads(storage.decode_sheets_data(held.sheets_data) or "{}")
	if not held.bound_doctype:
		made = make(title, data)
	else:
		made = make(
			title,
			table.emptied(data, held.bound_sheet),
			held.bound_doctype,
			held.bound_field,
			held.bound_sheet,
			json.loads(held.bound_columns or "[]"),
		)
	return {"name": made, "title": frappe.db.get_value(api.WORKBOOK, made, "title")}
