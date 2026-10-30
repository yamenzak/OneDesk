"""What a designed slide is made of: every kind of block, every property a
block can have, its range, and the section of the designer it is set in.

One table drives three things, so they cannot disagree: `clean` keeps only
what it declares, the designer draws its controls from `described`, and the
renderer both the screen and the designer run (public/js/one_display/
blocks.js) reads only these names. A property added here is a property a
person can set, the server keeps and the screen draws."""

import json
import re

from frappe import _lt

MOST = 80

GROUND = "#0e6e8c"

COLOUR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")

# The properties of every block, in the order the designer shows them. A
# "check" is 0 or 1, a "choice" one of its options, a "colour" #rgb,
# #rrggbb or #rrggbbaa or nothing, a "file" one of the workspace's /files/.
PROPERTIES = {
	"x": {"type": "number", "min": -100, "max": 200, "step": 0.5, "unit": "%", "label": _lt("Left"), "section": "position"},
	"y": {"type": "number", "min": -100, "max": 200, "step": 0.5, "unit": "%", "label": _lt("Top"), "section": "position"},
	"w": {"type": "number", "min": 0.2, "max": 300, "step": 0.5, "unit": "%", "label": _lt("Width"), "section": "position"},
	"h": {"type": "number", "min": 0.2, "max": 300, "step": 0.5, "unit": "%", "label": _lt("Height"), "section": "position"},
	"rotate": {"type": "number", "min": -360, "max": 360, "step": 1, "unit": "°", "label": _lt("Rotate"), "section": "position"},
	"text": {"type": "text", "max": 2000, "label": _lt("Words"), "section": "text"},
	"font": {"type": "choice", "options": ["sans", "serif", "mono", "condensed"], "labels": [_lt("Sans"), _lt("Serif"), _lt("Mono"), _lt("Condensed")], "label": _lt("Font"), "section": "text"},
	"size": {"type": "number", "min": 8, "max": 600, "step": 1, "unit": "px", "label": _lt("Size"), "section": "text"},
	"weight": {"type": "choice", "options": [300, 400, 500, 600, 700, 800, 900], "labels": [_lt("Light"), _lt("Regular"), _lt("Medium"), _lt("Semibold"), _lt("Bold"), _lt("Extra Bold"), _lt("Heavy")], "label": _lt("Weight"), "section": "text"},
	"colour": {"type": "colour", "label": _lt("Colour"), "section": "text"},
	"align": {"type": "choice", "options": ["start", "center", "end", "justify"], "icons": ["align-left", "align-center", "align-right", "align-justify"], "labels": [_lt("Start"), _lt("Centre"), _lt("End"), _lt("Justify")], "label": _lt("Align"), "section": "text"},
	"valign": {"type": "choice", "options": ["top", "middle", "bottom"], "icons": ["arrow-up-to-line", "fold-vertical", "arrow-down-to-line"], "labels": [_lt("Top"), _lt("Middle"), _lt("Bottom")], "label": _lt("Vertical"), "section": "text"},
	"line": {"type": "number", "min": 0.6, "max": 3, "step": 0.05, "label": _lt("Line Height"), "section": "text"},
	"spacing": {"type": "number", "min": -0.1, "max": 0.6, "step": 0.01, "unit": "em", "label": _lt("Letter Spacing"), "section": "text"},
	"italic": {"type": "check", "label": _lt("Italic"), "section": "text"},
	"underline": {"type": "check", "label": _lt("Underline"), "section": "text"},
	"upper": {"type": "check", "label": _lt("Capitals"), "section": "text"},
	"padding": {"type": "number", "min": 0, "max": 400, "step": 1, "unit": "px", "label": _lt("Padding"), "section": "text"},
	"shape": {"type": "choice", "options": ["rectangle", "ellipse", "triangle", "diamond", "star", "arrow", "line"], "icons": ["square", "circle", "triangle", "diamond", "star", "arrow-right", "minus"], "labels": [_lt("Rectangle"), _lt("Ellipse"), _lt("Triangle"), _lt("Diamond"), _lt("Star"), _lt("Arrow"), _lt("Line")], "label": _lt("Shape"), "section": "shape"},
	"src": {"type": "file", "label": _lt("Picture"), "section": "image"},
	"fit": {"type": "choice", "options": ["cover", "contain"], "labels": [_lt("Fill"), _lt("Fit Inside")], "label": _lt("Fit"), "section": "image"},
	"link": {"type": "text", "max": 1000, "label": _lt("Address"), "section": "qr"},
	"fill": {"type": "colour", "label": _lt("Colour"), "section": "fill"},
	"fill2": {"type": "colour", "label": _lt("Fades To"), "section": "fill"},
	"angle": {"type": "number", "min": 0, "max": 360, "step": 1, "unit": "°", "label": _lt("Fade Angle"), "section": "fill"},
	"stroke": {"type": "number", "min": 0, "max": 200, "step": 1, "unit": "px", "label": _lt("Width"), "section": "border"},
	"stroke_colour": {"type": "colour", "label": _lt("Colour"), "section": "border"},
	"stroke_style": {"type": "choice", "options": ["solid", "dashed", "dotted"], "labels": [_lt("Solid"), _lt("Dashed"), _lt("Dotted")], "label": _lt("Style"), "section": "border"},
	"radius": {"type": "number", "min": 0, "max": 960, "step": 1, "unit": "px", "label": _lt("Corners"), "section": "border"},
	"shadow_colour": {"type": "colour", "label": _lt("Colour"), "section": "shadow"},
	"shadow_x": {"type": "number", "min": -200, "max": 200, "step": 1, "unit": "px", "label": _lt("Across"), "section": "shadow"},
	"shadow_y": {"type": "number", "min": -200, "max": 200, "step": 1, "unit": "px", "label": _lt("Down"), "section": "shadow"},
	"shadow_blur": {"type": "number", "min": 0, "max": 300, "step": 1, "unit": "px", "label": _lt("Blur"), "section": "shadow"},
	"opacity": {"type": "number", "min": 0, "max": 1, "step": 0.05, "label": _lt("Opacity"), "section": "effects"},
	"blur": {"type": "number", "min": 0, "max": 60, "step": 1, "unit": "px", "label": _lt("Blur"), "section": "effects"},
	"css": {"type": "css", "max": 2000, "label": _lt("CSS"), "section": "advanced"},
	"name": {"type": "text", "max": 60, "label": _lt("Name"), "section": None},
	"hidden": {"type": "check", "label": _lt("Hidden"), "section": None},
	"locked": {"type": "check", "label": _lt("Locked"), "section": None},
}

