"""Premade screens: a layout to start from, its words, shapes and widgets
already placed (one_display/AGENTS.md, Premade screens). Each is built here
rather than stored, as OneSlide's decks are, so it comes in the reader's
language, the business's colour and logo, and the shape of the screen it is
for. Choosing one in the editor puts it on the canvas as one step that
undoes; nothing is saved until the editor saves."""

import uuid
from typing import Annotated

import frappe
from frappe import _, _lt
from frappe.utils import get_url

from onedesk.one_display import screen, sizes
from onedesk.one_display import widgets as kinds

WHITE, INK, MUTED = "#FFFFFFFF", "#111827FF", "#6B7280FF"
NIGHT, PAPER, CREAM = "#0B0D10FF", "#F8FAFCFF", "#FFFBF5FF"
CLEAR = "#00000000"

#: Pictures a starter shows until it is given its own: abstract, shipped with One.
PICTURE = {one: f"/assets/onedesk/images/one_display/pictures/abstract-{one}.jpg" for one in ("blue", "teal", "warm", "dusk", "green", "sand", "violet", "ocean", "rose", "mono")}
PICTURES = tuple(PICTURE.values())

# words and lines on a dark ground, and on a light one
SOFT, FAINT = "#FFFFFFD9", "#FFFFFF99"
LINE_DARK, LINE_LIGHT = "#FFFFFF26", "#1118271A"
WHITE_CARD = "#FFFFFFFF"

#: The groups the gallery shows, in order.
GROUPS = {
	"welcome": _lt("Welcome"),
	"queues": _lt("Queues"),
	"boards": _lt("Boards and Rooms"),
	"information": _lt("Information"),
	"promotion": _lt("Promotion"),
	"retail": _lt("Shops"),
	"food": _lt("Food and Drink"),
	"health": _lt("Clinics and Care"),
	"office": _lt("Offices"),
	"events": _lt("Events"),
	"education": _lt("Schools and Training"),
	"over_slides": _lt("Over Slides"),
}

#: Which starters suit which shape of screen: wide, tall, or a strip.
SHAPES = {"Landscape": "wide", "Square": "wide", "Portrait": "tall", "Bar": "strip", "Wall": "strip"}


def shape_of(wide: int, high: int) -> str:
	"""Wide, tall or strip, from a frame. Pure."""
	if high > wide:
		return "tall"
	return "strip" if wide >= high * 2.5 else "wide"


def _mix(colour: str, other: str, part: float) -> str:
	"""A colour moved `part` of the way to another, as eight hex digits. Pure."""
	one = [int(colour[i : i + 2], 16) for i in (1, 3, 5)]
	two = [int(other[i : i + 2], 16) for i in (1, 3, 5)]
	return "#" + "".join(f"{round(a + (b - a) * part):02X}" for a, b in zip(one, two)) + "FF"


def _fade(top: str, bottom: str, angle: int = 135) -> str:
	return f"linear-gradient({angle}deg, {top}, {bottom})"


class Canvas:
	"""A screen being laid out in percent of its frame. Words are sized in
	the editor's pixels on a frame whose short side is 540, or 300 for a strip."""

	def __init__(self, wide: int, high: int, brand: dict, company: str):
		self.wide, self.high = wide, high
		self.unit = min(wide, high) / (300 if shape_of(wide, high) == "strip" else 540)
		self.brand = brand["colour"]
		self.logo_url = brand["logo"]
		self.company = company
		self.dark = _mix(self.brand, NIGHT, 0.55)
		self.deep = _mix(self.brand, NIGHT, 0.8)
		self.pale = _mix(self.brand, "#FFFFFFFF", 0.88)
		self.bright = _mix(self.brand, "#FFFFFFFF", 0.35)
		self.elements: list[dict] = []
		self.rows: list[dict] = []

	def _x(self, percent: float) -> float:
		return round(percent / 100 * self.wide, 2)

	def _y(self, percent: float) -> float:
		return round(percent / 100 * self.high, 2)

	def _id(self) -> str:
		return f"s{uuid.uuid4().hex[:10]}"

	def text(self, x, y, w, words, size=24, colour=WHITE, bold=False, align="left", italic=False, layer=3):
		from onedesk.one_slide import decks

		one = decks._text(self._id(), self._x(x), self._y(y), self._x(w), words, round(size * self.unit), colour, bold, align, italic)
		one["zIndex"] = layer
		self.elements.append(one)

	def box(self, x, y, w, h, fill, corner=0, stroke=None, shape="rectangle", layer=1, square=False, words=None, size=20, ink=WHITE):
		"""A shape, with words in its middle if given; `square` keeps it as
		tall as it is wide, for a circle."""
		from onedesk.one_slide import decks

		width = self._x(w)
		one = decks._box(self._id(), self._x(x), self._y(y), width, width if square else self._y(h), fill, shape, round(corner * self.unit), stroke, words, round(size * self.unit), ink)
		one["zIndex"] = layer
		self.elements.append(one)

	def eyebrow(self, x, y, w, words, colour=FAINT, align="left"):
		"""Small capitals above a title."""
		self.text(x, y, w, str(words).upper(), 15, colour, bold=True, align=align)

	def bar(self, x, y, w, colour=None):
		"""A short bar in the brand's colour, five pixels thick on any frame."""
		self.box(x, y, w, 5 * self.unit / self.high * 100, colour or self.brand, corner=3, layer=2)

	def card(self, x, y, w, h, fill="#FFFFFF1A", corner=20):
		"""A rounded panel that groups what is on it."""
		self.box(x, y, w, h, fill, corner=corner)

	def chip(self, x, y, w, h, words, fill, ink, size=20, square=False):
		"""Words on a rounded tag; `square` makes it a circle as tall as it is wide."""
		self.box(x, y, w, h, fill, corner=999 if square else 12, shape="oval" if square else "rectangle", square=square, words=words, size=size, ink=ink, layer=2)

	def picture(self, x, y, w, h, src, corner=0):
		"""A picture on the slide itself, cropped to fill its box, under the
		slide's words; a picture widget would sit above them."""
		self.elements.append({"id": self._id(), "type": "image", "src": src, "left": self._x(x), "top": self._y(y), "width": self._x(w), "height": self._y(h), "zIndex": 0, "opacity": 100, "borderRadius": round(corner * self.unit)})

	def logo(self, x, y, w, h, colour=WHITE, align="left"):
		"""The business's logo, or its name where it has none."""
		if self.logo_url:
			self.elements.append({"id": self._id(), "type": "image", "src": self.logo_url, "left": self._x(x), "top": self._y(y), "width": self._x(w), "height": self._y(h), "zIndex": 3, "opacity": 100})
		else:
			self.text(x, y, w, self.company, 22, colour, bold=True, align=align)

	def widget(self, preset, x, y, w, h, look=None, settings=None, source=None, mapping=None, label="", picture=None):
		"""A widget from a ready-made one (widgets.PRESETS) or a bare kind;
		`look` is a look's name, or keys laid over the preset's own."""
		found = next((one for one in kinds.PRESETS if one[0] == preset), None)
		kind = found[1] if found else preset
		said = {name: kinds._settled(value) for name, value in (found[3] if found else {}).items()}
		said.update(settings or {})
		named = look if isinstance(look, str) else (found[4] if found else kinds.FIRST_LOOK.get(kind, "Plain"))
		worn = {**kinds.worn(named, self.brand), **(look if isinstance(look, dict) else {})}
		source = _source(kind) if source is None else source
		# filled so the screen shows something from the first minute
		if kind == "QR Code" and not said.get("link"):
			said["link"] = get_url()
		if kind == "Image" and not said.get("image"):
			said["image"] = picture or PICTURES[len(self.rows) % len(PICTURES)]
		if kind == "Ticker" and not said.get("text") and not source:
			said["text"] = _("Latest news and updates appear here")
		self.rows.append(
			{
				"id": None,
				"widget_type": kind,
				"label": label or (str(found[2]) if found else ""),
				"source": source,
				"mapping": mapping if mapping is not None else _mapping(kind),
				"settings": {**said, **({"look": worn} if worn else {})},
				"x": x,
				"y": y,
				"w": w,
				"h": h,
				"layer": len(self.rows) + 1,
				"shown": "Always",
				"from_time": None,
				"to_time": None,
			}
		)

	def drawn(self, background: str) -> dict:
		"""The slide the editor puts on its canvas."""
		placed = []
		for row in self.rows:
			one = screen.element(row, self.wide, self.high)
			one["id"] = self._id()
			placed.append(one)
		return {"background": background, "elements": self.elements + placed}


# Where a widget reads from when a starter puts it down: the first source
# of the kind it takes, so a screen with one queue shows it at once.
TAKES = {"Queue Board": "Queue", "Kiosk": "Queue", "Weather": "Weather", "Board": "Board", "Board Item": "Board", "Ticker": "Feed"}


def _source(kind: str) -> str:
	return _first(TAKES[kind]) if kind in TAKES else ""


def _mapping(kind: str) -> dict:
	return {"text": "{title}"} if kind == "Ticker" else {}


# The screens. Words are in the editor's pixels on a short side of 540 (300
# for a strip): a hero 88, a title 52, a heading 34, words 24, an eyebrow 15.


