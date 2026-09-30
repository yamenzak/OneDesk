"""Printing: how a workspace's documents look on paper, for its administrators.
docs/DESK-COVERAGE.md, stage 3.

The formats are frappe's own: Print Format made in frappe's print format
builder, and Letter Head. The workspace administrator is given both, and the
builder page, through frappe's own Custom DocPerm and Custom Role. What is
held here is what a printed page may carry when somebody frappe does not let
customize wrote it (layer.held), because the page is drawn on this site's
origin, where a script runs as whoever opens it, and a PDF is drawn by a
browser on the server:

- **A format is made in the builder.** No hand-written HTML format, no raw
  printing, no JS format, and in the builder no Typst block, which reads
  files. An HTML block is allowed as print_html.py holds it: a template that
  reads only the record, rendered in a sandbox of its own, its markup cleaned.
  Everything else the builder offers (fields, tables, text, images, barcodes,
  a standard field template) is escaped by frappe's own macros.
- **Styles are styles.** A format's CSS goes into a <style> element as it
  is, so it may not contain markup, `@import`, or a URL that is not this
  site's file or an inline image; a block's own style, likewise.
- **A letter head is a picture or plain HTML.** Its top and foot are each a
  picture, which frappe turns into its own markup, or HTML with no template in
  it, stored cleaned (print_html.letter_head_html). The header and footer
  scripts stay frappe's System Managers'.

A standard format stays frappe's (it refuses changes outside developer
mode); a workspace copies it in the builder and changes the copy.
"""

import json
import re
from typing import Annotated

import frappe
from frappe import _
from frappe.printing.doctype.print_format.classic_converter import DEFAULT_PRINT_HEADING
from frappe.utils import flt, is_image
from frappe.utils.html_utils import sanitize_html

from onedesk.one import layer, print_html, roles
from onedesk.one.customize import REFUSED_MODULES
from onedesk.one_storage import store

#: What the workspace administrator may do with each.
GRANTS = {
	"Print Format": ("read", "write", "create", "delete", "print"),
	"Letter Head": ("read", "write", "create", "delete"),
	# The builder's Library: saved parts of a layout, checked as a format is.
	"Print Format Snippet": ("read", "write", "create", "delete"),
	# The builder reads the page size; changing it stays frappe's.
	"Print Settings": ("read",),
}

#: frappe's print format builder, a page whose only role is System Manager.
BUILDER = "print-format-builder"

#: Builder blocks the workspace may not add: Typst reads files.
UNSAFE_BLOCKS = ("Typst",)

#: The HTML blocks frappe's own default layout makes, which stay frappe's: its
#: heading, and an empty block where the doctype has an HTML field.
FRAPPES_HTML = (None, "", DEFAULT_PRINT_HEADING)

#: What frappe's renderer sets on a block as it draws, and trusts when it finds it
#: already there (print_format_generator: a stored `renderer` is used as is, a
#: stored `_value` is printed unescaped by the Data macro).
DRAWN_KEYS = ("renderer", "section")

#: A block's kind names a macro file; only a plain name may.
KIND = re.compile(r"^[A-Za-z ]+$")

#: Kinds whose value frappe prints as markup. A block may say one only of a field
#: that really is one, or a record's plain text would print as markup.
RICH = ("Text Editor", "HTML Editor", "Markdown Editor")

#: Where this site's files are served: frappe's folders, or One's store (one_storage).
FILES = rf"(/files/|/private/files/|{re.escape(store.FETCH)}\?)"

#: An image uploaded to this site, as frappe writes it into a letter head's markup.
FILE_URL = re.compile(rf"""^{FILES}[^"'<>]+$""")

#: What a URL in a style may point at: this site's files, or an inline image.
SAFE_URL = re.compile(rf"""url\(\s*['"]?\s*({FILES}|data:image/)""", re.I)


def settle() -> None:
	"""The grants, once per doctype (a doctype with a Custom DocPerm row for
	the role has been decided by the workspace), and the builder page."""
	roles.grant(GRANTS)
	roles.open_page(BUILDER)


def _doctype(doctype: str) -> None:
	if not doctype or not frappe.db.exists("DocType", doctype):
		frappe.throw(_("There is no such kind of record."))
	if frappe.get_meta(doctype).module in REFUSED_MODULES:
		frappe.throw(_("{0} is not printed from formats this workspace sets.").format(_(doctype)))
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("You cannot open {0}.").format(_(doctype)), frappe.PermissionError)


