"""One's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Kept, Region, Settle, _lt

APP = App(
	id="one",
	name="One",
	kind="app",
	module="One",
	ui="mixed",
	regions=(
		Region("page", "one", "One's Home: what waits for the reader in each app they have, the first few of each, and what in the workspace needs an administrator (Task, Event, Leave Application)"),
	),
	kept=Kept(_lt("Every app stands on One's Home, centres and window.")),
	mark="one",
	rail=10,
	sidebar="One",
	screens="one",
	help=(
		("overview", "info"),
		("home", "house"),
		("address-book", "book-user"),
		("announcements", "megaphone"),
		("records", "file-text"),
		("recycle-bin", "trash-2"),
		("weather", "cloud-sun"),
		("news", "newspaper"),
		("notifications", "bell"),
		("shortcuts", "keyboard"),
		("access-and-the-audit-log", "shield-check"),
		("your-data", "folder-lock"),
		("who-can-do-what", "shield"),
		("settings", "settings"),
	),
	ready={
		"ready": True,
	},
	hooks={
		"one_homes": ("lists.homes",),
		"one_record_tabs": ("tabs.TABS",),
	},
	settle=(
		Settle("roles.ensure"),
		Settle("notify.install"),
		Settle("access.settle"),
		Settle("rights.settle"),
		Settle("rights.everyone"),
		Settle("recycle.settle"),
		Settle("head.install"),
		Settle("brand.quiet_errors"),
		Settle("company.hide"),
		Settle("brand.apply", install_only=True, last=True),
		Settle("declutter.apply", install_only=True, last=True),
		Settle("companions.apply", last=True),
	),
	makes=(
		"Address",
		"Company",
		"Shift Type",
	),
)

PARTS = (
	App(id="control_center", name="ControlCenter", kind="centre", module=""),
	App(id="notification_center", name="NotificationCenter", kind="centre", module=""),
	App(id="access_center", name="AccessCenter", kind="centre", module=""),
	App(id="shortcut_center", name="ShortcutCenter", kind="centre", module=""),
	App(id="help_center", name="HelpCenter", kind="centre", module=""),
	App(id="update_center", name="UpdateCenter", kind="centre", module=""),
)
