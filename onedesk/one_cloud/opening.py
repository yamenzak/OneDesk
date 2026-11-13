"""How an office file opens in OneCloud and what Edit offers on it: in
OneSheet or OneDoc when it has nothing they would drop, else as its
exact PDF; Edit there, Edit in OneOS or a copy of One's own. What the
editor would drop is read once for each version of the file and kept on
it. A workbook, document or presentation of One's own leaves as the Excel,
Word or PowerPoint file the drive serves. AGENTS.md, Under the hood, Opening
an office file."""

import io
import json
import time

import frappe
from frappe import _
from frappe.realtime import get_doctype_room
from frappe.utils import get_fullname

from onedesk.one import registry
from onedesk.one_cloud import fidelity, lease

EDITS = {"xlsx": "workbook", "csv": "workbook", "docx": "document"}
MAKES = {"pptx": "presentation", "ppsx": "presentation"}
COPIES = {"xlsm": "workbook", "xltm": "workbook", "xls": "workbook", "docm": "document", "dotm": "document"}
WEIGHED = ("xlsx", "docx")
APPS = {"workbook": registry.name("one_sheet"), "document": registry.name("one_doc")}
HELD_BY = {"workbook": "Workbook", "document": "Writer Document"}


def extension_of(file_name: str) -> str:
	return (file_name or "").rsplit(".", 1)[-1].lower() if "." in (file_name or "") else ""


def way(file_name: str) -> dict | None:
	"""What Edit offers on an office file: `edit` in a native editor, `make`
	a presentation of One's own from it, or `copy` it into one of One's own
	where the editor would only read it. None for a file none of them takes.
	Pure."""
	extension = extension_of(file_name)
	found = {"edit": EDITS.get(extension), "make": MAKES.get(extension), "copy": COPIES.get(extension)}
	return found if any(found.values()) else None


def version_of(item: dict) -> str | None:
	return item.get("content_hash") or item.get("file_url")


def kept(item: dict) -> list | None:
	"""What was found the last time this version of the file was read, or
	None when it has not been read."""
	if extension_of(item.get("file_name")) not in WEIGHED:
		return []
	if not item.get("one_fidelity_of") or item.get("one_fidelity_of") != version_of(item):
		return None
	from onedesk.one_cloud import saving

	return saving.listed(item.get("one_fidelity"))


def weighed(item: dict) -> list:
	"""What OneSheet or OneDoc would drop from the file, read from its
	parts the first time this version is opened. A Word file's styles the
	reader does not know are only found once OneDoc reads it in."""
	found = kept(item)
	if found is not None:
		return found
	from onedesk.one_cloud import api

	content = api._content(frappe._dict(item))
	found = fidelity.workbook(content) if extension_of(item["file_name"]) == "xlsx" else fidelity.document(content)
	frappe.db.set_value("File", item["name"], {"one_fidelity": json.dumps(found), "one_fidelity_of": version_of(item)}, update_modified=False)
	return found


def row(item: dict) -> dict | None:
	"""What a listing says of an office file: what Edit offers, what the
	editor would drop when that is known already, and whether its preview is
	kept."""
	if item.get("is_folder"):
		return None
	previewed = {"previewed": True} if item.get("content_hash") and item.get("one_preview_of") == item.get("content_hash") else {}
	found = way(item.get("file_name"))
	if not found:
		return previewed or None
	known = kept(item) if found["edit"] else []
	return {**found, **({"loses": known} if known is not None else {}), **previewed}


def said(app: str, found: list[str]) -> str:
	"""The question asked before editing a file here would drop parts of it."""
	return _("This file has {0} {1} can't keep.").format(fidelity.named(found), app)


@frappe.whitelist(methods=["POST"])
def weigh(node: str) -> dict:
	"""What the editor would drop from an office file, and the question to
	ask before editing it there."""
	from onedesk.one_cloud import api

	item = api._item(node)
	api._need(item, "read")
	found = way(item.file_name) or {}
	if not found.get("edit"):
		return {"loses": []}
	loses = weighed(item)
	return {"loses": loses, "said": said(APPS[found["edit"]], loses) if loses else None, "waiting": waiting(item.name, found["edit"])}


def waiting(file: str, kind: str) -> bool:
	"""Whether edits made to the file in OneSheet or OneDoc wait to be
	saved over it or as a copy."""
	return bool(frappe.db.exists(HELD_BY[kind], {"file": file, "held_back": ["is", "set"]}))


def own_of(item: dict) -> tuple[str, str] | None:
	"""Which of One's own a File holds: ("workbook", its name), a document
	or a presentation. None for any other file."""
	from onedesk.one_cloud import namespace as ns

	for kind, found in (("workbook", ns._workbook), ("document", ns._document), ("presentation", ns._presentation)):
		name = found(item)
		if name:
			return kind, name
	return None


def _suffix(kind: str) -> str:
	from onedesk.one_deck import drive
	from onedesk.one_doc import word
	from onedesk.one_sheet import excel

	return {"workbook": excel.SUFFIX, "document": word.SUFFIX, "presentation": drive.SUFFIX}[kind]


def office_name(item: dict, kind: str) -> str:
	"""The name One's own goes out under: its own, as an Excel, Word or
	PowerPoint file. Pure."""
	name, suffix = item.get("file_name") or "", _suffix(kind)
	return name if name.lower().endswith(suffix) else name + suffix


def exported(kind: str, name: str) -> bytes:
	"""One's own as the drive serves it, for the reader."""
	from onedesk.one_deck import drive
	from onedesk.one_doc import word
	from onedesk.one_sheet import excel

	return {"workbook": excel.xlsx, "document": word.docx, "presentation": drive.pptx}[kind](name)


