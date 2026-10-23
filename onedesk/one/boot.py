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
	from onedesk.one import stamp

	bootinfo["one_assets"] = stamp.versions()

	from onedesk.one import outside

	outside.keep(bootinfo)

	from onedesk.one import titles

	bootinfo["one_titles"] = titles.for_boot()

	from onedesk.one import reports

	reports.reported(bootinfo.get("module_sidebars"))

	from onedesk.one import reach

	reach.unopened(bootinfo.get("module_sidebars"))

	from onedesk.one_inventory import measure

	bootinfo["one_measure"] = measure.for_boot()

	from onedesk.one import customize

	bootinfo["one_refused_modules"] = list(customize.REFUSED_MODULES)

	from onedesk.one_calendar import feed

	bootinfo["one_calendar_links"] = feed.allowed()

	from onedesk.one import homes

	bootinfo["one_homes"] = homes.for_boot()

	from onedesk.one_hr import passkey

	bootinfo["one_passkey_ask"] = passkey.ask()

	from onedesk.one_intake import mark

	bootinfo["one_intake_marked"] = sorted(mark.marked_doctypes())

	from onedesk.one import linked

	bootinfo["one_linked"] = linked.for_boot(bootinfo)

	from onedesk.one import tabs

	bootinfo["one_record_tabs"] = tabs.for_boot()

	from onedesk.one import head

	bootinfo["one_heads_live"] = head.live()

	if not frappe.is_setup_complete():
		from onedesk.one import setup_wizard

		bootinfo["one_weekends"] = setup_wizard.weekends()

	from onedesk.one_admin import site as admin

	if admin.is_admin():
		from onedesk.one_admin import steps

		bootinfo["one_steps"] = {name: str(said) for name, said in steps.SAID.items()}

	if platform():
		return

	for app in bootinfo.get("app_data") or []:
		if app.get("app_name") in ADMIN_APPS:
			app["on_apps_screen"] = False