SECTIONS = {
	"position": _lt("Position and Size"),
	"text": _lt("Text"),
	"shape": _lt("Shape"),
	"image": _lt("Picture"),
	"qr": _lt("QR Code"),
	"fill": _lt("Fill"),
	"border": _lt("Border"),
	"shadow": _lt("Shadow"),
	"effects": _lt("Effects"),
	"advanced": _lt("CSS"),
}

PLACED = {"x": 10, "y": 10, "w": 40, "h": 20, "rotate": 0, "opacity": 1, "blur": 0, "name": "", "hidden": 0, "locked": 0, "css": ""}
BORDER = {"stroke": 0, "stroke_colour": "#ffffff", "stroke_style": "solid", "radius": 0}
SHADOW = {"shadow_colour": "", "shadow_x": 0, "shadow_y": 12, "shadow_blur": 40}
FILL = {"fill": "", "fill2": "", "angle": 180}

# Each kind: what it is called, its icon, the size it is put down at, the
# sections it is set in, and what a new one starts as.
KINDS = {
	"text": {
		"label": _lt("Text"),
		"icon": "type",
		"size": [60, 18],
		"sections": ["position", "text", "fill", "border", "shadow", "effects", "advanced"],
		"defaults": {
			**PLACED, **FILL, **BORDER, **SHADOW,
			"text": "", "font": "sans", "size": 96, "weight": 700, "colour": "#ffffff", "align": "start", "valign": "top",
			"line": 1.15, "spacing": 0, "italic": 0, "underline": 0, "upper": 0, "padding": 0,
		},
	},
	"image": {
		"label": _lt("Picture"),
		"icon": "image",
		"size": [30, 40],
		"sections": ["position", "image", "border", "shadow", "effects", "advanced"],
		"defaults": {**PLACED, **BORDER, **SHADOW, "src": "", "fit": "cover"},
	},
	"shape": {
		"label": _lt("Shape"),
		"icon": "shapes",
		"size": [30, 30],
		"sections": ["position", "shape", "fill", "border", "shadow", "effects", "advanced"],
		"defaults": {**PLACED, **BORDER, **SHADOW, **FILL, "shape": "rectangle", "fill": "#ffffff", "opacity": 0.2, "radius": 24},
	},
	"qr": {
		"label": _lt("QR Code"),
		"icon": "qr-code",
		"size": [14, 25],
		"sections": ["position", "qr", "border", "shadow", "effects"],
		"defaults": {**PLACED, **BORDER, **SHADOW, "link": ""},
	},
}

# The slide itself: its ground, a fade across it and a picture behind.
SLIDE = {
	"orientation": {"type": "choice", "options": ["Landscape", "Portrait"], "labels": [_lt("Landscape"), _lt("Portrait")], "label": _lt("Orientation")},
	"background": {"type": "colour", "label": _lt("Background")},
	"background2": {"type": "colour", "label": _lt("Fades To")},
	"angle": {"type": "number", "min": 0, "max": 360, "step": 1, "unit": "°", "label": _lt("Fade Angle")},
	"image": {"type": "file", "label": _lt("Background Picture")},
	"dim": {"type": "number", "min": 0, "max": 0.9, "step": 0.05, "label": _lt("Darken Picture")},
}
SLIDE_DEFAULTS = {"orientation": "Landscape", "background": GROUND, "background2": "", "angle": 180, "image": "", "dim": 0}

