"""What OneAI can do with documents: find them and read what they say, and
write a new one or add to one as a card the reader approves
(one_ai/proposals.py, Setup). Every one runs as the person asking, with
OneCloud's answer for the File behind the document. AGENTS.md, Asking OneAI.
"""

from typing import Annotated

import frappe
from frappe import _

from onedesk.one_doc import api

# The calls that change something OneAI reaches as a card, by the tool whose
# card makes the call when it is approved (docs/READY.md, mechanism 11).
REACH = {"api.make": "draft_document"}

# Why OneAI's chat does not do these itself: each is the editor's own, or is
# OneAI already, asked from the editor.
NOT_FOR_AI = {
	"api.save_document": "The editor saves what is written as it goes, and OneAI writes through a card instead.",
	"api.save_settings": "Page setup is chosen by eye in the editor, where the page shows it.",
	"api.save_comments": "A comment is somebody's own words, written in the document's margin.",
	"api.rename_document": "A document is named from its path in the editor, by the person working on it.",
	"api.add_picture": "It answers a picture put into the document in the editor.",
	"api.make_picture": "It is OneAI making a picture, asked from the editor's picture button.",
	"api.drop_pictures": "It answers pictures taken out of the document in the editor.",
	"field.open_field": "A record's text opens in OneDoc from the record's form, by the person reading it.",
	"paper.pdf": "Printing is the person's choice of letter head and page, made in the editor's Print dialog.",
	"templates.save_as": "A template is kept from the editor's File menu by whoever may keep company templates.",
	"versions.new_version": "A version is taken while somebody writes, or named by them in Version History.",
	"word.open_file": "It answers a Word file opened from OneCloud.",
	"word.write_back": "It writes the Word file back when the person leaves it in the editor, or chooses how.",
	"api.dismiss_dropped": "It puts away the note of what a save from the drive left out, in the editor.",
}

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
	from onedesk.one_cloud import namespace as ns

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


def _template(said: str | None) -> str | None:
	"""A template by its id or its title, when the reader may use it."""
	from onedesk.one_doc import templates

	if not said:
		return None
	for one in templates.listed():
		if said in (one["name"], one["title"]):
			return one["name"]
	return None


