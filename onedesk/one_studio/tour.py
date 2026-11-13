"""OneStudio's tour (one/tours.py, docs/READY.md mechanism 10): its screens
are frappe's own lists and forms and its ControlCenter, so its one tour is
of the rail it keeps, found by the window's own marks."""

from frappe import _lt

RAIL = [
	{
		"target": "interface-nav",
		"side": "right",
		"title": _lt("Adapt One to Your Work"),
		"text": _lt("Extensions, custom fields and custom collections are at the top, with numbering, printing, approvals and automations under them."),
	},
	{
		"target": "interface-tour",
		"side": "top",
		"title": _lt("Settings and Tours"),
		"text": _lt("Settings is the cog, and the tour runs again from the button beside it."),
	},
]

TOURS = [{"key": "rail", "at": "interface-nav", "steps": RAIL}]
