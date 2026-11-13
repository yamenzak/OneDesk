"""What the document editor calls: make one in a folder, open it, save it,
rename it. Whether the reader may is OneCloud's answer for the File the
document sits behind, never the Writer Document's own permissions. AGENTS.md,
api.py.
"""

import json
from urllib.parse import parse_qs, urlparse

import frappe
from frappe import _

DOCUMENT = "Writer Document"

#: Where a document's File points, so OneCloud knows to open it in the editor.
URL = "/api/method/onedesk.one_doc.api.download?document="

MOST_TITLE = 140

MOST_TITLES = 10

#: The most a save may carry, the editor's state and its HTML together.
MOST_BYTES = 40 * 1024 * 1024

#: What a page may be set to (Suite's WriterSettings): anything else is dropped.
SETTINGS = {
	"font_family",
	"font_size",
	"line_height",
	"paragraph_spacing_before",
	"paragraph_spacing_after",
	"wide",
	"lock",
	"version",
	"print_header_left",
	"print_header_right",
	"print_footer_left",
	"print_footer_right",
	"print_show_pages",
	"print_header_separator",
	"print_footer_separator",
}


def document_of(url: str | None) -> str | None:
	"""The document a File's URL names, or None. Pure."""
	if not url or not url.startswith(URL):
		return None
	return (parse_qs(urlparse(url).query).get("document") or [None])[0]


def _file(name: str) -> dict:
	from onedesk.one_cloud import namespace as ns

	held = frappe.db.get_value(DOCUMENT, name, "file")
	item = ns.row(held) if held else None
	if not item or item.get("one_deleted_on"):
		frappe.throw(_("This document no longer exists."), frappe.DoesNotExistError)
	return item


def _may(name: str, ptype: str = "read") -> dict:
	from onedesk.one_cloud import namespace as ns

	item = _file(name)
	if not ns.may(item, ptype):
		frappe.throw(_("You do not have permission to open this document."), frappe.PermissionError)
	return item


@frappe.whitelist(methods=["POST"])
def make(parent: str, title: str | None = None, template: str | None = None) -> dict:
	"""A new document in a OneCloud folder or on a record, empty or a copy of
	a template, and the node the explorer draws."""
	from onedesk.one_cloud import api as cloud
	from onedesk.one_cloud import namespace as ns

	where = cloud._target(parent)
	if where[0] == "mount":
		frappe.throw(_("Documents cannot be created in a mounted drive."))
	title = _titled(title) or _("Untitled Document")
	values = {}
	if template:
		from onedesk.one_doc import templates

		values = templates.content_of(template)
	doc = frappe.get_doc({"doctype": DOCUMENT, "title": title, **values})
	doc.flags.ignore_permissions = True
	doc.insert()
	file = {"doctype": "File", "file_url": URL + doc.name, "is_private": 1}
	if where[0] == "folder":
		file.update(folder=where[1], file_name=ns.unique_name(title, cloud._taken(where[1])))
	else:
		file.update(attached_to_doctype=where[1], attached_to_name=where[2], file_name=title)
	made = frappe.get_doc(file)
	made.flags.ignore_permissions = True
	made.insert()
	doc.db_set("file", made.name)
	return {**ns.node(ns.row(made.name)), "document": doc.name}


@frappe.whitelist()
def get_document(name: str) -> dict:
	"""The document as the editor loads it, whether the reader may change it,
	and the OneCloud folders above it for its breadcrumb."""
	from onedesk.one_cloud import namespace as ns

	from onedesk.one import rights
	from onedesk.one_doc import field
	from onedesk.one_cloud import saving

	item = _may(name, "read")
	doc = frappe.get_doc(DOCUMENT, name)
	if doc.source_kind == "docx" and not doc.html and not doc.content:
		from onedesk.one_doc import word

		word.open_file(item["name"])
		doc.reload()
	bound = field.bound(name)
	return {
		"name": doc.name,
		"title": item["file_name"],
		"file": item["name"],
		"folder": item.get("folder"),
		**saving.state(DOCUMENT, name, item, ns.may(item, "write") and (not bound or bound["writable"])),
		"can_template": rights.held(DOCUMENT, "doc_template"),
		"bound": bound,
		"word": doc.source_kind == "docx",
		"owner": item.get("owner"),
		"content": doc.content or "",
		"html": doc.html or "",
		"settings": _settings(doc.settings),
		"comments": doc.comments or "",
		"record": _record(item),
		"trail": ns.trail(item["folder"]) if item.get("folder") and not item.get("attached_to_doctype") else [],
	}


def _record(item: dict) -> dict | None:
	"""The record a document is filed on, for its breadcrumb back."""
	if not item.get("attached_to_doctype") or not item.get("attached_to_name"):
		return None
	return {"doctype": item["attached_to_doctype"], "name": item["attached_to_name"]}


def _settings(raw) -> dict:
	held = json.loads(raw) if isinstance(raw, str) and raw else raw or {}
	return {key: value for key, value in held.items() if key in SETTINGS} if isinstance(held, dict) else {}


