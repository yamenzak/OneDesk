"""A document as a Word file, and a Word file as a document: "Name.docx" on
the network drive, through a link and attached to mail; Word's save read back
in with a version kept; and a .docx in OneCloud edited in place. AGENTS.md, Word.
"""

import io
import re

import frappe
from bs4 import BeautifulSoup, NavigableString
from frappe import _

from onedesk.one import registry
from onedesk.one_doc import api

SUFFIX = ".docx"

MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

CACHE = "one_doc_docx"

#: The widest a picture is put on a Word page, in inches.
PAGE_WIDTH = 6.0

#: Paragraph styles in python-docx's own template, by how deep a list is.
BULLETS = ("List Bullet", "List Bullet 2", "List Bullet 3")
NUMBERS = ("List Number", "List Number 2", "List Number 3")

ALIGN = {"left": 0, "center": 1, "right": 2, "justify": 3}

BLOCKS = ("p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "table", "blockquote", "pre", "div", "hr", "img")


def _picture(src: str | None) -> bytes | None:
	"""A picture in the document, from its File; nothing from elsewhere."""
	if not src or not src.startswith(api.PICTURE):
		return None
	held = src[len(api.PICTURE) :].split("&", 1)[0]
	if frappe.db.get_value("File", held, "attached_to_doctype") != api.DOCUMENT:
		return None
	try:
		return frappe.get_doc("File", held).get_content()
	except Exception:
		return None


def _align(tag, paragraph) -> None:
	found = re.search(r"text-align:\s*(left|center|right|justify)", tag.get("style") or "")
	if found:
		paragraph.alignment = ALIGN[found[1]]


def _runs(paragraph, node, look: dict | None = None) -> None:
	"""The inline content of `node` as runs of `paragraph`, with the bold,
	italics, underline, strike and code it sits in."""
	from docx.shared import Inches

	look = look or {}
	for child in node.children:
		if isinstance(child, NavigableString):
			text = str(child)
			if not text:
				continue
			run = paragraph.add_run(text)
			run.bold = look.get("bold")
			run.italic = look.get("italic")
			run.underline = look.get("underline")
			run.font.strike = look.get("strike")
			run.font.subscript = look.get("sub")
			run.font.superscript = look.get("sup")
			if look.get("code"):
				run.font.name = "Courier New"
			continue
		name = child.name
		if name == "br":
			paragraph.add_run().add_break()
		elif name == "img":
			content = _picture(child.get("src"))
			if content:
				try:
					paragraph.add_run().add_picture(io.BytesIO(content), width=Inches(PAGE_WIDTH))
				except Exception:
					pass
		else:
			more = dict(look)
			more.update(
				{
					"bold": look.get("bold") or name in ("strong", "b", "th"),
					"italic": look.get("italic") or name in ("em", "i"),
					"underline": look.get("underline") or name in ("u", "a"),
					"strike": look.get("strike") or name in ("s", "strike", "del"),
					"code": look.get("code") or name == "code",
					"sub": look.get("sub") or name == "sub",
					"sup": look.get("sup") or name == "sup",
				}
			)
			_runs(paragraph, child, more)


def _list(doc, tag, depth: int = 0) -> None:
	styles = NUMBERS if tag.name == "ol" else BULLETS
	tasks = tag.get("data-type") == "taskList"
	for item in tag.find_all("li", recursive=False):
		paragraph = doc.add_paragraph(style=styles[min(depth, len(styles) - 1)])
		if tasks:
			paragraph.add_run("☑ " if item.get("data-checked") == "true" else "☐ ")
		for child in item.children:
			if getattr(child, "name", None) in ("ul", "ol"):
				_list(doc, child, depth + 1)
			elif getattr(child, "name", None) in ("p", "div", "label"):
				_runs(paragraph, child)
			elif isinstance(child, NavigableString) or child.name not in BLOCKS:
				_runs(paragraph, BeautifulSoup(str(child), "html.parser"))


def _table(doc, tag) -> None:
	rows = tag.find_all("tr")
	if not rows:
		return
	width = max(len(row.find_all(["td", "th"], recursive=False)) for row in rows)
	if not width:
		return
	table = doc.add_table(rows=len(rows), cols=width)
	table.style = "Table Grid"
	for r, row in enumerate(rows):
		for c, cell in enumerate(row.find_all(["td", "th"], recursive=False)):
			paragraph = table.cell(r, c).paragraphs[0]
			_runs(paragraph, cell, {"bold": cell.name == "th"})


def _blocks(doc, node) -> None:
	for child in node.children:
		if isinstance(child, NavigableString):
			if str(child).strip():
				doc.add_paragraph(str(child).strip())
			continue
		name = child.name
		if name and re.fullmatch(r"h[1-6]", name):
			paragraph = doc.add_paragraph(style=f"Heading {name[1]}")
			_runs(paragraph, child)
			_align(child, paragraph)
		elif name == "p":
			paragraph = doc.add_paragraph()
			_runs(paragraph, child)
			_align(child, paragraph)
		elif name in ("ul", "ol"):
			_list(doc, child)
		elif name == "table":
			_table(doc, child)
		elif name == "blockquote":
			for inner in child.find_all(["p", "h1", "h2", "h3", "h4"], recursive=False) or [child]:
				_runs(doc.add_paragraph(style="Quote"), inner)
		elif name == "pre":
			_runs(doc.add_paragraph(), child, {"code": True})
		elif name == "div" and child.get("data-page-break"):
			doc.add_page_break()
		elif name == "hr":
			doc.add_paragraph()
		elif name == "img":
			_runs(doc.add_paragraph(), BeautifulSoup(str(child), "html.parser"))
		else:
			_blocks(doc, child)


def build(name: str) -> bytes:
	"""The document as a Word file: what it says, with the record's fields
	filled in as on paper, in the page setup's type size."""
	from docx import Document
	from docx.shared import Pt
	from frappe.utils.html_utils import sanitize_html

	from onedesk.one_doc import paper

	held = frappe.db.get_value(api.DOCUMENT, name, ["html", "settings"], as_dict=True) or frappe._dict()
	settings = api._settings(held.settings)
	html = paper.fill(sanitize_html(held.html or "", linkify=False), paper.record_of(name))
	doc = Document()
	size = frappe.utils.cint(settings.get("font_size")) or 14
	doc.styles["Normal"].font.size = Pt(max(8, min(size, 24)) * 0.75)
	_blocks(doc, BeautifulSoup(html, "html.parser"))
	out = io.BytesIO()
	doc.save(out)
	return out.getvalue()


def docx(name: str) -> bytes:
	"""`build`, kept until the document changes."""
	modified = frappe.db.get_value(api.DOCUMENT, name, "modified")
	key = f"{name}:{modified}"
	held = frappe.cache.hget(CACHE, key)
	if held:
		return held
	made = build(name)
	frappe.cache.hset(CACHE, key, made)
	frappe.cache.expire(CACHE, 600)
	return made


def read(name: str, content: bytes, heard: list | None = None) -> str:
	"""A Word file as the document's HTML: its pictures become pictures in
	the document, read through it. What the reader said about the file on
	the way (styles it did not know) goes into `heard`."""
	import mammoth
	from frappe.utils.html_utils import sanitize_html

	def kept(image) -> dict:
		with image.open() as held:
			data = held.read()
		extension = (image.content_type or "image/png").rsplit("/", 1)[-1].replace("jpeg", "jpg")
		made = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"picture.{extension}",
				"content": data,
				"is_private": 1,
				"attached_to_doctype": api.DOCUMENT,
				"attached_to_name": name,
			}
		)
		made.flags.ignore_permissions = True
		made.insert()
		return {"src": api.PICTURE + made.name}

	try:
		said = mammoth.convert_to_html(io.BytesIO(content), convert_image=mammoth.images.img_element(kept))
	except Exception:
		frappe.throw(_("This file cannot be opened."))
	if heard is not None:
		heard.extend(said.messages or [])
	return sanitize_html(said.value or "", linkify=False)


