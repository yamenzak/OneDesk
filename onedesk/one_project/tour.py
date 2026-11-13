"""OneProject's tours (one/tours.py, docs/READY.md mechanism 10), one for each
area of its screens, found by the mark at `at`; each step points at a
`data-tour` mark, the window's own (window-*) or OneProject's. A project's
form has one area of OneProject's own: what its kind needs, under ERPNext's
overview, with OneProject's rail beside it."""

from frappe import _lt

PROJECT = [
	{
		"target": "interface-nav",
		"side": "right",
		"title": _lt("Projects and Time"),
		"text": _lt("Every project you can see, the hours people have logged, and who has room this week."),
	},
	{
		"target": "record-cards",
		"side": "bottom",
		"title": _lt("How the Job Stands"),
		"text": _lt("How much of the work is done, what it cost and billed against the plan, and the margin so far."),
	},
	{
		"target": "oneproject-overview",
		"side": "top",
		"title": _lt("What Its Kind Needs"),
		"text": _lt("Billing, orders, the budget, milestones and contracts, as a project of its kind is run."),
	},
	{
		"target": "interface-tour",
		"side": "top",
		"title": _lt("Help and Tours"),
		"text": _lt("Help is the question mark and the tour is the button beside it, with Settings under the arrow at the end of the top bar."),
	},
]

TOURS = [{"key": "project", "at": "oneproject-overview", "steps": PROJECT}]
