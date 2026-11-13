"""OneCalendar's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Settle, _lt

APP = App(
	id="one_calendar",
	name="OneCalendar",
	kind="app",
	module="One Calendar",
	line=_lt("Meetings, leave and deadlines from every app, on one calendar."),
	mark="onecalendar",
	rail=120,
	sidebar="OneCalendar",
	screens="calendar",
	names=("one_calendar", "onecalendar"),
	help=(
		("overview", "info"),
		("calendars", "layers"),
		("events", "calendar-plus"),
		("deadlines", "alarm-clock"),
		("record-calendars", "folder-open"),
		("calendar-link", "link"),
		("notifications", "bell"),
		("asking-oneai", "sparkles"),
		("who-can-do-what", "shield"),
		("settings", "settings"),
	),
	ready={
		"ready": True,
	},
	hooks={
		"one_calendar_layers": ("events.LAYERS",),
	},
	settle=(
		Settle("feed.settle"),
		Settle("tell.install"),
	),
	makes=(
		"Contact",
	),
)
