"""Settings' single Server becomes the first row of its Servers list, and
every workspace already built is said to be on it. On the admin site only;
a customer's site has no Tenants."""

import frappe

from onedesk.one_admin import site


def execute():
	if not site.is_admin():
		return
	frappe.reload_doc("one_admin", "doctype", "workspace_server")
	frappe.reload_doc("one_admin", "doctype", "one_admin_settings")
	frappe.reload_doc("one_admin", "doctype", "tenant")
	was = frappe.db.sql(
		"select value from tabSingles where doctype='One Admin Settings' and field='press_server'"
	)
	server = (was[0][0] or "").strip() if was else ""
	if server:
		# Written as a row rather than a Settings save, which would mail the
		# operators that Settings changed.
		if not frappe.db.exists("Workspace Server", {"parent": "One Admin Settings"}):
			frappe.get_doc(
				{
					"doctype": "Workspace Server",
					"parent": "One Admin Settings",
					"parenttype": "One Admin Settings",
					"parentfield": "servers",
					"idx": 1,
					"server": server,
					"open": 1,
				}
			).db_insert()
		frappe.db.sql(
			"update tabTenant set server=%s where ifnull(server, '')='' and ifnull(site, '')!=''", server
		)
	frappe.db.sql("delete from tabSingles where doctype='One Admin Settings' and field='press_server'")
	# A default is not written into a Single that already exists.
	if not frappe.db.get_single_value("One Admin Settings", "press_plan"):
		frappe.db.set_single_value("One Admin Settings", "press_plan", "Unlimited - Hetzner")
