"""The decks One ships, and the slides of One's shelf in the slide library
(AGENTS.md, Decks and the library). Each is built here rather than stored, so
it comes in the reader's language and the business's own colour and logo.
Kept as template presentations too (`sync`), so Add Slide and Restyle from
Layouts find their slides by the same ids."""

import json

import frappe
from frappe import _, _lt

WIDE, HIGH = 960, 540
INK, MUTED, PALE, WHITE = "#1F2937FF", "#6B7280FF", "#F3F4F6FF", "#FFFFFFFF"
DEFAULT_BRAND = "#2563EB"

#: The kinds of slide the library is sorted by, in the order it shows them.
KINDS = ("title", "agenda", "section", "two_columns", "picture_text", "quote", "team", "timeline", "figures", "pricing", "thank_you")


def kind_labels() -> dict:
	return {
		"title": _("Title"),
		"agenda": _("Agenda"),
		"section": _("Section"),
		"two_columns": _("Two Columns"),
		"picture_text": _("Picture and Text"),
		"quote": _("Quote"),
		"team": _("Team"),
		"timeline": _("Timeline"),
		"figures": _("Figures"),
		"pricing": _("Pricing"),
		"thank_you": _("Thank You"),
	}


def deck_titles() -> dict:
	return {
		"pitch": _("Pitch"),
		"update": _("Project Update"),
		"tender": _("Tender Response"),
		"review": _("Monthly Review"),
		"training": _("Training Session"),
	}


#: Each deck's slides: a kind, and the words that differ from the kind's own.
DECKS = {
	"pitch": (
		("title", {"title": _lt("Our proposal"), "line": _lt("What we will do for you, and why us")}),
		("agenda", {}),
		("section", {"title": _lt("The challenge")}),
		("two_columns", {"left": _lt("The problem"), "right": _lt("Our answer")}),
		("figures", {}),
		("picture_text", {}),
		("team", {}),
		("pricing", {}),
		("quote", {}),
		("thank_you", {}),
	),
	"update": (
		("title", {"title": _lt("Project update"), "line": _lt("Where we are and what comes next")}),
		("figures", {"title": _lt("Progress")}),
		("timeline", {}),
		("two_columns", {"left": _lt("Done"), "right": _lt("Next")}),
		("picture_text", {"title": _lt("On site")}),
		("thank_you", {}),
	),
	"tender": (
		("title", {"title": _lt("Tender response"), "line": _lt("Our offer, in answer to your request")}),
		("agenda", {}),
		("two_columns", {"left": _lt("What you asked for"), "right": _lt("How we will do it")}),
		("timeline", {"title": _lt("Programme")}),
		("team", {}),
		("pricing", {"title": _lt("Our offer")}),
		("thank_you", {}),
	),
	"review": (
		("title", {"title": _lt("Monthly review"), "line": _lt("The month in figures")}),
		("figures", {}),
		("two_columns", {"left": _lt("Went well"), "right": _lt("To fix")}),
		("timeline", {"title": _lt("Next month")}),
		("thank_you", {}),
	),
	"training": (
		("title", {"title": _lt("Training session"), "line": _lt("What you will learn today")}),
		("agenda", {}),
		("section", {"title": _lt("Part one")}),
		("picture_text", {}),
		("two_columns", {"left": _lt("Do"), "right": _lt("Avoid")}),
		("quote", {}),
		("thank_you", {"title": _lt("Questions?")}),
	),
}

#: The template presentation each deck is kept as.
NAMES = {key: f"one-deck-{key}" for key in DECKS}


def brand() -> dict:
	"""The business's colour and logo, as One's mails wear them."""
	company = frappe.defaults.get_global_default("company")
	logo, colour = frappe.db.get_value("Company", company, ["company_logo", "one_brand_colour"]) if company else (None, None)
	colour = colour if isinstance(colour, str) and len(colour) == 7 and colour.startswith("#") else DEFAULT_BRAND
	logo = logo if logo and logo.startswith(("/files/", "/private/files/")) and not logo.lower().endswith(".svg") else None
	return {"colour": colour.upper() + "FF", "logo": logo}


def _text(id, left, top, width, words, size=24, colour=INK, bold=False, align="left", italic=False) -> dict:
	from frappe.utils import escape_html

	weight = "<strong>{}</strong>" if bold else "{}"
	slant = "<em>{}</em>" if italic else "{}"
	runs = "".join(
		f'<p style="text-align: {align}"><span style="font-size: {size}px; color: {colour}">{slant.format(weight.format(escape_html(line)))}</span></p>'
		for line in str(words).split("\n")
	)
	return {"id": id, "type": "text", "left": left, "top": top, "width": width, "zIndex": 2, "content": runs}


