"""OneDeck's module was One Slide and its folder one_slide (P2.2): the
Module Def and the two roles take the new names through frappe's own rename,
merged into what a migrate made first, and what holds an old name as plain
text follows. Run before the doctypes are synced; safe to run twice.
one_deck/AGENTS.md, Under the hood, says what it covers."""

import frappe
from frappe.cache_manager import clear_defaults_cache
from frappe.model.rename_doc import rename_doc

OLD = "One Slide"
NEW = "One Deck"
APP = ("OneSlide", "OneDeck")
ROLES = {"OneSlide User": "OneDeck User", "OneSlide Manager": "OneDeck Manager"}
FOLDER = ("one_slide", "one_deck")
PATHS = ("onedesk.one_slide.", "onedesk.one_deck.")
MARKS = {"oneslide": "onedeck", "oneslide-flat": "onedeck-flat"}
TEXT = (("Workspace Sidebar", "module"), ("Block Module", "module"))
KEYS = (("one_slide", "one_deck"), ("oneslide", "onedeck"))


def execute():
	_renamed("Module Def", OLD, NEW)
	if frappe.db.exists("Module Def", NEW):
		frappe.db.set_value("Module Def", NEW, "module_name", NEW, update_modified=False)
	for old, new in ROLES.items():
		_renamed("Role", old, new)
		if frappe.db.exists("Role", new):
			frappe.db.set_value("Role", new, "role_name", new, update_modified=False)
	for doctype, field in TEXT:
		if frappe.db.has_column(doctype, field):
			frappe.db.set_value(doctype, {field: OLD}, field, NEW, update_modified=False)
	if frappe.db.has_column("Record Head", "module"):
		frappe.db.set_value("Record Head", {"module": FOLDER[0]}, "module", FOLDER[1], update_modified=False)
	for doctype in ("Role", "Notification Type"):
		if frappe.db.has_column(doctype, "one_app"):
			frappe.db.set_value(doctype, {"one_app": APP[0]}, "one_app", APP[1], update_modified=False)
	for doctype, field in (("Patch Log", "patch"), ("Scheduled Job Type", "method")):
		_moved(doctype, field)
	_defaults()
	_marks()
	frappe.clear_cache()


def _renamed(doctype: str, old: str, new: str) -> None:
	if not frappe.db.exists(doctype, old):
		return
	rename_doc(
		doctype,
		old,
		new,
		force=True,
		merge=bool(frappe.db.exists(doctype, new)),
		ignore_permissions=True,
		show_alert=False,
		rebuild_search=False,
		validate=False,
	)


def _moved(doctype: str, field: str) -> None:
	old, new = PATHS
	for name, value in frappe.get_all(doctype, filters={field: ["like", f"{old}%"]}, fields=["name", field], as_list=True):
		frappe.db.set_value(doctype, name, field, new + value[len(old) :], update_modified=False)


def _defaults() -> None:
	table = frappe.qb.DocType("DefaultValue")
	for old, new in KEYS:
		rows = frappe.qb.from_(table).select(table.name, table.parent, table.defkey).where(table.defkey.like(f"%{old}%")).run(as_dict=True)
		for row in rows:
			key = row.defkey.replace(old, new)
			if key == row.defkey:
				continue
			if frappe.db.exists("DefaultValue", {"parent": row.parent, "defkey": key}):
				frappe.db.delete("DefaultValue", {"name": row.name})
			else:
				frappe.db.set_value("DefaultValue", row.name, "defkey", key, update_modified=False)
	clear_defaults_cache()


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
