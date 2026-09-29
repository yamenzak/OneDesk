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
  printing, no JS format, and in the builder no HTML or Typst block: an HTML
  block is markup rendered as it is, Typst reads files. Everything else the
  builder offers (fields, tables, text, images, barcodes, a standard field
  template) is escaped by frappe's own macros.
- **Styles are styles.** A format's CSS goes into a <style> element as it
  is, so it may not contain markup, `@import`, or a URL that is not this
  site's file or an inline image; a block's own style, likewise.
- **A letter head is an image.** Its header and footer are pictures, which
  frappe turns into its own markup; the HTML sources and the header and
  footer scripts stay frappe's System Managers'.

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

from onedesk.one import layer, roles
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

#: Builder blocks that are not frappe's escaped macros. The HTML blocks kept are the
#: ones frappe's own default layout makes: its heading, and an empty block where the
#: doctype has an HTML field, which prints nothing.
UNSAFE_BLOCKS = ("HTML", "Typst")

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
	from frappe.permissions import add_permission, setup_custom_perms, update_permission_property

	for doctype, ptypes in GRANTS.items():
		if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": roles.ADMINISTRATOR}):
			continue
		setup_custom_perms(doctype)
		add_permission(doctype, roles.ADMINISTRATOR, 0)
		for ptype in ptypes:
			update_permission_property(doctype, roles.ADMINISTRATOR, 0, ptype, 1, validate=False)

	# A Custom Role replaces the page's roles, so it keeps the page's own too.
	name = frappe.db.get_value("Custom Role", {"page": BUILDER})
	custom = frappe.get_doc("Custom Role", name) if name else frappe.new_doc("Custom Role")
	if not name:
		custom.page = BUILDER
	held = {row.role for row in custom.roles}
	own = frappe.get_all("Has Role", filters={"parenttype": "Page", "parent": BUILDER}, pluck="role")
	for role in (*own, roles.ADMINISTRATOR):
		if role not in held:
			custom.append("roles", {"role": role})
	if not name or len(custom.roles) != len(held):
		custom.save(ignore_permissions=True)


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
	_layout(json.loads(doc.format_data or "[]"), doc.doc_type, doc.name)


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
		if kind in UNSAFE_BLOCKS and not (
			kind == "HTML" and block.get("html") in (None, "", DEFAULT_PRINT_HEADING)
		):
			frappe.throw(
				_("{0}: an {1} block is not the workspace's to add; it prints as it is written.").format(
					where, kind
				)
			)
		if kind == "Field Template" and not frappe.db.get_value(
			"Print Format Field Template", block.get("field_template"), "standard"
		):
			frappe.throw(_("{0}: only a standard field template may be used.").format(where))
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
	whoever may print the record; anything else goes to frappe's, which refuses."""
	from frappe.utils import print_format_generator

	if not _known(template):
		return print_format_generator.render_jinja_template(template, doctype, docname)
	doc = frappe.get_doc(doctype, docname)
	doc.check_permission("print")
	try:
		return frappe.render_template(template, {"doc": doc})
	except Exception as e:
		frappe.clear_last_message()
		frappe.throw(_("Failed to render template: {0}").format(str(e)), frappe.ValidationError)


def _previewed(print_format) -> None:
	"""The builder previews a format before it is saved, so before the save's own
	checks: the same content checks run first (hooks.override_whitelisted_methods)."""
	if not layer.held():
		return
	doc = frappe.get_doc(frappe.parse_json(print_format))
	if doc.doctype != "Print Format":
		frappe.throw(_("Expected an unsaved Print Format document"))
	_doctype(doc.doc_type)
	_content(doc)


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

	_previewed(print_format)
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

	_previewed(print_format)
	return print_format_generator.download_builder_preview_pdf(
		print_format, doctype, name, letterhead, settings
	)


def _rich_fields(doctype: str) -> set:
	"""(fieldname, fieldtype) of every formatted-text field of the doctype and its tables."""
	meta = frappe.get_meta(doctype)
	metas = [meta, *(frappe.get_meta(df.options) for df in meta.get_table_fields())]
	return {(df.fieldname, df.fieldtype) for one in metas for df in one.fields if df.fieldtype in RICH}


def validate_letter_head(doc, method=None) -> None:
	"""Letter Head validate: a letter head written by the workspace is an image."""
	_stored_images(doc)
	if not layer.held():
		return
	# One the workspace did not make, frappe's own or its System Managers', may be made
	# the default or turned off, and nothing else.
	before = doc.get_doc_before_save()
	if before and (before.standard == "Yes" or before.source != "Image"):
		if any(doc.get(key) != before.get(key) for key in DRAWN):
			frappe.throw(
				_("{0} is not the workspace's to change; it can be made the default or turned off.").format(
					doc.name
				)
			)
		return
	if doc.standard == "Yes" or doc.source != "Image" or (doc.footer_source or "Image") != "Image":
		frappe.throw(
			_("A letter head here is an image: the logo at the top, and a picture at the foot if you like.")
		)
	if doc.header_script or doc.footer_script:
		frappe.throw(_("A letter head may not run a script."))
	# frappe writes the image into the letter head's markup as it is, and keeps
	# whatever markup was sent when there is no image to write.
	if any(ch in (doc.name or "") + (doc.letter_head_name or "") for ch in '"<>'):
		frappe.throw(_("A letter head's name may not contain quotes or angle brackets."))
	if not FILE_URL.match(doc.image or ""):
		frappe.throw(_("A letter head needs its image, uploaded here."))
	if doc.footer_image and not FILE_URL.match(doc.footer_image):
		frappe.throw(_("A letter head's footer is an image uploaded here."))
	if not doc.footer_image:
		doc.footer = None
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
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	frappe.flags.one_printing = True
	try:
		make_property_setter(
			doctype,
			None,
			"default_print_format",
			print_format,
			"Data",
			for_doctype=True,
			is_system_generated=False,
		)
	finally:
		frappe.flags.one_printing = False
	frappe.clear_cache(doctype=doctype)


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
		filters={"standard": "No", "print_format_for": "DocType", "disabled": 0},
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
		fields=["name", *LETTER_HEAD, "source", "standard", "modified"],
		order_by="is_default desc, name asc",
	)


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
	ours = not name or (doc.standard != "Yes" and doc.source == "Image")
	keys = LETTER_HEAD if ours else ("is_default", "disabled")
	doc.update(
		{key: values.get(key) for key in keys if key in values and not (name and key == "letter_head_name")}
	)
	if ours:
		doc.source = "Image"
		doc.footer_source = "Image"
		doc.letter_head_for = "DocType"
	doc.save()
	# The foot is optional here; frappe's reminder that it has no picture is not said.
	if not doc.footer_image:
		failed = _(PICTURES[1][-1])
		frappe.local.message_log = [one for one in frappe.local.message_log if failed not in str(one)]
	return doc.as_dict()