def _box(id, left, top, width, height, fill, shape="rectangle", corner=0, stroke=None, words=None, size=20, colour=WHITE) -> dict:
	one = {
		"id": id,
		"type": "shape",
		"shapeType": shape,
		"left": left,
		"top": top,
		"width": width,
		"height": height,
		"zIndex": 1,
		"fillColor": fill,
		"strokeColor": stroke or "#00000000",
		"strokeWidth": 2 if stroke else 0,
		"borderRadius": corner,
		"opacity": 100,
		"rotation": 0,
	}
	if words:
		one["content"] = _text("", 0, 0, 0, words, size, colour, align="center")["content"]
	return one


def _logo(id, left, top, width, height, logo) -> list:
	if not logo:
		return []
	return [{"id": id, "type": "image", "src": logo, "left": left, "top": top, "width": width, "height": height, "zIndex": 3, "opacity": 100}]


def _many(words: dict, key: str, most: int, fields: tuple) -> list | None:
	"""A list of a slide's parts given in `words`, each a dict of `fields`, or
	None when none is given. Pure."""
	given = words.get(key)
	if not isinstance(given, list) or not given:
		return None
	out = []
	for one in given[:most]:
		one = one if isinstance(one, dict) else {fields[0]: one}
		out.append(tuple(str(one.get(field) or "") for field in fields))
	return out


