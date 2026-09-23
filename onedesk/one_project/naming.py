"""A task named after its project: REEM-14 rather than TASK-2026-00042.

**Task Prefix** on a project is a short key. Setting it writes a frappe
Document Naming Rule for Task with the condition "project is this one", which
is the framework's own way to name a doctype differently by a field — nothing
of ERPNext's Task is overridden, and a task in a project with no prefix keeps
ERPNext's series.

The number comes from frappe's series for the prefix, which is global to the
site: a prefix changed and changed back carries on counting rather than
reusing a name. Tasks already made keep the names they have.
"""

import re

import frappe
from frappe import _

#: A letter, then letters and digits: what fits on a whiteboard.
KEY = re.compile(r"^[A-Z][A-Z0-9]{1,9}$")


def validate(doc, method=None) -> None:
	"""Project validate: a prefix is well formed and nobody else's."""
	key = (doc.get("one_key") or "").strip().upper()
	doc.one_key = key or None
	if not key:
		return
	if not KEY.match(key):
		frappe.throw(_("A task prefix is 2 to 10 letters and digits, starting with a letter."))
	other = frappe.db.get_value("Project", {"one_key": key, "name": ["!=", doc.name]}, "project_name")
	if other:
		frappe.throw(_("{0} already names the tasks of {1}.").format(key, other))


def on_update(doc, method=None) -> None:
	"""Project on_update: the naming rule follows the prefix."""
	if not doc.has_value_changed("one_key"):
		return
	name = _rule(doc.name)
	if not doc.one_key:
		if name:
			frappe.delete_doc("Document Naming Rule", name, ignore_permissions=True)
		return
	rule = frappe.get_doc("Document Naming Rule", name) if name else frappe.new_doc("Document Naming Rule")
	rule.update({"document_type": "Task", "prefix": f"{doc.one_key}-", "prefix_digits": 1, "priority": 1, "disabled": 0})
	if not name:
		rule.append("conditions", {"field": "project", "condition": "=", "value": doc.name})
	rule.flags.ignore_permissions = True
	rule.save()


def _rule(project: str) -> str | None:
	"""The naming rule for one project's tasks, if it has one."""
	found = frappe.get_all(
		"Document Naming Rule Condition",
		filters={"parenttype": "Document Naming Rule", "field": "project", "condition": "=", "value": project},
		pluck="parent",
	)
	return next((one for one in found if frappe.db.get_value("Document Naming Rule", one, "document_type") == "Task"), None)
