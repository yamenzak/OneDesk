"""Document templates: a document kept in OneCloud's Document Templates
folder to start others from. Anyone in the company opens them; whoever made
one, or an administrator, changes it, as with any company file. A template
is its own content and nothing else. README, Templates.
"""

import frappe
from frappe import _

from onedesk.one_doc import api

FOLDER_NAME = "Document Templates"

#: What a template gives a document started from it.
KEPT = ("content", "html", "settings")


def folder() -> str:
	"""The Document Templates folder in the company's files, made the first
	time it's needed."""
	from onedesk.one_storage import namespace as ns

	found = frappe.db.get_value("File", {"is_folder": 1, "folder": ns.HOME, "file_name": FOLDER_NAME})
	if found:
		return found
	made = frappe.get_doc({"doctype": "File", "is_folder": 1, "folder": ns.HOME, "file_name": FOLDER_NAME})
	made.flags.ignore_permissions = True
	made.insert()
	return made.name


@frappe.whitelist()
@frappe.read_only()
def listed(html: int = 0) -> list[dict]:
	"""The templates the reader may use, by title; with `html`, what each
	says, for putting one into a document that is open."""
	from onedesk.one_storage import namespace as ns

	out = []
	fields = ["name", "file", "html"] if frappe.utils.cint(html) else ["name", "file"]
	for one in frappe.get_all(api.DOCUMENT, filters={"is_template": 1}, fields=fields, order_by="title asc"):
		item = ns.row(one.file) if one.file else None
		if item and not item.get("one_deleted_on") and ns.may(item, "read"):
			out.append({"name": one.name, "title": item["file_name"], **({"html": one.html or ""} if "html" in fields else {})})
	return out


def content_of(template: str) -> dict:
	"""A template's content, for a new document."""
	held = frappe.db.get_value(api.DOCUMENT, template, ["is_template", *KEPT], as_dict=True)
	if not held or not held.is_template:
		frappe.throw(_("This document is not a template."))
	api._may(template, "read")
	return {key: held.get(key) for key in KEPT}


def make(title: str, values: dict) -> str:
	"""A template in the Document Templates folder; its name."""
	from onedesk.one_storage import api as cloud
	from onedesk.one_storage import namespace as ns

	where = folder()
	title = api._titled(title) or _("Untitled Template")
	doc = frappe.get_doc({"doctype": api.DOCUMENT, "title": title, "is_template": 1, **values})
	doc.flags.ignore_permissions = True
	doc.insert()
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_url": api.URL + doc.name,
			"is_private": 0,
			"folder": where,
			"file_name": ns.unique_name(title, cloud._taken(where)),
		}
	)
	file.flags.ignore_permissions = True
	file.insert()
	doc.db_set("file", file.name)
	return doc.name


@frappe.whitelist(methods=["POST"])
def save_as(name: str, title: str) -> dict:
	"""This document as a template."""
	api._may(name, "read")
	held = frappe.db.get_value(api.DOCUMENT, name, list(KEPT), as_dict=True)
	made = make(title, {key: held.get(key) for key in KEPT})
	return {"name": made, "title": frappe.db.get_value(api.DOCUMENT, made, "title")}
