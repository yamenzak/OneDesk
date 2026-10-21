"""What the workbook editor calls: make one in a folder, open it, save it,
rename it. Whether the reader may is OneCloud's answer for the File the
workbook sits behind, never the Workbook's own permissions. README, api.py.
"""

import json
from urllib.parse import parse_qs, urlparse

import frappe
from frappe import _

from onedesk.one_sheet import storage

WORKBOOK = "Workbook"

#: Where a workbook's File points, so OneCloud knows to open it in the editor.
URL = "/api/method/onedesk.one_sheet.api.download?workbook="

MOST_TITLE = 140

MOST_TITLES = 10


def workbook_of(url: str | None) -> str | None:
	"""The workbook a File's URL names, or None. Pure."""
	if not url or not url.startswith(URL):
		return None
	return (parse_qs(urlparse(url).query).get("workbook") or [None])[0]


def _file(name: str) -> dict:
	from onedesk.one_storage import namespace as ns

	held = frappe.db.get_value(WORKBOOK, name, ["file", "title"], as_dict=True)
	item = ns.row(held.file) if held and held.file else None
	if not item or item.get("one_deleted_on"):
		frappe.throw(_("This workbook no longer exists."), frappe.DoesNotExistError)
	return item


def _may(name: str, ptype: str = "read") -> dict:
	from onedesk.one_storage import namespace as ns

	item = _file(name)
	if not ns.may(item, ptype):
		frappe.throw(_("You do not have permission to open this workbook."), frappe.PermissionError)
	return item


@frappe.whitelist(methods=["POST"])
def make(parent: str, title: str | None = None, template: str | None = None) -> dict:
	"""A new workbook in a OneCloud folder, empty or a copy of a template's
	sheets, and the node the explorer draws."""
	from onedesk.one_storage import api as cloud
	from onedesk.one_storage import namespace as ns

	where = cloud._target(parent)
	if where[0] == "mount":
		frappe.throw(_("Workbooks cannot be created in a mounted drive."))
	title = _titled(title) or _("Untitled Workbook")
	content = "{}"
	if template:
		from onedesk.one_sheet import templates

		content = json.dumps(templates.data_of(template), default=str)
	book = frappe.get_doc({"doctype": WORKBOOK, "title": title, "sheets_data": storage.encode_sheets_data(content)})
	book.flags.ignore_permissions = True
	book.insert()
	file = {
		"doctype": "File",
		"file_url": URL + book.name,
		"is_private": 1,
	}
	if where[0] == "folder":
		file.update(folder=where[1], file_name=ns.unique_name(title, cloud._taken(where[1])))
	else:
		file.update(attached_to_doctype=where[1], attached_to_name=where[2], file_name=title)
	doc = frappe.get_doc(file)
	doc.flags.ignore_permissions = True
	doc.insert()
	book.db_set("file", doc.name)
	return {**ns.node(ns.row(doc.name)), "workbook": book.name}


@frappe.whitelist()
def get_sheet(name: str, compressed: int = 0) -> dict:
	"""The workbook as the editor loads it, and whether the reader may change it.
	A workbook bound to a record's table is brought up to the table first."""
	from onedesk.one_sheet import style, table
	from onedesk.one_storage import namespace as ns

	item = _may(name, "read")
	table.refresh(name)
	doc = frappe.get_doc(WORKBOOK, name)
	raw = doc.sheets_data
	return {
		"name": doc.name,
		"title": item["file_name"],
		"file": item["name"],
		"folder": item.get("folder"),
		"can_write": ns.may(item, "write"),
		"sheets_data": raw if frappe.utils.cint(compressed) else storage.decode_sheets_data(raw),
		"owner": item.get("owner"),
		"table": table.bound(name),
		"brand": style.brand(),
		"record": table.record_of(name),
		"source": _source(doc, item),
	}


def _source(doc, item: dict) -> dict | None:
	"""For a workbook editing an xlsx or csv File, what it is and where its
	bytes are, so the editor reads it in the first time it opens."""
	if not doc.get("source_kind"):
		return None
	fresh = not doc.sheets_data or storage.decode_sheets_data(doc.sheets_data) in ("", "{}")
	return {"kind": doc.source_kind, "url": item.get("file_url"), "fresh": fresh, "name": item["file_name"]}


#: The most records FIELD() asks for at once.
MOST_RECORDS = 50


