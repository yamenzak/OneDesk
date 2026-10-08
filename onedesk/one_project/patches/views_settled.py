"""Two things the Projects views once showed are kept out of what each person
saved. The HR checklist filter is now asked for quietly (project_list.js),
and the Report view no longer opens with the Cover column, a file path."""

import json

import frappe
from frappe.model.utils.user_settings import clear_user_settings_cache, sync_user_settings

BOARDING = ["Project", "project_type", "!=", "Employee Boarding"]


def settled(settings: dict) -> bool:
	"""Take both out of one person's saved views. Whether anything changed."""
	changed = False
	for view in settings.values():
		if not isinstance(view, dict):
			continue
		if view.get("filters"):
			kept = [one for one in view["filters"] if list(one[:4]) != BOARDING]
			changed = changed or len(kept) != len(view["filters"])
			view["filters"] = kept
		if view.get("fields"):
			kept = [one for one in view["fields"] if list(one[:2]) != ["one_cover", "Project"]]
			changed = changed or len(kept) != len(view["fields"])
			view["fields"] = kept
	return changed


def execute():
	sync_user_settings()
	rows = frappe.qb.DocType("__UserSettings")
	for user, data in (
		frappe.qb.from_(rows).select(rows.user, rows.data).where(rows.doctype == "Project").run()
	):
		settings = json.loads(data or "{}")
		if settled(settings):
			(
				frappe.qb.update(rows)
				.set(rows.data, json.dumps(settings))
				.where((rows.doctype == "Project") & (rows.user == user))
				.run()
			)
	clear_user_settings_cache("Project")
