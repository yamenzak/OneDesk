"""OneAI's tours (one/tours.py, docs/READY.md mechanism 10), one for each
area of its screen, found by the mark at `at`; each step points at a
`data-tour` mark. OneAI has one area of its own, the panel, which opens
beside whatever is on screen."""

from frappe import _lt

PANEL = [
	{
		"target": "oneai-panel",
		"side": "left",
		"title": _lt("Ask OneAI"),
		"text": _lt("Ask about what is on screen, or anything else, in your own words and language."),
	},
	{
		"target": "oneai-new",
		"side": "bottom",
		"title": _lt("A New Conversation"),
		"text": _lt("Start afresh here; every conversation stays in the list to pick up again."),
	},
	{
		"target": "oneai-grow",
		"side": "bottom",
		"title": _lt("More Room"),
		"text": _lt("Widen the panel, or give it the whole window, and bring it back from the same button."),
	},
]

TOURS = [{"key": "panel", "at": "oneai-panel", "steps": PANEL}]
