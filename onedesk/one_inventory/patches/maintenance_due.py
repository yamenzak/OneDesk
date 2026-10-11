"""Schedules saved without the form had no next date for their tasks, so no
service was due on anybody's calendar (one_inventory/maintenance.py `due`).
Saved again, each task has its date and its log says when it is due."""

import frappe


def execute():
	plans = frappe.get_all(
		"Asset Maintenance Task",
		filters={"next_due_date": ["is", "not set"], "parenttype": "Asset Maintenance"},
		pluck="parent",
		distinct=True,
	)
	for name in plans:
		plan = frappe.get_doc("Asset Maintenance", name)
		plan.flags.ignore_permissions = True
		plan.save()
