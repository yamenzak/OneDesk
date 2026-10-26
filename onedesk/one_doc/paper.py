"""A document on paper: its HTML under the company's letter head, with the
record's fields filled in where it names them, as a PDF to print, keep beside
the document, or attach to its record. README, Paper.
"""

import re

import frappe
from bs4 import BeautifulSoup
from frappe import _
from frappe.utils import cint, escape_html

from onedesk.one_doc import api
from onedesk.one_sheet import paper as sheet_paper

MARGIN = 15

#: What a document may be kept as, beside the answer itself.
KEEP = ("", "cloud", "record")

#: Suite's typefaces, as the PDF renderer has them: a serif, a fixed width,
#: or the sans the rest of One prints in.
SERIF = ("eb-garamond", "lora", "merriweather")
FIXED = ("jetbrains", "ibm-plex")

#: Columns whose figures, and headings, sit right.
NUMBERS = ("Currency", "Float", "Int", "Percent")

#: The most rows of a child table a field block prints.
MOST_ROWS = 500

#: Page setup's header and footer, as wkhtmltopdf's own options.
CORNERS = {
	"print_header_left": "header-left",
	"print_header_right": "header-right",
	"print_footer_left": "footer-left",
	"print_footer_right": "footer-right",
}


def record_of(name: str) -> object | None:
	"""The record a document belongs to: the one whose text it is, else the
	one it is filed on, when the reader may open it."""
	held = frappe.db.get_value(api.DOCUMENT, name, ["bound_doctype", "bound_name", "file"], as_dict=True)
	if not held:
		return None
	doctype, docname = held.bound_doctype, held.bound_name
	if not doctype and held.file:
		doctype, docname = frappe.db.get_value("File", held.file, ["attached_to_doctype", "attached_to_name"]) or (None, None)
	if not doctype or not docname or doctype == api.DOCUMENT or not frappe.db.exists(doctype, docname):
		return None
	if not frappe.has_permission(doctype, "read", docname):
		return None
	return frappe.get_doc(doctype, docname)


def _readable(doc, df) -> bool:
	return not df.permlevel or df.permlevel in doc.get_permlevel_access("read")


def printable(df) -> bool:
	"""Whether a field can stand in a document: it holds a value, or rows.
	Hidden ones too, since a quotation keeps its customer in one a print
	hides; whoever puts a field in a document asked for it."""
	from frappe.model import no_value_fields, table_fields

	return bool(df.fieldname) and (df.fieldtype in table_fields or df.fieldtype not in no_value_fields)


def _column(df) -> bool:
	return printable(df) and not df.hidden and not df.print_hide


def _table(doc, df) -> str:
	"""A child table as a print shows it: the columns its list shows, the rows
	formatted."""
	meta = frappe.get_meta(df.options)
	cols = [one for one in meta.fields if one.in_list_view and _column(one)] or [one for one in meta.fields if _column(one)][:6]
	head = "".join(
		f'<th{" class=num" if one.fieldtype in NUMBERS else ""}>{escape_html(_(one.label or one.fieldname))}</th>' for one in cols
	)
	rows = []
	for row in (doc.get(df.fieldname) or [])[:MOST_ROWS]:
		cells = "".join(
			f'<td{" class=num" if one.fieldtype in NUMBERS else ""}>'
			f"{frappe.format(row.get(one.fieldname), one, row)}</td>"
			for one in cols
		)
		rows.append(f"<tr>{cells}</tr>")
	return f'<table class="rows"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>'


def value_of(doc, field: str) -> str:
	"""A field of the record as HTML, formatted as a print shows it; empty
	for one the reader may not see."""
	from frappe.model import table_fields

	if field == "name":
		return escape_html(doc.name)
	df = doc.meta.get_field(field)
	if not df or not printable(df) or not _readable(doc, df):
		return ""
	if df.fieldtype in table_fields:
		return _table(doc, df)
	shown = frappe.format(doc.get(field), df, doc)
	return "" if shown is None else str(shown)


