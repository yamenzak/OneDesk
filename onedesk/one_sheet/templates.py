"""Workbook templates: a workbook kept in OneCloud's Workbook Templates folder
to start others from. Anyone in the company opens them; whoever made one, or
an administrator, changes it, as with any company file. A template made from
a record's table workbook is for that table: it carries the sheets beside
the table and the column map, and is offered when that table is first
opened in a workbook. README, Templates.
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
def listed(doctype: str | None = None, field: str | None = None, name: str | None = None) -> list[dict]:
	"""The templates the reader may use: for a record's table when one is
	named, else those that are workbooks of their own. None for a record
	whose table already has its workbook: that one opens."""
	from onedesk.one_storage import namespace as ns

	if name and frappe.db.exists(api.WORKBOOK, {"bound_doctype": doctype, "bound_name": name, "bound_field": field}):
		return []
	filters = {"is_template": 1}
	filters.update({"template_for": doctype, "template_field": field} if doctype else {"template_for": ["is", "not set"]})
	out = []
	for one in frappe.get_all(api.WORKBOOK, filters=filters, fields=["name", "title", "file"], order_by="title asc"):
		item = ns.row(one.file) if one.file else None
		if item and not item.get("one_deleted_on") and ns.may(item, "read"):
			out.append({"name": one.name, "title": item["file_name"]})
	return out


def data_of(template: str, doctype: str | None = None, field: str | None = None) -> tuple[dict, dict | None]:
	"""A template's sheets and column map, for a new workbook. A template for
	a table starts only that table's workbook."""
	held = frappe.db.get_value(api.WORKBOOK, template, ["is_template", "template_for", "template_field", "fill_map", "sheets_data"], as_dict=True)
	if not held or not held.is_template:
		frappe.throw(_("That isn't a template."))
	api._may(template, "read")
	if held.template_for and (held.template_for, held.template_field) != (doctype, field):
		frappe.throw(_("That template is for another table."))
	data = json.loads(storage.decode_sheets_data(held.sheets_data) or "{}")
	fill_map = json.loads(held.fill_map) if held.fill_map else None
	return data, fill_map


def make(title: str, data: dict, template_for: str | None = None, template_field: str | None = None, fill_map: dict | None = None) -> str:
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
			"fill_map": json.dumps(fill_map) if fill_map else None,
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


def without(data: dict, sheet: str) -> dict:
	"""A workbook's content without one sheet and what belongs to it. Pure."""
	held = dict(data.get("sheet") or {})
	held["sheets"] = {name: one for name, one in (held.get("sheets") or {}).items() if name != sheet}
	if held.get("current") == sheet:
		held["current"] = next(iter(held["sheets"]), None)
	out = {**data, "sheet": held}
	for key in ("validation", "protection", "view", "formats", "comments", "condFormat", "sortFilter"):
		if isinstance(out.get(key), dict) and sheet in out[key]:
			out[key] = {name: one for name, one in out[key].items() if name != sheet}
	return out


@frappe.whitelist(methods=["POST"])
def save_as(name: str, title: str) -> dict:
	"""This workbook as a template. A record's table workbook gives one for
	that table, without the table itself, which each record fills."""
	api._may(name, "read")
	held = frappe.db.get_value(
		api.WORKBOOK, name, ["sheets_data", "bound_doctype", "bound_field", "bound_sheet", "fill_map"], as_dict=True
	)
	data = json.loads(storage.decode_sheets_data(held.sheets_data) or "{}")
	if held.bound_doctype:
		data = without(data, held.bound_sheet)
	made = make(
		title,
		data,
		held.bound_doctype,
		held.bound_field,
		json.loads(held.fill_map) if held.fill_map else None,
	)
	return {"name": made, "title": frappe.db.get_value(api.WORKBOOK, made, "title")}
