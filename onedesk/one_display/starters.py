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
PICTURES = tuple(f"/assets/onedesk/images/one_display/pictures/abstract-{one}.jpg" for one in ("blue", "teal", "warm", "dusk"))

#: The groups the gallery shows, in order.
GROUPS = {
	"welcome": _lt("Welcome"),
	"queues": _lt("Queues"),
	"boards": _lt("Boards and Rooms"),
	"information": _lt("Information"),
	"promotion": _lt("Promotion"),
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

	def box(self, x, y, w, h, fill, corner=0, stroke=None, shape="rectangle", layer=1, square=False):
		"""A shape; `square` keeps it as tall as it is wide, for a circle."""
		from onedesk.one_slide import decks

		width = self._x(w)
		one = decks._box(self._id(), self._x(x), self._y(y), width, width if square else self._y(h), fill, shape, round(corner * self.unit), stroke)
		one["zIndex"] = layer
		self.elements.append(one)

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


# --- the screens ---------------------------------------------------------


def welcome(c: Canvas) -> str:
	c.box(58, -30, 70, 0, "#FFFFFF14", shape="oval", square=True)
	c.box(74, 40, 46, 0, "#FFFFFF0F", shape="oval", square=True)
	c.logo(6, 7, 22, 9)
	c.text(6, 30, 60, _("Welcome"), 92, bold=True)
	c.text(6, 52, 52, _("We are glad you are here. Make yourself at home."), 26, "#FFFFFFD9")
	c.widget("glass_clock", 72, 7, 22, 20)
	c.widget("week_ahead", 64, 56, 30, 26, look="Glass")
	c.widget("news_ticker", 0, 90, 100, 10, look="Dark Glass", settings={"text": _("Opening hours today: 9:00 to 18:00")})
	return _fade(c.brand, c.deep)


def welcome_tall(c: Canvas) -> str:
	c.box(-20, -8, 90, 0, "#FFFFFF14", shape="oval", square=True)
	c.logo(8, 5, 50, 5)
	c.widget("glass_clock", 8, 16, 84, 12)
	c.text(8, 40, 84, _("Welcome"), 96, bold=True)
	c.text(8, 52, 84, _("We are glad you are here. Make yourself at home."), 30, "#FFFFFFD9")
	c.widget("weather_card", 8, 68, 84, 16, look="Glass")
	c.widget("news_ticker", 0, 93, 100, 7, look="Dark Glass", settings={"text": _("Opening hours today: 9:00 to 18:00")})
	return _fade(c.brand, c.deep, 180)


def lobby(c: Canvas) -> str:
	c.box(0, 0, 100, 14, c.brand)
	c.logo(4, 3.5, 30, 8)
	c.widget("corner_clock", 80, 2, 16, 10, look="Dark Glass")
	c.widget("full_picture", 0, 14, 62, 76, picture=PICTURES[1])
	c.text(66, 20, 30, _("Today"), 18, "#FFFFFFA6", bold=True)
	c.text(66, 27, 30, _("Team meeting\n10:00, Room 2"), 30, bold=True)
	c.text(66, 46, 30, _("Visitors sign in\nat the front desk"), 24, "#FFFFFFD9")
	c.widget("weather_card", 66, 64, 30, 22, look="Dark Glass")
	c.widget("accent_ticker", 0, 90, 100, 10, settings={"text": _("Welcome to our visitors today")})
	return NIGHT


def now_serving(c: Canvas) -> str:
	c.logo(4, 5, 30, 8)
	c.widget("clock_and_date", 76, 4, 20, 14, look="Dark Glass")
	c.widget("now_serving", 4, 22, 58, 64, look="Floating")
	c.box(66, 22, 30, 64, "#FFFFFF14", corner=16)
	c.text(69, 27, 24, _("How it works"), 18, "#FFFFFFA6", bold=True)
	c.text(69, 34, 24, _("Take a ticket, watch for your number, and go to the counter shown."), 20, "#FFFFFFD9")
	c.widget("give_feedback", 69, 60, 13, 23, look="Light Card")
	c.widget("news_ticker", 0, 91, 100, 9, look="Dark Glass", settings={"text": _("Your number will be called and shown here")})
	return _fade(c.dark, NIGHT)


def queue_full(c: Canvas) -> str:
	c.widget("full_queue", 0, 0, 100, 90, look="Solid")
	c.widget("accent_ticker", 0, 90, 100, 10, settings={"text": _("Your number will be called and shown here")})
	return NIGHT


def queue_tall(c: Canvas) -> str:
	c.box(0, 0, 100, 10, c.brand)
	c.logo(6, 2.5, 50, 5)
	c.widget("corner_clock", 66, 2.5, 28, 5, look="Dark Glass")
	c.widget("now_serving", 5, 14, 90, 70, look="Card")
	c.widget("accent_ticker", 0, 94, 100, 6, settings={"text": _("Your number will be called and shown here")})
	return NIGHT


def kiosk_tall(c: Canvas) -> str:
	c.box(0, 0, 100, 22, c.brand)
	c.logo(8, 5, 60, 6)
	c.text(8, 12, 84, _("Take a ticket"), 44, bold=True)
	c.widget("light_kiosk", 6, 26, 88, 62, look="Soft", settings={"heading": _("Choose a service")})
	c.text(8, 91, 84, _("Your number will be called on the screens"), 20, MUTED, align="center")
	return PAPER


def counter(c: Canvas) -> str:
	c.text(5, 8, 60, _("Counter {0}").format(1), 40, "#FFFFFFA6", bold=True)
	c.widget("counter_tile", 5, 26, 58, 64, settings={"item": "1"}, source=_first("Queue"))
	c.widget("clock_and_date", 68, 8, 27, 22, look="Dark Glass")
	c.text(68, 40, 27, _("Now serving the number shown"), 22, "#FFFFFFD9")
	c.widget("compact_queue", 68, 58, 27, 32, look="Dark Glass")
	return _fade(c.dark, NIGHT)


def status_board(c: Canvas) -> str:
	c.text(4, 5, 60, _("Status"), 44, bold=True)
	c.widget("corner_clock", 80, 4, 16, 11, look="Glass")
	c.widget("board_columns", 4, 20, 92, 70, look="Plain")
	return _fade(c.deep, NIGHT)


def rooms(c: Canvas) -> str:
	c.box(0, 0, 100, 16, CLEAR)
	c.text(5, 6, 60, _("Rooms"), 40, INK, bold=True)
	c.widget("light_clock", 74, 4, 22, 16, look="Soft")
	c.widget("simple_board", 5, 22, 90, 70, look="Plain")
	return PAPER


def room_sign(c: Canvas) -> str:
	c.box(0, 0, 38, 100, c.brand)
	c.text(4, 10, 32, _("Room {0}").format(1), 44, bold=True)
	c.widget("large_clock", 4, 38, 30, 22)
	c.text(4, 78, 32, _("Book at the front desk"), 18, "#FFFFFFD9")
	c.widget("door_sign", 44, 12, 50, 76, settings={"item": _("Room {0}").format(1)})
	return PAPER


def schedule(c: Canvas) -> str:
	c.text(6, 7, 60, _("Today's Schedule"), 44, INK, bold=True)
	c.widget("light_clock", 74, 5, 20, 15, look="Floating")
	times = [("09:00", _("Morning briefing"), _("Room 1")), ("11:00", _("Training session"), _("Hall")), ("13:00", _("Lunch"), _("Ground floor")), ("15:30", _("Workshop"), _("Room 3"))]
	for at, (when, what, where) in enumerate(times):
		top = 26 + at * 16
		c.box(6, top, 88, 13, "#FFFFFFFF", corner=12, layer=1)
		c.box(6, top, 1.2, 13, c.brand, layer=2)
		c.text(10, top + 3.5, 14, when, 26, c.brand, bold=True)
		c.text(26, top + 3.5, 44, what, 26, INK, bold=True)
		c.text(70, top + 4.2, 22, where, 20, MUTED, align="right")
	return PAPER


def directory(c: Canvas) -> str:
	c.box(0, 0, 34, 100, c.brand)
	c.logo(5, 7, 26, 8)
	c.text(5, 30, 26, _("Directory"), 48, bold=True)
	c.widget("large_clock", 5, 66, 24, 18)
	floors = [("3", _("Meeting rooms"), "→"), ("2", _("Offices"), "→"), ("1", _("Reception and cafe"), "←"), ("0", _("Parking"), "↓")]
	for at, (level, what, way) in enumerate(floors):
		top = 10 + at * 21
		c.box(40, top, 9, 0, c.pale, shape="oval", square=True, layer=1)
		c.text(40, top + 3.5, 9, level, 34, c.brand, bold=True, align="center")
		c.text(53, top + 4.5, 32, what, 30, INK, bold=True)
		c.text(86, top + 3.5, 8, way, 40, c.brand, bold=True, align="center")
	return PAPER


def announcement(c: Canvas) -> str:
	c.box(-12, 52, 50, 0, "#FFFFFF12", shape="oval", square=True)
	c.widget("tag", 6, 10, 16, 7, settings={"text": _("Announcement")}, look="Glass")
	c.text(6, 22, 48, _("Something new is coming"), 54, bold=True)
	c.text(6, 54, 46, _("Write what is changing, when, and who to ask about it."), 24, "#FFFFFFD9")
	c.text(6, 72, 46, _("From Monday"), 22, "#FFFFFFA6", bold=True)
	c.widget("framed_picture", 58, 12, 36, 66, picture=PICTURES[3])
	c.widget("news_ticker", 0, 90, 100, 10, look="Dark Glass")
	return _fade(c.brand, c.deep)


def notices_tall(c: Canvas) -> str:
	c.box(0, 0, 100, 12, c.brand)
	c.text(7, 3.5, 60, _("Notice Board"), 40, bold=True)
	c.widget("corner_clock", 68, 3.5, 26, 5, look="Dark Glass")
	notes = [(_("Fire drill on Thursday at 11:00"), "#FEF3C7FF", "#78350FFF"), (_("New parking rules from next month"), "#FFFFFFFF", INK), (_("Welcome to our new team members"), c.pale, c.dark)]
	for at, (words, fill, ink) in enumerate(notes):
		top = 16 + at * 20
		c.box(6, top, 88, 17, fill, corner=14)
		c.text(11, top + 5, 78, words, 30, ink, bold=True)
	c.widget("give_feedback", 34, 77, 32, 19, look="Floating")
	return PAPER


def figures(c: Canvas) -> str:
	c.text(4, 5, 60, _("This Month"), 40, bold=True)
	c.widget("corner_clock", 80, 4, 16, 11, look="Glass")
	tiles = [("128", _("Orders")), ("96%", _("On time")), ("4.8", _("Rating")), ("37", _("New customers"))]
	for at, (value, caption) in enumerate(tiles):
		left = 4 + at * 23.5
		c.widget("big_number", left, 22, 21, 30, settings={"text": value}, look="Glass")
		c.text(left, 54, 21, caption, 22, "#FFFFFFD9", align="center")
	c.widget("progress", 4, 66, 92, 14, look="Glass")
	c.widget("news_ticker", 0, 90, 100, 10, look="Dark Glass")
	return _fade(c.deep, NIGHT)


def rates(c: Canvas) -> str:
	c.text(5, 8, 60, _("Exchange Rates"), 48, bold=True)
	c.text(5, 24, 60, _("Rates are for guidance and may change during the day."), 20, "#FFFFFFA6")
	c.widget("clock_and_date", 74, 6, 22, 18, look="Glass")
	c.widget("headline", 5, 40, 90, 30, settings={"text": "USD 1.00", "size": 14}, source="", label=_("Rate"))
	c.widget("accent_ticker", 0, 86, 100, 14, source=_first("Exchange Rates"), mapping={"text": "{line}"})
	return _fade(c.dark, NIGHT)


def clock_weather(c: Canvas) -> str:
	c.widget("large_clock", 20, 12, 60, 46)
	c.widget("week_ahead", 25, 62, 50, 28, look="Glass")
	return _fade(c.brand, c.deep, 160)


def countdown(c: Canvas) -> str:
	c.box(60, -20, 60, 0, "#FFFFFF12", shape="oval", square=True)
	c.text(6, 12, 88, _("Opening Soon"), 64, bold=True, align="center")
	c.widget("countdown", 15, 36, 70, 34, look="Dark Glass")
	c.text(6, 76, 88, _("Something new is on its way. See you there."), 24, "#FFFFFFD9", align="center")
	return _fade(c.brand, c.deep)


def promotion(c: Canvas) -> str:
	c.widget("full_picture", 0, 0, 52, 100, picture=PICTURES[2])
	c.widget("tag", 58, 12, 14, 7, settings={"text": _("Offer")})
	c.text(58, 23, 38, _("Twenty percent off this week"), 44, INK, bold=True)
	c.text(58, 52, 36, _("Ask at the counter for details."), 22, MUTED)
	c.widget("price", 58, 64, 22, 14, settings={"text": "49.00", "align": "start"}, look={"color": c.brand})
	c.widget("visit_website", 81, 64, 14, 28, look="Soft")
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
		c.box(6, top + 11.5, 60, 0.3, "#11182714")
	c.widget("tag", 32, 36.5, 10, 6, settings={"text": _("New")})
	c.box(72, 0, 28, 100, c.brand)
	c.widget("see_menu", 76, 30, 20, 34, look="Light Card")
	c.widget("corner_clock", 76, 82, 20, 11, look="Dark Glass")
	return CREAM


def follow_us(c: Canvas) -> str:
	c.text(6, 10, 88, _("Stay in Touch"), 60, bold=True, align="center")
	c.text(6, 26, 88, _("Scan a code with your phone's camera."), 24, "#FFFFFFD9", align="center")
	for at, preset in enumerate(("visit_website", "follow_us", "give_feedback")):
		c.widget(preset, 13 + at * 26, 42, 22, 38, look="Floating")
	return _fade(c.brand, c.deep)


def spotlight(c: Canvas) -> str:
	c.widget("rounded_picture", 8, 12, 30, 76, picture=PICTURES[0])
	c.widget("tag", 46, 16, 16, 7, settings={"text": _("Team Spotlight")}, look="Accent Pill")
	c.text(46, 28, 48, _("Name Surname"), 50, INK, bold=True)
	c.text(46, 42, 48, _("Role in the team"), 26, c.brand, bold=True)
	c.text(46, 54, 46, _("“A few words from them about what they do and what they enjoy about it.”"), 24, MUTED, italic=True)
	return PAPER


def thanks(c: Canvas) -> str:
	c.widget("rotating_messages", 6, 18, 56, 30, look="Plain")
	c.text(6, 54, 56, _("Your feedback helps us do better."), 26, "#FFFFFFD9")
	c.widget("give_feedback", 68, 18, 26, 46, look="Floating")
	c.widget("news_ticker", 0, 90, 100, 10, look="Dark Glass")
	return _fade(c.brand, c.deep)


def sidebar(c: Canvas) -> str:
	c.box(72, 0, 28, 100, NIGHT)
	c.logo(75, 5, 22, 8)
	c.widget("clock_and_date", 75, 22, 22, 16, look="Plain")
	c.widget("weather_card", 75, 40, 22, 26, look="Dark Glass")
	c.widget("visit_website", 79, 70, 14, 26, look="Light Card")
	return NIGHT


def lower_third(c: Canvas) -> str:
	c.box(0, 82, 100, 18, NIGHT)
	c.box(0, 82, 1, 18, c.brand, layer=2)
	c.logo(3, 85, 22, 12)
	c.widget("news_ticker", 26, 84, 57, 14, look="Plain")
	c.widget("corner_clock", 85, 85, 12, 12, look="Accent Pill")
	return NIGHT


def banner(c: Canvas) -> str:
	c.box(0, 0, 22, 100, c.brand)
	c.logo(2, 25, 18, 50)
	c.text(26, 18, 50, _("Welcome"), 64, bold=True)
	c.text(26, 58, 50, _("We are glad you are here"), 28, "#FFFFFFD9")
	c.widget("clock_and_date", 80, 15, 17, 70, look="Glass")
	return _fade(c.dark, NIGHT, 90)


def banner_ticker(c: Canvas) -> str:
	c.box(0, 0, 14, 100, c.brand)
	c.logo(1.5, 20, 11, 60)
	c.widget("news_ticker", 14, 0, 74, 100, look="Plain", settings={"text": _("Welcome to our visitors today")})
	c.widget("corner_clock", 89, 20, 10, 60, look="Accent")
	return NIGHT


#: key: (builder, shape, group, name, what it is for)
STARTERS = {
	"welcome": (welcome, "wide", "welcome", _lt("Welcome"), _lt("A greeting with the time, the weather and a ticker.")),
	"lobby": (lobby, "wide", "welcome", _lt("Lobby"), _lt("A large picture beside today's news and the weather.")),
	"clock_weather": (clock_weather, "wide", "welcome", _lt("Clock and Weather"), _lt("The time and the week's weather, large.")),
	"welcome_tall": (welcome_tall, "tall", "welcome", _lt("Welcome, Standing"), _lt("A greeting for a screen on its side.")),
	"banner": (banner, "strip", "welcome", _lt("Welcome Strip"), _lt("A greeting and the time across a long screen.")),
	"now_serving": (now_serving, "wide", "queues", _lt("Now Serving"), _lt("The queue, how it works, and a feedback code.")),
	"queue_full": (queue_full, "wide", "queues", _lt("Queue, Full Screen"), _lt("Only the queue, as large as it goes.")),
	"counter": (counter, "wide", "queues", _lt("Counter"), _lt("The ticket one counter is serving, for above it.")),
	"queue_tall": (queue_tall, "tall", "queues", _lt("Queue, Standing"), _lt("The queue on a screen on its side.")),
	"kiosk_tall": (kiosk_tall, "tall", "queues", _lt("Ticket Kiosk"), _lt("Buttons that issue a ticket, for a touch screen.")),
	"status_board": (status_board, "wide", "boards", _lt("Status Board"), _lt("Every item on a board in columns.")),
	"rooms": (rooms, "wide", "boards", _lt("Rooms"), _lt("Which rooms are free and which are in use.")),
	"room_sign": (room_sign, "wide", "boards", _lt("Room Sign"), _lt("One room's state, for beside its door.")),
	"schedule": (schedule, "wide", "information", _lt("Today's Schedule"), _lt("What happens today, when and where.")),
	"directory": (directory, "wide", "information", _lt("Directory"), _lt("Where everything is, floor by floor.")),
	"announcement": (announcement, "wide", "information", _lt("Announcement"), _lt("One piece of news with a picture.")),
	"notices_tall": (notices_tall, "tall", "information", _lt("Notice Board"), _lt("Several notices on a screen on its side.")),
	"figures": (figures, "wide", "information", _lt("Figures"), _lt("Four figures and progress to a goal.")),
	"rates": (rates, "wide", "information", _lt("Exchange Rates"), _lt("Rates from an Exchange Rates source, with the time.")),
	"countdown": (countdown, "wide", "promotion", _lt("Countdown"), _lt("Days, hours and minutes to an opening or an event.")),
	"promotion": (promotion, "wide", "promotion", _lt("Offer"), _lt("A picture, an offer, its price and a code.")),
	"price_list": (price_list, "wide", "promotion", _lt("Price List"), _lt("Items and prices with a code to see more.")),
	"follow_us": (follow_us, "wide", "promotion", _lt("Stay in Touch"), _lt("Codes for your website, social pages and feedback.")),
	"spotlight": (spotlight, "wide", "promotion", _lt("Team Spotlight"), _lt("A picture of someone and a few words about them.")),
	"thanks": (thanks, "wide", "promotion", _lt("Feedback"), _lt("Messages that change, and a code to give feedback.")),
	"sidebar": (sidebar, "wide", "over_slides", _lt("Sidebar"), _lt("The time, the weather and a code beside the slides.")),
	"lower_third": (lower_third, "wide", "over_slides", _lt("Lower Third"), _lt("A ticker and the time along the foot of the slides.")),
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
