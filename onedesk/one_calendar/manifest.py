"""OneCalendar's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, _lt

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
		"checked": {
			"copy": {"on": "2026-11-07", "commit": "5536d07d51f8", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-07", "commit": "5536d07d51f8", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-07", "commit": "5536d07d51f8", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-07", "commit": "5536d07d51f8", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-07", "commit": "5536d07d51f8", "by": "Claude, for Yamen"},
		},
	},
)
