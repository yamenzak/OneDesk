"""Every kind of widget a collection can hold: what it draws (its slots), what
it can be told (its settings), and which kinds of source may fill it.

A slot is filled through a widget's mapping, `{"title": "{customer}"}`: a
field's name in braces, as many as the line needs. A premade widget takes
its source whole instead (the queue board takes a queue, the weather takes
the weather), and its `slots` are empty. A widget is bare: what surrounds
its content is its element's `look` (LOOK, below). Pure."""

import json

from frappe import _lt
from frappe.utils import escape_html

# A setting is (key, kind, label, default); kinds are what the editor draws.
TEXT, LONG, NUMBER, CHECK, COLOUR, SELECT, IMAGE, CODE = ("text", "long", "number", "check", "colour", "select", "image", "code")

TYPES = {
	"Queue Board": {
		"label": _lt("Queue Board"),
		"about": _lt("Tickets being served at each counter and how many are waiting."),
		"sources": ("Queue",),
		"slots": (),
		"settings": (
			("layout", SELECT, _lt("Layout"), "now_serving", (("now_serving", _lt("Now Serving")), ("latest", _lt("Latest Call")), ("counter", _lt("One Counter")), ("counters", _lt("Every Counter")), ("list", _lt("Recent Calls")), ("waiting", _lt("Waiting by Service")))),
			("heading", TEXT, _lt("Heading"), _lt("Now Serving")),
			("counter", TEXT, _lt("Counter"), "1"),
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
		"settings": (
			("layout", SELECT, _lt("Layout"), "grid", (("grid", _lt("Grid")), ("list", _lt("List")))),
			("heading", TEXT, _lt("Heading"), _lt("Take a ticket")),
		),
		"size": (100, 100),
	},
	"Ticker": {
		"label": _lt("Ticker"),
		"about": _lt("Scrolling text, written here or from a source."),
		"sources": ("Records", "Record", "Report", "Feed", "Exchange Rates"),
		"slots": ("text",),
		"settings": (
			("layout", SELECT, _lt("Layout"), "scroll", (("scroll", _lt("Scrolling")), ("fade", _lt("One at a Time")), ("labelled", _lt("With a Label")))),
			("text", LONG, _lt("Words"), ""),
			("speed", NUMBER, _lt("Scroll Duration (Seconds)"), 30),
			("label", TEXT, _lt("Label"), _lt("News")),
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
			("layout", SELECT, _lt("Layout"), "digital", (("digital", _lt("Digital")), ("analog", _lt("Analog")), ("date", _lt("Date Card")), ("stacked", _lt("Time and Day")), ("minimal", _lt("Time Only")))),
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
		"settings": (
			("layout", SELECT, _lt("Layout"), "week", (("week", _lt("Week Ahead")), ("today", _lt("Today")), ("hours", _lt("By the Hour")), ("list", _lt("Week as a List")), ("compact", _lt("Compact")), ("big", _lt("Large Temperature")))),
			("days", NUMBER, _lt("Forecast Days"), 3),
		),
		"size": (25, 30),
	},
	"Board": {
		"label": _lt("Board"),
		"about": _lt("Every item on a board with its state, time in state and value."),
		"sources": ("Board",),
		"slots": (),
		"settings": (
			("layout", SELECT, _lt("Layout"), "tiles", (("tiles", _lt("Tiles")), ("list", _lt("List")), ("summary", _lt("Count by State")))),
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
			("layout", SELECT, _lt("Layout"), "card", (("card", _lt("Code and Caption")), ("side", _lt("Caption Beside")))),
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
	"fillColor", "color", "accentColor", "fontFamily", "padding",
	"textSize", "mainSize", "labelSize", "detailSize",
	"borderStyle", "borderColor", "borderWidth", "borderRadius",
	"shadowColor", "shadowBlur", "shadowOpacity", "shadowOffset", "shadowAngle",
)

# Looks offered for every widget. Plain is no look at all; BRAND is the
# business's colour, filled in when the looks are read (`looks`).
BRAND = "brand"
LOOKS = {
	"Plain": {},
	"Card": {"fillColor": "#0B0D10DB", "color": "#FFFFFFFF", "borderRadius": 8, "padding": 10},
	"Light Card": {"fillColor": "#FFFFFFF2", "color": "#111827FF", "borderRadius": 8, "padding": 10},
	"Soft": {"fillColor": "#F3F4F6FF", "color": "#111827FF", "borderRadius": 14, "padding": 12},
	"Floating": {"fillColor": "#FFFFFFFF", "color": "#111827FF", "borderRadius": 16, "padding": 14, "shadowColor": "#0000004D", "shadowBlur": 12, "shadowOffset": 3, "shadowAngle": 90},
	"Outline": {"color": "#FFFFFFFF", "borderStyle": "solid", "borderColor": "#FFFFFF66", "borderWidth": 1, "borderRadius": 8, "padding": 10},
	"Glass": {"fillColor": "#FFFFFF1F", "color": "#FFFFFFFF", "borderStyle": "solid", "borderColor": "#FFFFFF40", "borderWidth": 1, "borderRadius": 16, "padding": 12},
	"Dark Glass": {"fillColor": "#00000066", "color": "#FFFFFFFF", "borderRadius": 16, "padding": 12},
	"Pill": {"fillColor": "#0B0D10DB", "color": "#FFFFFFFF", "borderRadius": 999, "padding": 8},
	"Rounded": {"borderRadius": 24},
	"Band": {"fillColor": "#111827EB", "color": "#FFFFFFFF"},
	"Light Band": {"fillColor": "#FFFFFFF2", "color": "#111827FF"},
	"Solid": {"fillColor": "#0B0D10FF", "color": "#FFFFFFFF", "padding": 12},
	"Accent": {"fillColor": BRAND, "color": "#FFFFFFFF", "accentColor": "#FFFFFFFF", "borderRadius": 8, "padding": 10},
	"Accent Band": {"fillColor": BRAND, "color": "#FFFFFFFF", "accentColor": "#FFFFFFFF"},
	"Accent Pill": {"fillColor": BRAND, "color": "#FFFFFFFF", "accentColor": "#FFFFFFFF", "borderRadius": 999, "padding": 8},
	"Accent Outline": {"color": "#FFFFFFFF", "borderStyle": "solid", "borderColor": BRAND, "borderWidth": 2, "borderRadius": 8, "padding": 10},
	"Alert": {"fillColor": "#DC2626FF", "color": "#FFFFFFFF", "borderRadius": 8, "padding": 10},
	"Highlight": {"fillColor": "#FEF3C7FF", "color": "#78350FFF", "borderRadius": 8, "padding": 10},
	"Contrast": {"fillColor": "#000000FF", "color": "#FFFFFFFF", "borderStyle": "solid", "borderColor": "#FFFFFFFF", "borderWidth": 2, "borderRadius": 4, "padding": 10},
}
LOOK_LABELS = {
	"Plain": _lt("Plain"),
	"Card": _lt("Card"),
	"Light Card": _lt("Light Card"),
	"Soft": _lt("Soft"),
	"Floating": _lt("Floating"),
	"Outline": _lt("Outline"),
	"Glass": _lt("Glass"),
	"Dark Glass": _lt("Dark Glass"),
	"Pill": _lt("Pill"),
	"Rounded": _lt("Rounded"),
	"Band": _lt("Band"),
	"Light Band": _lt("Light Band"),
	"Solid": _lt("Solid"),
	"Accent": _lt("Accent"),
	"Accent Band": _lt("Accent Band"),
	"Accent Pill": _lt("Accent Pill"),
	"Accent Outline": _lt("Accent Outline"),
	"Alert": _lt("Alert"),
	"Highlight": _lt("Highlight"),
	"Contrast": _lt("Contrast"),
}

# The look a widget is given when it is put on a screen, which is how each
# was drawn before widgets were bare.
FIRST_LOOK = {"Queue Board": "Card", "Weather": "Card", "Ticker": "Band", "Kiosk": "Solid", "Board Item": "Card"}


# Ready-made widgets, a kind with settings, a look and a size (AGENTS.md,
# Templates). Custom code runs on the screen's own browser, so it is ES5.
COUNTDOWN = """<div id="c" style="height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;font-weight:600;font-size:26vh;line-height:1">
<div id="t"></div><div style="font-size:8vh;opacity:.7;margin-top:3vh">{words}</div></div>
<script>
var target = new Date(new Date().getFullYear() + 1, 0, 1).getTime();
function two(n) { return (n < 10 ? "0" : "") + n; }
function tick() {
	var left = Math.max(0, Math.floor((target - Date.now()) / 1000));
	var days = Math.floor(left / 86400), hours = Math.floor(left / 3600) % 24, minutes = Math.floor(left / 60) % 60;
	document.getElementById("t").textContent = days + " : " + two(hours) + " : " + two(minutes);
}
tick(); setInterval(tick, 1000);
</script>"""
ROTATING = """<div id="m" style="height:100%;display:flex;align-items:center;justify-content:center;text-align:center;font-weight:600;font-size:30vh;line-height:1.2;transition:opacity .6s"></div>
<script>
var lines = {words};
var at = 0, box = document.getElementById("m");
function next() {
	box.style.opacity = 0;
	setTimeout(function () { box.textContent = lines[at % lines.length]; box.style.opacity = 1; at++; }, 600);
}
next(); setInterval(next, 8000);
</script>"""
PROGRESS = """<div style="height:100%;display:flex;flex-direction:column;justify-content:center;font-weight:600;font-size:22vh;line-height:1.2">
<div style="display:flex;justify-content:space-between"><span>{words}</span><span id="v"></span></div>
<div style="height:14vh;margin-top:4vh;border-radius:7vh;background:rgba(127,127,127,.25);overflow:hidden"><div id="b" style="height:100%;width:0;border-radius:7vh;background:currentColor;transition:width 1s"></div></div></div>
<script>
var goal = 100;
function draw() {
	var row = (window.one_display_rows || [])[0] || {};
	var value = Number(row.value) || 0;
	document.getElementById("v").textContent = value + " / " + goal;
	document.getElementById("b").style.width = Math.min(100, (value / goal) * 100) + "%";
}
window.one_display_changed = draw; draw();
</script>"""

PRESETS = (
	# key, kind, label, settings, look, size
	("clock_and_date", "Clock", _lt("Clock and Date"), {"date": 1}, "Card", (24, 20)),
	("corner_clock", "Clock", _lt("Corner Clock"), {"date": 0}, "Pill", (16, 12)),
	("large_clock", "Clock", _lt("Time Only"), {"layout": "minimal"}, "Plain", (40, 26)),
	("analog_clock", "Clock", _lt("Analog Clock"), {"layout": "analog"}, "Plain", (20, 36)),
	("analog_card", "Clock", _lt("Analog Clock on a Card"), {"layout": "analog"}, "Floating", (20, 36)),
	("date_card", "Clock", _lt("Date Card"), {"layout": "date"}, "Light Card", (16, 30)),
	("time_and_day", "Clock", _lt("Time and Day"), {"layout": "stacked"}, "Plain", (30, 30)),
	("headline", "Text", _lt("Headline"), {"text": _lt("Welcome"), "size": 9}, "Plain", (80, 14)),
	("centred_title", "Text", _lt("Centred Title"), {"text": _lt("Welcome"), "size": 10, "align": "center"}, "Plain", (90, 16)),
	("subheading", "Text", _lt("Subheading"), {"text": _lt("We are glad you are here"), "size": 5}, "Plain", (70, 9)),
	("caption", "Text", _lt("Caption"), {"text": _lt("Caption"), "size": 3}, "Plain", (50, 6)),
	("notice", "Text", _lt("Notice Bar"), {"text": _lt("Opening hours today: 9:00 to 18:00"), "size": 4, "align": "center"}, "Accent Band", (100, 10)),
	("big_number", "Text", _lt("Big Number"), {"text": "128", "size": 14, "align": "center"}, "Card", (22, 24)),
	("tag", "Text", _lt("Tag"), {"text": _lt("New"), "size": 3, "align": "center"}, "Accent Pill", (14, 7)),
	("price", "Text", _lt("Price"), {"text": "24.00", "size": 7, "align": "end"}, "Plain", (20, 10)),
	("highlight_text", "Text", _lt("Highlighted Text"), {"text": _lt("Today only"), "size": 5, "align": "center"}, "Highlight", (30, 10)),
	("news_ticker", "Ticker", _lt("News Ticker"), {}, "Band", (100, 8)),
	("accent_ticker", "Ticker", _lt("Ticker in Your Colour"), {}, "Accent Band", (100, 8)),
	("labelled_ticker", "Ticker", _lt("Ticker with a Label"), {"layout": "labelled", "label": _lt("News")}, "Band", (100, 8)),
	("one_at_a_time", "Ticker", _lt("One Message at a Time"), {"layout": "fade"}, "Accent Band", (100, 8)),
	("alert_ticker", "Ticker", _lt("Alert Ticker"), {"layout": "labelled", "label": _lt("Notice")}, "Alert", (100, 8)),
	("latest_call", "Queue Board", _lt("Latest Call"), {"layout": "latest"}, "Accent", (40, 40)),
	("one_counter", "Queue Board", _lt("One Counter"), {"layout": "counter"}, "Accent", (40, 40)),
	("every_counter", "Queue Board", _lt("Every Counter"), {"layout": "counters"}, "Plain", (70, 60)),
	("recent_calls", "Queue Board", _lt("Recent Calls"), {"layout": "list", "rows": 6}, "Card", (40, 70)),
	("waiting_count", "Queue Board", _lt("Waiting by Service"), {"layout": "waiting"}, "Card", (36, 40)),
	("ticket_kiosk", "Kiosk", _lt("Ticket Kiosk"), {}, "Solid", (100, 100)),
	("light_kiosk", "Kiosk", _lt("Ticket Kiosk as a List"), {"layout": "list"}, "Soft", (100, 100)),
	("weather_card", "Weather", _lt("Weather Card"), {}, "Card", (25, 30)),
	("weather_today", "Weather", _lt("Today's Weather"), {"layout": "today"}, "Card", (32, 26)),
	("hourly", "Weather", _lt("Weather by the Hour"), {"layout": "hours"}, "Glass", (60, 26)),
	("week_ahead", "Weather", _lt("Week Ahead"), {"days": 5}, "Glass", (40, 30)),
	("week_list", "Weather", _lt("Week as a List"), {"layout": "list", "days": 5}, "Card", (32, 50)),
	("weather_compact", "Weather", _lt("Compact Weather"), {"layout": "compact"}, "Pill", (16, 9)),
	("big_temperature", "Weather", _lt("Large Temperature"), {"layout": "big"}, "Plain", (26, 40)),
	("status_board", "Board", _lt("Status Board"), {}, "Plain", (60, 60)),
	("board_columns", "Board", _lt("Board in Columns"), {"columns": 4}, "Card", (90, 60)),
	("simple_board", "Board", _lt("Simple Board"), {"time": 0, "value": 0}, "Light Card", (60, 60)),
	("board_list", "Board", _lt("Board as a List"), {"layout": "list"}, "Card", (40, 60)),
	("board_summary", "Board", _lt("Count by State"), {"layout": "summary"}, "Plain", (60, 30)),
	("status_tile", "Board Item", _lt("Status Tile"), {}, "Card", (30, 30)),
	("door_sign", "Board Item", _lt("Door Sign"), {}, "Floating", (40, 40)),
	("logo", "Image", _lt("Logo"), {}, "Plain", (16, 12)),
	("full_picture", "Image", _lt("Full Screen Picture"), {"fit": "cover"}, "Plain", (100, 100)),
	("framed_picture", "Image", _lt("Framed Picture"), {"fit": "cover"}, "Floating", (40, 40)),
	("rounded_picture", "Image", _lt("Rounded Picture"), {"fit": "cover"}, "Rounded", (24, 40)),
	("visit_website", "QR Code", _lt("Visit Our Website"), {"caption": _lt("Scan to visit our website")}, "Light Card", (15, 25)),
	("qr_beside", "QR Code", _lt("Code with Caption Beside"), {"layout": "side", "caption": _lt("Scan to visit our website")}, "Light Card", (36, 16)),
	("see_menu", "QR Code", _lt("See the Menu"), {"caption": _lt("Scan for the menu")}, "Light Card", (15, 25)),
	("give_feedback", "QR Code", _lt("Give Feedback"), {"caption": _lt("Tell us how we did")}, "Floating", (15, 25)),
	("follow_us", "QR Code", _lt("Follow Us"), {"caption": _lt("Follow us")}, "Accent", (15, 25)),
	("countdown", "Custom", _lt("Countdown"), {"html": (COUNTDOWN, _lt("days, hours and minutes to go"))}, "Card", (50, 30)),
	("rotating_messages", "Custom", _lt("Rotating Messages"), {"html": (ROTATING, (_lt("Welcome"), _lt("Thank you for visiting"), _lt("Ask us anything")))}, "Plain", (80, 20)),
	("progress", "Custom", _lt("Progress to a Goal"), {"html": (PROGRESS, _lt("Progress"))}, "Card", (50, 16)),
)


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


def _choices(options: tuple) -> list:
	"""A select's choices: plain values, or values with a name to show."""
	return [{"value": one[0], "label": str(one[1])} if isinstance(one, tuple) else one for one in options]


def described(colour: str) -> list[dict]:
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
					"options": _choices(rest[0]) if rest else None,
				}
				for key, kind_, label, default, *rest in spec["settings"]
			],
			"size": list(spec["size"]),
			"look": worn(FIRST_LOOK.get(kind, "Plain"), colour),
		}
		for kind, spec in TYPES.items()
	]


