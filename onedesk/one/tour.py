"""One's tours (one/tours.py, docs/READY.md mechanism 10), one for each of
its screens, found by the screen's own mark at `at`; each step points at a
`data-tour` mark on that screen. A step whose mark is not on screen (Home's
workspace notices, which only an administrator has) is passed over."""

from frappe import _lt

HOME = [
	{
		"target": "one-home-needs",
		"side": "bottom",
		"title": _lt("What the Workspace Needs"),
		"text": _lt("Things only an administrator can put right, such as a mailbox that stopped connecting."),
	},
	{
		"target": "one-home-glance",
		"side": "bottom",
		"title": _lt("The Workspace"),
		"text": _lt("Its people, apps, storage and OneCredits, each opening where it is managed."),
	},
	{
		"target": "one-home-approvals",
		"side": "bottom",
		"title": _lt("Your Approvals"),
		"text": _lt("What waits for your approval in every app, oldest first."),
	},
	{
		"target": "one-home-asked",
		"side": "bottom",
		"title": _lt("Asked of You"),
		"text": _lt("Files someone has asked you for, each sent from here."),
	},
	{
		"target": "one-home-announcements",
		"side": "top",
		"title": _lt("Announcements"),
		"text": _lt("What the office is saying now, with every announcement one click away."),
	},
	{
		"target": "one-home-news",
		"side": "top",
		"title": _lt("New in Your Apps"),
		"text": _lt("Apps with a version you haven't opened yet, each saying what changed."),
	},
]


TOURS = [
	{"key": "home", "at": "one-home", "steps": HOME},
]