def dropped(content: bytes, heard: list, own: bool) -> list[str]:
	"""What OneDoc does not keep of a Word file, but for the styles
	`build` writes itself; a document of One's own never had fonts and
	colours to lose."""
	from onedesk.one_cloud import fidelity

	return fidelity.document(content, heard, built=("Quote", *BULLETS, *NUMBERS), formatting=not own)


def write(name: str, content: bytes) -> None:
	"""Word's save of a document on the drive: its HTML becomes the
	document's, what it said before kept as a version, and the editor builds
	itself from it the next time it opens. A record's text, or a document
	with the record's fields in it, is not written from Word, which would
	keep the fields' values and lose the fields. What the Word file had that
	the document does not keep is noted on it, shown when it next opens."""
	from onedesk.one_cloud import saving
	from onedesk.one_doc import versions

	item = api._may(name, "write")
	saving.check(api.DOCUMENT, name, item)
	held = frappe.db.get_value(api.DOCUMENT, name, ["html", "bound_doctype"], as_dict=True)
	if held.bound_doctype or 'data-field="' in (held.html or ""):
		frappe.throw(_("A document with a record's fields in it can only be edited in {0}.").format(registry.name("one_doc")), frappe.PermissionError)
	heard = []
	html = read(name, content, heard)
	if held.html:
		versions.new_version(name, held.html, saving.before(_("Before a Word save")))
	frappe.db.set_value(api.DOCUMENT, name, {"html": html, "content": None, "byte_size": len(html.encode("utf-8"))}, update_modified=True)
	saving.outside(api.DOCUMENT, name, dropped(content, heard, own=True))


