"""OneCRM's tours (one/tours.py, docs/READY.md mechanism 10), one for each
area of its screens, found by the mark at `at`; each step points at a
`data-tour` mark, the window's own (window-*) or OneCRM's. Its Home has one
area: the figures, and the row of views under them."""

from frappe import _lt

HOME = [
	{
		"target": "interface-nav",
		"side": "right",
		"title": _lt("Leads, Opportunities and Quotations"),
		"text": _lt("Everyone who might buy, what they might buy, the quotes sent them and the orders that came of it."),
	},
	{
		"target": "onecrm-figures",
		"side": "bottom",
		"title": _lt("Sales at a Glance"),
		"text": _lt("New leads, the pipeline and what it is likely worth, what was won and how often; click one to open it."),
	},
	{
		"target": "onecrm-views",
		"side": "bottom",
		"title": _lt("The Views of Home"),
		"text": _lt("Overview says how sales are going, Today what needs you, Everything finds any list, and Reports and Setup sit beside them."),
	},
	{
		"target": "interface-tour",
		"side": "top",
		"title": _lt("Settings and Tours"),
		"text": _lt("Settings is the cog, and the tour runs again from the button beside it."),
	},
]

TOURS = [{"key": "home", "at": "onecrm-views", "steps": HOME}]
