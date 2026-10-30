"""Designed slides: a slide drawn as blocks on a 1920 × 1080 canvas (text, a
picture, a shape, a QR code), kept as JSON on the slide and drawn here into
the HTML the player plays. The designer (frontend/src/display/Slides.vue)
edits the blocks; nothing a person types reaches a screen unescaped."""

import html
import json
import re
from typing import Annotated

import frappe
from frappe import _
from frappe.utils import cint

DOCTYPE = "Slide Playlist"
COLOUR = re.compile(r"^#[0-9a-fA-F]{3,8}$")
MOST = 60
KEPT = ("kind", "title", "duration", "fit", "file", "url", "from_date", "to_date", "paused")

# What a new block starts as. Colours live here, not in the designer, so a
# screen's look is said in one place.
DEFAULTS = {
	"text": {"text": "", "size": 96, "weight": 700, "colour": "#ffffff", "align": "start", "line": 1.15, "upper": 0, "spacing": 0},
	"image": {"src": "", "fit": "cover", "radius": 0},
	"shape": {"fill": "#ffffff", "radius": 24, "opacity": 0.15},
	"qr": {"link": ""},
}
GROUND = "#0e6e8c"


def _colour(value, fallback: str = "") -> str:
	value = (value or "").strip()
	return value if COLOUR.match(value) else fallback


def _file(value) -> str:
	value = (value or "").strip()
	return value if value.startswith("/files/") else ""


def _span(value, low: float, high: float, default: float) -> float:
	try:
		return min(max(float(value), low), high)
	except (TypeError, ValueError):
		return default


def clean(design) -> dict:
	"""A design as the server will keep it: known kinds and keys only, each
	value in its range, colours as colours and pictures from the workspace's
	own files."""
	if isinstance(design, str):
		design = json.loads(design or "{}")
	design = design if isinstance(design, dict) else {}
	blocks = []
	for i, one in enumerate((design.get("blocks") or [])[:MOST]):
		if not isinstance(one, dict) or one.get("kind") not in DEFAULTS:
			continue
		kind = one["kind"]
		base = DEFAULTS[kind]
		block = {
			"id": re.sub(r"[^\w-]", "", str(one.get("id") or ""))[:20] or f"b{i}",
			"kind": kind,
			"x": _span(one.get("x"), 0, 99, 10),
			"y": _span(one.get("y"), 0, 99, 10),
			"w": _span(one.get("w"), 0.2, 100, 40),
			"h": _span(one.get("h"), 0.2, 100, 20),
		}
		if kind == "text":
			block.update(
				text=str(one.get("text") or "")[:2000],
				size=int(_span(one.get("size"), 8, 400, base["size"])),
				weight=cint(one.get("weight")) if cint(one.get("weight")) in (400, 600, 700, 800) else base["weight"],
				colour=_colour(one.get("colour"), base["colour"]),
				align=one.get("align") if one.get("align") in ("start", "center", "end") else base["align"],
				line=_span(one.get("line"), 0.8, 2.5, base["line"]),
				upper=1 if one.get("upper") else 0,
				spacing=_span(one.get("spacing"), 0, 0.5, 0),
			)
		elif kind == "image":
			block.update(src=_file(one.get("src")), fit=one.get("fit") if one.get("fit") in ("cover", "contain") else "cover", radius=int(_span(one.get("radius"), 0, 540, 0)))
		elif kind == "shape":
			block.update(fill=_colour(one.get("fill"), base["fill"]), radius=int(_span(one.get("radius"), 0, 960, base["radius"])), opacity=_span(one.get("opacity"), 0, 1, base["opacity"]))
		else:
			block.update(link=str(one.get("link") or "")[:1000])
		blocks.append(block)
	return {
		"orientation": "Portrait" if design.get("orientation") == "Portrait" else "Landscape",
		"background": _colour(design.get("background"), GROUND),
		"image": _file(design.get("image")),
		"blocks": blocks,
	}


