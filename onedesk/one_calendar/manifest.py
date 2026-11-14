"""OneCalendar's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Region, Settle, _lt

APP = App(
	id="one_calendar",
	name="OneCalendar",
	kind="app",
	module="One Calendar",
	ui="bespoke",
	regions=(
		Region("page", "onecalendar", "everybody's calendar (Event, and the dated records shown on it)"),
	),
	line=_lt("Meetings, leave and deadlines from every app, on one calendar."),
	pitch=_lt("{one_calendar} shows everything dated in {one} on one calendar: meetings, tasks, deals' next steps, leave, interviews and holidays. Each kind is a calendar of its own, shown or hidden."),
	brings=(
		_lt("Meetings and events"),
		_lt("Deadlines from every app"),
		_lt("Holidays and who is off"),
		_lt("A link for other calendar apps"),
	),
	media=("month.webp", "month-and-week.gif", "event.webp"),
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
