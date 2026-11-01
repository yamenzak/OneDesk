"""OneInterface's tour (one/tours.py, docs/READY.md mechanism 10): one, of the
window itself, the first time anybody opens a screen of One; after it, each
module's own tour of its screen. The window draws every mark it points at."""

from frappe import _lt

WINDOW = [
	{
		"target": "interface-search",
		"side": "bottom",
		"title": _lt("Find What You Need"),
		"text": _lt("Type here to search what is on this screen, or press Ctrl+K to search everything."),
	},
	{
		"target": "interface-nav",
		"side": "right",
		"title": _lt("The App's Places"),
		"text": _lt("Every place of the app you are in, and its settings at the foot."),
	},
	{
		"target": "interface-foot",
		"side": "top",
		"title": _lt("Settings, Tour and Help"),
		"text": _lt("The app's settings, this tour again, its help and what is new in it."),
	},
]

TOURS = [{"key": "window", "at": "interface-search", "steps": WINDOW}]
