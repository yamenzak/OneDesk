"""OneSlide's tours (one/tours.py, docs/READY.md mechanism 10), one for each
area of its screen, found by the mark at `at`; each step points at a
`data-tour` mark of OneSlide's. OneSlide has one area, the editor."""

from frappe import _lt

EDITOR = [
	{
		"target": "oneslide-slides",
		"side": "right",
		"title": _lt("Your Slides"),
		"text": _lt("Click a slide to work on it, drag to reorder, and add one from the theme's layouts."),
	},
	{
		"target": "oneslide-tools",
		"side": "top",
		"title": _lt("Add to the Slide"),
		"text": _lt("Text, pictures and videos, shapes, lines and tables go on the slide from here."),
	},
	{
		"target": "oneslide-panel",
		"side": "left",
		"title": _lt("Design and Layers"),
		"text": _lt("Everything about what you chose is here, and Layers lists what is on the slide to name, hide or lock."),
	},
	{
		"target": "oneslide-head",
		"side": "bottom",
		"title": _lt("OneAI, File and Present"),
		"text": _lt("Ask OneAI for a slide, a picture or a video, keep versions and print from File, and play the presentation."),
	},
]

TOURS = [{"key": "editor", "at": "oneslide-editor", "steps": EDITOR}]
