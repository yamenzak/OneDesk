"""TrustCenter's tours (one/tours.py, docs/READY.md mechanism 10): one, of
TrustCenter open on an agreement, found by the mark at `at`. TrustCenter has
no foot, so it starts the tour itself the first time it opens there."""

from frappe import _lt

AGREEMENTS = [
	{
		"target": "trust-standing",
		"side": "bottom",
		"title": _lt("Where You Stand"),
		"text": _lt("Whether you and your organisation agreed, with Agree here when it is owed."),
	},
	{
		"target": "centre-tree",
		"side": "right",
		"title": _lt("Everything in One Place"),
		"text": _lt("Each agreement, the optional services, who receives data and what is changing."),
	},
	{
		"target": "centre-search",
		"side": "right",
		"title": _lt("Find a Clause"),
		"text": _lt("Search every agreement by a word in it."),
	},
]

TOURS = [{"key": "agreements", "at": "trust-standing", "steps": AGREEMENTS}]