def _style(text: str | None, where: str) -> None:
	"""A style is a style: no markup, no import, no URL off this site."""
	if not text:
		return
	lowered = text.lower()
	if "<" in text or "@import" in lowered or "expression(" in lowered or "javascript:" in lowered:
		frappe.throw(_("{0}: a style may not contain markup or load anything.").format(where))
	for found in re.finditer(r"url\(", text, re.I):
		if not SAFE_URL.match(text, found.start()):
			frappe.throw(_("{0}: a style may only use this site's files and images.").format(where))


def _blocks(data) -> list[dict]:
	"""Every block in a builder format, wherever it sits."""
	if isinstance(data, dict):
		found = [data] if data.get("fieldtype") else []
		return found + [one for value in data.values() for one in _blocks(value)]
	if isinstance(data, list):
		return [one for value in data for one in _blocks(value)]
	return []


def validate_format(doc, method=None) -> None:
	"""Print Format validate: what a format written by the workspace may carry."""
	if not layer.held():
		return
	if doc.print_format_for != "DocType" or doc.standard == "Yes":
		frappe.throw(_("A workspace makes print formats for its own kinds of record."))
	_doctype(doc.doc_type)
	doc.print_format_builder_beta = 1
	_content(doc)


def _content(doc) -> None:
	"""What a format prints: made in the builder, of frappe's escaped blocks."""
	if doc.custom_format or doc.raw_printing or (doc.print_format_type or "Jinja") != "Jinja":
		frappe.throw(_("Print formats are made in the print format builder here, not written by hand."))
	_style(doc.css, _("Style"))
	data = json.loads(doc.format_data or "[]")
	_layout(data, doc.doc_type, doc.name)
	doc.format_data = json.dumps(data)


def _layout(data, doctype: str | None, name: str) -> None:
	"""Every block of a builder layout is one of frappe's escaped macros."""
	rich = _rich_fields(doctype) if doctype else set()
	for block in _blocks(data):
		where = block.get("label") or name
		kind = block.get("fieldtype") or ""
		if (
			not KIND.match(kind)
			or any(key in block for key in DRAWN_KEYS)
			or any(str(key).startswith("_") for key in block)
		):
			frappe.throw(_("{0}: this block is not one the print format builder makes.").format(where))
		if kind in RICH and (block.get("fieldname"), kind) not in rich:
			frappe.throw(
				_("{0}: only a field that holds formatted text may print as formatted text.").format(where)
			)
		if kind in UNSAFE_BLOCKS:
			frappe.throw(
				_("{0}: an {1} block is not the workspace's to add; it prints as it is written.").format(
					where, kind
				)
			)
		if kind == "HTML":
			# Marked or not by this save alone, so a mark is never the writer's to leave off.
			block.pop(print_html.MARK, None)
			if block.get("html") not in FRAPPES_HTML:
				if not isinstance(block["html"], str):
					frappe.throw(
						_("{0}: this block is not one the print format builder makes.").format(where)
					)
				print_html.check_template(block["html"], where)
				block[print_html.MARK] = 1
		if kind == "Field Template" and not frappe.db.get_value(
			"Print Format Field Template", block.get("field_template"), "standard"
		):
			frappe.throw(_("{0}: only a standard field template may be used.").format(where))
		if kind == "Image" and block.get("image_url") and not print_html.IMAGE.match(str(block["image_url"])):
			frappe.throw(_("{0}: a picture here is one uploaded to this workspace.").format(where))
		for key in ("custom_style", "style", "label_color", "value_color"):
			_style(block.get(key), where)


def validate_snippet(doc, method=None) -> None:
	"""Print Format Snippet validate: a saved part of a layout is checked as a
	format is, since a System Manager may put it into theirs."""
	if not layer.held():
		return
	if doc.standard:
		frappe.throw(_("A workspace makes print formats for its own kinds of record."))
	if doc.document_type:
		_doctype(doc.document_type)
	try:
		data = json.loads(doc.content or "null")
	except ValueError:
		frappe.throw(_("{0}: this block is not one the print format builder makes.").format(doc.name))
	_layout(data, doc.document_type, doc.name)
	doc.content = json.dumps(data)


