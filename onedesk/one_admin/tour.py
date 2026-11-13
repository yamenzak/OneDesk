"""OneAdmin's tour (one/tours.py, docs/READY.md mechanism 10): the window's
own marks, since Home draws none of its own yet."""

from frappe import _lt

CONSOLE = [
	{
		"target": "interface-nav",
		"side": "right",
		"title": _lt("Your Console"),
		"text": _lt("Workspaces, servers, jobs, billing and OneAI each have their place on the rail."),
	},
	{
		"target": "interface-tour",
		"side": "top",
		"title": _lt("Help and Tours"),
		"text": _lt("Help is the question mark and the tour is the button beside it, with Settings under the arrow at the end of the top bar."),
	},
]

TOURS = [{"key": "console", "at": "interface-nav", "steps": CONSOLE}]
