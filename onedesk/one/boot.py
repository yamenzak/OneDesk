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
	if "System Manager" in frappe.get_roles():
		return

	for app in bootinfo.get("app_data") or []:
		if app.get("app_name") in ADMIN_APPS:
			app["on_apps_screen"] = False