def _top(c: Canvas, ink=WHITE) -> None:
	"""The logo at the top left and the time at the top right, on a pill
	that reads on the screen's ground."""
	c.logo(5, 6, 26, 8, ink)
	c.widget("corner_clock", 80, 5, 15, 9, look=None if ink == WHITE else {"fillColor": "#1118270F", "color": INK})


def _bare(ink: str) -> dict:
	"""A widget's look with nothing around it, in one colour."""
	return {"fillColor": "#00000000", "color": ink, "padding": 0}


def _sessions(*rows) -> str:
	"""A Schedule widget's sessions, a line each: time | what | where."""
	return "\n".join(" | ".join(str(part) for part in row) for row in rows)


def _glows(c: Canvas, alpha="14") -> None:
	"""Two soft circles off the right edge, for depth on a coloured ground."""
	c.box(62, -34, 70, 0, f"#FFFFFF{alpha}", shape="oval", square=True)
	c.box(80, 46, 40, 0, "#FFFFFF0D", shape="oval", square=True)


# Welcome


def welcome(c: Canvas) -> str:
	_glows(c)
	c.logo(5, 7, 26, 8)
	c.eyebrow(5, 30, 50, _("Welcome to"))
	c.text(5, 35, 56, c.company or _("Our Office"), 56, bold=True)
	c.bar(5.2, 63, 5)
	c.text(5, 67, 50, _("We are glad you are here. Make yourself at home."), 24, SOFT)
	c.widget("time_and_day", 66, 9, 28, 30, look="Glass")
	c.widget("weather_today", 66, 44, 28, 30, look="Glass")
	c.widget("news_ticker", 0, 89, 100, 11, look="Dark Glass", settings={"text": _("Opening hours today: 9:00 to 18:00")})
	return _fade(c.brand, c.deep)


def welcome_split(c: Canvas) -> str:
	c.widget("full_picture", 50, 0, 50, 100, picture=PICTURE["ocean"], look="Plain")
	c.logo(6, 8, 26, 8, INK)
	c.eyebrow(6, 27, 40, _("Welcome"), MUTED)
	c.text(6, 32, 43, _("Good to see you"), 48, INK, bold=True)
	c.bar(6.2, 56, 5)
	c.text(6, 60, 38, _("Reception is to your left. Sign in when you arrive."), 22, MUTED)
	c.widget("clock_and_date", 6, 83, 20, 11, look=_bare(INK))
	return PAPER


def lobby(c: Canvas) -> str:
	_top(c)
	c.widget("full_picture", 5, 20, 56, 66, picture=PICTURE["teal"], look="Rounded")
	c.eyebrow(66, 21, 29, _("Today"))
	c.text(66, 26, 29, _("Team meeting at 10:00 in Room 2"), 30, bold=True)
	c.text(66, 46, 29, _("Visitors sign in at the front desk"), 22, SOFT)
	c.widget("weather_today", 66, 62, 29, 24, look="Dark Glass")
	c.widget("accent_ticker", 0, 91, 100, 9, settings={"text": _("Welcome to our visitors today")})
	return _fade(c.deep, NIGHT, 160)


def clock_weather(c: Canvas) -> str:
	_glows(c, "10")
	c.widget("analog_clock", 6, 14, 34, 72)
	c.widget("weather_today", 48, 12, 46, 36, look="Glass")
	c.widget("hourly", 48, 54, 46, 32, look="Glass")
	return _fade(c.brand, c.deep, 160)


def time_only(c: Canvas) -> str:
	c.widget("large_clock", 10, 22, 80, 42)
	c.text(10, 66, 80, c.company, 24, FAINT, align="center")
	c.bar(47.5, 76, 5)
	return NIGHT


def welcome_tall(c: Canvas) -> str:
	c.box(-30, -10, 100, 0, "#FFFFFF12", shape="oval", square=True)
	c.logo(8, 5, 50, 5)
	c.widget("time_and_day", 8, 15, 84, 13, look="Glass")
	c.eyebrow(8, 37, 84, _("Welcome to"))
	c.text(8, 41, 84, c.company or _("Our Office"), 56, bold=True)
	c.bar(8.4, 56, 9)
	c.text(8, 59, 84, _("We are glad you are here. Make yourself at home."), 26, SOFT)
	c.widget("hourly", 8, 72, 84, 15, look="Glass")
	c.widget("news_ticker", 0, 93, 100, 7, look="Dark Glass", settings={"text": _("Opening hours today: 9:00 to 18:00")})
	return _fade(c.brand, c.deep, 180)


def reception_tall(c: Canvas) -> str:
	c.box(0, 0, 100, 30, c.brand)
	c.logo(8, 5, 50, 5)
	c.text(8, 14, 84, _("Reception"), 60, bold=True)
	c.widget("clock_and_date", 8, 34, 84, 11, look=_bare(INK))
	c.card(8, 49, 84, 22, WHITE_CARD)
	c.text(13, 52, 74, _("Sign in on arrival"), 30, INK, bold=True)
	c.text(13, 58, 74, _("Scan the code to tell us who you are here to see. We will let them know."), 20, MUTED)
	c.widget("visit_website", 33, 74, 34, 20, look="Soft", settings={"caption": _("Sign in here")})
	return PAPER


def banner(c: Canvas) -> str:
	c.box(0, 0, 24, 100, c.brand)
	c.logo(3, 25, 18, 50)
	c.text(28, 20, 50, _("Welcome"), 72, bold=True)
	c.text(28, 60, 50, _("We are glad you are here"), 28, SOFT)
	c.widget("time_and_day", 80, 14, 17, 72, look="Glass")
	return _fade(c.dark, NIGHT, 90)


# Queues


def now_serving(c: Canvas) -> str:
	_top(c)
	c.widget("Queue Board", 5, 20, 57, 68, look="Floating")
	c.card(66, 20, 29, 68)
	c.eyebrow(69, 25, 23, _("How it works"))
	for at, step in enumerate((_("Take a ticket at the kiosk"), _("Watch for your number"), _("Go to the counter shown"))):
		c.chip(69, 31 + at * 10, 4.2, 7.4, str(at + 1), c.brand, WHITE, 20, square=True)
		c.text(75, 32 + at * 10, 18, step, 20, SOFT)
	c.widget("give_feedback", 72, 64, 17, 22, look="Light Card")
	c.widget("news_ticker", 0, 92, 100, 8, look="Dark Glass", settings={"text": _("Your number will be called and shown here")})
	return _fade(c.dark, NIGHT)


def queue_full(c: Canvas) -> str:
	c.widget("Queue Board", 0, 0, 100, 90, look="Solid", settings={"rows": 8})
	c.widget("accent_ticker", 0, 90, 100, 10, settings={"text": _("Your number will be called and shown here")})
	return NIGHT


def counter(c: Canvas) -> str:
	c.widget("one_counter", 5, 9, 54, 82, settings={"counter": "1"})
	c.widget("clock_and_date", 63, 9, 32, 20, look="Dark Glass")
	c.eyebrow(63, 37, 32, _("Also called"))
	c.widget("recent_calls", 63, 42, 32, 49, look="Dark Glass", settings={"rows": 4, "heading": ""})
	return _fade(c.dark, NIGHT)


def every_counter(c: Canvas) -> str:
	_top(c)
	c.widget("every_counter", 5, 20, 59, 70)
	c.widget("latest_call", 68, 20, 27, 40)
	c.widget("waiting_count", 68, 64, 27, 26, look="Dark Glass")
	return _fade(c.deep, NIGHT)


def waiting_room(c: Canvas) -> str:
	_top(c)
	c.widget("latest_call", 5, 20, 42, 56)
	c.widget("recent_calls", 51, 20, 44, 56, look="Dark Glass", settings={"rows": 5})
	c.text(5, 80, 60, _("Have your ticket ready when your number is called."), 22, SOFT)
	c.widget("one_at_a_time", 0, 91, 100, 9, look="Dark Glass", settings={"text": _("Thank you for waiting")})
	return _fade(c.dark, NIGHT, 160)


def queue_offers(c: Canvas) -> str:
	c.widget("Queue Board", 0, 0, 40, 100, look="Solid", settings={"rows": 6})
	c.widget("full_picture", 40, 0, 60, 100, picture=PICTURE["warm"], look="Plain")
	c.box(40, 58, 60, 42, "#0B0D10B3")
	c.eyebrow(45, 64, 50, _("While you wait"))
	c.text(45, 69, 50, _("Ask about this month's offer"), 40, bold=True)
	c.text(45, 85, 50, _("Our team will be happy to help."), 22, SOFT)
	return NIGHT


def kiosk_wide(c: Canvas) -> str:
	c.logo(6, 8, 26, 8, INK)
	c.text(6, 26, 36, _("Take a ticket"), 56, INK, bold=True)
	c.bar(6.2, 48, 5)
	c.text(6, 52, 34, _("Choose what you are here for. Your number will be called on the screens."), 22, MUTED)
	c.widget("ticket_kiosk", 46, 8, 48, 84, look="Plain", settings={"heading": ""})
	return PAPER


def queue_tall(c: Canvas) -> str:
	c.box(0, 0, 100, 10, c.brand)
	c.logo(6, 2.5, 50, 5)
	c.widget("corner_clock", 64, 2.5, 30, 5, look="Plain")
	c.widget("latest_call", 6, 14, 88, 26)
	c.widget("recent_calls", 6, 43, 88, 46, look="Dark Glass", settings={"rows": 5})
	c.widget("accent_ticker", 0, 94, 100, 6, settings={"text": _("Your number will be called and shown here")})
	return NIGHT


