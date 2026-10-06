"""erpnext and hrms become companions of One rather than apps beside it.

Their `Dock` rows are made to name One as their host, on every migrate, so
their doctypes open in One's rail rather than their own.
"""

import frappe

COMPANIONS = ("erpnext", "hrms")
HOST = "onedesk"
SITE_LAYER = ""


def apply() -> None:
	for app in COMPANIONS:
		name = frappe.db.exists("Dock", {"app": app, "user": SITE_LAYER, "standard": 1})
		if name and frappe.db.get_value("Dock", name, "mount_on") != HOST:
			frappe.db.set_value("Dock", name, "mount_on", HOST, update_modified=False)
	_hide_borrowed_rows()


def _hide_borrowed_rows() -> None:
	"""Keep One's own five on the rail and drop what mounting appended.

	The layer names every row and not only the hidden ones: `resolve_app_dock`
	resolves with `keep_unnamed=False`, so a saved layer is the whole rail and a
	row it does not name is absent rather than inherited.
	"""
	from frappe.desk.doctype.dock.dock import get_app_base, get_app_dock

	ours = {row.get("link_to") for row in get_app_dock(HOST)}
	rows = get_app_base(HOST)
	if len(rows) == len(ours):
		return

	name = frappe.db.exists("Dock", {"app": HOST, "user": SITE_LAYER, "standard": 0})
	layer = frappe.get_doc("Dock", name) if name else frappe.new_doc("Dock")
	layer.app = HOST
	layer.user = SITE_LAYER
	layer.standard = 0
	layer.set(
		"items",
		[
			{
				"link_type": row.get("link_type"),
				"link_to": row.get("link_to"),
				"title": row.get("title"),
				"icon": row.get("icon"),
				"hidden": 0 if row.get("link_to") in ours else 1,
			}
			for row in rows
		],
	)
	layer.save(ignore_permissions=True)
	frappe.cache.delete_value("dock_layers")
