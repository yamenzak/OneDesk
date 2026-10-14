"""OneBook's Home is the `books` page, as OneInventory's is `inventory`: the
figures with their months, the story, Today and the directory. The `OneBook`
workspace it replaces goes, and with it the six number cards only it showed;
home.py still works each figure out."""

import frappe

CARDS = ("Cash", "Owed to Us", "Overdue", "We Owe", "Due This Week", "Profit This Month")


def execute():
	if frappe.db.get_value("Workspace", "OneBook", "module") == "One Book":
		frappe.delete_doc("Workspace", "OneBook", force=True, ignore_permissions=True)
	for card in CARDS:
		if frappe.db.get_value("Number Card", card, "module") == "One Book":
			frappe.delete_doc("Number Card", card, force=True, ignore_permissions=True)