def kiosk_tall(c: Canvas) -> str:
	c.box(0, 0, 100, 24, c.brand)
	c.logo(8, 5, 60, 5)
	c.text(8, 12, 84, _("Take a ticket"), 48, bold=True)
	c.widget("light_kiosk", 6, 28, 88, 60, look="Soft", settings={"heading": _("Choose a service")})
	c.text(8, 91, 84, _("Your number will be called on the screens"), 20, MUTED, align="center")
	return PAPER


def queue_strip(c: Canvas) -> str:
	c.box(0, 0, 18, 100, c.brand)
	c.logo(2, 25, 14, 50)
	c.widget("latest_call", 20, 8, 26, 84)
	c.widget("every_counter", 48, 8, 38, 84)
	c.widget("corner_clock", 88, 30, 10, 40, look="Plain")
	return NIGHT


# Boards and rooms


def status_board(c: Canvas) -> str:
	_top(c)
	c.text(5, 17, 60, _("Status"), 44, bold=True)
	c.widget("board_columns", 5, 30, 90, 62, look="Plain")
	return _fade(c.deep, NIGHT)


def status_glance(c: Canvas) -> str:
	_top(c)
	c.text(5, 17, 60, _("Status at a Glance"), 40, bold=True)
	c.widget("board_summary", 5, 30, 90, 24, look="Plain")
	c.widget("board_list", 5, 58, 90, 36, look="Dark Glass")
	return _fade(c.deep, NIGHT)


def rooms(c: Canvas) -> str:
	_top(c, INK)
	c.text(5, 17, 60, _("Rooms"), 44, INK, bold=True)
	c.widget("simple_board", 5, 30, 90, 62, look="Plain")
	return PAPER


def room_sign(c: Canvas) -> str:
	c.box(0, 0, 38, 100, c.brand)
	c.text(5, 10, 30, _("Room {0}").format(1), 48, bold=True)
	c.widget("analog_clock", 9, 34, 20, 36)
	c.text(5, 80, 30, _("Book at the front desk"), 18, SOFT)
	c.widget("door_sign", 44, 12, 50, 76, settings={"item": _("Room {0}").format(1)})
	return PAPER


def workshop(c: Canvas) -> str:
	_top(c)
	c.text(5, 17, 60, _("Workshop"), 44, bold=True)
	c.widget("board_columns", 5, 30, 90, 52, look="Plain")
	c.widget("labelled_ticker", 0, 89, 100, 11, look="Dark Glass", settings={"label": _("Notice"), "text": _("Collect your car at the front desk when it shows Ready")})
	return _fade(c.dark, NIGHT, 160)


def room_tall(c: Canvas) -> str:
	c.box(0, 0, 100, 34, c.brand)
	c.text(8, 8, 84, _("Room {0}").format(1), 56, bold=True)
	c.widget("clock_and_date", 8, 20, 50, 9, look="Plain")
	c.widget("door_sign", 8, 40, 84, 40, settings={"item": _("Room {0}").format(1)})
	c.text(8, 86, 84, _("Book at the front desk"), 22, MUTED, align="center")
	return PAPER


# Information


def schedule(c: Canvas) -> str:
	_top(c, INK)
	c.text(5, 17, 60, _("Today's Schedule"), 44, INK, bold=True)
	c.widget("day_schedule", 5, 29, 58, 64, look="Light Card", settings={"rows": _sessions(("09:00", _("Morning briefing"), _("Room 1")), ("11:00", _("Training session"), _("Hall")), ("13:00", _("Lunch"), _("Ground floor")), ("15:30", _("Workshop"), _("Room 3")), ("17:00", _("Drinks"), _("Terrace")))})
	c.widget("now_and_next", 67, 29, 28, 64, look="Accent")
	return PAPER


def directory(c: Canvas) -> str:
	c.box(0, 0, 34, 100, c.brand)
	c.logo(5, 7, 26, 8)
	c.text(5, 30, 26, _("Directory"), 48, bold=True)
	c.widget("time_and_day", 5, 62, 26, 26)
	floors = [("3", _("Meeting rooms"), "→"), ("2", _("Offices"), "→"), ("1", _("Reception and cafe"), "←"), ("0", _("Parking"), "↓")]
	for at, (level, what, way) in enumerate(floors):
		top = 10 + at * 21
		c.chip(40, top, 9, 0, level, c.pale, c.brand, 34, square=True)
		c.text(53, top + 4.5, 32, what, 30, INK, bold=True)
		c.text(86, top + 3.5, 8, way, 40, c.brand, bold=True, align="center")
	return PAPER


def directory_tall(c: Canvas) -> str:
	c.box(0, 0, 100, 18, c.brand)
	c.logo(8, 4, 50, 5)
	c.text(8, 10, 84, _("Directory"), 44, bold=True)
	floors = [("4", _("Meeting rooms")), ("3", _("Offices")), ("2", _("Training rooms")), ("1", _("Reception and cafe")), ("0", _("Parking"))]
	for at, (level, what) in enumerate(floors):
		top = 23 + at * 14
		c.card(6, top, 88, 11.5, WHITE_CARD)
		c.chip(10, top + 2.2, 13, 0, level, c.pale, c.brand, 30, square=True)
		c.text(28, top + 3.8, 62, what, 28, INK, bold=True)
	c.widget("time_and_day", 6, 93, 88, 5, look={"color": MUTED})
	return PAPER


def announcement(c: Canvas) -> str:
	_glows(c, "10")
	c.widget("tag", 6, 12, 18, 7, settings={"text": _("Announcement")}, look="Glass")
	c.text(6, 24, 46, _("Something new is coming"), 56, bold=True)
	c.text(6, 56, 44, _("Write what is changing, when, and who to ask about it."), 24, SOFT)
	c.bar(6.2, 72, 5)
	c.text(6, 75, 44, _("From Monday"), 22, WHITE, bold=True)
	c.widget("framed_picture", 56, 12, 38, 70, picture=PICTURE["dusk"])
	c.widget("news_ticker", 0, 90, 100, 10, look="Dark Glass")
	return _fade(c.brand, c.deep)


def notices_tall(c: Canvas) -> str:
	c.box(0, 0, 100, 12, c.brand)
	c.text(7, 3.5, 60, _("Notice Board"), 40, bold=True)
	c.widget("corner_clock", 66, 3.5, 28, 5, look="Plain")
	notes = [(_("Fire drill on Thursday at 11:00"), "#FEF3C7FF", "#78350FFF"), (_("New parking rules from next month"), WHITE_CARD, INK), (_("Welcome to our new team members"), c.pale, c.dark)]
	for at, (words, fill, ink) in enumerate(notes):
		top = 16 + at * 20
		c.card(6, top, 88, 17, fill)
		c.text(11, top + 5, 78, words, 30, ink, bold=True)
	c.widget("give_feedback", 34, 77, 32, 19, look="Floating")
	return PAPER


def figures(c: Canvas) -> str:
	_top(c)
	c.text(5, 17, 60, _("This Month"), 44, bold=True)
	tiles = [("128", _("Orders")), ("96%", _("On time")), ("4.8", _("Rating")), ("37", _("New customers"))]
	for at, (value, caption) in enumerate(tiles):
		left = 5 + at * 23
		c.card(left, 31, 21, 34)
		c.text(left, 36, 21, value, 60, bold=True, align="center")
		c.text(left, 54, 21, caption, 20, SOFT, align="center")
	c.widget("progress", 5, 70, 90, 14, look="Glass")
	c.widget("news_ticker", 0, 90, 100, 10, look="Dark Glass")
	return _fade(c.deep, NIGHT)


def weather(c: Canvas) -> str:
	c.text(5, 7, 60, _("Weather"), 44, bold=True)
	c.widget("date_card", 80, 5, 15, 26, look="Glass")
	c.widget("big_temperature", 5, 22, 32, 46)
	c.widget("week_list", 42, 24, 34, 46, look="Plain")
	c.widget("hourly", 5, 72, 90, 22, look="Glass")
	return _fade(c.brand, c.deep, 170)


def rates(c: Canvas) -> str:
	_top(c)
	c.text(5, 18, 60, _("Exchange Rates"), 48, bold=True)
	c.text(5, 32, 60, _("Rates are for guidance and may change during the day."), 20, FAINT)
	rates = _first("Exchange Rates")
	c.widget("one_at_a_time", 5, 42, 90, 30, look="Glass", source=rates, mapping={"text": "{line}"}, label=_("Rate"))
	c.widget("labelled_ticker", 0, 88, 100, 12, look="Band", source=rates, mapping={"text": "{line}"}, settings={"label": _("Rates")})
	return _fade(c.dark, NIGHT)