def of_file(file: str) -> str | None:
	"""The document that edits a .docx File in place."""
	return frappe.db.get_value(api.DOCUMENT, {"file": file, "source_kind": "docx"}, "name")


@frappe.whitelist(methods=["POST"])
def open_file(file: str) -> dict:
	"""The document that edits a .docx File in place, made the first time it
	is opened from the File's content. What is written is put back into the
	File when the editor is left (write_back)."""
	from onedesk.one_cloud import namespace as ns

	item = ns.row(file)
	if not item or item.get("is_folder") or item.get("one_deleted_on") or not ns.may(item, "read"):
		frappe.throw(_("This file cannot be opened."), frappe.PermissionError)
	if not (item.get("file_name") or "").lower().endswith(SUFFIX):
		frappe.throw(_("Only Word files can be opened as a document."))
	held = of_file(file)
	if held and frappe.db.get_value(api.DOCUMENT, held, "html"):
		return {"document": held}
	if not held:
		made = frappe.get_doc({"doctype": api.DOCUMENT, "title": item["file_name"], "file": file, "source_kind": "docx"})
		made.flags.ignore_permissions = True
		made.insert()
		held = made.name
	from onedesk.one_cloud import saving

	content = frappe.get_doc("File", file).get_content()
	heard = []
	html = read(held, content, heard)
	frappe.db.set_value(api.DOCUMENT, held, {"html": html, "content": None})
	saving.opened(api.DOCUMENT, held, dropped(content, heard, own=False))
	return {"document": held}


@frappe.whitelist(methods=["POST"])
def write_back(name: str, choice: str = "", edited: int = 1) -> dict:
	"""What was written in a .docx File's document, as the File's content:
	what it held before is kept as a version (one_cloud/history.py). When
	that would drop parts of the file, it waits for the reader's `choice`,
	over or copy (one_cloud/saving.py); `edited` says whether anything
	was written beyond the editor's first paint."""
	from onedesk.one_cloud import saving

	item = api._may(name, "write")
	if frappe.db.get_value(api.DOCUMENT, name, "source_kind") != "docx":
		frappe.throw(_("This document is not linked to a Word file."))
	waits = not choice and saving.listed(frappe.db.get_value(api.DOCUMENT, name, "would_lose"))
	return saving.write_back(api.DOCUMENT, name, item, b"" if waits else build(name), choice, edited=frappe.utils.cint(edited))


def file_replaced(file: str) -> None:
	"""A new version of a .docx File put in from outside the editor: its
	document reads it in again the next time it is opened, or, holding
	changes that waited for a choice, is kept as a copy instead."""
	from onedesk.one_cloud import saving

	name = None if frappe.flags.one_writing_back else of_file(file)
	if name and not saving.set_aside(api.DOCUMENT, name, api.URL):
		frappe.db.set_value(api.DOCUMENT, name, {"html": "", "content": None})


def file_gone(file: str) -> None:
	"""A .docx File deleted: the document that edited it goes too."""
	from onedesk.one_doc import versions

	name = of_file(file)
	if name:
		versions.forget(name)
		frappe.delete_doc(api.DOCUMENT, name, ignore_permissions=True, force=True)
