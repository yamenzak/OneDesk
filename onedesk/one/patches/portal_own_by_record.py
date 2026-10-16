"""Who sees a record on the portal is set on the record now (one/portal.py
`mine`), not on the contact: the contact's Portal Shows Only Their Own goes."""

import frappe


def execute():
	if frappe.db.exists("Custom Field", "Contact-one_portal_own"):
		frappe.delete_doc("Custom Field", "Contact-one_portal_own", ignore_permissions=True)