def safety(c: Canvas) -> str:
	c.box(0, 0, 100, 22, "#B91C1CFF")
	c.text(5, 6, 70, _("Safety First"), 52, bold=True)
	c.widget("corner_clock", 80, 7, 15, 9, look="Plain")
	rules = [_("Know your nearest exit"), _("Keep walkways clear"), _("Report any hazard at once"), _("Meet at the assembly point")]
	for at, rule in enumerate(rules):
		left, top = 5 + (at % 2) * 46, 30 + (at // 2) * 30
		c.card(left, top, 44, 26, WHITE_CARD)
		c.chip(left + 3, top + 6, 6, 0, str(at + 1), "#FEE2E2FF", "#B91C1CFF", 26, square=True)
		c.text(left + 12, top + 8.5, 30, rule, 26, INK, bold=True)
	c.text(5, 92, 90, _("In an emergency, call reception on 0"), 20, MUTED)
	return PAPER


def wifi(c: Canvas) -> str:
	_glows(c, "10")
	c.logo(6, 8, 26, 8)
	c.eyebrow(6, 28, 50, _("Guest Wi-Fi"))
	c.text(6, 33, 50, _("Get online"), 64, bold=True)
	c.text(6, 56, 40, _("Point your phone's camera at the code to join. No typing needed."), 24, SOFT)
	c.widget("wifi_code", 52, 22, 42, 58, look="Light Card", settings={"network": _("Guest"), "password": "welcome2025", "caption": ""})
	return _fade(c.brand, c.deep)


def hours(c: Canvas) -> str:
	_top(c, INK)
	c.text(5, 17, 50, _("Opening Hours"), 48, INK, bold=True)
	c.text(5, 29, 46, _("We look forward to seeing you."), 22, MUTED)
	c.widget("opening_hours", 5, 37, 56, 58, look=_bare(INK))
	c.card(68, 26, 27, 64, c.pale)
	c.widget("open_today", 70.5, 31, 22, 14, look="Accent Pill")
	c.widget("visit_website", 70.5, 52, 22, 34, look="Light Card", settings={"caption": _("Book online")})
	return PAPER


def news(c: Canvas) -> str:
	_top(c)
	c.widget("full_picture", 5, 20, 46, 64, picture=PICTURE["violet"], look="Rounded")
	c.eyebrow(55, 21, 40, _("Latest"))
	c.text(55, 26, 40, _("Our new branch opens next month"), 34, bold=True)
	c.text(55, 46, 40, _("Write two or three lines about the news here."), 20, SOFT)
	for at, story in enumerate((_("Team wins regional award"), _("New services from June"))):
		c.card(55, 62 + at * 12, 40, 10)
		c.text(58, 64.6 + at * 12, 34, story, 20, bold=True)
	c.widget("news_ticker", 0, 90, 100, 10, look="Dark Glass")
	return _fade(c.deep, NIGHT, 160)


def agenda_tall(c: Canvas) -> str:
	c.box(0, 0, 100, 16, c.brand)
	c.text(8, 4, 84, _("Today's Schedule"), 40, bold=True)
	c.widget("clock_and_date", 8, 10.5, 60, 4, look="Plain")
	sessions = _sessions(("09:00", _("Morning briefing"), _("Room 1")), ("10:30", _("Team stand-up"), _("Room 2")), ("12:00", _("Lunch"), _("Restaurant")), ("14:00", _("Workshop"), _("Room 3")), ("16:30", _("Review"), _("Room 1")))
	c.widget("now_and_next", 6, 19, 88, 20, look="Accent", settings={"rows": sessions})
	c.widget("day_schedule", 6, 42, 88, 54, look="Light Card", settings={"rows": sessions})
	return PAPER


# Promotion


def promotion(c: Canvas) -> str:
	c.widget("full_picture", 0, 0, 50, 100, picture=PICTURE["warm"], look="Plain")
	c.widget("tag", 56, 12, 14, 7, settings={"text": _("Offer")})
	c.text(56, 22, 38, _("Twenty percent off this week"), 44, INK, bold=True)
	c.text(56, 56, 36, _("Ask at the counter for details."), 22, MUTED)
	c.widget("price", 56, 68, 22, 14, settings={"text": "49.00", "align": "start"}, look={"color": c.brand})
	c.widget("visit_website", 80, 62, 14, 28, look="Soft")
	return CREAM


def price_list(c: Canvas) -> str:
	c.logo(6, 6, 50, 8, INK)
	c.text(6, 17, 60, _("Price List"), 50, INK, bold=True)
	items = [(_("Basic"), _("The essentials"), "25.00"), (_("Standard"), _("Most chosen"), "45.00"), (_("Premium"), _("Everything included"), "80.00"), (_("Add-on"), _("For any package"), "10.00")]
	for at, (name, about, price) in enumerate(items):
		top = 36 + at * 14
		c.text(6, top, 40, name, 30, INK, bold=True)
		c.text(6, top + 6, 40, about, 18, MUTED)
		c.text(48, top + 1, 18, price, 30, c.brand, bold=True, align="right")
		c.box(6, top + 11.5, 60, 0.3, LINE_LIGHT)
	c.box(72, 0, 28, 100, c.brand)
	c.widget("see_menu", 76, 30, 20, 34, look="Light Card")
	c.widget("corner_clock", 76, 84, 20, 9, look="Plain")
	return CREAM


def countdown(c: Canvas) -> str:
	_glows(c, "10")
	c.eyebrow(6, 12, 88, _("Coming soon"), align="center")
	c.text(6, 17, 88, _("Opening Soon"), 64, bold=True, align="center")
	c.widget("countdown", 15, 38, 70, 32, look="Dark Glass")
	c.text(6, 76, 88, _("Something new is on its way. See you there."), 24, SOFT, align="center")
	return _fade(c.brand, c.deep)


def follow_us(c: Canvas) -> str:
	c.text(6, 10, 88, _("Stay in Touch"), 60, bold=True, align="center")
	c.text(6, 26, 88, _("Scan a code with your phone's camera."), 24, SOFT, align="center")
	for at, preset in enumerate(("visit_website", "follow_us", "give_feedback")):
		c.widget(preset, 13 + at * 26, 42, 22, 38, look="Floating")
	return _fade(c.brand, c.deep)


def spotlight(c: Canvas) -> str:
	c.widget("rounded_picture", 8, 12, 30, 76, picture=PICTURE["blue"])
	c.widget("tag", 46, 16, 18, 7, settings={"text": _("Team Spotlight")}, look="Accent Pill")
	c.text(46, 28, 48, _("Name Surname"), 52, INK, bold=True)
	c.text(46, 42, 48, _("Role in the team"), 26, c.brand, bold=True)
	c.text(46, 54, 46, _("“A few words from them about what they do and what they enjoy about it.”"), 24, MUTED, italic=True)
	return PAPER


def thanks(c: Canvas) -> str:
	c.widget("rotating_messages", 6, 18, 56, 30, look="Plain")
	c.text(6, 54, 56, _("Your feedback helps us do better."), 26, SOFT)
	c.widget("give_feedback", 68, 18, 26, 46, look="Floating")
	c.widget("one_at_a_time", 0, 90, 100, 10, look="Dark Glass", settings={"text": _("Thank you for visiting")})
	return _fade(c.brand, c.deep)


def reviews(c: Canvas) -> str:
	c.eyebrow(5, 9, 90, _("Reviews"), MUTED, align="center")
	c.text(5, 14, 90, _("What our customers say"), 48, INK, bold=True, align="center")
	quotes = [(_("Friendly and quick. Will come again."), "Sara"), (_("The best service in town."), "Omar"), (_("They took care of everything."), "Lina")]
	for at, (words, who) in enumerate(quotes):
		left = 5 + at * 24.5
		c.card(left, 34, 22, 50, WHITE_CARD)
		c.text(left + 2.5, 39, 18, "★★★★★", 24, "#F59E0BFF")
		c.text(left + 2.5, 47, 18, f"“{words}”", 24, INK, bold=True)
		c.text(left + 2.5, 74, 18, f"— {who}", 18, MUTED)
	c.widget("give_feedback", 79.5, 34, 15.5, 50, look="Light Card")
	return CREAM


def promo_tall(c: Canvas) -> str:
	c.widget("full_picture", 0, 0, 100, 52, picture=PICTURE["rose"], look="Plain")
	c.widget("tag", 8, 56, 26, 3.6, settings={"text": _("This week")})
	c.text(8, 62, 84, _("Twenty percent off everything"), 52, INK, bold=True)
	c.text(8, 78, 60, _("Ask at the counter for details."), 22, MUTED)
	c.widget("price", 8, 85, 40, 7, settings={"text": "49.00", "align": "start"}, look={"color": c.brand})
	c.widget("visit_website", 64, 82, 28, 15, look="Soft")
	return CREAM


def sale_strip(c: Canvas) -> str:
	c.text(4, 18, 34, _("Sale"), 120, bold=True)
	c.text(34, 22, 36, _("Up to fifty percent off selected items"), 36, bold=True)
	c.text(34, 62, 36, _("While stocks last"), 24, SOFT)
	c.widget("qr_beside", 72, 18, 25, 64, look="Light Card", settings={"caption": _("See all offers")})
	return _fade(c.brand, c.dark, 90)


# Shops


def store_welcome(c: Canvas) -> str:
	c.picture(0, 0, 100, 100, PICTURE["sand"])
	c.box(0, 0, 100, 100, "#0B0D1066")
	c.logo(6, 8, 26, 8)
	c.text(6, 30, 60, _("Come on in"), 80, bold=True)
	c.text(6, 54, 50, _("New season styles are here. Take a look around."), 26, SOFT)
	c.card(6, 70, 34, 18, "#FFFFFF26")
	c.text(9, 73, 30, _("Open today"), 18, SOFT)
	c.text(9, 78, 30, "09:00 – 21:00", 30, bold=True)
	c.widget("follow_us", 80, 62, 14, 28, look="Light Card")
	return NIGHT


def sale(c: Canvas) -> str:
	_glows(c, "12")
	c.eyebrow(6, 14, 60, _("Limited time"))
	c.text(6, 19, 60, _("Sale"), 150, bold=True)
	c.text(6, 58, 50, _("Up to fifty percent off selected items"), 34, bold=True)
	c.text(6, 74, 50, _("Until Sunday, in store and online"), 22, SOFT)
	c.widget("visit_website", 72, 30, 22, 40, look="Light Card", settings={"caption": _("See all offers")})
	return _fade(c.brand, c.dark, 120)


def new_arrival(c: Canvas) -> str:
	c.picture(0, 0, 100, 100, PICTURE["violet"])
	c.box(0, 68, 100, 32, "#0B0D10CC")
	c.widget("tag", 5, 73, 14, 6.5, settings={"text": _("New in")}, look="Accent Pill")
	c.text(5, 82, 60, _("The new collection"), 40, bold=True)
	c.widget("price", 66, 76, 16, 12, settings={"text": "89.00", "align": "end"})
	c.widget("visit_website", 85, 72, 10, 24, look="Light Card", settings={"caption": ""})
	return NIGHT


def product_feature(c: Canvas) -> str:
	c.widget("rounded_picture", 6, 10, 40, 80, picture=PICTURE["green"])
	c.eyebrow(52, 14, 42, _("Featured"), MUTED)
	c.text(52, 19, 42, _("Product name"), 52, INK, bold=True)
	for at, point in enumerate((_("Made to last"), _("Two-year guarantee"), _("Free delivery"))):
		c.chip(52, 40 + at * 10, 3.6, 0, "✓", c.pale, c.brand, 18, square=True)
		c.text(57, 41 + at * 10, 36, point, 24, INK)
	c.widget("price", 52, 72, 22, 14, settings={"text": "129.00", "align": "start"}, look={"color": c.brand})
	c.widget("qr_beside", 74, 74, 22, 12, look="Soft", settings={"caption": _("Buy online")})
	return PAPER


def loyalty(c: Canvas) -> str:
	c.eyebrow(6, 12, 50, _("Rewards"), MUTED)
	c.text(6, 17, 50, _("Join and earn on every visit"), 48, INK, bold=True)
	steps = [_("Scan the code"), _("Sign up in a minute"), _("Earn points each time you buy")]
	for at, step in enumerate(steps):
		top = 46 + at * 14
		c.chip(6, top, 5, 0, str(at + 1), c.brand, WHITE, 24, square=True)
		c.text(13, top + 2.2, 40, step, 26, INK, bold=True)
	c.card(62, 14, 32, 72, c.pale)
	c.widget("follow_us", 66, 22, 24, 44, look="Light Card", settings={"caption": _("Join now")})
	c.text(62, 72, 32, _("It is free"), 24, c.dark, bold=True, align="center")
	return PAPER


def click_collect(c: Canvas) -> str:
	_top(c)
	c.text(5, 17, 50, _("Click and Collect"), 44, bold=True)
	c.text(5, 28, 44, _("Orders ready to collect at the desk"), 22, SOFT)
	c.widget("latest_call", 5, 38, 42, 50, settings={"heading": _("Ready")})
	c.widget("recent_calls", 51, 20, 44, 68, look="Dark Glass", settings={"rows": 6, "heading": _("Also ready")})
	return _fade(c.deep, NIGHT, 160)


# Food and drink


def menu_board(c: Canvas) -> str:
	c.logo(4, 6, 24, 8)
	c.widget("corner_clock", 81, 5, 15, 9, look="Plain")
	columns = [
		(_("Breakfast"), [(_("Eggs your way"), "28"), (_("Pancakes"), "32"), (_("Granola bowl"), "26")]),
		(_("Lunch"), [(_("Grilled chicken"), "48"), (_("Pasta of the day"), "42"), (_("Garden salad"), "34")]),
		(_("Drinks"), [(_("Fresh juice"), "18"), (_("Coffee"), "14"), (_("Mint tea"), "12")]),
	]
	for at, (title, dishes) in enumerate(columns):
		left = 4 + at * 32
		c.text(left, 20, 28, title, 34, c.bright, bold=True)
		c.bar(left + 0.2, 31, 4)
		for row, (dish, price) in enumerate(dishes):
			top = 36 + row * 15
			c.text(left, top, 22, dish, 24, bold=True)
			c.text(left + 20, top, 8, price, 24, SOFT, align="right")
			c.box(left, top + 9, 28, 0.25, LINE_DARK)
	c.widget("labelled_ticker", 0, 89, 100, 11, look="Dark Glass", settings={"label": _("Today"), "text": _("Ask about today's special")})
	return "#1C1917FF"


def menu_tall(c: Canvas) -> str:
	c.logo(8, 4, 50, 5)
	c.text(8, 11, 84, _("Menu"), 64, bold=True)
	c.widget("corner_clock", 62, 4, 30, 5, look="Plain")
	c.bar(8.4, 18.5, 10)
	dishes = [(_("Grilled chicken"), _("With rice and salad"), "48"), (_("Pasta of the day"), _("Ask us what it is"), "42"), (_("Garden salad"), _("Fresh from the market"), "34"), (_("Fresh juice"), _("Orange, mango or mixed"), "18"), (_("Coffee"), _("Espresso, latte or flat white"), "14")]
	for at, (dish, about, price) in enumerate(dishes):
		top = 23 + at * 14
		c.text(8, top, 64, dish, 30, bold=True)
		c.text(8, top + 4.2, 64, about, 20, FAINT)
		c.text(72, top, 20, price, 30, WHITE, bold=True, align="right")
		c.box(8, top + 10, 84, 0.15, LINE_DARK)
	return "#1C1917FF"


def daily_special(c: Canvas) -> str:
	c.widget("full_picture", 0, 0, 55, 100, picture=PICTURE["warm"], look="Plain")
	c.eyebrow(60, 16, 34, _("Today's special"), MUTED)
	c.text(60, 21, 34, _("Slow-cooked lamb with rice"), 44, INK, bold=True)
	c.text(60, 46, 34, _("Served with salad and fresh bread."), 22, MUTED)
	c.chip(60, 62, 18, 12, "65", c.brand, WHITE, 40)
	c.widget("see_menu", 82, 60, 12, 26, look="Soft", settings={"caption": ""})
	return CREAM


def coffee_menu(c: Canvas) -> str:
	c.text(5, 8, 60, _("Coffee"), 56, INK, bold=True)
	c.widget("corner_clock", 80, 7, 15, 9, look={"fillColor": "#1118270F", "color": INK})
	for at, size in enumerate((_("Small"), _("Medium"), _("Large"))):
		c.text(56 + at * 13, 24, 12, size, 18, MUTED, bold=True, align="center")
	drinks = [(_("Espresso"), ("10", "12", "14")), (_("Cappuccino"), ("14", "16", "18")), (_("Latte"), ("14", "16", "18")), (_("Flat white"), ("15", "17", "19")), (_("Hot chocolate"), ("13", "15", "17"))]
	for at, (drink, prices) in enumerate(drinks):
		top = 31 + at * 12
		c.text(5, top, 46, drink, 28, INK, bold=True)
		for i, price in enumerate(prices):
			c.text(56 + i * 13, top, 12, price, 28, c.brand, bold=True, align="center")
		c.box(5, top + 9, 90, 0.25, LINE_LIGHT)
	c.text(5, 93, 90, _("Oat or almond milk on request"), 18, MUTED)
	return CREAM


def order_ready(c: Canvas) -> str:
	c.box(0, 0, 50, 100, c.brand)
	c.eyebrow(6, 10, 40, _("Ready to collect"))
	c.widget("latest_call", 6, 18, 38, 50, look="Plain", settings={"heading": ""})
	c.text(6, 76, 38, _("Collect your order at the counter"), 24, SOFT)
	c.eyebrow(56, 10, 38, _("Being prepared"), MUTED)
	c.widget("recent_calls", 56, 18, 38, 72, look=_bare(INK), settings={"rows": 6, "heading": ""})
	return PAPER


def happy_hour(c: Canvas) -> str:
	_glows(c, "12")
	c.eyebrow(6, 16, 60, _("Every day"))
	c.text(6, 21, 60, _("Happy Hour"), 88, bold=True)
	c.text(6, 50, 60, "17:00 – 19:00", 44, bold=True)
	c.text(6, 64, 56, _("Two drinks for the price of one"), 28, SOFT)
	c.widget("countdown", 64, 24, 30, 26, look="Dark Glass")
	c.widget("see_menu", 72, 56, 14, 30, look="Light Card")
	return _fade("#7C2D12FF", "#1C1917FF", 135)


# Clinics and care


def clinic_waiting(c: Canvas) -> str:
	_top(c, INK)
	c.text(5, 17, 50, _("Welcome to the clinic"), 44, INK, bold=True)
	c.widget("one_counter", 5, 29, 42, 60, look="Accent", settings={"counter": "1", "heading": _("Now seeing")})
	c.widget("recent_calls", 51, 29, 44, 44, look="Card", settings={"rows": 3, "heading": ""})
	c.card(51, 76, 44, 13, c.pale)
	c.text(54, 78.5, 38, _("Average wait today: about 15 minutes"), 22, c.dark, bold=True)
	c.widget("labelled_ticker", 0, 93, 100, 7, look="Band", settings={"label": _("Health tip"), "text": _("Drink water through the day")})
	return PAPER


def pharmacy(c: Canvas) -> str:
	c.box(0, 0, 100, 16, "#047857FF")
	c.text(5, 4, 60, _("Pharmacy"), 44, bold=True)
	c.widget("corner_clock", 80, 4, 15, 8, look="Plain")
	c.widget("latest_call", 5, 22, 42, 52, look="Card", settings={"heading": _("Ready")})
	c.widget("recent_calls", 51, 22, 44, 52, look="Card", settings={"rows": 5})
	c.text(5, 80, 90, _("Bring your ticket to the counter. Ask us anything about your medicine."), 22, MUTED)
	return PAPER


def health_tips_tall(c: Canvas) -> str:
	c.box(0, 0, 100, 18, "#0F766EFF")
	c.text(8, 5, 84, _("Stay Well"), 52, bold=True)
	tips = [_("Wash your hands often"), _("Drink water through the day"), _("Walk for thirty minutes"), _("Get enough sleep")]
	for at, tip in enumerate(tips):
		top = 23 + at * 17
		c.card(6, top, 88, 14, WHITE_CARD)
		c.chip(10, top + 3, 12, 0, str(at + 1), "#CCFBF1FF", "#0F766EFF", 30, square=True)
		c.text(27, top + 4.6, 64, tip, 28, INK, bold=True)
	c.widget("time_and_day", 6, 93, 88, 5, look={"color": MUTED})
	return PAPER


def on_duty(c: Canvas) -> str:
	_top(c, INK)
	c.text(5, 17, 60, _("On duty today"), 44, INK, bold=True)
	people = [(_("Dr Name Surname"), _("General practice"), _("Room 1")), (_("Dr Name Surname"), _("Children's health"), _("Room 2")), (_("Dr Name Surname"), _("Dentistry"), _("Room 3"))]
	for at, (who, what, where) in enumerate(people):
		top = 31 + at * 20
		c.card(5, top, 90, 17, WHITE_CARD)
		c.chip(8, top + 3.4, 6, 0, "+", c.pale, c.brand, 30, square=True)
		c.text(17, top + 3.4, 50, who, 28, INK, bold=True)
		c.text(17, top + 9.4, 50, what, 20, MUTED)
		c.text(70, top + 5.6, 22, where, 24, c.brand, bold=True, align="right")
	return PAPER


# Offices


def office_dashboard(c: Canvas) -> str:
	_top(c)
	c.text(5, 17, 60, _("This Week"), 44, bold=True)
	tiles = [("24", _("Projects running")), ("8", _("Due this week")), ("98%", _("On time"))]
	for at, (value, caption) in enumerate(tiles):
		left = 5 + at * 20
		c.card(left, 30, 18, 30)
		c.text(left, 34, 18, value, 52, bold=True, align="center")
		c.text(left, 50, 18, caption, 18, SOFT, align="center")
	c.widget("board_summary", 66, 30, 29, 30, look="Dark Glass")
	c.widget("progress", 5, 66, 90, 14, look="Glass")
	c.widget("news_ticker", 0, 89, 100, 11, look="Dark Glass")
	return _fade(c.deep, NIGHT)


def celebrations(c: Canvas) -> str:
	_glows(c, "12")
	c.widget("corner_clock", 80, 5, 15, 9)
	c.eyebrow(6, 10, 88, _("This month"), align="center")
	c.text(6, 15, 88, _("Celebrations"), 60, bold=True, align="center")
	people = [(_("Name Surname"), _("Birthday on the 4th")), (_("Name Surname"), _("Five years with us")), (_("Name Surname"), _("Birthday on the 21st"))]
	for at, (who, why) in enumerate(people):
		left = 6 + at * 30
		c.card(left, 38, 28, 42)
		c.chip(left + 9, 42, 10, 0, "★", WHITE, c.brand, 30, square=True)
		c.text(left + 1, 62, 26, who, 26, bold=True, align="center")
		c.text(left + 1, 70, 26, why, 20, SOFT, align="center")
	return _fade(c.brand, c.deep)


def meeting_rooms_tall(c: Canvas) -> str:
	c.box(0, 0, 100, 16, c.brand)
	c.text(8, 4, 84, _("Meeting Rooms"), 40, bold=True)
	c.widget("clock_and_date", 8, 10.5, 60, 4, look="Plain")
	c.widget("board_list", 6, 20, 88, 66, look="Card")
	c.text(8, 90, 84, _("Book a room at the front desk"), 22, MUTED, align="center")
	return PAPER


def town_hall(c: Canvas) -> str:
	_glows(c)
	c.widget("date_card", 6, 12, 18, 36, look="Glass")
	c.eyebrow(30, 14, 60, _("All hands"))
	c.text(30, 19, 60, _("Quarterly town hall"), 52, bold=True)
	c.text(30, 42, 56, _("Hear the plan for the next quarter and ask your questions."), 24, SOFT)
	for at, (label, value) in enumerate(((_("When"), "15:00"), (_("Where"), _("Main hall")))):
		c.card(30 + at * 22, 60, 20, 18)
		c.text(32 + at * 22, 62.5, 16, label, 18, FAINT)
		c.text(32 + at * 22, 67.5, 16, value, 28, bold=True)
	c.widget("visit_website", 78, 56, 16, 30, look="Light Card", settings={"caption": _("Join online")})
	return _fade(c.brand, c.deep)


def guest_welcome(c: Canvas) -> str:
	c.logo(6, 8, 26, 8, INK)
	c.eyebrow(6, 34, 88, _("A warm welcome to"), MUTED)
	c.text(6, 39, 88, _("Our Guests Today"), 80, INK, bold=True)
	c.bar(6.2, 66, 6)
	c.text(6, 70, 70, _("We are delighted to have you with us."), 28, MUTED)
	c.widget("clock_and_date", 70, 78, 24, 16, look=_bare(INK))
	return PAPER


# Events


def event_welcome(c: Canvas) -> str:
	_glows(c, "12")
	c.widget("tag", 6, 12, 18, 7, settings={"text": _("Welcome")}, look="Glass")
	c.text(6, 23, 58, _("Annual Conference"), 64, bold=True)
	c.text(6, 55, 56, _("Two days of talks, workshops and good company"), 26, SOFT)
	c.bar(6.2, 70, 5)
	c.text(6, 73, 50, "#OurEvent", 26, bold=True)
	c.widget("time_and_day", 70, 12, 24, 30, look="Glass")
	c.widget("qr_beside", 66, 62, 28, 18, look="Light Card", settings={"caption": _("See the agenda")})
	return _fade(c.brand, c.deep, 145)


def event_agenda(c: Canvas) -> str:
	_top(c)
	c.text(5, 17, 60, _("Agenda"), 44, bold=True)
	sessions = _sessions(("09:30", _("Opening words"), _("Main hall")), ("10:15", _("Keynote"), _("Main hall")), ("11:30", _("Workshops"), _("Rooms 1 to 4")), ("13:00", _("Lunch"), _("Terrace")), ("14:30", _("Panel discussion"), _("Main hall")))
	c.widget("day_schedule", 5, 29, 60, 64, look="Plain", settings={"rows": sessions})
	c.widget("now_and_next", 69, 29, 26, 64, look="Glass", settings={"rows": sessions})
	return _fade(c.deep, NIGHT, 160)


def speaker(c: Canvas) -> str:
	c.widget("rounded_picture", 6, 12, 32, 76, picture=PICTURE["mono"])
	c.widget("tag", 44, 14, 16, 7, settings={"text": _("Up next")}, look="Accent Pill")
	c.text(44, 25, 50, _("Name Surname"), 56, bold=True)
	c.text(44, 41, 50, _("Title of the talk goes here"), 30, SOFT)
	for at, (label, value) in enumerate(((_("Starts"), "10:15"), (_("Where"), _("Main hall")))):
		c.card(44 + at * 22, 60, 20, 18)
		c.text(46 + at * 22, 62.5, 16, label, 18, FAINT)
		c.text(46 + at * 22, 67.5, 16, value, 28, bold=True)
	return _fade(c.deep, NIGHT, 145)


def sponsors(c: Canvas) -> str:
	c.widget("corner_clock", 80, 5, 15, 9, look={"fillColor": "#1118270F", "color": INK})
	c.eyebrow(5, 10, 90, _("With thanks"), MUTED, align="center")
	c.text(5, 15, 90, _("Our Sponsors"), 52, INK, bold=True, align="center")
	for at in range(6):
		left, top = 8 + (at % 3) * 29, 36 + (at // 3) * 26
		c.card(left, top, 26, 22, WHITE_CARD)
		c.text(left, top + 8, 26, _("Sponsor {0}").format(at + 1), 24, MUTED, bold=True, align="center")
	return PAPER


def event_tall(c: Canvas) -> str:
	c.box(-30, -8, 110, 0, "#FFFFFF14", shape="oval", square=True)
	c.widget("tag", 8, 8, 40, 5.5, settings={"text": _("Save the date")}, look="Glass")
	c.text(8, 16, 84, _("Annual Conference"), 64, bold=True)
	c.widget("date_card", 8, 38, 40, 18, look="Glass")
	c.text(52, 40, 40, "09:30", 44, bold=True)
	c.text(52, 47, 40, _("Main hall"), 24, SOFT)
	c.text(8, 62, 84, _("Two days of talks, workshops and good company"), 28, SOFT)
	c.widget("visit_website", 30, 76, 40, 19, look="Light Card", settings={"caption": _("Register here")})
	return _fade(c.brand, c.deep, 170)


# Schools and training


def timetable(c: Canvas) -> str:
	_top(c, INK)
	c.text(5, 17, 50, _("Timetable"), 44, INK, bold=True)
	rooms_ = [_("Room 1"), _("Room 2"), _("Room 3")]
	for at, room in enumerate(rooms_):
		c.text(25 + at * 24, 31, 22, room, 20, MUTED, bold=True, align="center")
	periods = [("08:00", (_("Maths"), _("English"), _("Science"))), ("09:00", (_("History"), _("Maths"), _("Art"))), ("10:30", (_("Science"), _("Music"), _("English"))), ("11:30", (_("Sport"), _("Science"), _("Maths")))]
	for row, (when, subjects) in enumerate(periods):
		top = 37 + row * 14
		c.text(5, top + 3, 16, when, 24, c.brand, bold=True)
		for at, subject in enumerate(subjects):
			c.chip(25 + at * 24, top, 22, 11, subject, WHITE_CARD if (row + at) % 2 else c.pale, INK, 22)
	return PAPER


def campus_news(c: Canvas) -> str:
	_top(c)
	c.text(5, 17, 60, _("Campus News"), 44, bold=True)
	stories = [(_("Open day on Saturday"), _("Families welcome from ten")), (_("Library hours extended"), _("Open until eight during exams")), (_("Science fair winners"), _("See the projects in the hall"))]
	pictures = (PICTURE["green"], PICTURE["blue"], PICTURE["sand"])
	for at, (title, about) in enumerate(stories):
		left = 5 + at * 31
		c.widget("framed_picture", left, 30, 28, 34, picture=pictures[at], look="Rounded")
		c.text(left, 67, 28, title, 22, bold=True)
		c.text(left, 77, 28, about, 18, SOFT)
	c.widget("news_ticker", 0, 90, 100, 10, look="Dark Glass")
	return _fade(c.deep, NIGHT, 160)


def exams(c: Canvas) -> str:
	c.eyebrow(6, 12, 50, _("Exams start in"), MUTED)
	c.widget("countdown", 6, 18, 52, 30, look="Card")
	c.text(6, 54, 50, _("Before you come"), 30, INK, bold=True)
	for at, rule in enumerate((_("Bring your student card"), _("Phones off and in your bag"), _("Arrive fifteen minutes early"))):
		c.chip(6, 62 + at * 9, 3.4, 0, "✓", c.pale, c.brand, 16, square=True)
		c.text(11, 63 + at * 9, 44, rule, 22, INK)
	c.widget("rounded_picture", 64, 10, 30, 80, picture=PICTURE["ocean"])
	return PAPER


# Over slides


def sidebar(c: Canvas) -> str:
	c.box(72, 0, 28, 100, NIGHT)
	c.logo(75, 5, 22, 8)
	c.widget("time_and_day", 75, 20, 22, 18, look="Plain")
	c.widget("week_list", 75, 40, 22, 28, look="Dark Glass", settings={"days": 3})
	c.widget("visit_website", 79, 70, 14, 26, look="Light Card")
	return NIGHT


def lower_third(c: Canvas) -> str:
	c.box(0, 82, 100, 18, NIGHT)
	c.box(0, 82, 1, 18, c.brand, layer=2)
	c.logo(3, 85, 22, 12)
	c.widget("labelled_ticker", 26, 85, 57, 12, look="Plain")
	c.widget("corner_clock", 85, 85, 12, 12, look="Accent Pill")
	return NIGHT


def top_bar(c: Canvas) -> str:
	c.box(0, 0, 100, 11, NIGHT)
	c.logo(2, 2, 18, 7)
	c.widget("one_at_a_time", 22, 1.5, 58, 8, look="Plain", settings={"text": _("Welcome to our visitors today")})
	c.widget("corner_clock", 84, 1.5, 14, 8, look="Accent Pill")
	return NIGHT


def corner_bug(c: Canvas) -> str:
	c.card(72, 4, 24, 26, "#0B0D10B3")
	c.logo(74, 7, 20, 9)
	c.widget("corner_clock", 74, 18, 20, 9, look="Plain")
	return NIGHT


def banner_ticker(c: Canvas) -> str:
	c.box(0, 0, 14, 100, c.brand)
	c.logo(1.5, 20, 11, 60)
	c.widget("news_ticker", 14, 30, 74, 40, look="Plain", settings={"text": _("Welcome to our visitors today")})
	c.widget("corner_clock", 89, 25, 10, 50, look="Plain")
	return NIGHT


#: key: (builder, shape, group, name, what it is for)
STARTERS = {
	"welcome": (welcome, "wide", "welcome", _lt("Welcome"), _lt("A greeting with the time, the weather and a ticker.")),
	"welcome_split": (welcome_split, "wide", "welcome", _lt("Welcome, Light"), _lt("A greeting beside a large picture, on white.")),
	"lobby": (lobby, "wide", "welcome", _lt("Lobby"), _lt("A large picture beside today's news and the weather.")),
	"clock_weather": (clock_weather, "wide", "welcome", _lt("Clock and Weather"), _lt("The time and the week's weather, large.")),
	"time_only": (time_only, "wide", "welcome", _lt("Time"), _lt("Just the time, very large.")),
	"welcome_tall": (welcome_tall, "tall", "welcome", _lt("Welcome, Standing"), _lt("A greeting for a screen on its side.")),
	"reception_tall": (reception_tall, "tall", "welcome", _lt("Reception"), _lt("The time and a code to sign in, for a reception desk.")),
	"banner": (banner, "strip", "welcome", _lt("Welcome Strip"), _lt("A greeting and the time across a long screen.")),
	"now_serving": (now_serving, "wide", "queues", _lt("Now Serving"), _lt("The queue, how it works, and a feedback code.")),
	"queue_full": (queue_full, "wide", "queues", _lt("Queue, Full Screen"), _lt("Only the queue, as large as it goes.")),
	"counter": (counter, "wide", "queues", _lt("Counter"), _lt("The ticket one counter is serving, for above it.")),
	"every_counter": (every_counter, "wide", "queues", _lt("Every Counter"), _lt("What each counter is serving, and the latest call large.")),
	"waiting_room": (waiting_room, "wide", "queues", _lt("Waiting Room"), _lt("The latest call large and the calls before it.")),
	"queue_offers": (queue_offers, "wide", "queues", _lt("Queue with an Offer"), _lt("The queue beside a picture and an offer.")),
	"kiosk_wide": (kiosk_wide, "wide", "queues", _lt("Ticket Kiosk, Wide"), _lt("Buttons that issue a ticket, on a wide touch screen.")),
	"queue_tall": (queue_tall, "tall", "queues", _lt("Queue, Standing"), _lt("The queue on a screen on its side.")),
	"kiosk_tall": (kiosk_tall, "tall", "queues", _lt("Ticket Kiosk"), _lt("Buttons that issue a ticket, for a touch screen.")),
	"queue_strip": (queue_strip, "strip", "queues", _lt("Queue Strip"), _lt("The latest call and every counter across a long screen.")),
	"status_board": (status_board, "wide", "boards", _lt("Status Board"), _lt("Every item on a board in columns.")),
	"status_glance": (status_glance, "wide", "boards", _lt("Status at a Glance"), _lt("How many items are in each state, and every item below.")),
	"rooms": (rooms, "wide", "boards", _lt("Rooms"), _lt("Which rooms are free and which are in use.")),
	"room_sign": (room_sign, "wide", "boards", _lt("Room Sign"), _lt("One room's state, for beside its door.")),
	"workshop": (workshop, "wide", "boards", _lt("Workshop"), _lt("Every job in columns, with a notice along the foot.")),
	"room_tall": (room_tall, "tall", "boards", _lt("Room Sign, Standing"), _lt("One room's state on a screen on its side.")),
	"schedule": (schedule, "wide", "information", _lt("Today's Schedule"), _lt("What happens today, when and where.")),
	"directory": (directory, "wide", "information", _lt("Directory"), _lt("Where everything is, floor by floor.")),
	"announcement": (announcement, "wide", "information", _lt("Announcement"), _lt("One piece of news with a picture.")),
	"news": (news, "wide", "information", _lt("News"), _lt("A main story with a picture and two short ones.")),
	"figures": (figures, "wide", "information", _lt("Figures"), _lt("Four figures and progress to a goal.")),
	"weather": (weather, "wide", "information", _lt("Weather"), _lt("The temperature large, the week and the next hours.")),
	"rates": (rates, "wide", "information", _lt("Exchange Rates"), _lt("Rates from an Exchange Rates source, with the time.")),
	"hours": (hours, "wide", "information", _lt("Opening Hours"), _lt("When you are open, day by day.")),
	"wifi": (wifi, "wide", "information", _lt("Guest Wi-Fi"), _lt("The network, its password and a code to join.")),
	"safety": (safety, "wide", "information", _lt("Safety"), _lt("Four safety rules and who to call.")),
	"notices_tall": (notices_tall, "tall", "information", _lt("Notice Board"), _lt("Several notices on a screen on its side.")),
	"directory_tall": (directory_tall, "tall", "information", _lt("Directory, Standing"), _lt("Where everything is, for a screen on its side.")),
	"agenda_tall": (agenda_tall, "tall", "information", _lt("Schedule, Standing"), _lt("Today's schedule on a screen on its side.")),
	"promotion": (promotion, "wide", "promotion", _lt("Offer"), _lt("A picture, an offer, its price and a code.")),
	"price_list": (price_list, "wide", "promotion", _lt("Price List"), _lt("Items and prices with a code to see more.")),
	"countdown": (countdown, "wide", "promotion", _lt("Countdown"), _lt("Days, hours and minutes to an opening or an event.")),
	"follow_us": (follow_us, "wide", "promotion", _lt("Stay in Touch"), _lt("Codes for your website, social pages and feedback.")),
	"reviews": (reviews, "wide", "promotion", _lt("Reviews"), _lt("Three things your customers said.")),
	"spotlight": (spotlight, "wide", "promotion", _lt("Team Spotlight"), _lt("A picture of someone and a few words about them.")),
	"thanks": (thanks, "wide", "promotion", _lt("Feedback"), _lt("Messages that change, and a code to give feedback.")),
	"promo_tall": (promo_tall, "tall", "promotion", _lt("Offer, Standing"), _lt("A picture, an offer and a code on a screen on its side.")),
	"sale_strip": (sale_strip, "strip", "promotion", _lt("Sale Strip"), _lt("A sale and a code across a long screen.")),
	"store_welcome": (store_welcome, "wide", "retail", _lt("Shop Welcome"), _lt("A picture behind a greeting and today's hours.")),
	"sale": (sale, "wide", "retail", _lt("Sale"), _lt("A sale in large letters, with a code.")),
	"new_arrival": (new_arrival, "wide", "retail", _lt("New In"), _lt("A full picture with the new collection and its price.")),
	"product_feature": (product_feature, "wide", "retail", _lt("Product"), _lt("One product, three reasons to buy it, and its price.")),
	"loyalty": (loyalty, "wide", "retail", _lt("Rewards"), _lt("How to join your rewards, in three steps.")),
	"click_collect": (click_collect, "wide", "retail", _lt("Click and Collect"), _lt("Orders ready to collect, from a queue.")),
	"menu_board": (menu_board, "wide", "food", _lt("Menu Board"), _lt("Three columns of dishes and prices.")),
	"daily_special": (daily_special, "wide", "food", _lt("Today's Special"), _lt("One dish with a picture and its price.")),
	"coffee_menu": (coffee_menu, "wide", "food", _lt("Coffee Menu"), _lt("Drinks with a price for each size.")),
	"order_ready": (order_ready, "wide", "food", _lt("Orders Ready"), _lt("The order ready to collect and those being prepared.")),
	"happy_hour": (happy_hour, "wide", "food", _lt("Happy Hour"), _lt("A time-limited offer with a countdown.")),
	"menu_tall": (menu_tall, "tall", "food", _lt("Menu, Standing"), _lt("Dishes and prices on a screen on its side.")),
	"clinic_waiting": (clinic_waiting, "wide", "health", _lt("Clinic Waiting Room"), _lt("Who is being seen, the wait, and a health tip.")),
	"pharmacy": (pharmacy, "wide", "health", _lt("Pharmacy"), _lt("Prescriptions ready to collect, from a queue.")),
	"on_duty": (on_duty, "wide", "health", _lt("On Duty Today"), _lt("Who is working today and in which room.")),
	"health_tips_tall": (health_tips_tall, "tall", "health", _lt("Health Tips"), _lt("Four tips on a screen on its side.")),
	"office_dashboard": (office_dashboard, "wide", "office", _lt("Team Dashboard"), _lt("This week's figures, a board and progress to a goal.")),
	"celebrations": (celebrations, "wide", "office", _lt("Celebrations"), _lt("Birthdays and anniversaries this month.")),
	"town_hall": (town_hall, "wide", "office", _lt("Town Hall"), _lt("An all-hands meeting: when, where and a link to join.")),
	"guest_welcome": (guest_welcome, "wide", "office", _lt("Guest Welcome"), _lt("A welcome for visitors, in large letters.")),
	"meeting_rooms_tall": (meeting_rooms_tall, "tall", "office", _lt("Meeting Rooms"), _lt("Every room's state on a screen on its side.")),
	"event_welcome": (event_welcome, "wide", "events", _lt("Event Welcome"), _lt("The event's name, the time and a code for the agenda.")),
	"event_agenda": (event_agenda, "wide", "events", _lt("Agenda"), _lt("The day's sessions, the next one marked.")),
	"speaker": (speaker, "wide", "events", _lt("Up Next"), _lt("The next speaker, their talk, when and where.")),
	"sponsors": (sponsors, "wide", "events", _lt("Sponsors"), _lt("Six places for your sponsors' logos.")),
	"event_tall": (event_tall, "tall", "events", _lt("Event Poster"), _lt("An event's date, place and a code to register.")),
	"timetable": (timetable, "wide", "education", _lt("Timetable"), _lt("Lessons by time and room.")),
	"campus_news": (campus_news, "wide", "education", _lt("Campus News"), _lt("Three stories with pictures.")),
	"exams": (exams, "wide", "education", _lt("Exams"), _lt("A countdown to exams and what to bring.")),
	"sidebar": (sidebar, "wide", "over_slides", _lt("Sidebar"), _lt("The time, the weather and a code beside the slides.")),
	"lower_third": (lower_third, "wide", "over_slides", _lt("Lower Third"), _lt("A ticker and the time along the foot of the slides.")),
	"top_bar": (top_bar, "wide", "over_slides", _lt("Top Bar"), _lt("Your logo, a message and the time above the slides.")),
	"corner_bug": (corner_bug, "wide", "over_slides", _lt("Corner"), _lt("Your logo and the time in one corner of the slides.")),
	"banner_ticker": (banner_ticker, "strip", "over_slides", _lt("Ticker Strip"), _lt("A ticker across a long screen, with the time.")),
}


def _first(kind: str) -> str:
	found = frappe.get_list("Display Source", filters={"kind": kind}, pluck="name", order_by="creation asc", limit=1)
	return found[0] if found else ""


def build(key: str, wide: int, high: int, brand: dict | None = None, company: str = "") -> dict:
	"""A starter on a frame: its background and its elements, widgets among them."""
	from onedesk.one_slide import decks

	builder = STARTERS[key][0]
	canvas = Canvas(wide, high, brand or decks.brand(), company or frappe.defaults.get_global_default("company") or "")
	return canvas.drawn(builder(canvas))


@frappe.whitelist()
@frappe.read_only()
def offered(collection: Annotated[str, "The widget collection."]) -> dict:
	"""The starters for a collection's shape first, then the rest, by group."""
	doc = frappe.get_doc("Widget Collection", collection)
	doc.check_permission("read")
	shape = shape_of(*sizes.editor(doc))
	return {
		"shape": shape,
		"groups": [{"key": key, "label": str(label)} for key, label in GROUPS.items()],
		"starters": [
			{"key": key, "group": group, "label": str(name), "about": str(about), "shape": fits, "picture": f"/assets/onedesk/images/one_display/starters/{key}.jpg"}
			for key, (_builder, fits, group, name, about) in STARTERS.items()
		],
	}


@frappe.whitelist()
def made(collection: Annotated[str, "The widget collection."], starter: Annotated[str, "A starter's key."]) -> dict:
	"""A starter laid out on a collection's frame, for the editor to put on its canvas."""
	doc = frappe.get_doc("Widget Collection", collection)
	doc.check_permission("write")
	if starter not in STARTERS:
		frappe.throw(_("Choose a template from the list."))
	return build(starter, *sizes.editor(doc))


def apply(collection: str, starter: str) -> None:
	"""Put a starter on a collection and save it, as the editor would: its
	backdrop slide takes the words and shapes, its rows the widgets."""
	import json

	from onedesk.one_slide import api

	doc = frappe.get_doc("Widget Collection", collection)
	doc.check_permission("write")
	name = screen.backdrop(collection)["presentation"]
	held = frappe.get_doc(api.PRESENTATION, name)
	built = build(starter, *sizes.editor(doc))
	first = held.slides[0].client_id if held.slides else uuid.uuid4().hex[:10]
	api.save_slides(name, [{"client_id": first, "background": built["background"], "elements": json.dumps(built["elements"])}], str(held.modified))


@frappe.whitelist(methods=["POST"])
def for_channel(channel: Annotated[str, "The display channel."]) -> dict:
	"""A channel's layout, made empty the first time, for the editor to open
	on its templates."""
	doc = frappe.get_doc("Display Channel", channel)
	doc.check_permission("write")
	if not doc.widget_collection:
		named, count = doc.channel_name or doc.name, 1
		while frappe.db.exists("Widget Collection", named):
			count += 1
			named = f"{doc.channel_name or doc.name} {count}"
		made = frappe.get_doc(
			{
				"doctype": "Widget Collection",
				"collection_name": named,
				"screen_size": doc.screen_size or "Landscape",
				"width": doc.width,
				"height": doc.height,
			}
		).insert()
		doc.db_set("widget_collection", made.name)
	return screen.backdrop(doc.widget_collection)