def _known(template: str) -> bool:
	"""Whether a template the builder previews is frappe's own writing: the default
	heading, a standard field template, the empty block frappe's layout leaves for
	an HTML field, or a letter head's markup, which every print already carries."""
	if not template or template == DEFAULT_PRINT_HEADING:
		return True
	if frappe.db.exists("Print Format Field Template", {"standard": 1, "template": template}):
		return True
	return bool(
		frappe.db.exists("Letter Head", {"content": template})
		or frappe.db.exists("Letter Head", {"footer": template})
	)


@frappe.whitelist()
def render_jinja_template(template: str, doctype: str, docname: str) -> str:
	"""frappe's canvas preview of a Jinja template, which frappe keeps to its System
	Managers since a template is code. The ones frappe wrote are previewed for
	whoever may print the record, and a workspace's HTML block as it will print
	(print_html.render); anything else goes to frappe's, which refuses."""
	from frappe.utils import print_format_generator

	held = layer.held()
	if not _known(template) and not held:
		return print_format_generator.render_jinja_template(template, doctype, docname)
	doc = frappe.get_doc(doctype, docname)
	doc.check_permission("print")
	if not _known(template):
		print_html.check_template(template, _("HTML"))
		return print_html.render(template, doc)
	try:
		return frappe.render_template(template, {"doc": doc})
	except Exception as e:
		frappe.clear_last_message()
		frappe.throw(_("Failed to render template: {0}").format(str(e)), frappe.ValidationError)


def _previewed(print_format):
	"""The builder previews a format before it is saved, so before the save's own
	checks: the same content checks run first (hooks.override_whitelisted_methods),
	and what is previewed is the format as they leave it, its HTML blocks marked."""
	if not layer.held():
		return print_format
	doc = frappe.get_doc(frappe.parse_json(print_format))
	if doc.doctype != "Print Format":
		frappe.throw(_("Expected an unsaved Print Format document"))
	_doctype(doc.doc_type)
	_content(doc)
	return doc.as_dict()


@frappe.whitelist()
def render_builder_preview(
	print_format: str | dict,
	doctype: str,
	name: str | None = None,
	letterhead: str | None = None,
	settings: str | dict | None = None,
) -> str:
	"""frappe's builder preview, of a format the workspace may print."""
	from frappe.utils import print_format_generator

	print_format = _previewed(print_format)
	return print_format_generator.render_builder_preview(print_format, doctype, name, letterhead, settings)


@frappe.whitelist()
def download_builder_preview_pdf(
	print_format: str | dict,
	doctype: str,
	name: str | None = None,
	letterhead: str | None = None,
	settings: str | dict | None = None,
):
	"""frappe's builder preview as a PDF, of a format the workspace may print."""
	from frappe.utils import print_format_generator

	print_format = _previewed(print_format)
	return print_format_generator.download_builder_preview_pdf(
		print_format, doctype, name, letterhead, settings
	)


def _rich_fields(doctype: str) -> set:
	"""(fieldname, fieldtype) of every formatted-text field of the doctype and its tables."""
	meta = frappe.get_meta(doctype)
	metas = [meta, *(frappe.get_meta(df.options) for df in meta.get_table_fields())]
	return {(df.fieldname, df.fieldtype) for one in metas for df in one.fields if df.fieldtype in RICH}


