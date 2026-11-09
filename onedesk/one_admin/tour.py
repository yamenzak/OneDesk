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
		"title": _lt("Settings and Tours"),
		"text": _lt("The cog holds what OneAdmin runs on, and the tour runs again from the button beside it."),
	},
]

TOURS = [{"key": "console", "at": "interface-nav", "steps": CONSOLE}]
