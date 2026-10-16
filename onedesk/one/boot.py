"""What the apps screen shows.

Frappe's own Framework tile is taken off it, for everyone it is of no use to.
"""

import frappe

ADMIN_APPS = ("frappe",)


def platform() -> bool:
	"""Whether the reader is the platform's own (System Manager), who keeps
	frappe's whole desk. Nobody on a workspace is."""
	return "System Manager" in frappe.get_roles()


def boot_session(bootinfo) -> None:
	# One's sidebars and workspaces, not frappe's, erpnext's or hrms's; see
	# one/outside.py.
	from onedesk.one import outside

	outside.keep(bootinfo)

	# A report or dashboard is called what the rail called it; see one/titles.py.
	from onedesk.one import titles

	bootinfo["one_titles"] = titles.for_boot()

	# A saved report in a sidebar is drawn; see one/reports.py.
	from onedesk.one import reports

	reports.reported(bootinfo.get("module_sidebars"))

	from onedesk.one import reach

	reach.unopened(bootinfo.get("module_sidebars"))

	# Which records' lines carry a size; see one_inventory/measure.py.
	from onedesk.one_inventory import measure

	bootinfo["one_measure"] = measure.for_boot()

	# The modules no workspace changes, for the Customize and Settings menu items.
	from onedesk.one import customize

	bootinfo["one_refused_modules"] = list(customize.REFUSED_MODULES)

	from onedesk.one_calendar import feed

	bootinfo["one_calendar_links"] = feed.allowed()

	# Where a record whose home is a page leads back to; see one/homes.py.
	from onedesk.one import homes

	bootinfo["one_homes"] = homes.for_boot()

	# Whether to offer a passkey after signing in. See one_hr/passkey.py, `ask`.
	from onedesk.one_hr import passkey

	bootinfo["one_passkey_ask"] = passkey.ask()

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

	# The heads that redraw as the form changes, and on which fields. See
	# one/head.py, `preview`.
	from onedesk.one import head

	bootinfo["one_heads_live"] = head.live()

	# What each provisioning step is doing, in words, for the list and the form alike,
	# and only on the admin site, where those screens exist.
	from onedesk.one_admin import site as admin

	if admin.is_admin():
		from onedesk.one_admin import steps

		bootinfo["one_steps"] = {name: str(said) for name, said in steps.SAID.items()}

	if platform():
		return

	for app in bootinfo.get("app_data") or []:
		if app.get("app_name") in ADMIN_APPS:
			app["on_apps_screen"] = False