def validate_letter_head(doc, method=None) -> None:
	"""Letter Head validate: a letter head written by the workspace is a picture
	or plain HTML, at its top and at its foot; a top drawn from a preset is
	drawn first (letter_heads.apply) and held like any other."""
	from onedesk.one import letter_heads

	letter_heads.apply(doc)
	_stored_images(doc)
	if not layer.held():
		# The top and foot are filtered here rather than by frappe's XSS filter, which
		# takes out an inline picture (letter_heads draws its icons as one): a drawn
		# one is ours and escaped, and any other gets frappe's own filter.
		if doc.content and not doc.one_top:
			doc.content = sanitize_html(doc.content)
		if doc.footer and not doc.get("one_foot"):
			doc.footer = sanitize_html(doc.footer)
		return
	# One the workspace did not make, frappe's own or one that runs a script, may be
	# made the default or turned off, and nothing else.
	before = doc.get_doc_before_save()
	if before and (before.standard == "Yes" or before.header_script or before.footer_script):
		if any(doc.get(key) != before.get(key) for key in DRAWN):
			frappe.throw(
				_("{0} is not the workspace's to change; it can be made the default or turned off.").format(
					doc.name
				)
			)
		return
	if doc.standard == "Yes":
		frappe.throw(_("A workspace makes its own letter heads."))
	if doc.header_script or doc.footer_script:
		frappe.throw(_("A letter head may not run a script."))
	# frappe writes the image into the letter head's markup as it is, and keeps
	# whatever markup was sent when there is no image to write.
	if any(ch in (doc.name or "") + (doc.letter_head_name or "") for ch in '"<>'):
		frappe.throw(_("A letter head's name may not contain quotes or angle brackets."))
	if (doc.source or "Image") == "HTML":
		doc.content = print_html.letter_head_html(doc.content, _("Header"))
		if not (doc.content or "").strip():
			frappe.throw(_("A letter head's header needs something to print."))
	elif not FILE_URL.match(doc.image or ""):
		frappe.throw(_("A letter head needs its image, uploaded here."))
	if (doc.footer_source or "Image") == "HTML":
		doc.footer = print_html.letter_head_html(doc.footer, _("Footer"))
	else:
		if doc.footer_image and not FILE_URL.match(doc.footer_image):
			frappe.throw(_("A letter head's footer is an image uploaded here."))
		if not doc.footer_image:
			doc.footer = None
			# The foot is optional; frappe's reminder that it has no picture is not said.
			failed = _(PICTURES[1][-1])
			frappe.local.message_log = [one for one in frappe.local.message_log if failed not in str(one)]
	if (doc.source or "Image") not in ("Image", "HTML") or (doc.footer_source or "Image") not in (
		"Image",
		"HTML",
	):
		frappe.throw(_("A letter head's header and footer are each a picture or HTML."))
	_style(doc.custom_css, _("Style"))


#: A letter head's two pictures: which source says so, the field, its size fields,
#: its alignment, where frappe writes the markup, and what frappe says when it cannot
#: (LetterHead.set_image).
PICTURES = (
	(
		"source",
		"image",
		"image_",
		"align",
		"content",
		"Please attach an image file to set HTML for Letter Head.",
	),
	(
		"footer_source",
		"footer_image",
		"footer_image_",
		"footer_align",
		"footer",
		"Please attach an image file to set HTML for Footer.",
	),
)


def _stored_images(doc) -> None:
	"""frappe writes a letter head's picture into its markup only when the URL names
	an image file, and reads the name before any query, where One's store keeps it
	(one_storage/store.py). Such a picture is written here as frappe writes it
	(LetterHead.set_image_as_html), and frappe's word that it was not an image
	is taken back."""
	for source, field, prefix, align, html_field, failed in PICTURES:
		url = doc.get(field)
		if doc.get(source) != "Image" or not store.is_stored(url) or not is_image(store.key_of(url) or ""):
			continue
		if any(ch in url + (doc.name or "") for ch in '"<>'):
			continue
		for key in ("width", "height"):
			doc.set(prefix + key, flt(doc.get(prefix + key)))
		dimension = "width" if doc.get(prefix + "width") > doc.get(prefix + "height") else "height"
		value = doc.get(prefix + dimension) or ""
		doc.set(
			html_field,
			f"""<div style="text-align: {(doc.get(align) or "").lower()};">
<img src="{url}" alt="{doc.name}"
{dimension}="{value}" style="{dimension}: {value}px;">
</div>""",
		)
		failed = _(failed)
		frappe.local.message_log = [one for one in frappe.local.message_log if failed not in str(one)]


@frappe.whitelist(methods=["POST"])
def set_default(
	doctype: Annotated[str, "The kind of record."],
	print_format: Annotated[str, "The format it prints with unless another is chosen."],
) -> None:
	"""What frappe's make_default does for a standard doctype: a property setter,
	which the workspace layer would otherwise refuse (layer.property_setter), and
	which frappe's own writes as whoever calls it, who may not make one."""
	roles.require()
	_doctype(doctype)
	if frappe.get_meta(doctype).custom:
		frappe.throw(_("{0} is not printed from formats this workspace sets.").format(_(doctype)))
	if frappe.db.get_value("Print Format", print_format, "doc_type") != doctype:
		frappe.throw(_("{0} is not a format of {1}.").format(print_format, _(doctype)))
	frappe.has_permission("Print Format", "write", doc=print_format, throw=True)
	layer.set_default(doctype, "default_print_format", print_format)


