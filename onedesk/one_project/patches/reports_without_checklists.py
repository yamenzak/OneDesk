"""ERPNext's Project Summary and Project wise Stock Tracking took in the HR
checklists; OneProject's Project Progress and Stock by Project replace them
(one_project/report), and theirs are disabled as declutter.py disables the
others One has replaced."""

import frappe


def execute():
	for name in ("Project Summary", "Project wise Stock Tracking"):
		if frappe.db.exists("Report", name):
			frappe.db.set_value("Report", name, "disabled", 1)
