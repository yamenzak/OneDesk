"""Projects that said Hourly can be saved again.

OneProject took Hourly off how often a project asks for updates
(updates.py), but every project made before still said Hourly, ERPNext's
first choice, whether it asked or not, and frappe refuses a choice that is
no longer offered: none of them could be saved. They now say Weekly, the
new default."""

import frappe


def execute():
	frappe.db.set_value("Project", {"frequency": "Hourly"}, "frequency", "Weekly", update_modified=False)
