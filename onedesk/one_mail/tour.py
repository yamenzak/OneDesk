"""OneMail's tours (one/tours.py, docs/READY.md mechanism 10), one for each
area of its screen, found by the mark at `at`; each step points at a
`data-tour` mark, the window's own (window-*) or OneMail's. OneMail has one
area, the mailbox."""

from frappe import _lt

MAILBOX = [
	{
		"target": "interface-nav",
		"side": "right",
		"title": _lt("Your Mailboxes"),
		"text": _lt("Every mailbox you can read is here, and each opens to its folders."),
	},
	{
		"target": "interface-new",
		"side": "bottom",
		"title": _lt("Write an Email"),
		"text": _lt("Start a new email here, or press C anywhere in OneMail."),
	},
	{
		"target": "onemail-list",
		"side": "right",
		"title": _lt("Your Conversations"),
		"text": _lt("Open one to read it, or tick several to file or archive them together."),
	},
	{
		"target": "onemail-reading",
		"side": "left",
		"title": _lt("Read and Reply"),
		"text": _lt("The conversation opens here, with the records it is linked to above it."),
	},
	{
		"target": "interface-search",
		"side": "bottom",
		"title": _lt("Search Your Mail"),
		"text": _lt("Type to search, and narrow it with from:, subject: or is:unread."),
	},
	{
		"target": "interface-tour",
		"side": "top",
		"title": _lt("Help and Tours"),
		"text": _lt("Help is the question mark and the tour is the button beside it, with Settings under the arrow at the end of the top bar."),
	},
]

TOURS = [{"key": "mailbox", "at": "onemail-list", "steps": MAILBOX}]
