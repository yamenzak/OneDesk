"""Taking the other apps' furniture off One's shell.

A list of names of site data (navbar rows, onboardings, reports) rather than a
patch, so a tenant can put any of it back.
"""

import frappe

#: Navbar rows that send a One tenant somewhere that is not One: Frappe's own
#: support desk, a dialog naming the framework and its version, and an erpnext
#: action for demo data a paying site never had.
HIDE_ROWS = ("Frappe Support", "About", "Delete Demo Data")

#: Navbar rows shown only to whoever can open where they go, on frappe's own
#: read check: System Health is a System Manager's report.
SHOW_IF = {"System Health": "frappe.model.can_read('System Health Report')"}

#: Reports One has replaced with one of its own, disabled rather than deleted, since
#: the row is theirs and would come back; a tenant who wants one enables it.
HIDE_REPORTS = (
	"Monthly Attendance Sheet",
	"Shift Attendance",
	"Employee Hours Utilization Based On Timesheet",
	"Recruitment Analytics",
	# OneProject's, without the HR checklists; see one_project/report.
	"Project Summary",
	"Project wise Stock Tracking",
	# OneCRM's board, Opportunity Forecast and Won and Lost; see one_crm/measure.py.
	"Sales Pipeline Analytics",
	"Opportunity Summary by Sales Stage",
	"Lost Opportunity",
)

#: erpnext's per-module checklists. They are written in erpnext's voice, about
#: erpnext's modules, and they open over whatever One put on the page.
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
