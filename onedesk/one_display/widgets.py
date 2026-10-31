"""Every kind of widget a collection can hold: what it draws (its slots), what
it can be told (its settings), and which kinds of source may fill it.

A slot is filled through a widget's mapping, `{"title": "{customer}"}`: a
field's name in braces, as many as the line needs. A premade widget takes
its source whole instead (the queue board takes a queue, the weather takes
the weather), and its `slots` are empty. A widget is bare: what surrounds
its content is its element's `look` (LOOK, below). Pure."""

from frappe import _lt

# A setting is (key, kind, label, default); kinds are what the editor draws.
TEXT, LONG, NUMBER, CHECK, COLOUR, SELECT, IMAGE, CODE = ("text", "long", "number", "check", "colour", "select", "image", "code")

TYPES = {
	"Queue Board": {
		"label": _lt("Queue Board"),
		"about": _lt("Tickets being served at each counter and how many are waiting."),
		"sources": ("Queue",),
		"slots": (),
		"settings": (
			("heading", TEXT, _lt("Heading"), _lt("Now Serving")),
			("rows", NUMBER, _lt("Rows"), 6),
			("waiting", CHECK, _lt("Show Waiting Count"), 1),
		),
		"size": (60, 80),
	},
	"Kiosk": {
		"label": _lt("Kiosk"),
		"about": _lt("Buttons that issue a ticket for each service."),
		"sources": ("Queue",),
		"slots": (),
		"settings": (("heading", TEXT, _lt("Heading"), _lt("Take a ticket")),),
		"size": (100, 100),
	},
	"Ticker": {
		"label": _lt("Ticker"),
		"about": _lt("Scrolling text, written here or from a source."),
		"sources": ("Records", "Record", "Report", "Feed", "Exchange Rates"),
		"slots": ("text",),
		"settings": (
			("text", LONG, _lt("Words"), ""),
			("speed", NUMBER, _lt("Scroll Duration (Seconds)"), 30),
		),
		"size": (100, 8),
	},
	"Text": {
		"label": _lt("Text"),
		"about": _lt("A heading or text, written here or from a record."),
		"sources": ("Record", "Records", "Report", "Exchange Rates"),
		"slots": ("text",),
		"settings": (
			("text", LONG, _lt("Words"), ""),
			("size", NUMBER, _lt("Size"), 5),
			("align", SELECT, _lt("Align"), "start", ("start", "center", "end")),
		),
		"size": (40, 12),
	},
	"Clock": {
		"label": _lt("Clock", context="A widget that shows the time"),
		"about": _lt("The current time, with an optional date."),
		"sources": (),
		"slots": (),
		"settings": (
			("date", CHECK, _lt("Show Date"), 1),
			("hours", SELECT, _lt("Hours"), "24", ("24", "12")),
		),
		"size": (20, 14),
	},
	"Weather": {
		"label": _lt("Weather"),
		"about": _lt("Current weather and forecast for a place."),
		"sources": ("Weather",),
		"slots": (),
		"settings": (("days", NUMBER, _lt("Forecast Days"), 3),),
		"size": (25, 30),
	},
	"Board": {
		"label": _lt("Board"),
		"about": _lt("Every item on a board with its state, time in state and value."),
		"sources": ("Board",),
		"slots": (),
		"settings": (
			("columns", NUMBER, _lt("Columns"), 0),
			("time", CHECK, _lt("Show Time in State"), 1),
			("value", CHECK, _lt("Show Value"), 1),
		),
		"size": (60, 60),
	},
	"Board Item": {
		"label": _lt("Board Item"),
		"about": _lt("One board item, or the ticket a counter is serving."),
		"sources": ("Board", "Queue"),
		"slots": (),
		"settings": (
			("item", TEXT, _lt("Item or Counter"), ""),
			("time", CHECK, _lt("Show Time in State"), 1),
			("idle", TEXT, _lt("When Idle"), _lt("Closed")),
		),
		"size": (30, 30),
	},
	"Image": {
		"label": _lt("Image"),
		"about": _lt("An uploaded image or one from a record."),
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
		"about": _lt("A code that opens a link on a phone."),
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
		"about": _lt("HTML, CSS and JavaScript run in a sandbox. Rows are available as one_display_rows."),
		"sources": ("Records", "Record", "Report", "Feed", "Weather", "Exchange Rates"),
		"slots": (),
		"settings": (("html", CODE, _lt("Code"), ""),),
		"size": (30, 30),
	},
}

# What an element's look may set, in the editor's own names (BorderSection,
# ShadowSection, shim/WidgetLookSection.vue); lengths are in the editor's
# units, half a screen's pixels.
LOOK = (
	"fillColor", "color", "fontFamily", "padding",
	"borderStyle", "borderColor", "borderWidth", "borderRadius",
	"shadowColor", "shadowBlur", "shadowOpacity", "shadowOffset", "shadowAngle",
)

# Looks offered for every widget. Plain is no look at all.
LOOKS = {
	"Plain": {},
	"Card": {"fillColor": "#0B0D10DB", "color": "#FFFFFFFF", "borderRadius": 8, "padding": 10},
	"Light Card": {"fillColor": "#FFFFFFF2", "color": "#111827FF", "borderRadius": 8, "padding": 10},
	"Outline": {"color": "#FFFFFFFF", "borderStyle": "solid", "borderColor": "#FFFFFF66", "borderWidth": 1, "borderRadius": 8, "padding": 10},
	"Band": {"fillColor": "#111827EB", "color": "#FFFFFFFF"},
	"Solid": {"fillColor": "#0B0D10FF", "color": "#FFFFFFFF"},
}
LOOK_LABELS = {
	"Plain": _lt("Plain"),
	"Card": _lt("Card"),
	"Light Card": _lt("Light Card"),
	"Outline": _lt("Outline"),
	"Band": _lt("Band"),
	"Solid": _lt("Solid"),
}

# The look a widget is given when it is put on a screen, which is how each
# was drawn before widgets were bare.
FIRST_LOOK = {"Queue Board": "Card", "Weather": "Card", "Ticker": "Band", "Kiosk": "Solid", "Board Item": "Card"}


def look(settings: dict | None) -> dict:
	"""Only the look's own keys, from a widget's settings. Pure."""
	said = (settings or {}).get("look")
	return {key: said[key] for key in LOOK if key in said and said[key] not in (None, "")} if isinstance(said, dict) else {}


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
			"look": LOOKS.get(FIRST_LOOK.get(kind, "Plain"), {}),
		}
		for kind, spec in TYPES.items()
	]


def looks() -> list[dict]:
	"""The looks as the editor offers them, named in the reader's language."""
	return [{"name": name, "label": str(LOOK_LABELS[name]), "look": said} for name, said in LOOKS.items()]
