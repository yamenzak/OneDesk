"""OneInventory's tours (one/tours.py, docs/READY.md mechanism 10), one for each
area of its screens, found by the mark at `at`; each step points at a
`data-tour` mark, the window's own (window-*) or OneInventory's. Its Home has one
area: the figures, and the row of views under them."""

from frappe import _lt

HOME = [
	{
		"target": "window-nav",
		"side": "right",
		"title": _lt("Stock, Buying and Making"),
		"text": _lt("Items, warehouses, what is ordered and received, the workshop and the company's equipment."),
	},
	{
		"target": "oneinventory-figures",
		"side": "bottom",
		"title": _lt("Stock at a Glance"),
		"text": _lt("What stock is worth, what came in and went out this month, and what is still on order; click one to open it."),
	},
	{
		"target": "oneinventory-views",
		"side": "bottom",
		"title": _lt("The Views of Home"),
		"text": _lt("Overview says how stock is doing, Today what needs you, Everything finds any list, and Reports and Setup sit beside them."),
	},
	{
		"target": "window-tour",
		"side": "top",
		"title": _lt("Settings and Tours"),
		"text": _lt("Settings is the cog, and the tour runs again from the button beside it."),
	},
]

TOURS = [{"key": "home", "at": "oneinventory-views", "steps": HOME}]
