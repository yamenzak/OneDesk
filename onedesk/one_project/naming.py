"""A task named after its project: REEM-14 rather than TASK-2026-00042.

**Task Prefix** on a project is a short key. Setting it writes a frappe
Document Naming Rule for Task with the condition "project is this one", which
is the framework's own way to name a doctype differently by a field — nothing
of ERPNext's Task is overridden, and a task in a project with no prefix keeps
ERPNext's series.

The number comes from frappe's series for the prefix, which is global to the
site: a prefix changed and changed back carries on counting rather than
reusing a name. Tasks already made keep the names they have. A new project's
rule is written as it is saved, so the tasks a Project Template makes for it
carry the prefix too.
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
	if doc.is_new():
		# ERPNext makes a template's tasks in after_insert, before on_update.
		_write(doc)


def on_update(doc, method=None) -> None:
	"""Project on_update: the naming rule follows the prefix."""
	if doc.has_value_changed("one_key"):
		_write(doc)


def _write(doc) -> None:
	"""The naming rule for a project's prefix, made, changed or removed.

	frappe caches which rules name a Task, and clears that when a rule is saved
	but not when the save is rolled back: a project that failed to save would
	leave a rule in the cache that is not in the database, and no task could be
	made until the cache went. So a rollback clears it too."""
	frappe.db.after_rollback.add(_forget)
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


def _forget() -> None:
	frappe.cache_manager.clear_doctype_map("Document Naming Rule", "Task")


def _rule(project: str) -> str | None:
	"""The naming rule for one project's tasks, if it has one."""
	found = frappe.get_all(
		"Document Naming Rule Condition",
		filters={"parenttype": "Document Naming Rule", "field": "project", "condition": "=", "value": project},
		pluck="parent",
	)
	return next((one for one in found if frappe.db.get_value("Document Naming Rule", one, "document_type") == "Task"), None)
