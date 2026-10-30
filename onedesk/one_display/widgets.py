"""Every kind of widget a collection can hold: what it draws (its slots), what
it can be told (its settings), and which kinds of source may fill it.

A slot is filled through a widget's mapping, `{"title": "{customer}"}`: a
field's name in braces, as many as the line needs. A premade widget takes
its source whole instead (the queue board takes a queue, the weather takes
the weather), and its `slots` are empty. Pure, so the editor and the guards
read it without a site."""

from frappe import _lt

# A setting is (key, kind, label, default); kinds are what the editor draws.
TEXT, LONG, NUMBER, CHECK, COLOUR, SELECT, IMAGE, CODE = ("text", "long", "number", "check", "colour", "select", "image", "code")

TYPES = {
	"Queue Board": {
		"label": _lt("Queue Board"),
		"about": _lt("Who is being served at which counter, and how many wait for each service."),
		"sources": ("Queue",),
		"slots": (),
		"settings": (
			("heading", TEXT, _lt("Heading"), _lt("Now Serving")),
			("rows", NUMBER, _lt("Rows"), 6),
			("waiting", CHECK, _lt("Show Who Waits"), 1),
		),
		"size": (60, 80),
	},
	"Kiosk": {
		"label": _lt("Kiosk"),
		"about": _lt("A button for each service; a touch takes a ticket."),
		"sources": ("Queue",),
		"slots": (),
		"settings": (("heading", TEXT, _lt("Heading"), _lt("Take a ticket")),),
		"size": (100, 100),
	},
	"Ticker": {
		"label": _lt("Ticker"),
		"about": _lt("Words that run along the screen: headlines, notices, figures."),
		"sources": ("Records", "Record", "Report", "Feed"),
		"slots": ("text",),
		"settings": (
			("text", LONG, _lt("Words"), ""),
			("speed", NUMBER, _lt("Seconds Across"), 30),
		),
		"size": (100, 8),
	},
	"Text": {
		"label": _lt("Text"),
		"about": _lt("A heading or a line of words, written here or taken from a record."),
		"sources": ("Record", "Records", "Report"),
		"slots": ("text",),
		"settings": (
			("text", LONG, _lt("Words"), ""),
			("size", NUMBER, _lt("Size"), 5),
			("align", SELECT, _lt("Align"), "start", ("start", "center", "end")),
			("colour", COLOUR, _lt("Colour"), ""),
		),
		"size": (40, 12),
	},
	"Clock": {
		"label": _lt("Clock"),
		"about": _lt("The time, and the date if you want it."),
		"sources": (),
		"slots": (),
		"settings": (
			("date", CHECK, _lt("Show the Date"), 1),
			("hours", SELECT, _lt("Hours"), "24", ("24", "12")),
		),
		"size": (20, 14),
	},
	"Weather": {
		"label": _lt("Weather"),
		"about": _lt("The weather now and for the next days, for a place."),
		"sources": ("Weather",),
		"slots": (),
		"settings": (("days", NUMBER, _lt("Days Ahead"), 3),),
		"size": (25, 30),
	},
	"List": {
		"label": _lt("List"),
		"about": _lt("Rows from records or a report: a line, a smaller line, a figure and a picture each."),
		"sources": ("Records", "Report", "Feed"),
		"slots": ("title", "subtitle", "value", "image"),
		"settings": (
			("heading", TEXT, _lt("Heading"), ""),
			("rows", NUMBER, _lt("Rows"), 6),
		),
		"size": (35, 60),
	},
	"Number": {
		"label": _lt("Number"),
		"about": _lt("One figure, large, with what it counts under it."),
		"sources": ("Records", "Record", "Report"),
		"slots": ("value", "label"),
		"settings": (("label", TEXT, _lt("Label"), ""),),
		"size": (20, 20),
	},
	"Image": {
		"label": _lt("Image"),
		"about": _lt("A picture or a logo, uploaded or from a record."),
		"sources": ("Record",),
		"slots": ("image",),
		"settings": (
			("image", IMAGE, _lt("Picture"), ""),
			("fit", SELECT, _lt("Fit"), "contain", ("contain", "cover")),
		),
		"size": (20, 20),
	},
	"QR Code": {
		"label": _lt("QR Code"),
		"about": _lt("A code a phone opens: a menu, a form, a page."),
		"sources": ("Record",),
		"slots": ("link",),
		"settings": (
			("link", TEXT, _lt("Address"), ""),
			("caption", TEXT, _lt("Caption"), ""),
		),
		"size": (15, 25),
	},
	"Custom": {
		"label": _lt("Custom"),
		"about": _lt("HTML, CSS and JavaScript of your own or OneAI's, in a sandbox. Its rows arrive as one_display_rows."),
		"sources": ("Records", "Record", "Report", "Feed", "Weather"),
		"slots": (),
		"settings": (("html", CODE, _lt("Code"), ""),),
		"size": (30, 30),
	},
}

# The slot a ticker joins its rows into, and the separator between them.
JOINED = {"Ticker": ("text", "   •   ")}


def defaults(kind: str) -> dict:
	"""A widget's settings before anybody changes them, words in the
	language of the moment."""
	return {
		key: default if isinstance(default, (int, float)) else str(default)
		for key, _kind, _label, default, *_rest in TYPES[kind]["settings"]
	}


def described() -> list[dict]:
	"""The registry as the editor reads it, its words translated."""
	return [
		{
			"type": kind,
			"label": str(spec["label"]),
			"about": str(spec["about"]),
			"sources": list(spec["sources"]),
			"slots": list(spec["slots"]),
			"settings": [
				{
					"key": key,
					"kind": kind_,
					"label": str(label),
					"default": default if isinstance(default, (int, float)) else str(default),
					"options": list(rest[0]) if rest else None,
				}
				for key, kind_, label, default, *rest in spec["settings"]
			],
			"size": list(spec["size"]),
		}
		for kind, spec in TYPES.items()
	]