def worn(name: str, colour: str) -> dict:
	"""A look with the business's colour in it. Pure."""
	return {key: colour if value == BRAND else value for key, value in LOOKS.get(name, {}).items()}


def looks(colour: str) -> list[dict]:
	"""The looks as the editor offers them, named in the reader's language."""
	return [{"name": name, "label": str(LOOK_LABELS[name]), "look": worn(name, colour)} for name in LOOKS]


def _settled(value):
	"""A preset's setting in the reader's language: a Custom widget's code
	with its words put in, or words. Pure but for the translation."""
	if isinstance(value, tuple):
		code, words = value
		said = json.dumps([str(one) for one in words], ensure_ascii=False) if isinstance(words, tuple) else escape_html(str(words))
		return code.replace("{words}", said)
	return value if isinstance(value, (int, float)) else str(value)


def presets(colour: str) -> list[dict]:
	"""The ready-made widgets as the editor offers them, each kind bare first."""
	out = []
	for kind, spec in TYPES.items():
		out.append({"key": kind, "type": kind, "label": str(spec["label"]), "settings": {}, "look": worn(FIRST_LOOK.get(kind, "Plain"), colour), "size": list(spec["size"])})
		for key, of, label, settings, look_name, size in PRESETS:
			if of == kind:
				out.append({"key": key, "type": kind, "label": str(label), "settings": {name: _settled(value) for name, value in settings.items()}, "look": worn(look_name, colour), "size": list(size)})
	return out
