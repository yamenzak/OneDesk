"""Making joined OneInventory, so whoever uses it may make goods and whoever
manages it may run the workshop (one/settings.py `APPS`)."""

import frappe

USED = ("Stock User", "Purchase User")
MANAGED = ("Stock Manager", "Purchase Manager", "Item Manager")


def execute():
	for role, given in ((USED, "Manufacturing User"), (MANAGED, "Manufacturing Manager")):
		holders = frappe.get_all("Has Role", filters={"role": ["in", role], "parenttype": "User"}, pluck="parent", distinct=True)
		for user in holders:
			if user in ("Administrator", "Guest") or not frappe.db.get_value("User", user, "enabled"):
				continue
			frappe.get_doc("User", user).add_roles(given)
