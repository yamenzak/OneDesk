"""Taking the other apps' furniture off One's shell.

Every installed app writes into the same navbar and the same onboarding list, so
a One site arrives carrying rows nobody here authored. All of it is site data,
which is why this is a list of names rather than a patch, and why a tenant can
put any of it back.

`sync_standard_items` matches a navbar row by its label and only appends the
missing ones, so hiding a row survives every migrate. Marking an onboarding
complete is what its own "Skip All" writes, and `import_file` never overwrites
that field.
"""

import frappe

#: Navbar rows that send a One tenant somewhere that is not One: Frappe's own
#: support desk, a dialog naming the framework and its version, and an erpnext
#: action for demo data a paying site never had.
HIDE_ROWS = ("Frappe Support", "About", "Delete Demo Data")

#: erpnext's per-module checklists. They are written in erpnext's voice, about
#: erpnext's modules, and they open over whatever One put on the page.
HIDE_ONBOARDING = ("erpnext", "hrms")


def apply() -> None:
	navbar = frappe.get_single("Navbar Settings")
	for key in ("settings_dropdown", "help_dropdown"):
		for row in navbar.get(key):
			if row.item_label in HIDE_ROWS:
				row.hidden = 1
	navbar.save(ignore_permissions=True)

	ours = set(frappe.get_all("Module Def", filters={"app_name": "onedesk"}, pluck="name"))
	for name, module in frappe.get_all("Module Onboarding", fields=["name", "module"], as_list=True):
		if module in ours:
			continue
		if frappe.db.get_value("Module Def", module, "app_name") in HIDE_ONBOARDING:
			frappe.db.set_value("Module Onboarding", name, "is_complete", 1)
