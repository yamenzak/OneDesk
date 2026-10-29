"""HR Settings' two prevent_self switches on, so frappe's own desk path holds
leave and claims to the rule One's Approve and Reject already keep: nobody
answers their own request (decision.own)."""

import frappe


def execute():
	for switch in ("prevent_self_expense_approval", "prevent_self_leave_approval"):
		if frappe.get_meta("HR Settings").has_field(switch):
			frappe.db.set_single_value("HR Settings", switch, 1)
