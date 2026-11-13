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
		"text": _lt("New leads, the pipeline and what it is likely worth, and what was won and how often, each opening its report."),
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
		"title": _lt("Help and Tours"),
		"text": _lt("Help is the question mark and the tour is the button beside it, with Settings under the arrow at the end of the top bar."),
	},
]

OPPORTUNITY = [
	{
		"target": "record-track",
		"side": "bottom",
		"title": _lt("Where the Sale Stands"),
		"text": _lt("Quoted, ordered, billed and paid as its papers say, and won once its quotation becomes an order."),
	},
	{
		"target": "record-cards",
		"side": "bottom",
		"title": _lt("What It Is Worth"),
		"text": _lt("Its amount and probability, how long it has been in its stage, its next step and when it should close."),
	},
	{
		"target": "record-panel",
		"side": "left",
		"title": _lt("Calls, Mail and Notes"),
		"text": _lt("Log a Call writes a call down, and Activity holds everything said about it with the mail and comments."),
	},
]

LEAD = [
	{
		"target": "record-cards",
		"side": "bottom",
		"title": _lt("Where It Stands"),
		"text": _lt("Its next step, how soon it was answered, the last call or mail, and the opportunities made from it."),
	},
	{
		"target": "record-panel",
		"side": "left",
		"title": _lt("Calls, Mail and Notes"),
		"text": _lt("Log a Call writes a call down, and Activity holds everything said about it with the mail and comments."),
	},
]

TOURS = [
	{"key": "home", "at": "onecrm-views", "steps": HOME},
	{"key": "opportunity", "at": "record-opportunity", "steps": OPPORTUNITY},
	{"key": "lead", "at": "record-lead", "steps": LEAD},
]
