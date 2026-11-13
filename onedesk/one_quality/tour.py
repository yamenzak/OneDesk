"""OneQuality's tour (one/tours.py, docs/READY.md mechanism 10): its screens
are frappe's own lists and forms, so its one tour is of the rail it keeps,
found by the window's own marks."""

from frappe import _lt

RAIL = [
	{
		"target": "interface-nav",
		"side": "right",
		"title": _lt("Procedures, Problems and Fixes"),
		"text": _lt("How work is done, the goals it is held to, what went wrong and what is done about it."),
	},
	{
		"target": "interface-tour",
		"side": "top",
		"title": _lt("Help and Tours"),
		"text": _lt("Help is the question mark and the tour is the button beside it, with Settings under the arrow at the end of the top bar."),
	},
]

TOURS = [{"key": "rail", "at": "interface-nav", "steps": RAIL}]
