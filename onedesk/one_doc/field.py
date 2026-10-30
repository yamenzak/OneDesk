"""A record's long text written in OneWriter: a Text Editor field opens as a
document filed on the record, and what is written goes back into the field
through the record's own save, as the workbook does for a table. AGENTS.md,
On a record.
"""

import frappe
from frappe import _

from onedesk.one_doc import api

#: The fields that open in OneWriter: those that already hold HTML.
LONG = ("Text Editor",)

SAVEPOINT = "one_doc_field"


def _field(doc, field: str):
	df = doc.meta.get_field(field)
	if not df or df.fieldtype not in LONG or df.read_only:
		frappe.throw(_("This record has no such text."))
	return df


def same(one: str | None, other: str | None) -> bool:
	"""Whether two HTML texts say the same, the way a Text Editor field and
	the editor write an empty one differently. Pure."""

	def flat(html):
		html = (html or "").strip()
		return "" if html in ("<p></p>", "<p><br></p>", '<div class="ql-editor read-mode"><p><br></p></div>') else html

	return flat(one) == flat(other)


def writable(doc, df) -> bool:
	"""Whether the field can still change: a draft, or a field allowed to
	change on a submitted record, and the reader may write the record."""
	return (doc.docstatus == 0 or (doc.docstatus == 1 and df.allow_on_submit)) and doc.has_permission("write")


@frappe.whitelist(methods=["POST"])
def open_field(doctype: str, name: str, field: str) -> str:
	"""The document a record's text is written in, made the first time it is
	asked for. When the text was changed on the record since, the document
	starts again from the record. Answers its name."""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	df = _field(doc, field)
	value = doc.get(field) or ""
	held = frappe.db.get_value(api.DOCUMENT, {"bound_doctype": doctype, "bound_name": name, "bound_field": field}, ["name", "file", "html"], as_dict=True)
	if held and held.file and frappe.db.exists("File", held.file):
		if not same(held.html, value):
			frappe.db.set_value(api.DOCUMENT, held.name, {"html": value, "content": None})
		return held.name
	title = api._titled(f"{doc.name} {_(df.label or field)}")
	made = frappe.get_doc(
		{"doctype": api.DOCUMENT, "title": title, "html": value, "bound_doctype": doctype, "bound_name": name, "bound_field": field}
	)
	made.flags.ignore_permissions = True
	made.insert()
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_url": api.URL + made.name,
			"is_private": 1,
			"attached_to_doctype": doctype,
			"attached_to_name": name,
			"file_name": title,
		}
	)
	file.flags.ignore_permissions = True
	file.insert()
	made.db_set("file", file.name)
	return made.name


def bound(name: str) -> dict | None:
	"""What get_document tells the editor about the record's text it is:
	the record, the field's label, and whether it can still change."""
	held = frappe.db.get_value(api.DOCUMENT, name, ["bound_doctype", "bound_name", "bound_field"], as_dict=True)
	if not held or not held.bound_doctype or not frappe.db.exists(held.bound_doctype, held.bound_name):
		return None
	doc = frappe.get_doc(held.bound_doctype, held.bound_name)
	df = doc.meta.get_field(held.bound_field)
	if not df:
		return None
	return {
		"doctype": held.bound_doctype,
		"name": held.bound_name,
		"field": held.bound_field,
		"label": _(df.label) if df.label else held.bound_field,
		"writable": writable(doc, df),
	}


def put(name: str, before: str | None, html: str) -> dict:
	"""save_document for a record's text: the field becomes the document's
	HTML through the record's save. `before` is what the document held, which
	is what the field held unless it was changed on the record since; then
	nothing is written and the person is told. Answers ok, and the HTML the
	record kept, which may be cleaned of what a field may not hold."""
	held = frappe.db.get_value(api.DOCUMENT, name, ["bound_doctype", "bound_name", "bound_field"], as_dict=True)
	if not held or not held.bound_doctype:
		return {"ok": True}
	doc = frappe.get_doc(held.bound_doctype, held.bound_name)
	df = _field(doc, held.bound_field)
	label = _(df.label or held.bound_field)
	if not writable(doc, df):
		return {"ok": False, "message": _("{0} can no longer be changed on {1}.").format(label, doc.name)}
	if not same(doc.get(held.bound_field), before):
		return {
			"ok": False,
			"message": _("{0} was changed on the record after this document was opened. Reopen it from the record to load the changes.").format(label),
		}
	if same(doc.get(held.bound_field), html):
		return {"ok": True}
	doc.set(held.bound_field, html)
	doc.flags.from_writer = True
	frappe.db.savepoint(SAVEPOINT)
	try:
		doc.save()
	except (frappe.ValidationError, frappe.PermissionError) as error:
		frappe.db.rollback(save_point=SAVEPOINT)
		frappe.clear_messages()
		return {"ok": False, "message": frappe.utils.strip_html(str(error)) or _("The record refused this text.")}
	return {"ok": True, "html": frappe.db.get_value(held.bound_doctype, held.bound_name, held.bound_field) or ""}
