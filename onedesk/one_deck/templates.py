"""Presentation templates: a presentation kept in OneCloud's Presentation
Templates folder to start others from, and to take slides from, as the
themes' layouts are taken. Anyone in the company opens them; a role with
the template ability (abilities.py) keeps one; whoever made one, or an
administrator, changes it, as with any company file. AGENTS.md, Templates.
"""

import json
import uuid

import frappe
from frappe import _

from onedesk.one_deck import api

FOLDER_NAME = "Presentation Templates"


def folder() -> str:
	"""The Presentation Templates folder in the company's files, made the first
	time it's needed."""
	from onedesk.one_cloud import namespace as ns

	found = frappe.db.get_value("File", {"is_folder": 1, "folder": ns.HOME, "file_name": FOLDER_NAME})
	if found:
		return found
	made = frappe.get_doc({"doctype": "File", "is_folder": 1, "folder": ns.HOME, "file_name": FOLDER_NAME})
	made.flags.ignore_permissions = True
	made.insert()
	return made.name


@frappe.whitelist(methods=["POST"])
def save_as(name: str, title: str) -> dict:
	"""This presentation, kept as a template: a copy, with copies of its pictures."""
	from onedesk.one_cloud import api as cloud
	from onedesk.one_cloud import namespace as ns

	from onedesk.one import rights

	api._may(name, "read")
	if not rights.held(api.PRESENTATION, "slide_template"):
		frappe.throw(_("Your role doesn't keep company templates. Ask a workspace administrator."), frappe.PermissionError)
	title = api._titled(title) or _("Untitled Template")
	source = frappe.get_doc(api.PRESENTATION, name)
	made = frappe.get_doc(
		{"doctype": api.PRESENTATION, "title": title, "theme": source.theme, "is_template": 1, "width": source.width, "height": source.height}
	)
	made.flags.ignore_permissions = True
	made.insert()
	for row in source.slides:
		elements = json.loads(row.elements or "[]")
		for one in elements:
			api._adopted(made.name, one)
		made.append(
			"slides",
			{
				"client_id": str(uuid.uuid4()),
				"background": row.background,
				"elements": json.dumps(elements),
				"transition": row.transition,
				"transition_duration": row.transition_duration,
				"fade_unmatched_elements": row.fade_unmatched_elements,
				"advance_after": row.advance_after,
			},
		)
	made.save(ignore_permissions=True)
	from onedesk.one_deck import master

	master.copy(name, made.name)
	where = folder()
	file = frappe.get_doc(
		{"doctype": "File", "file_url": api.URL + made.name, "is_private": 0, "folder": where, "file_name": ns.unique_name(title, cloud._taken(where))}
	)
	file.flags.ignore_permissions = True
	file.insert()
	made.db_set("file", file.name)
	return {"name": made.name, "title": file.file_name}
