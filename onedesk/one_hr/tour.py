"""OneHR's tours (one/tours.py, docs/READY.md mechanism 10), one for each
area of its screens, found by the mark at `at`; each step points at a
`data-tour` mark, the window's own (window-*) or OneHR's. Its Home has one
area: the figures, and the row of views under them."""

from frappe import _lt

HOME = [
	{
		"target": "interface-nav",
		"side": "right",
		"title": _lt("People, Time and Pay"),
		"text": _lt("Employees, leave, attendance, payroll, expenses and hiring, each a row of its own."),
	},
	{
		"target": "onehr-figures",
		"side": "bottom",
		"title": _lt("The Figures That Matter"),
		"text": _lt("For HR, headcount, who is in and away today, the last payroll and open positions; for everybody, the leave they have left."),
	},
	{
		"target": "onehr-views",
		"side": "bottom",
		"title": _lt("The Views of Home"),
		"text": _lt("Today is what needs you, from checking in to requests waiting; HR also gets Overview, and Everything finds any list."),
	},
	{
		"target": "interface-tour",
		"side": "top",
		"title": _lt("Settings and Tours"),
		"text": _lt("Settings is the cog, and the tour runs again from the button beside it."),
	},
]

TOURS = [{"key": "home", "at": "onehr-views", "steps": HOME}]
