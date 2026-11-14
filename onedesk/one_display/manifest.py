"""OneDisplay's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Region, Roles, _lt

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
	line=_lt("Slides, live widgets and queues on any screen with a browser."),
	pitch=_lt("{one_display} puts what the business wants people to see on any screen with a web browser, such as a TV in the lobby or a display behind a counter. Each screen plays a channel of slides, live widgets, music and spoken ads, on a schedule."),
	brings=(
		_lt("Every screen, and whether it is online"),
		_lt("Channels on a schedule"),
		_lt("Queues with tickets and counters"),
		_lt("Boards changed from a phone"),
	),
	media=("screens.webp", "channel.webp", "boards.webp"),
	mark="onedisplay",
	rail=130,
	sidebar="OneDisplay",
	roles=Roles(user=("OneDisplay User",), manager=("OneDisplay Manager",)),
	agent=_lt("screen keeper"),
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
