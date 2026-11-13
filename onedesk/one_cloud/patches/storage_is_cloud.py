"""OneCloud's module was One Storage and its folder one_storage (P2.1):
the Module Def takes the new name through frappe's own rename, merged into
the One Cloud a migrate makes from modules.txt first, and what holds either
name as plain text follows. Run before the doctypes are synced; safe to run
twice. one_cloud/AGENTS.md, Under the hood, says what it covers."""

import frappe
from frappe.model.rename_doc import rename_doc

OLD = "One Storage"
NEW = "One Cloud"
FOLDER = ("one_storage", "one_cloud")
PATHS = ("onedesk.one_storage.", "onedesk.one_cloud.")
MARKS = {"onestorage": "onecloud", "onestorage-flat": "onecloud-flat"}
TEXT = (("Workspace Sidebar", "module"), ("Block Module", "module"))


def execute():
	if frappe.db.exists("Module Def", OLD):
		merge = bool(frappe.db.exists("Module Def", NEW))
		rename_doc(
			"Module Def",
			OLD,
			NEW,
			force=True,
			merge=merge,
			ignore_permissions=True,
			show_alert=False,
			rebuild_search=False,
			validate=False,
		)
		frappe.db.set_value("Module Def", NEW, "module_name", NEW, update_modified=False)
	for doctype, field in TEXT:
		if frappe.db.has_column(doctype, field):
			frappe.db.set_value(doctype, {field: OLD}, field, NEW, update_modified=False)
	if frappe.db.has_column("Record Head", "module"):
		frappe.db.set_value("Record Head", {"module": FOLDER[0]}, "module", FOLDER[1], update_modified=False)
	for doctype, field in (("Patch Log", "patch"), ("Scheduled Job Type", "method")):
		_moved(doctype, field)
	_marks()
	frappe.clear_cache()


def _moved(doctype: str, field: str) -> None:
	old, new = PATHS
	for name, value in frappe.get_all(doctype, filters={field: ["like", f"{old}%"]}, fields=["name", field], as_list=True):
		frappe.db.set_value(doctype, name, field, new + value[len(old) :], update_modified=False)


def _marks() -> None:
	fields = frappe.get_all("DocField", filters={"fieldtype": "Icon"}, fields=["parent", "fieldname"])
	fields += frappe.get_all("Custom Field", filters={"fieldtype": "Icon"}, fields=["dt as parent", "fieldname"])
	for one in fields:
		if frappe.db.get_value("DocType", one.parent, "issingle") or not frappe.db.has_column(one.parent, one.fieldname):
			continue
		for old, new in MARKS.items():
			frappe.db.set_value(one.parent, {one.fieldname: old}, one.fieldname, new, update_modified=False)
	for old in MARKS:
		if frappe.db.exists("Custom Icon", old):
			frappe.delete_doc("Custom Icon", old, ignore_permissions=True, force=True)
