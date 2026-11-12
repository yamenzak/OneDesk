"""How an office file opens in OneCloud and what Edit offers on it: in
OneWorkbook or OneWriter when it has nothing they would drop, else as its
exact PDF; Edit there, Edit in OneOS or a copy of One's own. What the
editor would drop is read once for each version of the file and kept on
it. README, Under the hood, Opening an office file."""

import io
import json
import time

import frappe
from frappe import _
from frappe.realtime import get_doctype_room
from frappe.utils import get_fullname

from onedesk.one_storage import fidelity, lease

EDITS = {"xlsx": "workbook", "csv": "workbook", "docx": "document"}
MAKES = {"pptx": "presentation", "ppsx": "presentation"}
COPIES = {"xlsm": "workbook", "xltm": "workbook", "xls": "workbook", "docm": "document", "dotm": "document"}
WEIGHED = ("xlsx", "docx")
APPS = {"workbook": "OneWorkbook", "document": "OneWriter"}


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
	from onedesk.one_storage import saving

	return saving.listed(item.get("one_fidelity"))


def weighed(item: dict) -> list:
	"""What OneWorkbook or OneWriter would drop from the file, read from its
	parts the first time this version is opened. A Word file's styles the
	reader does not know are only found once OneWriter reads it in."""
	found = kept(item)
	if found is not None:
		return found
	from onedesk.one_storage import api

	content = api._content(frappe._dict(item))
	found = fidelity.workbook(content) if extension_of(item["file_name"]) == "xlsx" else fidelity.document(content)
	frappe.db.set_value("File", item["name"], {"one_fidelity": json.dumps(found), "one_fidelity_of": version_of(item)}, update_modified=False)
	return found


def row(item: dict) -> dict | None:
	"""What a listing says of an office file: what Edit offers, and what the
	editor would drop when that is known already."""
	if item.get("is_folder"):
		return None
	found = way(item.get("file_name"))
	if not found:
		return None
	known = kept(item) if found["edit"] else []
	return {**found, **({"loses": known} if known is not None else {})}


def said(app: str, found: list[str]) -> str:
	"""The question asked before editing a file here would drop parts of it."""
	return _("This file has {0} {1} can't keep.").format(fidelity.named(found), app)


@frappe.whitelist(methods=["POST"])
def weigh(node: str) -> dict:
	"""What the editor would drop from an office file, and the question to
	ask before editing it there."""
	from onedesk.one_storage import api

	item = api._item(node)
	api._need(item, "read")
	found = way(item.file_name) or {}
	if not found.get("edit"):
		return {"loses": []}
	loses = weighed(item)
	return {"loses": loses, "said": said(APPS[found["edit"]], loses) if loses else None}


def editing(items: list[dict]) -> None:
	"""Who is in each office file, workbook or document of a listing in
	OneWorkbook or OneWriter to change it, put on its row."""
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
	"""Somebody came into or left a file in OneWorkbook or OneWriter: the
	folders it shows in redraw its row."""
	from onedesk.one_storage import live

	item = frappe.db.get_value("File", file, ["folder", "attached_to_doctype", "attached_to_name"], as_dict=True)
	keys = live.keys_of(item or {})
	if keys:
		frappe.publish_realtime(live.EVENT, {"keys": sorted(keys)}, room=get_doctype_room("File"))


@frappe.whitelist(methods=["POST"])
def one_copy(node: str) -> dict:
	"""A workbook or document of One's own made from a file the editors only
	read (macros, an older Excel file), beside it, or in My Files where the
	reader may not add to its folder. The file stays as it was."""
	from onedesk.one_storage import api
	from onedesk.one_storage import namespace as ns

	item = api._item(node)
	api._need(item, "read")
	kind = (way(item.file_name) or {}).get("copy")
	if not kind:
		frappe.throw(_("{0} can't be copied into One.").format(item.file_name))
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