@frappe.whitelist()
@frappe.read_only()
def records(asked: str) -> dict:
	"""Other records' fields as FIELD() reads them, {doctype: {name: fields}}
	for each [doctype, name] asked: only those the reader may open, and only
	the fields they may read; any other is left out."""
	from onedesk.one_sheet import style

	out = {}
	for doctype, name in (json.loads(asked or "[]") or [])[:MOST_RECORDS]:
		if not isinstance(doctype, str) or not isinstance(name, str) or not frappe.db.exists("DocType", doctype) or frappe.get_meta(doctype).istable:
			continue
		if not frappe.db.exists(doctype, name) or not frappe.has_permission(doctype, "read", name):
			continue
		doc = frappe.get_doc(doctype, name)
		doc.apply_fieldlevel_read_permissions()
		out.setdefault(doctype, {})[name] = style.record(doc)
	return out


@frappe.whitelist(methods=["POST"])
def save_sheet(title: str, sheets_data: str, name: str = "", ops: str = "", request_id: str = "", table: str = "") -> dict:
	"""Keep what the editor sends as it is: the browser works the formulas out,
	and this only checks the size and that it reads as a workbook. `table` is
	the bound sheet's worked-out values, for the record behind it (table.py)."""
	if not name:
		frappe.throw(_("Create the workbook in OneCloud first."))
	item = _may(name, "write")
	plain = storage.decode_sheets_data(sheets_data)
	if len(plain.encode("utf-8")) > storage.MAX_SHEETS_DATA_BYTES:
		storage._throw_bomb()
	try:
		json.loads(plain or "{}")
	except ValueError:
		frappe.throw(_("The workbook data is invalid."))
	from onedesk.one_sheet import versions

	stored = sheets_data if sheets_data.startswith('{"_z"') else storage.encode_sheets_data(plain)
	head = versions.record(name, ops, len(plain.encode("utf-8")), request_id or None)
	frappe.db.set_value(
		WORKBOOK, name, {"sheets_data": stored, "byte_size": len(plain.encode("utf-8"))}, update_modified=True
	)
	_retitle(item, title)
	if not frappe.db.get_value(WORKBOOK, name, "source_kind"):
		frappe.db.set_value("File", item["name"], "file_size", len(stored), update_modified=True)
	versions.maybe_take(name)
	said = {"name": name, "head_seq": head}
	if table:
		from onedesk.one_sheet import table as bound

		said["table"] = bound.apply(name, table)
	return said


@frappe.whitelist(methods=["POST"])
def rename_sheet(name: str, title: str) -> dict:
	item = _may(name, "write")
	_retitle(item, title)
	return {"name": name, "title": frappe.db.get_value("File", item["name"], "file_name")}


def _retitle(item: dict, title: str | None) -> None:
	"""The File's name is the workbook's title, kept unique in its folder."""
	from onedesk.one_storage import api as cloud
	from onedesk.one_storage import namespace as ns

	title = _titled(title)
	if not title or title == item["file_name"]:
		return
	if item.get("folder") and not item.get("attached_to_doctype"):
		title = ns.unique_name(title, cloud._taken(item["folder"], but=item["name"]))
	kind = frappe.db.get_value(WORKBOOK, {"file": item["name"]}, "source_kind")
	if kind and not title.lower().endswith(f".{kind}") and "." not in title[-5:]:
		title = f"{title}.{kind}"
	frappe.db.set_value("File", item["name"], "file_name", title)
	frappe.db.set_value(WORKBOOK, workbook_of(item["file_url"]) or of_file(item["name"]), "title", title)


def _titled(title: str | None) -> str:
	return " ".join((title or "").replace("/", " ").split())[:MOST_TITLE]


#: Files the editor opens in place, by their extension, and what is written
#: back to them.
OPENS = {"xlsx": "xlsx", "xlsm": "xlsx", "xls": "xlsx", "csv": "csv"}


@frappe.whitelist(methods=["POST"])
def open_file(file: str) -> dict:
	"""The workbook that edits an xlsx or csv File in place, made the first
	time it is opened: its sheets come from the File in the editor, and what
	is changed is written back to it (write_back)."""
	from onedesk.one_storage import namespace as ns

	item = ns.row(file)
	if not item or item.get("is_folder") or item.get("one_deleted_on") or not ns.may(item, "read"):
		frappe.throw(_("This file cannot be opened."), frappe.PermissionError)
	kind = OPENS.get((item["file_name"] or "").rsplit(".", 1)[-1].lower())
	if not kind:
		frappe.throw(_("Only Excel and CSV files can be opened as a workbook."))
	held = frappe.db.get_value(WORKBOOK, {"file": file, "source_kind": ["is", "set"]}, "name")
	if held:
		return {"workbook": held}
	book = frappe.get_doc({"doctype": WORKBOOK, "title": item["file_name"], "sheets_data": "{}", "file": file, "source_kind": kind})
	book.flags.ignore_permissions = True
	book.insert()
	return {"workbook": book.name}