def _passes(check) -> bool:
	muted = frappe.flags.mute_messages
	frappe.flags.mute_messages = True
	try:
		check()
		return True
	except frappe.ValidationError:
		frappe.clear_last_message()
		return False
	finally:
		frappe.flags.mute_messages = muted


def _hold_copy(doc) -> None:
	"""A copy of a frappe format as the workspace may keep it: the blocks and
	styles validate_format refuses (a standard format's own HTML block, say)
	left out, and everything else as it was."""

	def kept(data):
		if isinstance(data, list):
			return [
				kept(one)
				for one in data
				if not (
					isinstance(one, dict)
					and one.get("fieldtype")
					and not _passes(
						lambda one=one: _layout(
							[{k: v for k, v in one.items() if not isinstance(v, list | dict)}],
							doc.doc_type,
							doc.name,
						)
					)
				)
			]
		if isinstance(data, dict):
			return {key: kept(value) for key, value in data.items()}
		return data

	doc.format_data = json.dumps(kept(json.loads(doc.format_data or "[]")))
	if not _passes(lambda: _style(doc.css, "")):
		doc.css = None


def starts(doctype: str) -> list[dict]:
	"""The builder formats a new format of a kind may start as a copy of, the
	one it prints with first: the frappe builder's own (Classic, Modern) and the
	workspace's."""
	_doctype(doctype)
	default = frappe.get_meta(doctype).default_print_format
	rows = frappe.get_all(
		"Print Format",
		filters={
			"doc_type": doctype,
			"print_format_builder_beta": 1,
			"disabled": 0,
			"name": ["!=", DESIGNER],
		},
		fields=["name", "standard"],
		order_by="name asc",
	)
	return sorted(rows, key=lambda one: (one.name != default, one.standard != "Yes", one.name))


@frappe.whitelist()
def new_format_starts(doctype: Annotated[str, "The kind of record."]) -> list[dict]:
	"""What New in the Print Formats tab offers to start from."""
	roles.require()
	return starts(doctype)


@frappe.whitelist(methods=["POST"])
def new_format(
	doctype: Annotated[str, "The kind of record."],
	name: Annotated[str, "The new format's name."],
	start_from: Annotated[str, "A builder format of the kind to copy, or empty for every field."]
	| None = None,
) -> str:
	"""A new format, made as frappe's builder makes one: a copy of a format the
	kind already prints with, as frappe's Duplicate copies it, or, from nothing,
	a builder format frappe lays out from the kind's fields. Held by
	validate_format like any other."""
	roles.require()
	_doctype(doctype)
	name = (name or "").strip()
	if not name:
		frappe.throw(_("A print format needs a name."))
	if start_from:
		if start_from not in {one.name for one in starts(doctype)}:
			frappe.throw(_("{0} is not a format {1} can start from.").format(start_from, _(doctype)))
		doc = frappe.copy_doc(frappe.get_doc("Print Format", start_from))
		doc.standard = "No"
		doc.disabled = 0
		if layer.held():
			_hold_copy(doc)
	else:
		doc = frappe.new_doc("Print Format")
		doc.update({"doc_type": doctype, "print_format_builder_beta": 1})
	doc.set("__newname", name)
	doc.insert()
	return doc.name


#: Builder blocks that are not a field of the record: the builder's palette.
PALETTE = ("HTML", "Spacer", "Divider", "Image", "Barcode", "Repeater", "Static Text", "Linked Field")


#: Where a format may print its page number (Print Format's page_number).
#: A Google Font's name as frappe's Print Format takes it (its `font`, which
#: frappe imports from Google Fonts itself): words of letters and digits.
FONT = re.compile(r"[A-Za-z0-9]+(?: [A-Za-z0-9]+){0,5}")

PAGE_NUMBER = ("Hide", "Top Left", "Top Center", "Top Right", "Bottom Left", "Bottom Center", "Bottom Right")