def kept_inside(kind: str, name: str) -> str | None:
	"""Why One's own can only be changed in its own editor: a workbook of a
	record's table, a document with a record's fields, a presentation with
	words from records. None when an outside save may come back into it."""
	if kind == "workbook" and frappe.db.get_value("Workbook", name, "bound_doctype"):
		return _("A record's workbook can only be edited in {0}.").format(registry.name("one_sheet"))
	if kind == "document":
		held = frappe.db.get_value("Writer Document", name, ["html", "bound_doctype"], as_dict=True) or frappe._dict()
		if held.bound_doctype or 'data-field="' in (held.html or ""):
			return _("A document with a record's fields in it can only be edited in {0}.").format(registry.name("one_doc"))
	if kind == "presentation":
		from onedesk.one_deck import data

		if data.cleaned(frappe.db.get_value("Presentation", name, "sources")):
			return _("A presentation with words from records can only be edited in {0}.").format(registry.name("one_deck"))
	return None


@frappe.whitelist()
def download(node: str) -> None:
	"""A workbook, document or presentation of One's own as its Excel, Word
	or PowerPoint file."""
	from onedesk.one_cloud import api

	item = api._item(node)
	api._need(item, "read")
	own = own_of(item)
	if not own:
		frappe.throw(_("{0} can't be downloaded this way.").format(item.file_name))
	frappe.local.response.filename = office_name(item, own[0])
	frappe.local.response.filecontent = exported(*own)
	frappe.local.response.type = "download"


def editing(items: list[dict]) -> None:
	"""Who is in each office file, workbook or document of a listing in
	OneSheet or OneDoc to change it, put on its row."""
	files = [one["id"] for one in items if not one.get("folder") and (one.get("office") or one.get("workbook") or one.get("document"))]
	if not files:
		return
	import pickle

	try:
		pipe = frappe.cache.pipeline()
		for file in files:
			pipe.hgetall(frappe.cache.make_key(lease._live_key(file)))
		heard = dict(zip(files, pipe.execute(), strict=True))
	except Exception:
		return
	now, me = time.time(), frappe.session.user
	for one in items:
		raw = heard.get(one["id"])
		if not raw:
			continue
		live = lease.present({key: pickle.loads(value) for key, value in raw.items()}, now)
		writing = sorted((user, held) for user, held in live.items() if held["write"])
		if writing:
			one["editing"] = {
				"by": [get_fullname(user) for user, _held in writing if user != me],
				"mine": any(user == me for user, _held in writing),
				"app": lease.APPS.get(writing[0][1].get("app")),
			}


def redraw(file: str) -> None:
	"""Somebody came into or left a file in OneSheet or OneDoc: the
	folders it shows in redraw its row."""
	from onedesk.one_cloud import live

	item = frappe.db.get_value("File", file, ["folder", "attached_to_doctype", "attached_to_name"], as_dict=True)
	keys = live.keys_of(item or {})
	if keys:
		frappe.publish_realtime(live.EVENT, {"keys": sorted(keys)}, room=get_doctype_room("File"))


@frappe.whitelist(methods=["POST"])
def one_copy(node: str) -> dict:
	"""A workbook or document of One's own made from a file the editors only
	read (macros, an older Excel file), beside it, or in My Files where the
	reader may not add to its folder. The file stays as it was."""
	from onedesk.one_cloud import api
	from onedesk.one_cloud import namespace as ns

	item = api._item(node)
	api._need(item, "read")
	kind = (way(item.file_name) or {}).get("copy")
	if not kind:
		frappe.throw(_("{0} can't be copied into {1}.").format(item.file_name, registry.name("one")))
	folder = ns.row(item.folder) if item.folder else None
	parent = item.folder if folder and ns.may(folder, "add") else ns.home()
	title = item.file_name.rsplit(".", 1)[0]
	content = api._content(item)
	if kind == "workbook":
		return _workbook(parent, title, content, extension_of(item.file_name))
	return _document(parent, title, content)


def _workbook(parent: str, title: str, content: bytes, extension: str) -> dict:
	from onedesk.one_sheet import api as sheets
	from onedesk.one_sheet import excel, storage

	if extension == "xls":
		content = xlsx_of_xls(content)
	made = sheets.make(parent, title)
	data = excel.read(made["workbook"], content)
	frappe.db.set_value(sheets.WORKBOOK, made["workbook"], "sheets_data", storage.encode_sheets_data(json.dumps(data, default=str)))
	return {"workbook": made["workbook"], "name": made["name"]}


def _document(parent: str, title: str, content: bytes) -> dict:
	from onedesk.one_doc import api as writing
	from onedesk.one_doc import word

	made = writing.make(parent, title)
	frappe.db.set_value(writing.DOCUMENT, made["document"], {"html": word.read(made["document"], content), "content": None})
	return {"document": made["document"], "name": made["name"]}


def xlsx_of_xls(content: bytes) -> bytes:
	"""An older Excel file's sheets and values as an xlsx. Pure."""
	import xlrd
	from openpyxl import Workbook

	try:
		older = xlrd.open_workbook(file_contents=content)
	except Exception:
		frappe.throw(_("This file cannot be opened."))
	out = Workbook()
	out.remove(out.active)
	for sheet in older.sheets():
		page = out.create_sheet(sheet.name[:31])
		for r in range(sheet.nrows):
			for c in range(sheet.ncols):
				value = sheet.cell_value(r, c)
				if value not in ("", None):
					page.cell(row=r + 1, column=c + 1, value=value)
	held = io.BytesIO()
	out.save(held)
	return held.getvalue()
