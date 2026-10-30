"""OneWorkbook's tours (one/tours.py, docs/READY.md mechanism 10), one for
each area of its screen, found by the mark at `at`; each step points at a
`data-tour` mark of OneWorkbook's. OneWorkbook has one area, the editor."""

from frappe import _lt

EDITOR = [
	{
		"target": "oneworkbook-toolbar",
		"side": "bottom",
		"title": _lt("Format the Cells"),
		"text": _lt("Number formats, fonts, colours, borders, filters, charts and pivot tables are here."),
	},
	{
		"target": "oneworkbook-formula",
		"side": "bottom",
		"title": _lt("Values and Formulas"),
		"text": _lt("Type into a cell or here, and start with an equals sign for a formula."),
	},
	{
		"target": "oneworkbook-tabs",
		"side": "top",
		"title": _lt("Your Sheets"),
		"text": _lt("Add a sheet with the plus, and right-click a sheet's name to rename, copy, colour or hide it."),
	},
	{
		"target": "oneworkbook-head",
		"side": "bottom",
		"title": _lt("File, Notes and History"),
		"text": _lt("File prints, exports and keeps templates, and beside it are the notes, the version history and the shortcuts."),
	},
]

TOURS = [{"key": "editor", "at": "oneworkbook-editor", "steps": EDITOR}]
