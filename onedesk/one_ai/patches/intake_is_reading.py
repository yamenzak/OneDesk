"""OneIntake is OneAI's reading now (docs/AICENTER.md, stage 4): its doctypes,
reports, page and fields belong to the One AI module, the One Intake module
goes, and the notification of a change to it is Reading Changed. Run before
the doctypes are synced, so they are found where they now live."""

import frappe

GONE = "One Intake"
NOW = "One AI"


def execute():
	tables = frappe.db.sql(
		"select table_name from information_schema.columns where table_schema = database() and column_name = 'module'",
		pluck=True,
	)
	for table in tables:
		if table.startswith("tab") and table != "tabModule Def":
			frappe.db.sql(f"update `{table}` set module = %s where module = %s", (NOW, GONE))
	frappe.db.delete("Module Def", {"name": GONE})
	if frappe.db.exists("Notification Type", "OneIntake Changed"):
		if frappe.db.exists("Notification Type", "Reading Changed"):
			frappe.delete_doc("Notification Type", "OneIntake Changed", force=True, ignore_permissions=True)
		else:
			frappe.rename_doc("Notification Type", "OneIntake Changed", "Reading Changed", force=True)
	frappe.clear_cache()