def fill(html: str, doc) -> str:
	"""The document's HTML with each field block holding the record's value;
	with no record, the field's name in brackets."""
	soup = BeautifulSoup(html or "", "html.parser")
	for span in soup.select("span[data-field]"):
		field = span.get("data-field") or ""
		said = value_of(doc, field) if doc is not None else escape_html(f"[{span.get_text()}]")
		made = BeautifulSoup(said, "html.parser")
		parent = span.parent
		if made.find("table") and parent is not None and parent.name == "p" and parent.get_text(strip=True) == span.get_text(strip=True):
			parent.replace_with(made)
		else:
			span.replace_with(made)
	return str(soup)


def _font(settings: dict) -> str:
	family = settings.get("font_family")
	if family in SERIF:
		return "Georgia, 'Times New Roman', serif"
	if family in FIXED:
		return "'DejaVu Sans Mono', monospace"
	return sheet_paper.FONT


def page(name: str, letter_head: str | None = None) -> str:
	"""The whole print as HTML: the letter head's top, the document with the
	record's fields in it, then the foot."""
	from frappe.utils.html_utils import sanitize_html

	held = frappe.db.get_value(api.DOCUMENT, name, ["title", "html", "settings"], as_dict=True)
	settings = api._settings(held.settings)
	doc = record_of(name)
	top, foot = sheet_paper._letter_head(letter_head, doc if doc is not None else _company())
	body = fill(sanitize_html(held.html or "", linkify=False), doc)
	size = max(10, min(cint(settings.get("font_size")) or 14, 24))
	line = settings.get("line_height")
	line = line if isinstance(line, (int, float)) and 1 <= line <= 3 else 1.5
	before = max(0, min(cint(settings.get("paragraph_spacing_before")), 48))
	after = max(0, min(cint(settings.get("paragraph_spacing_after")), 48)) or 8
	return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{escape_html(held.title or "")}</title>
