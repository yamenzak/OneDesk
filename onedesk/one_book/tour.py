"""OneBook's tours (one/tours.py, docs/READY.md mechanism 10), one for each
area of its screens, found by the mark at `at`; each step points at a
`data-tour` mark, the window's own (window-*) or OneBook's. Its Home has one
area: the figures, and the row of views under them."""

from frappe import _lt

HOME = [
	{
		"target": "window-nav",
		"side": "right",
		"title": _lt("Invoices, Payments and the Bank"),
		"text": _lt("What you billed and were billed, the money either way, the bank and the reports."),
	},
	{
		"target": "onebook-figures",
		"side": "bottom",
		"title": _lt("The Money at a Glance"),
		"text": _lt("Cash, what customers owe and you owe, and how profit is going; click one to open it."),
	},
	{
		"target": "onebook-views",
		"side": "bottom",
		"title": _lt("The Views of Home"),
		"text": _lt("Overview says how the money is doing, Today what needs you, Everything finds any list, and Reports and Setup sit beside them."),
	},
	{
		"target": "window-tour",
		"side": "top",
		"title": _lt("Settings and Tours"),
		"text": _lt("Settings is the cog, and the tour runs again from the button beside it."),
	},
]

TOURS = [{"key": "home", "at": "onebook-views", "steps": HOME}]