def draft_document(
	name: Annotated[str, "What to call it."],
	html: Annotated[str, HTML] | None = None,
	folder: Annotated[str, "The OneCloud folder to make it in, as its id. Defaults to the reader's own files."] | None = None,
	record_doctype: Annotated[str, "To file it on a record instead, the record's type, such as Quotation."] | None = None,
	record_name: Annotated[str, "And that record's id."] | None = None,
	template: Annotated[str, "A template to start from, by its title or id (Document Templates in OneCloud)."] | None = None,
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest a new document, as a card the reader approves: in a folder or
	filed on a record (a covering letter on a quotation), from a template or
	from the HTML given, or both, the HTML then following the template.
	Approving makes it as New › Document does. On a record, the template's
	field blocks print what that record says."""
	from onedesk.one_ai import proposals

	written = clean(html)
	chosen = _template(template)
	if template and not chosen:
		return {"mend": "draft_document", "error": f"There is no template called {template} the reader may use."}
	if not chosen and not text_of(written):
		return {"mend": "draft_document", "error": "A document says something; send its words as HTML, or name a template."}
	if len(written) > MOST_HTML:
		return {"mend": "draft_document", "error": "That is too long for one document."}
	if record_doctype or record_name:
		if not (record_doctype and record_name and frappe.db.exists(record_doctype, record_name)):
			return {"mend": "draft_document", "error": f"There is no {record_doctype} {record_name}."}
		if not frappe.has_permission(record_doctype, "write", record_name):
			return {"error": f"The reader may not add documents to {record_doctype} {record_name}."}
	shown = [{"label": _("Opens with"), "value": text_of(written)[:200]}] if text_of(written) else []
	changes = {
		"what": "document",
		"title": _("Create Document {0}").format(name),
		"name": name,
		"folder": folder or "",
		"record": [record_doctype, record_name] if record_doctype else None,
		"template": chosen,
		"html": written,
		"summary": [
			*([{"label": _("On"), "value": f"{_(record_doctype)} {record_name}"}] if record_doctype else []),
			*([{"label": _("From the template"), "value": template}] if chosen else []),
			*shown,
		],
	}
	return {
		"proposal": proposals.propose("Setup", api.DOCUMENT, changes=changes, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what approving it makes. Nothing is made until they approve it.",
	}


#: Where write_document puts its words.
WHERE = ("selection", "after", "end")


def _selection(document: str) -> dict:
	"""What the reader has selected in this document, as the page said when
	the question was asked: the selected text and the paragraph the cursor
	is in."""
	page = frappe.flags.one_ai_page or {}
	said = page.get("selection") if isinstance(page.get("selection"), dict) else {}
	return said if said.get("document") == document else {}


def write_document(
	document: Annotated[str, "The document's id, from my_documents or the page the reader is on."],
	html: Annotated[str, HTML],
	where: Annotated[
		str,
		"selection to put it in place of what the reader has selected; after to put it after the paragraph "
		"the reader's cursor is in; end (the default) to add it at the end.",
	] = "end",
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest writing into a document, as a card the reader approves: in
	place of the selection (to rewrite, shorten, translate or fix it), after
	the paragraph the cursor is in, or at the end. Read it first so what is
	written follows from what is there. A record's field goes in as
	<span data-field="fieldname">Label</span>."""
	from onedesk.one_ai import proposals

	item = _readable(document)
	if not item:
		return {"error": f"No document the reader may open is {document}."}
	try:
		api._may(document, "write")
	except frappe.PermissionError:
		return {"error": "The reader may not change this document."}
	if where not in WHERE:
		return {"mend": "write_document", "error": f"where is one of {', '.join(WHERE)}."}
	written = clean(html)
	if not text_of(written):
		return {"mend": "write_document", "error": "Send the words to write as HTML."}
	selected = _selection(document)
	if where == "selection" and not (selected.get("text") or "").strip():
		return {"mend": "write_document", "error": "Nothing is selected in that document; use after or end, or ask the reader to select the words."}
	if where == "after" and not (selected.get("block") or "").strip():
		where = "end"
	titles = {"selection": _("Rewrite in {0}"), "after": _("Add to {0}"), "end": _("Add to {0}")}
	changes = {
		"what": "writing",
		"title": titles[where].format(item["file_name"]),
		"document": document,
		"html": written,
		"where": where,
		"replacing": (selected.get("text") or "")[:MOST_TEXT] if where == "selection" else "",
		"after": (selected.get("block") or "")[:MOST_TEXT] if where == "after" else "",
		"summary": [
			*([{"label": _("In place of"), "value": (selected.get("text") or "")[:200]}] if where == "selection" else []),
			{"label": _("Writes"), "value": text_of(written)[:200]},
		],
	}
	return {
		"proposal": proposals.propose("Setup", api.DOCUMENT, changes=changes, record=document, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what approving it writes and where. Nothing changes until they approve it.",
	}


def _blocks(soup):
	return soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th", "blockquote"])


def _said(tag) -> str:
	return " ".join(tag.get_text().split())


def placed(held: str, written: str, where: str, replacing: str = "", after: str = "") -> str | None:
	"""The document's HTML with `written` put where the card said, or None
	when the place can't be found in the stored HTML (the selection ran
	across paragraphs, or changed since); the open editor puts it in then.
	Pure but for BeautifulSoup."""
	from bs4 import BeautifulSoup

	if where == "end":
		return held + written
	soup = BeautifulSoup(held or "", "html.parser")
	new = BeautifulSoup(written, "html.parser")
	if where == "after":
		found = [one for one in _blocks(soup) if one.name in ("p", "h1", "h2", "h3", "h4", "h5", "h6", "li") and _said(one) == " ".join(after.split())]
		if len(found) != 1:
			return None
		found[0].insert_after(new)
		return str(soup)
	wanted = " ".join(replacing.split())
	whole = [one for one in _blocks(soup) if _said(one) == wanted]
	if len(whole) == 1:
		whole[0].replace_with(new)
		return str(soup)
	hits = [node for node in soup.find_all(string=True) if replacing and replacing in node]
	if len(hits) != 1 or str(hits[0]).count(replacing) != 1:
		return None
	top = new.find_all(recursive=False)
	inline = list((top[0] if len(top) == 1 and top[0].name == "p" else new).contents)
	node = hits[0]
	before, _, rest = str(node).partition(replacing)
	for part in (before, *inline, rest):
		node.insert_before(part)
	node.extract()
	return str(soup)


def approved(changes: dict) -> str:
	"""A document card approved, as the person who pressed Approve. What is
	written goes into the stored HTML where it can be found there, and the
	editor builds itself from it the next time the document opens; an open
	copy is told to put it in now, where the reader left the selection."""
	if changes["what"] == "document":
		from onedesk.one_cloud import namespace as ns

		where = "@records/{}/{}".format(*changes["record"]) if changes.get("record") else changes.get("folder") or ns.HOME
		made = api.make(where, changes["name"], changes.get("template"))
		if changes.get("html"):
			held = frappe.db.get_value(api.DOCUMENT, made["document"], "html") or ""
			frappe.db.set_value(api.DOCUMENT, made["document"], {"html": held + clean(changes["html"]), "content": None})
		return made["document"]
	name = changes["document"]
	api._may(name, "write")
	where = changes.get("where") or "end"
	held = frappe.db.get_value(api.DOCUMENT, name, "html") or ""
	written = clean(changes["html"])
	result = placed(held, written, where, changes.get("replacing") or "", changes.get("after") or "")
	if result is not None:
		from onedesk.one_doc import field

		put = field.put(name, held, result)
		if not put["ok"]:
			frappe.throw(put["message"])
		frappe.db.set_value(api.DOCUMENT, name, {"html": put.get("html", result), "content": None})
	frappe.publish_realtime(
		"one_document_written",
		{"document": name, "html": written, "where": where, "replacing": changes.get("replacing") or "", "after": changes.get("after") or ""},
		user=frappe.session.user,
		after_commit=True,
	)
	return name


#: How much of the open document the panel is told up front.
MOST_SEEN = 3000


def page(said: dict) -> str | None:
	"""The sentence the model is told on a document's page: which document,
	what it says, the record it is on and that record's fields, and what the
	reader has selected or where their cursor is."""
	if said.get("page") != "document":
		return None
	name = (said.get("record") or "").strip()
	item = _readable(name) if name else None
	if not item:
		return "The reader is on a document's page in OneDoc."
	from onedesk.one_doc import paper

	held = frappe.db.get_value(api.DOCUMENT, name, ["html", "bound_doctype", "bound_field"], as_dict=True)
	text = text_of(held.html)
	where = f'The reader has the document "{item["file_name"]}" open in OneDoc (its id is {name})'
	record = paper.record_of(name)
	if held.bound_doctype and record is not None:
		where += f", which is the {held.bound_field} text of {record.doctype} {record.name}; what is written there goes into that field"
	elif record is not None:
		fields = ", ".join(f"{one['field']} ({one['label']})" for one in paper.fields_of(name)[:60])
		where += (
			f", filed on {record.doctype} {record.name}. A field of that record goes into the document as "
			f'<span data-field="fieldname">Label</span> and prints what the record says; its fields are {fields}'
		)
	where += f'. It says:\n"""\n{text[:MOST_SEEN]}\n"""' + (" (and more; read_document reads it all)" if len(text) > MOST_SEEN else "")
	selected = said.get("selection") if isinstance(said.get("selection"), dict) else {}
	if selected.get("document") == name and (selected.get("text") or "").strip():
		where += f'\nThe reader has selected: """{selected["text"][:MOST_SEEN]}""". A request about "this" or "it" means the selection; write_document with where=selection puts new words in its place.'
	elif selected.get("document") == name and (selected.get("block") or "").strip():
		where += f'\nThe reader\'s cursor is in the paragraph: """{selected["block"][:500]}"""; write_document with where=after puts new words after it.'
	return where + (
		"\nwrite_document writes into it as a card; draft_document makes a new one, in a folder or on a record, "
		"from a template or not. How OneDoc works is in its documentation (how_to)."
	)


READS = (
	"my_documents",
	"read_document",
)
"""The tools OneAI reads here (registry/hooks.py lists them in one_ai_reads)."""


SUGGESTS = (
	"draft_document",
	"write_document",
)
"""The tools OneAI suggests, each as a card a person applies here (registry/hooks.py lists them in one_ai_suggests)."""