<style>
body{{margin:0;font-family:{_font(settings)};font-size:{size}px;line-height:{line};color:#111827;-webkit-print-color-adjust:exact}}
.top{{margin-bottom:24px}}
.foot{{margin-top:32px}}
p{{margin:{before}px 0 {after}px}}
h1,h2,h3,h4{{line-height:1.25;margin:1.2em 0 .5em}}
h1{{font-size:1.75em}}h2{{font-size:1.4em}}h3{{font-size:1.15em}}h4{{font-size:1em}}
ul,ol{{padding-left:1.5em}}
table{{border-collapse:collapse;width:100%;margin:8px 0}}
td,th{{border:1px solid #d1d5db;padding:4px 6px;vertical-align:top;text-align:left}}
th{{background:#f3f4f6;font-weight:600}}
td.num,th.num{{text-align:right}}
tr{{page-break-inside:avoid}}
img{{max-width:100%}}
blockquote{{border-left:3px solid #d1d5db;margin:0;padding-left:12px;color:#4b5563}}
div[data-page-break]{{page-break-after:always;height:0;border:0}}
</style></head><body>
{f'<div class="top">{top}</div>' if top else ''}{body}{f'<div class="foot">{foot}</div>' if foot else ''}
</body></html>"""


def _company() -> dict:
	"""What a letter head's template reads when the document is on no record."""
	from onedesk.one import control

	company = control._company()
	address = control._company_address(company)
	return frappe._dict(doctype="", name="", company=company.name if company else "", company_address=address.name if address else "")


def options(name: str, landscape: bool = False) -> dict:
	"""wkhtmltopdf's options: the margins, and page setup's header and footer
	text, page numbers and lines."""
	settings = api._settings(frappe.db.get_value(api.DOCUMENT, name, "settings"))
	out = {"orientation": "Landscape" if landscape else "Portrait"}
	for side in ("top", "bottom", "left", "right"):
		out[f"margin-{side}"] = f"{MARGIN}mm"
	for key, option in CORNERS.items():
		text = " ".join(str(settings.get(key) or "").split())[:120]
		if text:
			out[option] = text.replace("[", "(").replace("]", ")")
	if settings.get("print_show_pages"):
		out["footer-right"] = _("Page [page] of [topage]")
	if any(option.startswith("header-") for option in out):
		out.update({"header-font-size": "8", "header-spacing": "5", "margin-top": f"{MARGIN + 5}mm"})
	if any(option.startswith("footer-") for option in out):
		out.update({"footer-font-size": "8", "footer-spacing": "5", "margin-bottom": f"{MARGIN + 5}mm"})
	if settings.get("print_header_separator"):
		out["header-line"] = ""
	if settings.get("print_footer_separator"):
		out["footer-line"] = ""
	return out


def _file_name(title: str) -> str:
	return re.sub(r'[\\/:*?"<>|]', " ", f"{(title or '').strip() or _('Document')}.pdf")


@frappe.whitelist(methods=["POST"])
def pdf(name: str, letter_head: str | None = None, landscape: int = 0, keep: str = "") -> dict | None:
	"""The document as a PDF. With no `keep` it is the answer; with "cloud"
	it is a file beside the document; with "record" it is attached to the
	record the document belongs to."""
	from frappe.utils.pdf import get_pdf

	item = api._may(name, "read")
	if keep not in KEEP:
		frappe.throw(_("A PDF can only be saved to OneCloud or attached to the record."))
	content = get_pdf(page(name, letter_head or None), options(name, bool(cint(landscape))))
	file_name = _file_name(item.get("file_name"))
	if not keep:
		frappe.local.response.filename = file_name
		frappe.local.response.filecontent = content
		frappe.local.response.type = "pdf"
		return None
	return _keep(name, item, file_name, content, keep)


def _keep(name: str, item: dict, file_name: str, content: bytes, keep: str) -> dict:
	"""The PDF as a File: on the record the document belongs to, or beside it
	in its folder."""
	from onedesk.one_storage import api as cloud
	from onedesk.one_storage import namespace as ns

	fields = {"doctype": "File", "content": content, "is_private": 1}
	doc = record_of(name)
	if keep == "record" or (doc is not None and not item.get("folder")):
		if doc is None:
			frappe.throw(_("This document is not on a record."))
		frappe.has_permission(doc.doctype, "write", doc.name, throw=True)
		taken = set(frappe.get_all("File", filters={"attached_to_doctype": doc.doctype, "attached_to_name": doc.name}, pluck="file_name"))
		fields.update(attached_to_doctype=doc.doctype, attached_to_name=doc.name)
		where = [doc.doctype, doc.name]
	elif item.get("folder"):
		if not ns.may(ns.row(item["folder"]), "add"):
			frappe.throw(_("You can't add to this folder."), frappe.PermissionError)
		taken = cloud._taken(item["folder"])
		fields["folder"] = item["folder"]
		where = [item["folder"]]
	else:
		frappe.throw(_("This document is not in a folder."))
	fields["file_name"] = ns.unique_name(file_name, taken)
	made = frappe.get_doc(fields)
	made.flags.ignore_permissions = True
	made.insert()
	return {**ns.node(ns.row(made.name)), "file_url": made.file_url, "where": where}


@frappe.whitelist()
@frappe.read_only()
def fields_of(name: str) -> list[dict]:
	"""The fields of the record a document is on that can stand in it, each
	with what it says now, for Insert a Field."""
	from frappe.model import table_fields
	from frappe.utils import strip_html

	api._may(name, "read")
	doc = record_of(name)
	if doc is None:
		return []
	out = [{"field": "name", "label": _("ID"), "value": doc.name, "table": False}]
	for df in doc.meta.fields:
		if not printable(df) or not _readable(doc, df):
			continue
		table = df.fieldtype in table_fields
		shown = _("{0} rows").format(len(doc.get(df.fieldname) or [])) if table else strip_html(str(frappe.format(doc.get(df.fieldname), df, doc) or ""))
		out.append({"field": df.fieldname, "label": _(df.label or df.fieldname), "value": " ".join(shown.split())[:80], "table": table})
	return out


@frappe.whitelist()
@frappe.read_only()
def on_record(doctype: str, name: str) -> list[dict]:
	"""The documents on a record the reader may open, for the record's print
	page: those filed on it and those that are its text."""
	from onedesk.one_storage import namespace as ns

	if not frappe.has_permission(doctype, "read", name):
		return []
	files = frappe.get_all(
		"File",
		filters={"attached_to_doctype": doctype, "attached_to_name": name, "file_url": ["like", api.URL + "%"]},
		pluck="name",
	)
	out = []
	for file in files:
		item = ns.row(file)
		document = api.document_of(item.get("file_url"))
		if document and not item.get("one_deleted_on") and ns.may(item, "read"):
			out.append({"document": document, "title": item["file_name"]})
	return sorted(out, key=lambda one: one["title"].lower())
