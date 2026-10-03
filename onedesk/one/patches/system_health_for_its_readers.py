"""System Health in the help menu opens a System Manager's report, which nobody on a
workspace may read. Shown only to whoever can (declutter.SHOW_IF), on sites
installed before the condition was written."""

import frappe

from onedesk.one import declutter


def execute():
	navbar = frappe.get_single("Navbar Settings")
	changed = False
	for row in navbar.get("help_dropdown"):
		if row.item_label in declutter.SHOW_IF and not row.condition:
			row.condition = declutter.SHOW_IF[row.item_label]
			changed = True
	if changed:
		navbar.save(ignore_permissions=True)
