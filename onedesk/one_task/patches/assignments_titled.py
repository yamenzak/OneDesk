"""Assignments frappe described by the record's ID are described by its title,
in the to-do and in the record's history (capture.todo_made)."""

import frappe

from onedesk.one_task.capture import _default, titled


def execute():
	for one in frappe.get_all(
		"Comment",
		filters={"comment_type": "Assigned", "content": ["like", "%Assignment for %"]},
		fields=["name", "content", "reference_doctype", "reference_name"],
	):
		said = _default(one.reference_doctype, one.reference_name)
		title = said in (one.content or "") and titled(one.reference_doctype, one.reference_name)
		if title:
			frappe.db.set_value("Comment", one.name, "content", one.content.replace(said, title), update_modified=False)
	for one in frappe.get_all(
		"ToDo",
		filters={"description": ["like", "%Assignment for %"], "reference_name": ["is", "set"]},
		fields=["name", "description", "reference_type", "reference_name"],
	):
		said = _default(one.reference_type, one.reference_name)
		title = said in (one.description or "") and titled(one.reference_type, one.reference_name)
		if title:
			frappe.db.set_value("ToDo", one.name, "description", one.description.replace(said, title), update_modified=False)
