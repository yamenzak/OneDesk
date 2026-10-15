"""OneCRM's Home is the `crm` page, as OneBook's is `books`: the figures with
their months, the story, Today and the directory. The `OneCRM` workspace it
replaces goes, and with it the four number cards only it showed; story.py
works each figure out."""

import frappe

CARDS = ("Pipeline Value", "Weighted Pipeline", "Won This Month", "Win Rate (90 Days)")


def execute():
	if frappe.db.get_value("Workspace", "OneCRM", "module") == "One CRM":
		frappe.delete_doc("Workspace", "OneCRM", force=True, ignore_permissions=True)
	for card in CARDS:
		if frappe.db.get_value("Number Card", card, "module") == "One CRM":
			frappe.delete_doc("Number Card", card, force=True, ignore_permissions=True)
