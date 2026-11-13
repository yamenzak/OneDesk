"""OneDisplay's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Region

APP = App(
	id="one_display",
	name="OneDisplay",
	kind="app",
	module="One Display",
	ui="bespoke",
	regions=(
		Region("page", "boards", "a board's items, each set to a state or a value from a phone (Display Board)"),
		Region("page", "counter", "a queue counter: the ticket it serves, call the next, and who waits (Queue Ticket)"),
	),
	mark="onedisplay",
	rail=130,
	sidebar="OneDisplay",
	screens="display",
	names=("one_display", "onedisplay"),
	help=(
		("overview", "info"),
		("screens-and-pairing", "tv"),
		("templates", "layout-template"),
		("channels", "radio"),
		("slides", "images"),
		("widgets-and-sources", "layout-dashboard"),
		("sound", "speaker"),
		("queues", "list-ordered"),
		("boards", "layout-grid"),
		("alerts", "siren"),
		("notifications", "bell"),
		("asking-oneai", "sparkles"),
		("who-can-do-what", "shield"),
		("settings", "settings"),
	),
	ready={
		"ready": True,
	},
	hooks={
		"one_deck_loaded": ("screen.loaded",),
		"one_deck_saving": ("screen.saving",),
		"one_deck_rows": ("screen.rows",),
	},
)
