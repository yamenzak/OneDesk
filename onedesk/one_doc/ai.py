"""What OneAI can do with documents: find them and read what they say, and
write a new one or add to one as a card the reader approves
(one_ai/proposals.py, Setup). Every one runs as the person asking, with
OneCloud's answer for the File behind the document. README, Asking OneAI.
"""

from typing import Annotated

import frappe
from frappe import _

from onedesk.one_doc import api

#: The most characters of a document a read answers with.
MOST_TEXT = 20_000

#: The most HTML a card writes.
MOST_HTML = 200_000

HTML = (
	"The words as simple HTML: <h1>-<h3> for headings, <p> for paragraphs, <ul>/<ol> with <li> for lists, "
	"<strong> and <em>, <table> with <tr>/<th>/<td>. No styles, no scripts."
)


def _readable(document: str) -> dict | None:
	if not frappe.db.exists(api.DOCUMENT, document):
		return None
	try:
		return api._may(document, "read")
	except frappe.PermissionError:
		return None


def text_of(html: str | None) -> str:
	"""What a document says, as plain text with its headings kept. Pure but
	for Frappe's html2text."""
	from frappe.core.utils import html2text

	return (html2text(html or "") or "").strip()


def clean(html: str | None) -> str:
	"""HTML a model wrote, with nothing in it that runs or styles itself."""
	from frappe.utils.html_utils import sanitize_html

	return sanitize_html(html or "", linkify=False)


def my_documents(
	words: Annotated[str, "Words from the document's name, or nothing for the latest."] | None = None,
) -> list[dict]:
	"""Find documents the reader may open, newest first: each one's id, name
	and when it last changed. Templates are left out."""
	from onedesk.one_storage import namespace as ns

	filters = {"is_template": 0}
	if words:
		filters["title"] = ["like", f"%{words}%"]
	out = []
	for one in frappe.get_all(api.DOCUMENT, filters=filters, fields=["name", "file", "modified"], order_by="modified desc", limit=100):
		item = ns.row(one.file) if one.file else None
		if not item or item.get("one_deleted_on") or not ns.may(item, "read"):
			continue
		out.append({"document": one.name, "name": item["file_name"], "changed": str(one.modified)})
		if len(out) == 20:
			break
	return out


def read_document(document: Annotated[str, "The document's id, from my_documents."]) -> dict:
	"""Read what a document says, as text with its headings."""
	item = _readable(document)
	if not item:
		return {"error": f"No document the reader may open is {document}."}
	said = text_of(frappe.db.get_value(api.DOCUMENT, document, "html"))
	return {
		"document": document,
		"name": item["file_name"],
		"text": said[:MOST_TEXT],
		**({"cut": f"Only the first {MOST_TEXT} characters."} if len(said) > MOST_TEXT else {}),
	}


def draft_document(
	name: Annotated[str, "What to call it."],
	html: Annotated[str, HTML],
	folder: Annotated[str, "The OneCloud folder to make it in, as its path. Defaults to the reader's own files."] | None = None,
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest a new document, as a card the reader approves. Approving makes
	it in OneCloud as New › Document does and opens nothing."""
	from onedesk.one_ai import proposals

	written = clean(html)
	if not text_of(written):
		return {"mend": "draft_document", "error": "A document says something; send its words as HTML."}
	if len(written) > MOST_HTML:
		return {"mend": "draft_document", "error": "That is too long for one document."}
	changes = {
		"what": "document",
		"title": _("Create Document {0}").format(name),
		"name": name,
		"folder": folder or "",
		"html": written,
		"summary": [{"label": _("Opens with"), "value": text_of(written)[:200]}],
	}
	return {
		"proposal": proposals.propose("Setup", api.DOCUMENT, changes=changes, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what approving it makes. Nothing is made until they approve it.",
	}


def write_document(
	document: Annotated[str, "The document's id, from my_documents."],
	html: Annotated[str, HTML],
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest adding to the end of a document, as a card the reader
	approves. Read it first so what is added follows from what is there.
	Approving adds it as the reader would, and an open copy shows it."""
	from onedesk.one_ai import proposals

	item = _readable(document)
	if not item:
		return {"error": f"No document the reader may open is {document}."}
	try:
		api._may(document, "write")
	except frappe.PermissionError:
		return {"error": "The reader may not change this document."}
	written = clean(html)
	if not text_of(written):
		return {"mend": "write_document", "error": "Send the words to add as HTML."}
	changes = {
		"what": "writing",
		"title": _("Add to {0}").format(item["file_name"]),
		"document": document,
		"html": written,
		"summary": [{"label": _("Adds"), "value": text_of(written)[:200]}],
	}
	return {
		"proposal": proposals.propose("Setup", api.DOCUMENT, changes=changes, record=document, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what approving it adds. Nothing changes until they approve it.",
	}


def approved(changes: dict) -> str:
	"""A document card approved, as the person who pressed Approve. What is
	written is HTML, which the editor turns into its own state the next time
	the document opens; an open copy is told to draw it in now."""
	if changes["what"] == "document":
		from onedesk.one_storage import namespace as ns

		made = api.make(changes.get("folder") or ns.HOME, changes["name"])
		frappe.db.set_value(api.DOCUMENT, made["document"], "html", clean(changes["html"]))
		return made["document"]
	name = changes["document"]
	api._may(name, "write")
	held = frappe.db.get_value(api.DOCUMENT, name, "html") or ""
	written = held + clean(changes["html"])
	from onedesk.one_doc import field

	put = field.put(name, held, written)
	if not put["ok"]:
		frappe.throw(put["message"])
	frappe.db.set_value(api.DOCUMENT, name, {"html": put.get("html", written), "content": None})
	frappe.publish_realtime("one_document_written", {"document": name, "html": clean(changes["html"])}, user=frappe.session.user, after_commit=True)
	return name