@frappe.whitelist(methods=["POST"])
def write_back(name: str, content: str) -> dict:
	"""What the editor made of an xlsx or csv File, as that File's content:
	what it held before is kept as a version (one_storage/history.py)."""
	import base64

	from onedesk.one_storage import history
	from onedesk.one_storage import namespace as ns

	item = _may(name, "write")
	if not frappe.db.get_value(WORKBOOK, name, "source_kind"):
		frappe.throw(_("This workbook is not linked to an Excel or CSV file."))
	made = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": item["file_name"],
			"content": base64.b64decode(content),
			"is_private": item.get("is_private", 1),
			"folder": item.get("folder") or None,
		}
	)
	made.flags.ignore_permissions = True
	made.insert()
	frappe.flags.one_writing_back = True
	try:
		history.replace(ns.row(item["name"]), made.name)
	finally:
		frappe.flags.one_writing_back = False
	return {"file": item["name"], "size": frappe.db.get_value("File", item["name"], "file_size")}


def file_replaced(file: str) -> None:
	"""A new version of an Excel or CSV File put in from outside the editor:
	the workbook editing it reads it in again the next time it is opened."""
	name = None if frappe.flags.one_writing_back else of_file(file)
	if name:
		frappe.db.set_value(WORKBOOK, name, "sheets_data", "{}")


def of_file(file: str) -> str | None:
	"""The workbook editing a File in place, if it has been opened."""
	return frappe.db.get_value(WORKBOOK, {"file": file, "source_kind": ["is", "set"]}, "name")


@frappe.whitelist()
@frappe.read_only()
def titles(names: str | list) -> dict:
	"""The titles of the workbooks named that the reader may still open, for
	the bar's way back to them (public/js/workbooks.js)."""
	said = frappe.parse_json(names) if isinstance(names, str) else names
	out = {}
	for name in (said or [])[:MOST_TITLES]:
		try:
			out[name] = _may(str(name), "read")["file_name"]
		except (frappe.PermissionError, frappe.DoesNotExistError):
			continue
	return out


@frappe.whitelist()
def download(workbook: str) -> None:
	"""A workbook's File opened outside the editor goes to the editor."""
	_may(workbook, "read")
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = f"/desk/workbook/{workbook}"


def copied(doc, method=None) -> None:
	"""File before_insert: a File naming a workbook another File already holds
	is a copy, so it holds a copy of the workbook rather than sharing it. A
	copy of a record's table is a plain workbook: one table, one workbook."""
	name = workbook_of(doc.file_url)
	if not name or not frappe.db.exists("File", {"file_url": doc.file_url}):
		return
	book = frappe.copy_doc(frappe.get_doc(WORKBOOK, name))
	book.title = doc.file_name or book.title
	book.file = None
	book.update(dict.fromkeys(("bound_doctype", "bound_name", "bound_field", "bound_sheet", "bound_columns")))
	book.flags.ignore_permissions = True
	book.insert()
	doc.file_url = URL + book.name
	doc.content_hash = None
	doc.flags.one_workbook = book.name


def placed(doc, method=None) -> None:
	"""File after_insert: a copied workbook knows its File."""
	if doc.flags.one_workbook:
		frappe.db.set_value(WORKBOOK, doc.flags.one_workbook, "file", doc.name)


def file_gone(doc, method=None) -> None:
	"""File on_trash: the workbook it held, or that edited it in place, goes
	with it."""
	name = workbook_of(doc.file_url) or of_file(doc.name)
	if name and frappe.db.exists(WORKBOOK, name):
		for doctype in ("Workbook Change", "Workbook Version"):
			frappe.db.delete(doctype, {"workbook": name})
		frappe.delete_doc(WORKBOOK, name, ignore_permissions=True, force=True)


@frappe.whitelist()
@frappe.read_only()
def get_link_preview(url: str) -> dict:
	"""A link in a cell is shown as its address: One fetches nothing a cell names."""
	return {"url": url}
