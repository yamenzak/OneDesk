"""OneFactory's tours (one/tours.py, docs/READY.md mechanism 10), one for
each area of its screens, found by the mark at `at`. The Shop Floor has one
area: its figures, and the tabs under them for each workstation."""

from frappe import _lt

FLOOR = [
	{
		"target": "interface-nav",
		"side": "right",
		"title": _lt("Making and Subcontracting"),
		"text": _lt("Work orders, job cards, bills of materials, the plant floor and work sent out to suppliers."),
	},
	{
		"target": "onefactory-figures",
		"side": "bottom",
		"title": _lt("The Floor at a Glance"),
		"text": _lt("How many work orders are open, running, waiting to start and closed today."),
	},
	{
		"target": "onefactory-views",
		"side": "bottom",
		"title": _lt("Orders and Workstations"),
		"text": _lt("Open and Completed list the work orders, and each workstation's tab lists the operations waiting at it."),
	},
	{
		"target": "interface-tour",
		"side": "top",
		"title": _lt("Settings and Tours"),
		"text": _lt("Settings is the cog, and the tour runs again from the button beside it."),
	},
]

TOURS = [{"key": "floor", "at": "onefactory-views", "steps": FLOOR}]
