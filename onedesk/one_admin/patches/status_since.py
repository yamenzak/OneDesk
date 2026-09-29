"""A workspace's `status_since` is what the ladder counts from: one without it
never falls further, and its head shows no clock. Every rung writes it now
(steps._arrive, steps.live); this gives it to the workspaces written before,
from the last entry in its log, or when it was last changed."""

import frappe


def execute():
	for one in frappe.get_all(
		"Tenant", filters={"status_since": ["is", "not set"]}, fields=["name", "modified", "live_on"]
	):
		logged = frappe.get_all(
			"Tenant Event", filters={"tenant": one.name}, pluck="creation", order_by="creation desc", limit=1
		)
		since = logged[0] if logged else one.live_on or one.modified
		frappe.db.set_value("Tenant", one.name, "status_since", since, update_modified=False)
