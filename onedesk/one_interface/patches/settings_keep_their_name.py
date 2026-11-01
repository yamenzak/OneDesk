"""Each person's panes, widths and folded groups were saved under the user
settings key "One Window"; the window is OneInterface now and reads them
from "One Interface", so they move rather than being lost."""

import frappe


def execute():
	if not frappe.db.table_exists("__UserSettings"):
		return
	frappe.db.sql("""update `__UserSettings` set doctype = 'One Interface' where doctype = 'One Window'""")
