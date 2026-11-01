"""OneCalendar's tours (one/tours.py, docs/READY.md mechanism 10), one for
each area of its screen, found by the mark at `at`; each step points at a
`data-tour` mark, the window's own (window-*) or OneCalendar's. OneCalendar
has one area, the calendar, with its calendars in the rail beside it."""

from frappe import _lt

CALENDAR = [
	{
		"target": "interface-nav",
		"side": "right",
		"title": _lt("Your Calendars"),
		"text": _lt("Tick a calendar to show it, and untick it to hide it."),
	},
	{
		"target": "onecalendar-moves",
		"side": "bottom",
		"title": _lt("Move Through Time"),
		"text": _lt("Go back or ahead with the arrows, come back with Today, or pick a date from the title."),
	},
	{
		"target": "onecalendar-views",
		"side": "bottom",
		"title": _lt("Month, Week or Day"),
		"text": _lt("Choose how much you see, and the calendar opens on that view next time."),
	},
	{
		"target": "onecalendar-grid",
		"side": "mid-center",
		"title": _lt("Your Events"),
		"text": _lt("Drag across the calendar to make an event at that time, click one to see who is on it, or drag it to another time."),
	},
	{
		"target": "interface-tour",
		"side": "top",
		"title": _lt("Settings and Tours"),
		"text": _lt("Your calendar link is in the settings from the cog, and the tour runs again from the button beside it."),
	},
]

TOURS = [{"key": "calendar", "at": "onecalendar-grid", "steps": CALENDAR}]