def render(design) -> str:
	"""The design as the HTML a screen draws in its frame. Written for a 2017
	TV: no `inset`, no `gap`, flex only where Chromium 53 has it."""
	from onedesk.one_display.programme import _qr

	said = clean(design)
	ground = f"background:{said['background']};"
	if said["image"]:
		ground += f"background-image:url('{html.escape(said['image'], quote=True)}');background-size:cover;background-position:center;"
	parts = [f'<div style="position:absolute;top:0;left:0;right:0;bottom:0;overflow:hidden;{ground}">']
	for one in said["blocks"]:
		box = f"position:absolute;left:{one['x']}%;top:{one['y']}%;width:{one['w']}%;height:{one['h']}%;overflow:hidden;"
		if one["kind"] == "text":
			style = (
				f"{box}color:{one['colour']};font-size:{one['size']}px;font-weight:{one['weight']};"
				f"line-height:{one['line']};text-align:{one['align']};letter-spacing:{one['spacing']}em;"
				f"white-space:pre-wrap;word-wrap:break-word;{'text-transform:uppercase;' if one['upper'] else ''}"
			)
			parts.append(f'<div style="{style}">{html.escape(one["text"])}</div>')
		elif one["kind"] == "image" and one["src"]:
			parts.append(
				f'<div style="{box}border-radius:{one["radius"]}px;"><img src="{html.escape(one["src"], quote=True)}" '
				f'style="width:100%;height:100%;object-fit:{one["fit"]};display:block"></div>'
			)
		elif one["kind"] == "shape":
			parts.append(f'<div style="{box}background:{one["fill"]};border-radius:{one["radius"]}px;opacity:{one["opacity"]}"></div>')
		elif one["kind"] == "qr" and one["link"]:
			code = _qr(one["link"]).replace("<svg ", '<svg width="100%" height="100%" ', 1)
			parts.append(f'<div style="{box}">{code}</div>')
	parts.append("</div>")
	return "".join(parts)


def _row(row) -> dict:
	design = None
	if row.kind == "Design" and row.get("design"):
		try:
			design = clean(row.design)
		except ValueError:
			design = None
	return {
		"id": row.name,
		**{key: row.get(key) for key in KEPT},
		"design": design,
		"html": row.html if row.kind == "Design" and not design else None,
	}


@frappe.whitelist()
def get(playlist: Annotated[str, "The slide playlist."]) -> dict:
	"""A playlist's slides as the designer draws them."""
	doc = frappe.get_doc(DOCTYPE, playlist)
	doc.check_permission("read")
	return {
		"name": doc.name,
		"writable": doc.has_permission("write"),
		"slides": [_row(row) for row in doc.slides],
		"defaults": DEFAULTS,
		"ground": GROUND,
	}


@frappe.whitelist(methods=["POST"])
def save(
	playlist: Annotated[str, "The slide playlist."],
	slides: Annotated[str | list, "Its slides, in order, in the shape get() gives."],
	loaded: Annotated[str | list | None, "The ids of the slides the designer was given."] = None,
) -> dict:
	"""Write the designer's slides over the playlist's, keeping each row it
	knows by its id; a designed slide's HTML is drawn from its blocks. A slide
	added since the designer loaded (a video OneAI made meanwhile) is kept at
	the end rather than lost."""
	doc = frappe.get_doc(DOCTYPE, playlist)
	doc.check_permission("write")
	given = json.loads(slides) if isinstance(slides, str) else slides
	seen = set((json.loads(loaded) if isinstance(loaded, str) else loaded) or [row.name for row in doc.slides])
	known = {row.name: row for row in doc.slides}
	rows = []
	for one in given or []:
		values = {key: one.get(key) for key in KEPT}
		if values["kind"] not in ("Image", "Video", "Web Page", "Design"):
			frappe.throw(_("A slide is a picture, a video, a page or a design."))
		values["duration"] = cint(values["duration"]) or None
		if values["kind"] == "Design" and one.get("design"):
			values["design"] = json.dumps(clean(one["design"]), ensure_ascii=False)
		row = known.get(one.get("id"))
		if row:
			row.update(values)
			rows.append(row)
		else:
			rows.append(doc.append("slides", values))
	rows += [row for row in doc.slides if row.name not in seen and row not in rows]
	doc.set("slides", rows)
	doc.save()
	return get(playlist)


@frappe.whitelist()
def qr(link: Annotated[str, "What the code opens."]) -> str:
	"""A QR code as SVG, for the designer to draw while it is edited."""
	frappe.has_permission(DOCTYPE, "read", throw=True)
	from onedesk.one_display.programme import _qr

	return _qr((link or "")[:1000]) if link else ""


def drawn(doc, method=None) -> None:
	"""A designed slide's HTML is always its blocks drawn (Slide Playlist's
	validate), so the form, the designer and OneAI can't disagree."""
	for row in doc.slides:
		if row.kind == "Design" and row.get("design"):
			design = clean(row.design)
			row.design = json.dumps(design, ensure_ascii=False)
			row.html = render(design)
