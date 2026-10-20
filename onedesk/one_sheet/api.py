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
		frappe.throw(_("You can't open this workbook."), frappe.PermissionError)
	return item


@frappe.whitelist(methods=["POST"])
def make(parent: str, title: str | None = None, template: str | None = None) -> dict:
	"""A new workbook in a OneCloud folder, empty or a copy of a template's
	sheets, and the node the explorer draws."""
	from onedesk.one_storage import api as cloud
	from onedesk.one_storage import namespace as ns

	where = cloud._target(parent)
	if where[0] == "mount":
		frappe.throw(_("A workbook can't be made in a mounted drive."))
	title = _titled(title) or _("Untitled Workbook")
	content = "{}"
	if template:
		from onedesk.one_sheet import templates

		content = json.dumps(templates.data_of(template)[0], default=str)
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
	}


@frappe.whitelist(methods=["POST"])
def save_sheet(title: str, sheets_data: str, name: str = "", ops: str = "", request_id: str = "", table: str = "") -> dict:
	"""Keep what the editor sends as it is: the browser works the formulas out,
	and this only checks the size and that it reads as a workbook. `table` is
	the bound sheet's worked-out values, for the record behind it (table.py)."""
	if not name:
		frappe.throw(_("Make a workbook in OneCloud first."))
	item = _may(name, "write")
	plain = storage.decode_sheets_data(sheets_data)
	if len(plain.encode("utf-8")) > storage.MAX_SHEETS_DATA_BYTES:
		storage._throw_bomb()
	try:
		json.loads(plain or "{}")
	except ValueError:
		frappe.throw(_("This doesn't read as a workbook."))
	from onedesk.one_sheet import versions

	stored = sheets_data if sheets_data.startswith('{"_z"') else storage.encode_sheets_data(plain)
	head = versions.record(name, ops, len(plain.encode("utf-8")), request_id or None)
	frappe.db.set_value(
		WORKBOOK, name, {"sheets_data": stored, "byte_size": len(plain.encode("utf-8"))}, update_modified=True
	)
	_retitle(item, title)
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
	frappe.db.set_value("File", item["name"], "file_name", title)
	frappe.db.set_value(WORKBOOK, workbook_of(item["file_url"]), "title", title)


def _titled(title: str | None) -> str:
	return " ".join((title or "").replace("/", " ").split())[:MOST_TITLE]


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
	"""File on_trash: the workbook it held goes with it."""
	name = workbook_of(doc.file_url)
	if name and frappe.db.exists(WORKBOOK, name):
		for doctype in ("Workbook Change", "Workbook Version"):
			frappe.db.delete(doctype, {"workbook": name})
		frappe.delete_doc(WORKBOOK, name, ignore_permissions=True, force=True)


@frappe.whitelist()
@frappe.read_only()
def get_link_preview(url: str) -> dict:
	"""A link in a cell is shown as its address: One fetches nothing a cell names."""
	return {"url": url}
