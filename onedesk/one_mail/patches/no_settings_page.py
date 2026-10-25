"""OneMail's settings are a dialog now (public/js/one_mail/onemail_settings.js), opened
from the foot of its rail, not a page of their own."""

import frappe


def execute():
	if frappe.db.exists("Page", "onemail-settings"):
		frappe.delete_doc("Page", "onemail-settings", force=True, ignore_permissions=True)
