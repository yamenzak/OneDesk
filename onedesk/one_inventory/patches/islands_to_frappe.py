"""Pages OneInventory drew of its own that are frappe's own lists and forms
now (the passthrough of November 2026): their Page records go with their
files, and their addresses lead to the list (desk.js re_route)."""

import frappe

GONE = ("lots", "quotes", "sent_out", "upkeep", "plant")


def execute():
	for page in GONE:
		frappe.delete_doc("Page", page, ignore_missing=True, force=True)
