"""OneProject's tours (one/tours.py, docs/READY.md mechanism 10), one for each
area of its screens, found by the mark at `at`; each step points at a
`data-tour` mark, the window's own (window-*) or OneProject's. A project's
page has one area: its head and the row of views under it, with OneProject's
rail beside it."""

from frappe import _lt

PROJECT = [
	{
		"target": "interface-nav",
		"side": "right",
		"title": _lt("Projects and Time"),
		"text": _lt("Every project you can see, the hours people have logged, and who has room this week."),
	},
	{
		"target": "oneproject-head",
		"side": "bottom",
		"title": _lt("The Project at a Glance"),
		"text": _lt("Its name, status and health, with the facts its kind needs; click the name or the status to change it."),
	},
	{
		"target": "oneproject-views",
		"side": "bottom",
		"title": _lt("One Row of Views"),
		"text": _lt("Overview, tasks, time, money, invoices, the team and files, each one click away."),
	},
	{
		"target": "interface-tour",
		"side": "top",
		"title": _lt("Settings and Tours"),
		"text": _lt("Settings is the cog, and the tour runs again from the button beside it."),
	},
]

TOURS = [{"key": "project", "at": "oneproject-views", "steps": PROJECT}]