def format_doc(
	doctype: str,
	name: str,
	layout: dict,
	css: str | None = None,
	letter_head: str | None = None,
	page_number: str | None = None,
	font: str | None = None,
):
	"""A builder format, unsaved, from a layout as the builder stores one: a
	`header`, `sections` and a `footer`, each of columns of blocks. Every block
	is a field of the kind (a table's columns fields of its rows) or one of the
	builder's own (PALETTE), and the whole is held as the builder's save holds
	it (_content). What OneAI designs is made here, and checked here."""
	_doctype(doctype)
	if not isinstance(layout, dict) or not isinstance(layout.get("sections"), list):
		frappe.throw(_("A layout has sections, each of columns of blocks."))
	meta = frappe.get_meta(doctype)
	unknown = []
	for block in _placed(layout):
		kind = block.get("fieldtype")
		if kind in PALETTE:
			block["custom"] = 1
			if not block.get("fieldname") or meta.has_field(block["fieldname"]):
				block["fieldname"] = f"{kind.lower().replace(' ', '_')}_{frappe.generate_hash(length=8)}"
			continue
		fieldname = block.get("fieldname")
		if fieldname in ("name", "doctype"):
			continue
		field = meta.get_field(fieldname) if fieldname else None
		if not field:
			# A table's column is a field of its rows.
			if not any(frappe.get_meta(one.options).has_field(fieldname) for one in meta.get_table_fields()):
				unknown.append(str(fieldname))
			continue
		block.setdefault("label", field.label)
		block["fieldtype"] = field.fieldtype
		if field.fieldtype in frappe.model.table_fields:
			block["options"] = field.options
			rows = frappe.get_meta(field.options)
			for column in block.get("table_columns") or []:
				if column.get("fieldname") == "idx":
					column.setdefault("label", _("No."))
					column.setdefault("fieldtype", "Int")
					continue
				row_field = rows.get_field(column.get("fieldname"))
				if not row_field:
					unknown.append(f"{fieldname}.{column.get('fieldname')}")
					continue
				column.setdefault("label", row_field.label)
				column["fieldtype"] = row_field.fieldtype
				if row_field.options:
					column["options"] = row_field.options
	if unknown:
		frappe.throw(
			_("{0} has no field {1}.").format(_(doctype), ", ".join(dict.fromkeys(unknown))),
			frappe.ValidationError,
		)
	if letter_head:
		if not frappe.db.exists("Letter Head", letter_head):
			frappe.throw(_("There is no letter head {0}.").format(letter_head))
		layout["letter_head"] = letter_head
	if page_number and page_number not in PAGE_NUMBER:
		frappe.throw(_("The page number prints at one of: {0}.").format(", ".join(PAGE_NUMBER)))
	font = (font or "").strip()
	if font and not FONT.fullmatch(font):
		frappe.throw(_("A font is a Google Font's name, such as Playfair Display."))
	doc = frappe.new_doc("Print Format")
	doc.update(
		{
			**({"page_number": page_number} if page_number else {}),
			**({"font": font} if font else {}),
			"doc_type": doctype,
			"standard": "No",
			"print_format_for": "DocType",
			"print_format_builder_beta": 1,
			"format_data": json.dumps(layout),
			"css": css or None,
		}
	)
	doc.name = name
	_content(doc)
	return doc


def _placed(layout: dict) -> list[dict]:
	"""Every block a layout places, whether it says its kind or not."""
	parts = [layout.get("header"), *(layout.get("sections") or []), layout.get("footer")]
	placed = []
	for part in parts:
		if not isinstance(part, dict):
			continue
		for column in part.get("columns") or []:
			if not isinstance(column, dict) or not isinstance(column.get("fields") or [], list):
				frappe.throw(_("A layout has sections, each of columns of blocks."))
			for block in column.get("fields") or []:
				if not isinstance(block, dict):
					frappe.throw(_("A layout has sections, each of columns of blocks."))
				placed.append(block)
	return placed


