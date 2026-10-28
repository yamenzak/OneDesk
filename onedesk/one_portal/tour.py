"""OnePortal's tours (one/tours.py, docs/READY.md mechanism 10): one, of the
Portal dialog, found by the mark at `at`. The dialog has no foot, so it
starts the tour itself the first time it opens."""

from frappe import _lt

DIALOG = [
	{
		"target": "portal-people",
		"side": "bottom",
		"title": _lt("Who Is on the Portal"),
		"text": _lt("Each contact, whether they sign in, and Invite, Restore or the menu beside them."),
	},
]

TOURS = [{"key": "dialog", "at": "portal-people", "steps": DIALOG}]
