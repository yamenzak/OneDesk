"""OneWriter's tours (one/tours.py, docs/READY.md mechanism 10), one for each
area of its screen, found by the mark at `at`; each step points at a
`data-tour` mark of OneWriter's. OneWriter has one area, the editor."""

from frappe import _lt

EDITOR = [
	{
		"target": "onewriter-toolbar",
		"side": "bottom",
		"title": _lt("Format Your Words"),
		"text": _lt("Headings, lists, links, pictures, tables and page breaks go in from here."),
	},
	{
		"target": "onewriter-outline",
		"side": "right",
		"title": _lt("The Outline"),
		"text": _lt("Every heading is listed here, and clicking one takes you to it."),
	},
	{
		"target": "onewriter-page",
		"side": "top",
		"title": _lt("Write and Comment"),
		"text": _lt("It saves itself as you write, and selected words can be commented on in the margin."),
	},
	{
		"target": "onewriter-head",
		"side": "bottom",
		"title": _lt("The Path and File"),
		"text": _lt("The path leads back to where the document is kept, and File prints it, keeps versions and sets up the page."),
	},
]

TOURS = [{"key": "editor", "at": "onewriter-editor", "steps": EDITOR}]