def save_format(values: dict) -> str:
	"""A format OneAI designed, made or changed as whoever approved it."""
	name, kind = (values.get("name") or "").strip(), values["doctype"]
	doc = format_doc(
		kind,
		name,
		json.loads(values["format_data"]),
		values.get("css"),
		page_number=values.get("page_number"),
		font=values.get("font"),
	)
	if frappe.db.exists("Print Format", name):
		held = frappe.get_doc("Print Format", name)
		if held.standard == "Yes" or held.doc_type != kind:
			frappe.throw(_("{0} is not a format of {1} this workspace made.").format(name, _(kind)))
		held.update(
			{
				"format_data": doc.format_data,
				"css": doc.css,
				"draft_data": None,
				**({"page_number": doc.page_number} if values.get("page_number") else {}),
			}
		)
		held.save()
		return held.name
	doc.name = None
	doc.set("__newname", name)
	doc.insert()
	return doc.name


def _sample(doctype: str) -> str | None:
	found = frappe.get_list(doctype, limit_page_length=1, order_by="modified desc", pluck="name")
	return found[0] if found else None


@frappe.whitelist()
def proposal_preview(proposal: Annotated[str, "An AI Proposal of kind Printing."]) -> str:
	"""The page a Printing card would make, drawn before it is approved: a
	format on the kind's latest record, or a letter head's top and foot."""
	entry = frappe.get_doc("AI Proposal", proposal)
	entry.check_permission("read")
	if entry.kind != "Printing":
		frappe.throw(_("This suggestion does not change how anything prints."))
	changes = frappe.parse_json(entry.changes or "{}") or {}
	made = changes.get("format")
	if made:
		print_format = frappe.new_doc("Print Format")
		print_format.update(
			{
				"doc_type": made["doctype"],
				"standard": "No",
				"print_format_for": "DocType",
				"print_format_builder_beta": 1,
				"format_data": made["format_data"],
				"css": made.get("css"),
			}
		)
		print_format.name = made["name"]
		return render_builder_preview(print_format.as_dict(), made["doctype"], _sample(made["doctype"]))
	head = changes.get("letter_head") or {}
	held = frappe.db.get_value("Letter Head", head.get("name"), ["content", "footer"], as_dict=True) or {}
	top = head.get("content") if "content" in head else held.get("content")
	if not top and head.get("image"):
		top = f'<div><img src="{frappe.utils.escape_html(head["image"])}" style="max-height:80px"></div>'
	foot = head.get("footer") if "footer" in head else held.get("footer")
	lines = "".join('<div style="height:6px;margin:8px 0;background:#e5e7eb"></div>' for _ in range(4))
	return (
		'<!doctype html><html><body style="margin:0;padding:24px;font-family:sans-serif;background:#fff;color:#111">'
		f'{print_html.clean(top or "")}<div style="margin:24px 0">{lines}</div>{print_html.clean(foot or "")}'
		"</body></html>"
	)


#: The workspace's own format frappe's builder opens to design a letter head on:
#: the builder draws a format's letter head above and below it, top and foot, each
#: a picture or HTML. It is kept off, so nothing prints with it, and out of every
#: list of formats.
DESIGNER = "Letter Head Designer"

#: The kinds of record the designer is laid out as, the first one they can open.
DESIGNED_ON = ("Sales Invoice", "Quotation", "Sales Order", "Purchase Order", "Project", "Employee")


@frappe.whitelist(methods=["POST"])
def design_letter_head(letter_head: Annotated[str, "The letter head to design."]) -> str:
	"""Point the designer at a letter head and say where it is: frappe's print
	format builder, whose letter head zones are where it is drawn."""
	roles.require()
	if not frappe.db.exists("Letter Head", letter_head):
		frappe.throw(_("There is no letter head {0}.").format(letter_head))
	frappe.has_permission("Letter Head", "write", doc=letter_head, throw=True)
	if frappe.db.get_value("Letter Head", letter_head, "standard") == "Yes":
		frappe.throw(
			_("{0} is not the workspace's to change; it can be made the default or turned off.").format(
				letter_head
			)
		)
	if not frappe.db.exists("Print Format", DESIGNER):
		doctype = next(
			(
				one
				for one in DESIGNED_ON
				if frappe.db.exists("DocType", one)
				and frappe.get_meta(one).module not in REFUSED_MODULES
				and frappe.has_permission(one, "read")
			),
			None,
		)
		if not doctype:
			frappe.throw(_("There is no kind of record here to lay a letter head out on."))
		first = starts(doctype)
		new_format(doctype, DESIGNER, first[0].name if first else None)
	doc = frappe.get_doc("Print Format", DESIGNER)
	data = json.loads(doc.format_data or "{}")
	if isinstance(data, dict):
		data["letter_head"] = letter_head
		doc.format_data = json.dumps(data)
	# The builder opens a draft over the format when there is one.
	doc.draft_data = None
	doc.disabled = 1
	doc.save()
	return doc.name


