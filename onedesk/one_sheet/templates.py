"""Workbook templates: a workbook kept in OneCloud's Workbook Templates folder
to start others from. Anyone in the company opens them; a role with the
template ability (abilities.py) keeps one; whoever made one, or an
administrator, changes it, as with any company file. A template is its own
sheets and nothing else: made from a record's table workbook, it keeps the
sheets beside the table, not the table. AGENTS.md, Templates.
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
def listed() -> list[dict]:
	"""The templates the reader may use, by title."""
	from onedesk.one_storage import namespace as ns

	out = []
	for one in frappe.get_all(api.WORKBOOK, filters={"is_template": 1}, fields=["name", "title", "file"], order_by="title asc"):
		item = ns.row(one.file) if one.file else None
		if item and not item.get("one_deleted_on") and ns.may(item, "read"):
			out.append({"name": one.name, "title": item["file_name"]})
	return out


@frappe.whitelist()
@frappe.read_only()
def sheets_of(template: str) -> list[dict]:
	"""A template's sheets to add to a workbook already open, each by name
	with its cells, formats, merges, view, link cells and the formulas each
	line gets."""
	from onedesk.one_sheet import table
	from onedesk.one_sheet.cells import letters

	data = data_of(template)
	out = []
	for name in ((data.get("sheet") or {}).get("sheets") or {}):
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


def data_of(template: str) -> dict:
	"""A template's sheets, for a new workbook or one already open."""
	held = frappe.db.get_value(api.WORKBOOK, template, ["is_template", "sheets_data"], as_dict=True)
	if not held or not held.is_template:
		frappe.throw(_("This workbook is not a template."))
	api._may(template, "read")
	return json.loads(storage.decode_sheets_data(held.sheets_data) or "{}")


def make(title: str, data: dict) -> str:
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
	"""This workbook as a template. A record's table workbook gives its
	other sheets: the table is the record's, not the template's."""
	from onedesk.one import rights
	from onedesk.one_sheet import table

	api._may(name, "read")
	if not rights.held(api.WORKBOOK, "sheet_template"):
		frappe.throw(_("Your role doesn't keep company templates. Ask a workspace administrator."), frappe.PermissionError)
	held = frappe.db.get_value(api.WORKBOOK, name, ["sheets_data", "bound_doctype", "bound_sheet"], as_dict=True)
	data = json.loads(storage.decode_sheets_data(held.sheets_data) or "{}")
	if held.bound_doctype:
		data = table.without(data, held.bound_sheet)
		if not (data.get("sheet") or {}).get("sheets"):
			frappe.throw(_("This workbook has no sheets besides the record's table to keep as a template."))
	made = make(title, data)
	return {"name": made, "title": frappe.db.get_value(api.WORKBOOK, made, "title")}
