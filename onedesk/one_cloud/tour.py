"""OneCloud's tours (one/tours.py, docs/READY.md mechanism 10), one for each
area of its screen, found by the mark at `at`; each step points at a
`data-tour` mark, the window's own (window-*) or OneCloud's. OneCloud has one
area, the explorer."""

from frappe import _lt

EXPLORER = [
	{
		"target": "interface-nav",
		"side": "right",
		"title": _lt("Your Folders"),
		"text": _lt("My Files, Company, Libraries, Records and the Recycle Bin are here, and each opens to its folders."),
	},
	{
		"target": "interface-new",
		"side": "bottom",
		"title": _lt("Add Files"),
		"text": _lt("Make a folder, a workbook, a document or a presentation, or upload files from your computer."),
	},
	{
		"target": "onecloud-items",
		"side": "top",
		"title": _lt("Your Files"),
		"text": _lt("Open a file to see it, drag files onto a folder to move them, or right-click one to share it."),
	},
	{
		"target": "interface-ways",
		"side": "bottom",
		"title": _lt("Details or Tiles"),
		"text": _lt("Show the folder as a list with its columns, or as tiles with a picture of each file."),
	},
	{
		"target": "interface-search",
		"side": "bottom",
		"title": _lt("Search Your Files"),
		"text": _lt("Type to search this folder and the folders in it, or every file you can open."),
	},
	{
		"target": "interface-tour",
		"side": "top",
		"title": _lt("Help and Tours"),
		"text": _lt("Help is the question mark and the tour is the button beside it, with Settings under the arrow at the end of the top bar."),
	},
]

TOURS = [{"key": "explorer", "at": "onecloud-items", "steps": EXPLORER}]
