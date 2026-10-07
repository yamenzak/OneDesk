"""Templates made before their list said how long they run and who uses them
are measured once (templates.py)."""

import frappe

from onedesk.one_project import templates


def execute():
	if not frappe.db.has_column("Project Template", "one_projects"):
		return
	for name in frappe.get_all("Project Template", pluck="name"):
		doc = frappe.get_doc("Project Template", name)
		templates.measured(doc)
		doc.db_set({"one_tasks": doc.one_tasks, "one_days": doc.one_days}, update_modified=False)
		templates.counted(name)
