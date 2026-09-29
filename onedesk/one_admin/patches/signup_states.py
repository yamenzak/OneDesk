"""A signup's status, for the requests written before it moved on its own.

A request with a workspace that has been live is Done, one with a workspace
still being made is Provisioning, and one nobody paid for in a week is
Abandoned (signup.abandon), which lets its name go."""

import frappe
from frappe.utils import add_days, now_datetime

from onedesk.one_admin.signup import ABANDONED_DAYS

#: A workspace in any of these was live once.
BEEN_LIVE = ("Live", "Overdue", "Suspended", "Archived", "Dropped")


def execute():
	for name, tenant, status in frappe.get_all(
		"Account Request",
		filters={"tenant": ["is", "set"]},
		fields=["name", "tenant", "status"],
		as_list=True,
	):
		now = frappe.db.get_value("Tenant", tenant, "status")
		if now in BEEN_LIVE and status != "Done":
			frappe.db.set_value(
				"Account Request", name, {"status": "Done", "failed_reason": None}, update_modified=False
			)
		elif now and now not in BEEN_LIVE and status in ("New", "Paying", "Paid"):
			frappe.db.set_value("Account Request", name, "status", "Provisioning", update_modified=False)
	frappe.db.set_value(
		"Account Request",
		{
			"status": ["in", ["New", "Paying"]],
			"tenant": ["is", "not set"],
			"creation": ["<", add_days(now_datetime(), -ABANDONED_DAYS)],
		},
		"status",
		"Abandoned",
		update_modified=False,
	)
