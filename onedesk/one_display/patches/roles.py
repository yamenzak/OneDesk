"""OneDisplay's two roles, made before its doctypes so their permissions
resolve: the manager pairs screens and builds channels, the user works a
counter."""

import frappe

ROLES = ("OneDisplay Manager", "OneDisplay User")


def execute():
	for name in ROLES:
		if not frappe.db.exists("Role", name):
			frappe.get_doc({"doctype": "Role", "role_name": name, "desk_access": 1, "is_custom": 1}).insert(
				ignore_permissions=True
			)
