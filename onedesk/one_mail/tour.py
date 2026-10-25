"""OneMail's tour (one/tours.py, docs/READY.md mechanism 10): each step
points at a `data-tour` mark, the window's own (window-*) or OneMail's."""

from frappe import _lt

STEPS = [
	{
		"target": "window-nav",
		"side": "right",
		"title": _lt("Your Mailboxes"),
		"text": _lt("Every mailbox you can read is here, and each opens to its folders."),
	},
	{
		"target": "onemail-new",
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
		"target": "window-search",
		"side": "bottom",
		"title": _lt("Search Your Mail"),
		"text": _lt("Type to search, and narrow it with from:, subject: or is:unread."),
	},
	{
		"target": "window-foot",
		"side": "top",
		"title": _lt("Settings and Help"),
		"text": _lt("Set up your mailboxes in Settings, and find this tour again in Help."),
	},
]
