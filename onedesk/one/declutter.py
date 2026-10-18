"""Taking the other apps' furniture off One's shell.

A list of names of site data (navbar rows, onboardings, reports) rather than a
patch, so a tenant can put any of it back.
"""

import frappe

HIDE_ROWS = ("Frappe Support", "About", "Delete Demo Data")

SHOW_IF = {"System Health": "frappe.model.can_read('System Health Report')"}

HIDE_REPORTS = (
	"Monthly Attendance Sheet",
	"Shift Attendance",
	"Employee Hours Utilization Based On Timesheet",
	"Recruitment Analytics",
	"Project Summary",
	"Project wise Stock Tracking",
	"Sales Pipeline Analytics",
	"Opportunity Summary by Sales Stage",
	"Lost Opportunity",
)

HIDE_ONBOARDING = ("erpnext", "hrms")


def apply() -> None:
	navbar = frappe.get_single("Navbar Settings")
	for key in ("settings_dropdown", "help_dropdown"):
		for row in navbar.get(key):
			if row.item_label in HIDE_ROWS:
				row.hidden = 1
			if row.item_label in SHOW_IF and not row.condition:
				row.condition = SHOW_IF[row.item_label]
	navbar.save(ignore_permissions=True)

	for name in HIDE_REPORTS:
		if frappe.db.exists("Report", name):
			frappe.db.set_value("Report", name, "disabled", 1)

	ours = set(frappe.get_all("Module Def", filters={"app_name": "onedesk"}, pluck="name"))
	for name, module in frappe.get_all("Module Onboarding", fields=["name", "module"], as_list=True):
		if module in ours:
			continue
		if frappe.db.get_value("Module Def", module, "app_name") in HIDE_ONBOARDING:
			frappe.db.set_value("Module Onboarding", name, "is_complete", 1)
