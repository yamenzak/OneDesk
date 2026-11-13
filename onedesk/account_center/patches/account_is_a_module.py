"""AccountCenter is a module of its own (docs/ONE.md, stage 1): the records it
keeps belong to Account Center rather than One. Run before the doctypes are
synced, so they are found where they now live."""

import frappe

NOW = "Account Center"
MOVED = ("Device", "Workspace Account", "Workspace Add-on", "Workspace Domain")


def execute():
	if not frappe.db.exists("Module Def", NOW):
		frappe.get_doc({"doctype": "Module Def", "module_name": NOW, "app_name": "onedesk"}).insert(ignore_permissions=True)
	for doctype in MOVED:
		frappe.db.set_value("DocType", doctype, "module", NOW, update_modified=False)
	frappe.clear_cache()
