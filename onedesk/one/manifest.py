"""One's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Centre, Kept, Region, Settle, _lt

APP = App(
	id="one",
	name="One",
	kind="app",
	module="One",
	ui="mixed",
	regions=(
		Region("page", "one-hub", "every centre the reader may open as a tile, searchable, as a phone's Settings app: the centres are dialogs, so no list can hold them"),
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
		("setup", "list-checks"),
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
		"Fiscal Year",
		"Shift Type",
	),
)

PARTS = (
	App(id="one_hub", name="OneHub", kind="centre", module="", mark="one"),
	App(id="control_center", line=_lt("Each app's settings."), name="ControlCenter", kind="centre", module="", centre=Centre("settings", "settings")),
	App(id="notification_center", line=_lt("What reaches whom, and how."), name="NotificationCenter", kind="centre", module="", centre=Centre("notifications", "bell")),
	App(id="access_center", line=_lt("Who may open which app, and at what level."), name="AccessCenter", kind="centre", module="", centre=Centre("access", "key-round")),
	App(id="shortcut_center", line=_lt("The keys for what you do most."), name="ShortcutCenter", kind="centre", module="", centre=Centre("shortcuts", "keyboard")),
	App(id="help_center", line=_lt("Help for the apps that are on."), name="HelpCenter", kind="centre", module="", centre=Centre("help", "circle-question-mark")),
	App(id="update_center", line=_lt("What changed and what is coming."), name="UpdateCenter", kind="centre", module="", centre=Centre("updates", "sparkles")),
	App(id="setup_center", line=_lt("Each app's setup steps, done and waiting."), name="SetupCenter", kind="centre", module="", centre=Centre("setup", "list-checks")),
)