def build(kind: str, words: dict, look: dict) -> dict:
	"""One slide of a kind, in the business's colour, its words translated
	unless given (WORDS says which each kind takes). Pure but for the
	translations."""
	c = look["colour"]
	say = lambda key, default: str(words[key]) if words.get(key) else default  # noqa: E731
	background = WHITE
	if kind == "title":
		drawn = [
			_box("bar", 0, 0, 24, HIGH, c),
			_text("title", 80, 170, 760, say("title", _("The title of your presentation")), 60, INK, True),
			_text("line", 80, 300, 760, say("line", _("One line on what it is about")), 26, MUTED),
			*_logo("logo", 760, 40, 160, 70, look["logo"]),
		]
	elif kind == "agenda":
		drawn = [_text("title", 80, 50, 800, say("title", _("Agenda")), 44, INK, True)]
		items = [one[0] for one in _many(words, "items", 6, ("item",)) or []] or [_("Where we are"), _("What we propose"), _("How we will do it"), _("What it costs")]
		gap = min(80, 340 // len(items))
		for at, item in enumerate(items):
			drawn += [
				_box(f"n{at}", 80, 150 + at * gap, 48, 48, c, "oval", words=str(at + 1), size=20),
				_text(f"i{at}", 150, 158 + at * gap, 700, item, 26),
			]
	elif kind == "section":
		background = c
		drawn = [
			_text("title", 80, 210, 800, say("title", _("A new part")), 56, WHITE, True),
			_box("rule", 80, 310, 120, 6, WHITE),
		]
	elif kind == "two_columns":
		drawn = [_text("title", 80, 50, 800, say("title", _("Side by side")), 40, INK, True)]
		for at, (key, left) in enumerate((("left", 80), ("right", 500))):
			drawn += [
				_box(f"rule{at}", left, 130, 380, 6, c),
				_text(f"head{at}", left, 150, 380, say(key, _("A heading")), 28, INK, True),
				_text(f"body{at}", left, 205, 380, say(f"{key}_body", _("A few words on this side.\nKeep it to three lines.")), 20, MUTED),
			]
	elif kind == "picture_text":
		drawn = [
			_box("picture", 0, 0, 440, HIGH, PALE, words=_("Put a picture here"), size=20, colour=MUTED),
			_text("title", 500, 140, 400, say("title", _("What the picture shows")), 36, INK, True),
			_text("body", 500, 230, 400, say("body", _("Two or three lines that say why it matters.")), 22, MUTED),
		]
	elif kind == "quote":
		drawn = [
			_text("mark", 80, 40, 120, "“", 160, c, True),
			_text("quote", 120, 180, 720, say("quote", _("What a client said about working with us.")), 36, INK, italic=True),
			_text("who", 120, 330, 720, say("who", _("Name, Company")), 22, MUTED),
		]
	elif kind == "team":
		drawn = [_text("title", 80, 50, 800, say("title", _("The team")), 40, INK, True)]
		people = _many(words, "people", 3, ("name", "role")) or [(_("Name"), _("Role"))] * 3
		for at, (name, role) in enumerate(people):
			left = 110 + (3 - len(people)) * 135 + at * 270
			drawn += [
				_box(f"face{at}", left + 35, 150, 150, 150, PALE, "oval", stroke=c),
				_text(f"name{at}", left, 320, 220, name, 24, INK, True, "center"),
				_text(f"role{at}", left, 360, 220, role, 20, MUTED, align="center"),
			]
	elif kind == "timeline":
		drawn = [
			_text("title", 80, 50, 800, say("title", _("The plan")), 40, INK, True),
			_box("line", 100, 268, 760, 4, c),
		]
		steps = _many(words, "steps", 5, ("step", "when")) or [(step, _("Week {0}").format(at * 4 + 1)) for at, step in enumerate((_("Start"), _("Design"), _("Build"), _("Hand over")))]
		apart = 760 // max(1, len(steps) - 1) if len(steps) > 1 else 0
		for at, (step, when) in enumerate(steps):
			left = 100 + at * apart if len(steps) > 1 else 480
			drawn += [
				_box(f"dot{at}", left - 14, 256, 28, 28, c, "oval"),
				_text(f"step{at}", left - 80, 300, 160, step, 22, INK, True, "center"),
				_text(f"when{at}", left - 80, 335, 160, when, 18, MUTED, align="center"),
			]
	elif kind == "figures":
		drawn = [_text("title", 80, 50, 800, say("title", _("In figures")), 40, INK, True)]
		figures = _many(words, "figures", 3, ("figure", "label")) or [("85%", _("Done")), ("12", _("Weeks")), ("3", _("Sites"))]
		for at, (figure, label) in enumerate(figures):
			left = 80 + at * 280
			drawn += [
				_text(f"figure{at}", left, 170, 260, figure, 72, c, True),
				_text(f"label{at}", left, 280, 260, label, 22, MUTED),
			]
	elif kind == "pricing":
		drawn = [_text("title", 80, 40, 800, say("title", _("Pricing")), 40, INK, True)]
		plans = _many(words, "plans", 3, ("plan", "price", "what")) or [(plan, "—", _("What is included")) for plan in (_("Basic"), _("Standard"), _("Complete"))]
		for at, (plan, price, what) in enumerate(plans):
			left = 80 + at * 280
			drawn += [
				_box(f"card{at}", left, 120, 250, 360, WHITE if at != 1 else PALE, corner=16, stroke=c),
				_text(f"plan{at}", left + 20, 145, 210, plan, 26, INK, True, "center"),
				_text(f"price{at}", left + 20, 200, 210, price or "—", 40, c, True, "center"),
				_text(f"what{at}", left + 20, 280, 210, what, 18, MUTED, align="center"),
			]
	elif kind == "thank_you":
		background = c
		drawn = [
			_text("title", 80, 200, 800, say("title", _("Thank you")), 64, WHITE, True, "center"),
			_text("line", 80, 310, 800, say("line", _("Your name · your email · your phone")), 22, WHITE, align="center"),
			*_logo("logo", 400, 410, 160, 70, look["logo"]),
		]
	else:
		frappe.throw(_("There is no slide of that kind."))
	return {"background": background, "elements": drawn, "kind": kind}


#: The words each kind takes, for OneAI to fill (one_deck/agent.py draft_deck).
WORDS = {
	"title": "title, line",
	"agenda": "title, items (up to 6 strings)",
	"section": "title",
	"two_columns": "title, left, left_body, right, right_body",
	"picture_text": "title, body",
	"quote": "quote, who",
	"team": "title, people (up to 3 of {name, role})",
	"timeline": "title, steps (up to 5 of {step, when})",
	"figures": "title, figures (up to 3 of {figure, label})",
	"pricing": "title, plans (up to 3 of {plan, price, what})",
	"thank_you": "title, line",
}


def slides(deck: str, look: dict | None = None) -> list[dict]:
	"""A deck's slides as rows, each remembering the template slide it is."""
	look = look or brand()
	out = []
	for at, (kind, words) in enumerate(DECKS[deck], start=1):
		drawn = build(kind, words, look)
		for one in drawn["elements"]:
			one["from"] = one["id"]
		out.append(
			{
				"client_id": f"{NAMES[deck]}-{at}",
				"layout": f"{NAMES[deck]}:{NAMES[deck]}-{at}",
				"background": drawn["background"],
				"elements": json.dumps(drawn["elements"]),
				"transition": "Fade",
				"transition_duration": 0.6,
				"fade_unmatched_elements": 1,
				"kind": kind,
			}
		)
	return out


def deck_of(name: str) -> str | None:
	return next((key for key, held in NAMES.items() if held == name), None)


def sync() -> None:
	"""after_migrate: each deck kept as a template, in English and One's own
	colour, so Add Slide and Restyle from Layouts read its slides."""
	look = {"colour": DEFAULT_BRAND + "FF", "logo": None}
	frappe.local.lang = "en"
	for deck in DECKS:
		name = NAMES[deck]
		fresh = not frappe.db.exists("Presentation", name)
		doc = frappe.new_doc("Presentation") if fresh else frappe.get_doc("Presentation", name)
		doc.update({"title": deck_titles()[deck], "is_template": 1, "width": WIDE, "height": HIGH})
		doc.set("slides", [{key: value for key, value in row.items() if key != "layout"} for row in slides(deck, look)])
		doc.flags.ignore_permissions = True
		if fresh:
			doc.insert(set_name=name)
		else:
			doc.save()
