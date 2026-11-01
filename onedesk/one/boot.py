"""What the apps screen shows, and what else the boot carries for One.

Frappe's own Framework tile is taken off it, for everyone, a System Manager
included: the desk is One's (one/outside.py).
"""

import frappe

ADMIN_APPS = ("frappe",)


def boot_session(bootinfo) -> None:
	from onedesk.one import stamp

	bootinfo["one_assets"] = stamp.versions()

	from frappe.model.utils.user_settings import get_user_settings

	bootinfo["one_window"] = frappe.parse_json(get_user_settings("One Window")) or {}
	from onedesk.one import ready

	bootinfo["one_interface"] = ready.interface()
	from onedesk.one import company

	bootinfo["one_frame_colour"] = company.frame_colour()
	bootinfo["one_frame_ink"] = company.frame_ink(bootinfo["one_frame_colour"])
	bootinfo["one_workspace_name"] = frappe.db.get_single_value("Workspace Account", "workspace_name")
	from onedesk.one import weather

	bootinfo["one_weather"] = weather.shown()

	from onedesk.one import outside

	outside.keep(bootinfo)

	from onedesk.one import roles
	from onedesk.one_mail import holders

	bootinfo["one_mail_may"] = {
		"connect_shared": int(holders.may_do("connect_shared")),
		"holders": int(holders.may_do("holders")),
		"policy": int(holders.may_do("policy")),
		"templates": int(holders.may_do("templates")),
		"others": int(holders.may_open_others()),
		"roles": int(roles.administers()),
	}
	sends = holders.sending_rows()
	for one in bootinfo.get("email_accounts") or []:
		if one.get("email_account") in sends and not sends[one["email_account"]]:
			one["enable_outgoing"] = 0
	bootinfo["one_mail_domains"] = frappe.get_all("Email Domain", pluck="domain_name")
	from onedesk.one import versions
	from onedesk.one_mail import addresses

	bootinfo["one_versions"] = versions.for_boot()
	from onedesk.one import setup_steps

	bootinfo["one_setup"] = setup_steps.for_boot()
	bootinfo["one_setup_wizard"] = setup_steps.for_wizard()
	from onedesk.one import tours

	bootinfo["one_tours_unseen"] = tours.unseen()
	bootinfo["one_administers"] = int(roles.administers())
	from onedesk.one import access_center, apps, notification_center
	from onedesk.one_ai import actions as ai_actions
	from onedesk.one_ai import center as ai_center

	# The modules AccessCenter, NotificationCenter and AICenter have a part
	# for, for ControlCenter to offer them (docs/READY.md, mechanisms 14-16).
	bootinfo["one_centers"] = {
		"access": access_center.modules() if roles.administers() else [],
		"shared": access_center.shared() if roles.administers() else [],
		"notifications": notification_center.for_boot(),
		"ai": ai_center.modules() if roles.administers() and apps.ai_on() else [],
	}
	bootinfo["one_ai_may"] = ai_center.may() if apps.ai_on() else {}
	bootinfo["one_ai_actions"] = ai_actions.for_boot() if apps.ai_on() else {}
	bootinfo["one_mail_private"] = {"on": int(addresses.external()), "domains": addresses.allowed_domains()}
	default = holders.sends_from()
	bootinfo["one_mail_sends_from"] = (
		frappe.db.get_value("Email Account", default, "email_id") if default and sends.get(default) else None
	)

	from onedesk.one import titles

	bootinfo["one_titles"] = titles.for_boot()

	from onedesk.one_studio import reports

	reports.reported(bootinfo.get("module_sidebars"))

	from onedesk.one import reach

	reach.unopened(bootinfo.get("module_sidebars"))

	from onedesk.one_inventory import measure

	bootinfo["one_measure"] = measure.for_boot()

	from onedesk.one_studio import customize

	bootinfo["one_refused_modules"] = list(customize.REFUSED_MODULES)

	from onedesk.one_calendar import events, feed

	bootinfo["one_calendar_links"] = feed.allowed()
	bootinfo["one_calendar_publish"] = events.may_publish()

	from onedesk.one import homes

	bootinfo["one_homes"] = homes.for_boot()

	from onedesk.one_hr import passkey

	bootinfo["one_passkey_ask"] = passkey.ask()

	from onedesk.one import linked

	bootinfo["one_linked"] = linked.for_boot(bootinfo)

	from onedesk.one import tabs

	bootinfo["one_record_tabs"] = tabs.for_boot()

	from onedesk.one import lists

	bootinfo["one_lists"] = lists.listed()

	from onedesk.one import head

	bootinfo["one_heads_live"] = head.live()

	if not frappe.is_setup_complete():
		from onedesk.one import setup_wizard

		bootinfo["one_weekends"] = setup_wizard.weekends()

	from onedesk.one_admin import site as admin

	if admin.is_admin():
		from onedesk.one_admin import steps

		bootinfo["one_steps"] = {name: str(said) for name, said in steps.SAID.items()}

	for app in bootinfo.get("app_data") or []:
		if app.get("app_name") in ADMIN_APPS:
			app["on_apps_screen"] = False
