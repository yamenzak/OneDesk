"""Every mail frappe sends ended "Sent via ERPNext": erpnext's
default_mail_footer hook, which another app cannot take back. System
Settings' own switch leaves it out. brand.py sets it on a new site."""

import frappe


def execute():
	settings = frappe.get_single("System Settings")
	if not settings.disable_standard_email_footer:
		settings.disable_standard_email_footer = 1
		settings.save(ignore_permissions=True)
