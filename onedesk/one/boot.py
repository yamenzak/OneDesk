"""What the apps screen shows.

Frappe pins its own Framework tile last on every site. It is the desk's own
administration — Users, Build, Data, the System settings — and the people who
need it all hold System Manager, so anyone else gets a tile they cannot use.

The tile comes from frappe's own `add_to_apps_screen` hook, which we cannot
edit, so it is taken off the screen here instead. `extend_bootinfo` runs after
`app_data` is built, which is the only seam that sees it.
"""

import frappe

ADMIN_APPS = ("frappe",)


def boot_session(bootinfo) -> None:
	# A report or dashboard is called what the rail called it; see one/titles.py.
	from onedesk.one import titles

	bootinfo["one_titles"] = titles.for_boot()

	# The doctypes that hold a record OneAI made and nobody checked, so a list
	# of anything else never asks. See one_intake/mark.py.
	from onedesk.one_intake import mark

	bootinfo["one_intake_marked"] = sorted(mark.marked_doctypes())

	# The linked sections each form draws, for this person. See one/linked.py.
	from onedesk.one import linked

	bootinfo["one_linked"] = linked.for_boot(bootinfo)

	# The tabs after a record's fields, as each module declares them. See
	# one/tabs.py.
	from onedesk.one import tabs

	bootinfo["one_record_tabs"] = tabs.for_boot()

	# What each provisioning step is doing, in words. The list view needs it and
	# so does the form; putting a copy in JavaScript would be a second list to
	# be wrong the day somebody adds a step. Only on the admin site, where the
	# screens that read it exist.
	from onedesk.one_admin import site as admin

	if admin.is_admin():
		from onedesk.one_admin import steps

		bootinfo["one_steps"] = {name: frappe._(said) for name, said in steps.SAID.items()}

	if "System Manager" in frappe.get_roles():
		return

	for app in bootinfo.get("app_data") or []:
		if app.get("app_name") in ADMIN_APPS:
			app["on_apps_screen"] = False