@frappe.whitelist(methods=["POST"])
def save_document(name: str, content: str, html: str, title: str | None = None, manual: int = 0) -> dict:
	"""Keep what the editor sends: its Yjs state, which it opens from, and
	the same document as HTML, which everything else reads."""
	from onedesk.one_doc import field
	from onedesk.one_cloud import saving

	item = _may(name, "write")
	saving.check(DOCUMENT, name, item)
	size = len(content.encode("utf-8")) + len(html.encode("utf-8"))
	if size > MOST_BYTES:
		frappe.throw(_("This document is too large to save."))
	put = field.put(name, frappe.db.get_value(DOCUMENT, name, "html"), html)
	frappe.db.set_value(DOCUMENT, name, {"content": content, "html": put.get("html", html), "byte_size": size}, update_modified=True)
	if not frappe.db.get_value(DOCUMENT, name, "source_kind"):
		frappe.db.set_value("File", item["name"], "file_size", size, update_modified=True)
	_retitle(name, item, title)
	return {"name": name, **({} if put["ok"] else {"refused": put["message"]})}


@frappe.whitelist(methods=["POST"])
def dismiss_dropped(name: str) -> None:
	"""The note of what a save from the drive left out, put away."""
	from onedesk.one_cloud import saving

	_may(name, "write")
	saving.dismiss(DOCUMENT, name)


@frappe.whitelist(methods=["POST"])
def save_settings(name: str, settings: str | dict) -> dict:
	"""The page setup: typeface, size, spacing, width and the lock."""
	_may(name, "write")
	held = _settings(frappe.parse_json(settings) if isinstance(settings, str) else settings)
	frappe.db.set_value(DOCUMENT, name, "settings", json.dumps(held))
	return held


@frappe.whitelist(methods=["POST"])
def save_comments(name: str, data: str) -> dict:
	"""The comments' Yjs state. Commenting is reading and saying something,
	so whoever may open the document may comment on it."""
	_may(name, "read")
	if len(data.encode("utf-8")) > MOST_BYTES:
		frappe.throw(_("This document is too large to save."))
	frappe.db.set_value(DOCUMENT, name, "comments", data)
	return {"name": name}


@frappe.whitelist(methods=["POST"])
def rename_document(name: str, title: str) -> dict:
	item = _may(name, "write")
	_retitle(name, item, title)
	return {"name": name, "title": frappe.db.get_value("File", item["name"], "file_name")}


def _retitle(name: str, item: dict, title: str | None) -> None:
	"""The File's name is the document's title, kept unique in its folder; a
	Word file's keeps its .docx."""
	from onedesk.one_doc import word
	from onedesk.one_cloud import api as cloud
	from onedesk.one_cloud import namespace as ns

	title = _titled(title)
	if title and frappe.db.get_value(DOCUMENT, name, "source_kind") == "docx" and not title.lower().endswith(word.SUFFIX):
		title += word.SUFFIX
	if not title or title == item["file_name"]:
		return
	if item.get("folder") and not item.get("attached_to_doctype"):
		title = ns.unique_name(title, cloud._taken(item["folder"], but=item["name"]))
	frappe.db.set_value("File", item["name"], "file_name", title)
	frappe.db.set_value(DOCUMENT, name, "title", title)


def _titled(title: str | None) -> str:
	return " ".join((title or "").replace("/", " ").split())[:MOST_TITLE]


@frappe.whitelist()
@frappe.read_only()
def titles(names: str | list) -> dict:
	"""The titles of the documents named that the reader may still open, for
	the bar's way back to them (public/js/one_sheet/workbooks.js)."""
	said = frappe.parse_json(names) if isinstance(names, str) else names
	out = {}
	for name in (said or [])[:MOST_TITLES]:
		try:
			out[name] = _may(str(name), "read")["file_name"]
		except (frappe.PermissionError, frappe.DoesNotExistError):
			continue
	return out


@frappe.whitelist()
@frappe.read_only()
def people() -> list[dict]:
	"""Who may be mentioned in a comment: the company's active staff."""
	return [
		{"email": one.name, "full_name": one.full_name or one.name, "user_image": one.user_image}
		for one in frappe.get_all(
			"User",
			filters={"enabled": 1, "user_type": "System User", "name": ["not in", ("Administrator", "Guest")]},
			fields=["name", "full_name", "user_image"],
			order_by="full_name asc",
		)
	]


#: The largest picture or video one upload may put into a document.
MOST_PICTURE = 50 * 1024 * 1024

#: Where a picture in a document is read from: through the document, so only
#: those who may open it see what is in it.
PICTURE = "/api/method/onedesk.one_doc.api.picture?id="