def state(doctype: str | None = None, print_format: str | None = None) -> str:
	"""How printing stands now, so a card suggested against an older state is
	refused: the kind's default format, the format it changes, and every letter
	head as it was."""
	return frappe.as_json(
		{
			"default": frappe.get_meta(doctype).default_print_format if doctype else None,
			"format": str(frappe.db.get_value("Print Format", print_format, "modified") or "")
			if print_format
			else None,
			"letter_heads": {
				one.name: str(one.modified)
				for one in frappe.get_all("Letter Head", fields=["name", "modified"], order_by="name asc")
			},
		}
	)


@frappe.whitelist()
def default(doctype: Annotated[str, "The kind of record."]) -> str | None:
	"""The format the doctype prints with unless another is chosen. frappe's tab
	reads it from Property Setter and DocType, neither the administrator's to read."""
	roles.require()
	_doctype(doctype)
	return frappe.get_meta(doctype).default_print_format


def formats() -> list[dict]:
	"""Every print format the workspace made, for Workspace > Printing."""
	roles.require()
	rows = frappe.get_all(
		"Print Format",
		filters={"standard": "No", "print_format_for": "DocType", "disabled": 0, "name": ["!=", DESIGNER]},
		fields=["name", "doc_type", "modified"],
		order_by="doc_type asc, name asc",
	)
	return [
		dict(row, label=_(row.doc_type))
		for row in rows
		if frappe.get_meta(row.doc_type).module not in REFUSED_MODULES
		and frappe.has_permission(row.doc_type, "read")
	]


#: What a letter head prints, which only its maker changes.
DRAWN = (
	"source",
	"footer_source",
	"content",
	"footer",
	"image",
	"footer_image",
	"header_script",
	"footer_script",
	"custom_css",
	"image_height",
	"image_width",
	"footer_image_height",
	"footer_image_width",
	"align",
	"footer_align",
)

LETTER_HEAD = (
	"letter_head_name",
	"one_top",
	"one_foot",
	"source",
	"content",
	"footer_source",
	"footer",
	"image",
	"image_height",
	"align",
	"footer_image",
	"footer_image_height",
	"footer_align",
	"is_default",
	"disabled",
)


def letter_heads() -> list[dict]:
	roles.require()
	return frappe.get_all(
		"Letter Head",
		filters={"letter_head_for": "DocType"},
		fields=["name", *LETTER_HEAD, "standard", "modified"],
		order_by="is_default desc, name asc",
	)


def _start_letter_head(doc) -> None:
	"""A new letter head starts as the Classic top and the Centred foot, drawn
	from what Workspace > General keeps (letter_heads.py)."""
	doc.one_top = frappe.as_json({"preset": "classic"})
	doc.one_foot = frappe.as_json({"preset": "centred"})


@frappe.whitelist(methods=["POST"])
def save_letter_head(values: Annotated[str | dict, "The letter head's fields."]) -> dict:
	"""A letter head, made or changed: an image at the top and one at the foot."""
	roles.require()
	values = frappe.parse_json(values) or {}
	name = values.get("name")
	doc = frappe.get_doc("Letter Head", name) if name else frappe.new_doc("Letter Head")
	if name and values.get("modified") and str(doc.modified) != str(values["modified"]):
		frappe.throw(
			_("Somebody changed {0} after you opened it.").format(name), frappe.TimestampMismatchError
		)
	ours = not name or not (doc.standard == "Yes" or doc.header_script or doc.footer_script)
	if not name and not values.get("image") and not values.get("content") and not values.get("one_top"):
		_start_letter_head(doc)
	keys = LETTER_HEAD if ours else ("is_default", "disabled")
	doc.update(
		{key: values.get(key) for key in keys if key in values and not (name and key == "letter_head_name")}
	)
	if ours:
		doc.letter_head_for = "DocType"
	doc.save()
	return doc.as_dict()
