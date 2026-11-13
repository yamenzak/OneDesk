"""erpnext and hrms become companions of One rather than apps beside it.

Their `Dock` rows are made to name One as their host, on every migrate, so
their doctypes open in One's rail rather than their own. A private app's Dock
is mounted the same way, and its rows stay shown (account_center/private.py).
"""

import frappe

COMPANIONS = ("erpnext", "hrms")
HOST = "onedesk"
SITE_LAYER = ""


def apply() -> None:
	from onedesk.account_center import private

	for app in (*COMPANIONS, *private.names()):
		name = frappe.db.exists("Dock", {"app": app, "user": SITE_LAYER, "standard": 1})
		if name and frappe.db.get_value("Dock", name, "mount_on") != HOST:
			frappe.db.set_value("Dock", name, "mount_on", HOST, update_modified=False)
	layer()


def layer(order: list[str] | None = None) -> None:
	"""The site's Dock layer: One's own rows, less the apps turned off
	(one/apps.py) and what mounting appended, in the workspace's order
	(`order`, by dock key, else the layer's own; `rail.ordered`). It names
	every row: `resolve_app_dock` drops a row a saved layer does not name."""
	from frappe.desk.doctype.dock.dock import dock_key, get_app_base, get_app_dock

	from onedesk.one import apps, rail
	from onedesk.account_center import private

	ours = {row.get("link_to") for row in get_app_dock(HOST)} | private.rail()
	off = set(apps.hidden())
	rows = get_app_base(HOST)
	name = frappe.db.exists("Dock", {"app": HOST, "user": SITE_LAYER, "standard": 0})
	if len(rows) == len(ours) and not off and not name and not order:
		return
	layer = frappe.get_doc("Dock", name) if name else frappe.new_doc("Dock")
	if order is None:
		order = [dock_key(row) for row in layer.get("items") or []]
	by_key = {dock_key(row): row for row in rows}
	rows = [by_key[key] for key in rail.ordered(list(by_key), [key for key in order if key in by_key])]
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
				"hidden": 0 if row.get("link_to") in ours and row.get("link_to") not in off else 1,
			}
			for row in rows
		],
	)
	layer.save(ignore_permissions=True)
	frappe.cache.delete_value("dock_layers")
