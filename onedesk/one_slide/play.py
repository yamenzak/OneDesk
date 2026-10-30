"""What a slide holds, made safe to keep and to show. Every save passes each
element through `cleaned`: a text element's HTML is sanitised as any HTML
from a browser is, an address that is not a page's, a file's or ours is
dropped, and the Builder half (free CSS, blur, a fade, a name) is held to
`css.json`, the rules the editor reads too. README, api.py.
"""

import json
import re
from pathlib import Path

from frappe.utils import strip_html
from frappe.utils.html_utils import sanitize_html

#: Addresses a picture, a video or a poster may come from.
SAFE = ("/api/method/onedesk.one_slide.api.media?id=", "/assets/", "/files/", "/private/files/", "https://", "data:image/")

#: The free CSS rules, shared with the editor (`frontend/src/slide/shim/looks.js`).
RULES = json.loads((Path(__file__).parent / "css.json").read_text())

COLOUR = re.compile(r"^(#[0-9a-fA-F]{3,8}|transparent|rgba?\([\d\s.,%]+\))$")
FADE = re.compile(r"^linear-gradient\((-?\d+)deg, ([^,]+), ([^,]+)\)$")


def cleaned(elements) -> str:
	"""The editor's elements, as kept. Pure but for the sanitiser."""
	held = json.loads(elements or "[]") if isinstance(elements, str) else elements or []
	if not isinstance(held, list):
		return "[]"
	return json.dumps([_element(one) for one in held if isinstance(one, dict)])


def css(text) -> str:
	"""A free CSS box with only the declarations `css.json` allows. Pure."""
	if not isinstance(text, str) or len(text) > RULES["longest"]:
		return ""
	kept = []
	for declaration in text.split(";"):
		prop, colon, value = declaration.partition(":")
		prop, value = prop.strip().lower(), re.sub(r"(?i)!important", "", value).strip()
		lower = value.lower()
		if not colon or prop not in RULES["properties"] or not value or len(value) > RULES["longestValue"]:
			continue
		if any(word in lower for word in RULES["refused"]):
			continue
		kept.append(f"{prop}: {value}")
	return "; ".join(kept)


def background(value) -> str:
	"""A slide's background: a colour or a two-colour fade, else nothing. Pure."""
	value = (value or "").strip() if isinstance(value, str) else ""
	fade = FADE.match(value)
	if fade and COLOUR.match(fade[2].strip()) and COLOUR.match(fade[3].strip()):
		return value
	return value if COLOUR.match(value) else ""


def _element(one: dict) -> dict:
	if one.get("type") == "text" and isinstance(one.get("content"), str):
		one["content"] = sanitize_html(one["content"], always_sanitize=True)
	for key in ("src", "poster"):
		if isinstance(one.get(key), str) and one[key] and not one[key].startswith(SAFE):
			one[key] = ""
	_looks(one)
	return one


def _looks(one: dict) -> None:
	if "css" in one:
		one["css"] = css(one["css"]) or None
	if "blur" in one:
		blur = one["blur"] if isinstance(one["blur"], int | float) else 0
		one["blur"] = max(0, min(blur, RULES["mostBlur"])) or None
	fade = one.get("fade")
	if fade is not None:
		fine = isinstance(fade, dict) and COLOUR.match(str(fade.get("to", "")))
		one["fade"] = {"to": fade["to"], "angle": _angle(fade.get("angle"))} if fine else None
	if "name" in one:
		one["name"] = strip_html(str(one["name"] or "")).strip()[:140] or None
	if "hidden" in one:
		one["hidden"] = True if one["hidden"] else None
	for key in [key for key in ("css", "blur", "fade", "name", "hidden") if one.get(key) is None]:
		one.pop(key, None)


def _angle(value) -> int:
	try:
		return int(value) % 360
	except (TypeError, ValueError):
		return 180
