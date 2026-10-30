"""What a slide holds, made safe to keep and to show. Every save passes each
element through `cleaned`: a text element's HTML is sanitised as any HTML
from a browser is, an address that is not a page's, a file's or ours is
dropped, and the Builder half (free CSS, blur, a fade, a name) is held to
`css.json`, the rules the editor reads too. AGENTS.md, api.py.
"""

import html
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


# What a screen is given (stage 5 of docs/ONESLIDE.md): a screen signs in as
# nobody, so the pictures and videos on a slide reach it at an address
# sealed with the site's key, which names the one file and nothing else.
SHOWN = "/api/method/onedesk.one_slide.api.shown?id="
MEDIA = "/api/method/onedesk.one_slide.api.media?id="
OPEN = ("/files/", "/assets/", "https://", "data:image/")


def seal(file_id: str) -> str:
	"""The seal on a file's address for screens. Pure but for the site key."""
	import hashlib
	import hmac

	from frappe.utils.password import get_encryption_key

	return hmac.new(get_encryption_key().encode(), f"one_slide:{file_id}".encode(), hashlib.sha256).hexdigest()[:32]


def _shown(src) -> str:
	if not isinstance(src, str) or not src:
		return ""
	if src.startswith(MEDIA):
		file_id = src[len(MEDIA) :].split("&")[0]
		return f"{SHOWN}{file_id}&sig={seal(file_id)}"
	return src if src.startswith(OPEN) else ""


def for_screen(name: str, seconds: int, reader: str | None = None) -> list[dict]:
	"""A presentation's slides as a screen plays them: each for as long as
	`length` says, its own transition, its media at sealed addresses, a table
	drawn to HTML, and nothing hidden. Records are read as `reader`."""
	import frappe

	doc = frappe.get_cached_doc("Presentation", name)
	width, height = int(doc.get("width") or 960), int(doc.get("height") or 540)
	from onedesk.one_slide import data, master

	drawn = master.under(name, [{"elements": row.elements, "hide_master": row.get("hide_master")} for row in doc.slides])
	# a screen has no reader: it shows what whoever made the presentation may read
	drawn = data.poured(name, drawn, reader or doc.owner)
	played = []
	for row, kept in zip(doc.slides, drawn, strict=True):
		elements = []
		for one in json.loads(kept["elements"] or "[]"):
			if not isinstance(one, dict) or one.get("hidden"):
				continue
			for key in ("src", "poster"):
				if key in one:
					one[key] = _shown(one[key])
			if one.get("type") == "table":
				one = {**one, "html": _table(one.get("content")), "content": None}
			elements.append(one)
		played.append(
			{
				"id": f"{name}-{row.idx}",
				"ms": int(length(elements, row.advance_after, seconds) * 1000),
				"transition": _transition(row.transition),
				"transition_ms": int(min(max(_seconds(row.transition_duration) or 0.8, 0), 3) * 1000),
				"slide": {"background": background(row.background), "elements": elements, "width": width, "height": height},
			}
		)
	return played


#: Suite's transitions as a screen draws them: Magic Move needs the editor,
#: so a screen fades instead.
TRANSITIONS = {"None": "none", "Fade": "fade", "Slide In": "slide", "Magic Move": "fade"}


def _transition(value) -> str:
	return TRANSITIONS.get(value or "", "fade")


def _seconds(value) -> float:
	try:
		said = float(value)
	except (TypeError, ValueError):
		return 0
	return said if said == said and said > 0 else 0


def length(elements: list, advance_after, seconds) -> float:
	"""How long a slide stays on a screen, in seconds, as the slideshow
	keeps it: a video that does not loop is watched to its end first, then
	the slide waits its own Advance; with neither, the row's seconds. The
	editor keeps a video's `length` when it loads it. Pure."""
	held = max([_seconds(one.get("length")) for one in elements if one.get("type") == "video" and not one.get("loop")] or [0])
	advance = _seconds(advance_after)
	stays = held + advance if held else advance or _seconds(seconds) or 10
	return max(round(stays, 1), 2)


def _table(content) -> str:
	"""Suite's table as a plain HTML table of its words: kept as HTML now, as a
	TipTap document before."""
	if isinstance(content, str) and content.lstrip().startswith("<"):
		from frappe.utils.html_utils import sanitize_html

		return sanitize_html(content, always_sanitize=True)
	if isinstance(content, str):
		try:
			content = json.loads(content)
		except ValueError:
			return ""

	def words(node) -> str:
		if not isinstance(node, dict):
			return ""
		if node.get("type") == "text":
			return html.escape(str(node.get("text") or ""))
		inside = "".join(words(child) for child in node.get("content") or [])
		return f"{inside}<br>" if node.get("type") == "paragraph" else inside

	def rows(node) -> list:
		if not isinstance(node, dict):
			return []
		if node.get("type") == "tableRow":
			return [node]
		return [row for child in node.get("content") or [] for row in rows(child)]

	drawn = []
	for row in rows(content):
		cells = []
		for cell in row.get("content") or []:
			tag = "th" if cell.get("type") == "tableHeader" else "td"
			cells.append(f"<{tag}>{words(cell).removesuffix('<br>')}</{tag}>")
		drawn.append(f"<tr>{''.join(cells)}</tr>")
	return f"<table>{''.join(drawn)}</table>" if drawn else ""
