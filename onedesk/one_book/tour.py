"""OneBook's tours (one/tours.py, docs/READY.md mechanism 10), one for each
area of its screens, found by the mark at `at`; each step points at a
`data-tour` mark, the window's own (window-*) or OneBook's. Its Home has one
area: the figures, and the row of views under them."""

from frappe import _lt

HOME = [
	{
		"target": "interface-nav",
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
		"target": "interface-tour",
		"side": "top",
		"title": _lt("Help and Tours"),
		"text": _lt("Help is the question mark and the tour is the button beside it, with Settings under the arrow at the end of the top bar."),
	},
]

INVOICE = [
	{
		"target": "record-track",
		"side": "bottom",
		"title": _lt("Where It Stands"),
		"text": _lt("Billed and paid as the payments made against it say, red once a part is late."),
	},
	{
		"target": "record-cards",
		"side": "bottom",
		"title": _lt("What Is Owed"),
		"text": _lt("What is still owed and when the next part falls due, its total, and what the party was billed this year."),
	},
	{
		"target": "record-panel",
		"side": "left",
		"title": _lt("Mail and Notes"),
		"text": _lt("Activity holds the mail sent with it, the comments and every change."),
	},
]

PAYMENT = [
	{
		"target": "record-track",
		"side": "bottom",
		"title": _lt("Paid and Reconciled"),
		"text": _lt("Paid once submitted, and reconciled once the bank statement line is matched to it."),
	},
	{
		"target": "record-cards",
		"side": "bottom",
		"title": _lt("The Payment"),
		"text": _lt("How much, by what means, the bank's reference and the project it is for."),
	},
]

TOURS = [
	{"key": "home", "at": "onebook-views", "steps": HOME},
	{"key": "sales_invoice", "at": "record-sales-invoice", "steps": INVOICE},
	{"key": "purchase_invoice", "at": "record-purchase-invoice", "steps": INVOICE},
	{"key": "payment", "at": "record-payment-entry", "steps": PAYMENT},
]
