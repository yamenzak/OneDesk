"""AccountCenter's module was One Account, its folder one_account and its app
OneAccount (P2.6): the Module Def takes the new name through frappe's own
rename, merged into the Account Center a migrate makes from modules.txt;
what holds the module or the folder as plain text follows, and the roles,
`one_app` and the defaults keyed by either old name move through
one/renaming.py. The agreements keep every word and version. Run before the
doctypes are synced; safe to run twice."""

import frappe
from frappe.model.rename_doc import rename_doc

from onedesk.one.renaming import app_renamed

OLD = "One Account"
NEW = "Account Center"
FOLDER = ("one_account", "account_center")
PATHS = ("onedesk.one_account.", "onedesk.account_center.")
TEXT = (("Workspace Sidebar", "module"), ("Block Module", "module"))
ROLES = {"OneAccount User": "AccountCenter User", "OneAccount Manager": "AccountCenter Manager"}


def execute():
	if frappe.db.exists("Module Def", OLD):
		rename_doc(
			"Module Def",
			OLD,
			NEW,
			force=True,
			merge=bool(frappe.db.exists("Module Def", NEW)),
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
	app_renamed("OneAccount", "AccountCenter", ROLES, keys=(FOLDER,))


def _moved(doctype: str, field: str) -> None:
	old, new = PATHS
	for name, value in frappe.get_all(doctype, filters={field: ["like", f"{old}%"]}, fields=["name", field], as_list=True):
		frappe.db.set_value(doctype, name, field, new + value[len(old) :], update_modified=False)
