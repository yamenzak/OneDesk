"""One's tours (one/tours.py, docs/READY.md mechanism 10), one for each of
its screens, found by the screen's own mark at `at`; each step points at a
`data-tour` mark on that screen. A step whose mark is not on screen (Home's
workspace notices, which only an administrator has) is passed over."""

from frappe import _lt

HOME = [
	{
		"target": "one-home-counts",
		"side": "bottom",
		"title": _lt("What Waits for You"),
		"text": _lt("How much waits for you in each app you use, each number opening its list."),
	},
	{
		"target": "one-home-needs",
		"side": "bottom",
		"title": _lt("What the Workspace Needs"),
		"text": _lt("Things only an administrator can put right, such as a mailbox that stopped connecting."),
	},
	{
		"target": "one-home-tasks",
		"side": "right",
		"title": _lt("Your Tasks"),
		"text": _lt("Your tasks due today or late, with the rest in My Tasks."),
	},
	{
		"target": "one-home-today",
		"side": "left",
		"title": _lt("Today"),
		"text": _lt("What is on your calendar today, with the whole week in OneCalendar."),
	},
]

DASHBOARDS = [
	{
		"target": "one-dashboards-search",
		"side": "bottom",
		"title": _lt("Find a Dashboard"),
		"text": _lt("Type part of its name or its app's."),
	},
	{
		"target": "one-dashboards-group",
		"side": "top",
		"title": _lt("By App"),
		"text": _lt("Each dashboard is under the app it is about, and opens with a click."),
	},
]

ANNOUNCEMENTS = [
	{
		"target": "one-news-views",
		"side": "bottom",
		"title": _lt("Now and Earlier"),
		"text": _lt("Showing Now runs along the top bar, and Earlier keeps what has stopped."),
	},
	{
		"target": "one-news-card",
		"side": "top",
		"title": _lt("An Announcement"),
		"text": _lt("Each one in full, with who posted it and until when it shows."),
	},
]

BIN = [
	{
		"target": "one-bin-states",
		"side": "bottom",
		"title": _lt("Deleted and Put Back"),
		"text": _lt("What was deleted waits here, and Put Back lists what came back."),
	},
	{
		"target": "one-bin-filters",
		"side": "bottom",
		"title": _lt("Find It"),
		"text": _lt("Search by its name, or narrow the list to one kind of record."),
	},
	{
		"target": "one-bin-list",
		"side": "top",
		"title": _lt("Put It Back"),
		"text": _lt("Put Back on a row brings it back as it was, or tick several to put them back together."),
	},
]

ADDRESS_BOOK = [
	{
		"target": "one-book-list",
		"side": "right",
		"title": _lt("Contacts and Addresses"),
		"text": _lt("Switch between people and places, and search either."),
	},
	{
		"target": "one-book-chosen",
		"side": "left",
		"title": _lt("The One You Chose"),
		"text": _lt("Who it belongs to, and a person's addresses or a place's people, with Edit to change it."),
	},
]

TOURS = [
	{"key": "home", "at": "one-home", "steps": HOME},
	{"key": "dashboards", "at": "one-dashboards", "steps": DASHBOARDS},
	{"key": "announcements", "at": "one-news", "steps": ANNOUNCEMENTS},
	{"key": "recycle-bin", "at": "one-bin", "steps": BIN},
	{"key": "address-book", "at": "one-book", "steps": ADDRESS_BOOK},
]