# What may be written as CSS of one's own, by property. A value is plain
# words, numbers, units, colours and functions such as rgba() or
# linear-gradient(); never url(), quotes, braces or a second declaration.
CSS = {
	"background", "background-color", "background-blend-mode", "border", "border-top", "border-right", "border-bottom",
	"border-left", "border-radius", "border-color", "border-width", "border-style", "box-shadow", "clip-path", "color",
	"filter", "font-style", "font-variant", "letter-spacing", "line-height", "mix-blend-mode", "outline", "outline-offset",
	"overflow", "padding", "padding-top", "padding-right", "padding-bottom", "padding-left", "text-decoration",
	"text-indent", "text-shadow", "text-transform", "transform", "transform-origin", "white-space", "word-spacing",
	"word-break", "opacity",
}
CSS_VALUE = re.compile(r"^[\w\s#%.,()+*/-]{1,300}$")
CSS_NEVER = re.compile(r"url\s*\(|expression|javascript|@import|\\", re.I)


def _number(value, spec: dict, default):
	try:
		number = float(value)
	except (TypeError, ValueError):
		return default
	if number != number:
		return default
	number = min(max(number, spec["min"]), spec["max"])
	return int(number) if float(spec["step"]).is_integer() and number.is_integer() else round(number, 4)


def css(value) -> str:
	"""Somebody's own CSS, as declarations the screen may run: each a
	property we allow and a value with nothing that loads or breaks out."""
	kept = []
	for part in str(value or "")[:2000].split(";"):
		name, _sep, said = part.partition(":")
		name, said = name.strip().lower(), said.strip()
		if name in CSS and said and CSS_VALUE.match(said) and not CSS_NEVER.search(said):
			kept.append(f"{name}: {said}")
	return "; ".join(kept)


def value(name: str, given, default, spec: dict | None = None):
	"""One property's value, as the server keeps it, or its default."""
	spec = spec or PROPERTIES[name]
	kind = spec["type"]
	if kind == "number":
		return _number(given, spec, default)
	if kind == "check":
		return 1 if given in (1, True, "1", "true") else 0
	if kind == "choice":
		options = spec["options"]
		if given in options:
			return given
		try:
			return int(given) if int(given) in options else default
		except (TypeError, ValueError):
			return default
	if kind == "colour":
		given = (given or "").strip() if isinstance(given, str) else ""
		return given if (given == "" or COLOUR.match(given)) else default
	if kind == "file":
		given = (given or "").strip() if isinstance(given, str) else ""
		return given if given.startswith("/files/") and not re.search(r"[\s\"'<>()\\]", given) else ""
	if kind == "css":
		return css(given)
	return str(given if given is not None else default)[: spec["max"]]


def block(one, i: int) -> dict | None:
	"""A block as the server keeps it: a kind it knows, the properties that
	kind has, each in its range, and nothing else. A block from before the
	designer had a property gets that property's default."""
	if not isinstance(one, dict) or one.get("kind") not in KINDS:
		return None
	kind = one["kind"]
	defaults = KINDS[kind]["defaults"]
	kept = {"id": re.sub(r"[^\w-]", "", str(one.get("id") or ""))[:20] or f"b{i}", "kind": kind}
	for name, default in defaults.items():
		kept[name] = value(name, one.get(name, default), default)
	return kept


def clean(design) -> dict:
	"""A design as the server keeps it."""
	if isinstance(design, str):
		design = json.loads(design or "{}")
	design = design if isinstance(design, dict) else {}
	said = {name: value(name, design.get(name, default), default, SLIDE[name]) for name, default in SLIDE_DEFAULTS.items()}
	said["background"] = said["background"] or GROUND
	said["blocks"] = [kept for i, one in enumerate((design.get("blocks") or [])[:MOST]) if (kept := block(one, i))]
	return said


def described() -> dict:
	"""The table, in the reader's language, for the designer to draw its
	controls from."""

	def said(spec: dict) -> dict:
		out = {key: (str(item) if key == "label" else item) for key, item in spec.items()}
		if "labels" in spec:
			out["labels"] = [str(one) for one in spec["labels"]]
		return out

	return {
		"properties": {name: said(spec) for name, spec in PROPERTIES.items()},
		"sections": {name: str(label) for name, label in SECTIONS.items()},
		"kinds": {
			name: {**{k: v for k, v in kind.items() if k != "label"}, "label": str(kind["label"])} for name, kind in KINDS.items()
		},
		"slide": {name: said(spec) for name, spec in SLIDE.items()},
		"slide_defaults": SLIDE_DEFAULTS,
		"most": MOST,
	}
