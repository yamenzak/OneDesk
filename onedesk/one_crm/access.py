"""Who may do what in OneCRM, where ERPNext's defaults do not fit.

- A **Sales User** could delete a deal but not a lead. A deal carries its
  stage history, its calls and its reasons for being lost, so deleting one is
  a Sales Manager's, as deleting a lead already was.
- A **Sales User** could only read a Prospect, so the person who makes a lead
  into a business could not write the business down. They may now create and
  edit one.

Everybody in sales still sees every lead and deal: a small team shares its
pipeline, and one that does not can say so with User Permissions.

frappe's `update_permission_property` copies a doctype's standard permissions
into Custom DocPerm before changing one, which is what the Role Permissions
Manager does. Written once: a doctype that already has Custom DocPerm rows has
been decided by the workspace, and is left alone.
"""

import frappe
from frappe.permissions import update_permission_property

#: doctype: [(role, permission, value)]
CHANGES = {
	"Opportunity": [("Sales User", "delete", 0)],
	"Prospect": [("Sales User", "create", 1), ("Sales User", "write", 1)],
}


def settle() -> None:
	for doctype, changes in CHANGES.items():
		if frappe.db.exists("Custom DocPerm", {"parent": doctype}):
			continue
		for role, ptype, value in changes:
			update_permission_property(doctype, role, 0, ptype, value, validate=False)