@frappe.whitelist(methods=["POST"])
def add_picture(file_id: str) -> dict:
	"""A picture or video put into a document: a private File kept on the
	document, read back through `picture`."""
	_may(file_id, "write")
	upload = frappe.request.files.get("file")
	if not upload:
		frappe.throw(_("No file was sent."))
	content = upload.stream.read()
	if len(content) > MOST_PICTURE:
		frappe.throw(_("This file is too large to put into a document."))
	made = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": upload.filename,
			"content": content,
			"is_private": 1,
			"attached_to_doctype": DOCUMENT,
			"attached_to_name": file_id,
		}
	)
	made.flags.ignore_permissions = True
	made.insert()
	return {"name": made.name, "file_name": made.file_name, "file_url": PICTURE + made.name}


@frappe.whitelist(methods=["POST"])
def make_picture(file_id: str, description: str, shape: str | None = None) -> dict:
	"""A picture OneAI makes from a sentence, square, wide or tall, kept on
	the document as an uploaded one is (OneCloud's job, one_cloud/made.py)."""
	from onedesk.one import apps
	from onedesk.one_cloud import made as maker

	_may(file_id, "write")
	apps.refuse_ai()
	description = (description or "").strip()[: maker.MOST_WORDS]
	if not description:
		frappe.throw(_("Describe what OneAI should make."))
	try:
		content, extension = maker.making("picture", description, shape, None, reference="OneDoc picture")
	except frappe.ValidationError:
		frappe.throw(_("OneAI could not make it. Try again, or describe it differently."))
	made = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"picture-{frappe.generate_hash(length=6)}.{extension}",
			"content": content,
			"is_private": 1,
			"attached_to_doctype": DOCUMENT,
			"attached_to_name": file_id,
		}
	)
	made.flags.ignore_permissions = True
	made.insert()
	return {"name": made.name, "file_name": made.file_name, "file_url": PICTURE + made.name}


@frappe.whitelist()
def picture(id: str) -> None:
	"""A picture in a document, to whoever may open the document."""
	held = frappe.db.get_value("File", id, ["attached_to_doctype", "attached_to_name", "file_name"], as_dict=True)
	if not held or held.attached_to_doctype != DOCUMENT:
		raise frappe.DoesNotExistError
	_may(held.attached_to_name, "read")
	frappe.local.response.update(
		{
			"type": "download",
			"filename": held.file_name,
			"filecontent": frappe.get_doc("File", id).get_content(),
			"display_content_as": "inline",
		}
	)


@frappe.whitelist()
@frappe.read_only()
def picture_extension(entity_name: str) -> str:
	"""A picture's file extension, for naming it in an export."""
	held = frappe.db.get_value("File", entity_name, ["attached_to_doctype", "attached_to_name", "file_name"], as_dict=True)
	if not held or held.attached_to_doctype != DOCUMENT:
		raise frappe.DoesNotExistError
	_may(held.attached_to_name, "read")
	return (held.file_name or "").rsplit(".", 1)[-1].lower() if "." in (held.file_name or "") else "png"


@frappe.whitelist(methods=["POST"])
def drop_pictures(entity_names: str | list) -> None:
	"""Pictures a Word import put in before it failed, taken out again."""
	for name in (frappe.parse_json(entity_names) if isinstance(entity_names, str) else entity_names or [])[:200]:
		held = frappe.db.get_value("File", name, ["attached_to_doctype", "attached_to_name"], as_dict=True)
		if held and held.attached_to_doctype == DOCUMENT:
			_may(held.attached_to_name, "write")
			frappe.delete_doc("File", name, ignore_permissions=True)


@frappe.whitelist()
def download(document: str) -> None:
	"""A document's File opened outside the editor goes to the editor."""
	_may(document, "read")
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = f"/desk/document/{document}"


def copied(doc, method=None) -> None:
	"""File before_insert: a File naming a document another File already
	holds is a copy, so it holds a copy of the document rather than sharing
	it."""
	name = document_of(doc.file_url)
	if not name or not frappe.db.exists("File", {"file_url": doc.file_url}):
		return
	made = frappe.copy_doc(frappe.get_doc(DOCUMENT, name))
	made.title = doc.file_name or made.title
	made.file = None
	made.comments = None
	made.update(dict.fromkeys(("bound_doctype", "bound_name", "bound_field")))
	made.flags.ignore_permissions = True
	made.insert()
	doc.file_url = URL + made.name
	doc.content_hash = None
	doc.flags.one_document = made.name


def placed(doc, method=None) -> None:
	"""File after_insert: a copied document knows its File."""
	if doc.flags.one_document:
		frappe.db.set_value(DOCUMENT, doc.flags.one_document, "file", doc.name)


def file_gone(doc, method=None) -> None:
	"""File on_trash: the document it held, or that edited it, goes with it."""
	from onedesk.one_doc import word

	word.file_gone(doc.name)
	name = document_of(doc.file_url)
	if name and frappe.db.exists(DOCUMENT, name):
		from onedesk.one_doc import versions

		versions.forget(name)
		frappe.delete_doc(DOCUMENT, name, ignore_permissions=True, force=True)
