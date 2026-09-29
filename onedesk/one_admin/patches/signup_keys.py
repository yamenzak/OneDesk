"""A key for every signup written before signups had one (signup.owned), so the
welcome page and the reminder open for them too."""

import frappe


def execute():
	for name in frappe.get_all("Account Request", filters={"access_key": ["is", "not set"]}, pluck="name"):
		frappe.db.set_value(
			"Account Request", name, "access_key", frappe.generate_hash(length=32), update_modified=False
		)
