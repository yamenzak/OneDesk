"""OneOS's lease moved onto the File's one lease (one_storage/lease.py): a
session open now keeps its lock, and the OneOS fields go."""

import frappe

MOVED = {
	"one_os_lease": "one_lease_lock",
	"one_os_session": "one_lease_session",
	"one_os_user": "one_lease_user",
	"one_os_until": "one_lease_until",
}


def execute():
	if frappe.db.has_column("File", "one_os_user"):
		for row in frappe.get_all("File", filters={"one_os_user": ["is", "set"]}, fields=["name", *MOVED]):
			frappe.db.set_value(
				"File",
				row.name,
				{"one_lease_kind": "oneos", **{new: row[old] for old, new in MOVED.items()}},
				update_modified=False,
			)
	for old in MOVED:
		if frappe.db.exists("Custom Field", f"File-{old}"):
			frappe.delete_doc("Custom Field", f"File-{old}", ignore_permissions=True, force=True)
