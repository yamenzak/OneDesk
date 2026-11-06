"""OneInventory's tours (one/tours.py, docs/READY.md mechanism 10), one for each
area of its screens, found by the mark at `at`; each step points at a
`data-tour` mark, the window's own (window-*) or OneInventory's. Its Home has one
area: the figures, and the row of views under them."""

from frappe import _lt

HOME = [
	{
		"target": "interface-nav",
		"side": "right",
		"title": _lt("Stock, Buying and Equipment"),
		"text": _lt("Items, warehouses, what is ordered and received, and the company's equipment."),
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
		"target": "interface-tour",
		"side": "top",
		"title": _lt("Settings and Tours"),
		"text": _lt("Settings is the cog, and the tour runs again from the button beside it."),
	},
]

STOCK = [
	{
		"target": "oneinventory-stock-figures",
		"side": "bottom",
		"title": _lt("Stock at a Glance"),
		"text": _lt("What the stores are worth, and how many items are low or short; Low and Short narrow the list."),
	},
	{
		"target": "oneinventory-stock-find",
		"side": "bottom",
		"title": _lt("Find an Item"),
		"text": _lt("Pick a warehouse, search by name or code, or show only what is low, short or out of stock."),
	},
	{
		"target": "oneinventory-stock-list",
		"side": "top",
		"title": _lt("Each Item"),
		"text": _lt("What is on hand, promised, free and on order, and what it is worth; a line opens the item."),
	},
]

ORDER = [
	{
		"target": "oneinventory-order-figures",
		"side": "bottom",
		"title": _lt("What to Order"),
		"text": _lt("How many lines are requested or running low, and what they would cost at the last prices paid."),
	},
	{
		"target": "oneinventory-order-list",
		"side": "top",
		"title": _lt("Order in One Go"),
		"text": _lt("Tick lines and press Order, or Order All: one draft purchase order is made for each supplier."),
	},
]

TOURS = [
	{"key": "home", "at": "oneinventory-views", "steps": HOME},
	{"key": "stock", "at": "oneinventory-stock-list", "steps": STOCK},
	{"key": "order", "at": "oneinventory-order-list", "steps": ORDER},
]
