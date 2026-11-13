"""OneDisplay's tours (one/tours.py, docs/READY.md mechanism 10), one for each
area of its screens, found by the mark at `at`; each step points at a
`data-tour` mark, the window's own (window-*) or OneDisplay's. Its home is the
list of screens."""

from frappe import _lt

SCREENS = [
	{
		"target": "interface-nav",
		"side": "right",
		"title": _lt("Screens and What They Show"),
		"text": _lt("Screens and channels sit at the top, the slides, widgets, music and ads a channel plays under Content, and the queues under Queues."),
	},
	{
		"target": "onedisplay-screens",
		"side": "mid-center",
		"title": _lt("Every Screen"),
		"text": _lt("Each screen says whether it is online, and opening one lets you reload it, mute it or turn it off from here."),
	},
	{
		"target": "onedisplay-pair",
		"side": "bottom",
		"title": _lt("Add a Screen"),
		"text": _lt("Open the TV address on the screen, then type the code it shows here and choose its channel."),
	},
	{
		"target": "interface-tour",
		"side": "top",
		"title": _lt("Help and Tours"),
		"text": _lt("Help is the question mark and the tour is the button beside it, with Settings under the arrow at the end of the top bar."),
	},
]

TOURS = [{"key": "screens", "at": "onedisplay-screens", "steps": SCREENS}]
