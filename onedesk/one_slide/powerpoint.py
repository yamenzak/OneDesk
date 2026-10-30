"""A presentation as a PowerPoint file, made of PowerPoint's own pieces so it
can be edited there: words with their font, size, colour and weight, shapes,
lines, pictures, videos, tables, backgrounds and notes (AGENTS.md,
PowerPoint)."""

import base64
import io
import json
import math
import re
from html.parser import HTMLParser
from typing import Annotated

import frappe

#: A pixel on a slide, in PowerPoint's units: 96 to the inch.
EMU = 9525
#: A pixel of type, in points.
POINT = 0.75

COLOUR = re.compile(r"#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?")
RGB = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)")
FADE = re.compile(r"linear-gradient\(\s*(-?[\d.]+)deg\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)$")
TURN = re.compile(r"rotate\((-?[\d.]+)deg\)")
BLOCKS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li"}


def rgb(value) -> tuple[int, int, int] | None:
	"""A colour as red, green and blue, or None for none or a clear one. Pure."""
	value = str(value or "").strip()
	found = COLOUR.search(value)
	if found:
		if found[2] and int(found[2], 16) == 0:
			return None
		raw = found[1]
		return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
	found = RGB.search(value)
	return (int(found[1]), int(found[2]), int(found[3])) if found else None


class _Words(HTMLParser):
	"""A text's HTML as paragraphs of runs, each run with its look."""

	def __init__(self):
		super().__init__(convert_charrefs=True)
		self.paragraphs = []
		self.looks = [{}]
		self.listed = 0

	def _paragraph(self, align=None):
		self.paragraphs.append({"align": align, "runs": [], "bullet": bool(self.listed)})

	def handle_starttag(self, tag, attrs):
		style = dict(attrs).get("style") or ""
		said = {
			key.strip().lower(): value.strip()
			for key, _colon, value in (part.partition(":") for part in style.split(";"))
			if _colon
		}
		look = dict(self.looks[-1])
		if tag in ("ul", "ol"):
			self.listed += 1
		if tag in BLOCKS and not (tag == "p" and self.paragraphs and not self.paragraphs[-1]["runs"] and self.paragraphs[-1]["bullet"]):
			self._paragraph(said.get("text-align"))
		elif tag == "p" and self.paragraphs:
			self.paragraphs[-1]["align"] = said.get("text-align") or self.paragraphs[-1]["align"]
		if tag in ("strong", "b") or tag.startswith("h") and tag[1:].isdigit():
			look["bold"] = True
		if tag in ("em", "i"):
			look["italic"] = True
		if tag == "u":
			look["underline"] = True
		if "font-size" in said:
			size = re.match(r"([\d.]+)px", said["font-size"])
			if size:
				look["size"] = float(size[1])
		if "font-family" in said:
			look["family"] = said["font-family"].split(",")[0].strip("'\" ")
		if "color" in said:
			look["color"] = rgb(said["color"])
		if said.get("font-weight") in ("bold", "600", "700", "800", "900"):
			look["bold"] = True
		if said.get("font-style") == "italic":
			look["italic"] = True
		if tag == "br":
			self._paragraph(self.paragraphs[-1]["align"] if self.paragraphs else None)
			return
		self.looks.append(look)

	def handle_endtag(self, tag):
		if tag in ("ul", "ol"):
			self.listed = max(0, self.listed - 1)
		if len(self.looks) > 1:
			self.looks.pop()

	def handle_data(self, data):
		if not data:
			return
		if not self.paragraphs:
			self._paragraph()
		self.paragraphs[-1]["runs"].append({"text": data, **self.looks[-1]})


def paragraphs(html: str) -> list[dict]:
	"""A text's paragraphs, each its alignment, whether it is a bullet, and
	its runs of words with their look. Pure."""
	reader = _Words()
	reader.feed(html or "")
	return [one for one in reader.paragraphs if one["runs"] or not one["bullet"]] or [{"align": None, "runs": [], "bullet": False}]


def _words_into(frame, html: str, direction: str | None = None) -> None:
	from pptx.dml.color import RGBColor
	from pptx.enum.text import PP_ALIGN
	from pptx.util import Pt

	aligned = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT, "justify": PP_ALIGN.JUSTIFY}
	frame.word_wrap = True
	for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
		setattr(frame, side, 0)
	for at, one in enumerate(paragraphs(html)):
		paragraph = frame.paragraphs[0] if at == 0 else frame.add_paragraph()
		if one["align"] in aligned:
			paragraph.alignment = aligned[one["align"]]
		if direction == "rtl":
			paragraph._p.get_or_add_pPr().set("rtl", "1")
		for said in one["runs"]:
			run = paragraph.add_run()
			run.text = ("• " if one["bullet"] and not paragraph.runs[:-1] else "") + said["text"]
			if said.get("size"):
				run.font.size = Pt(said["size"] * POINT)
			if said.get("family"):
				run.font.name = said["family"]
			if said.get("color"):
				run.font.color.rgb = RGBColor(*said["color"])
			run.font.bold = said.get("bold") or None
			run.font.italic = said.get("italic") or None
			run.font.underline = said.get("underline") or None


def _content(src: str) -> bytes | None:
	"""A picture's or video's bytes, if it is the presentation's or the site's own."""
	from onedesk.one_slide import api

	if not isinstance(src, str) or not src:
		return None
	if src.startswith("data:image/") and "," in src:
		return base64.b64decode(src.split(",", 1)[1])
	if src.startswith(api.MEDIA):
		file_id = src[len(api.MEDIA) :].split("&")[0]
		url = frappe.db.get_value("File", file_id, "file_url")
		return _stored(file_id, url) if url else None
	if src.startswith(("/files/", "/private/files/")):
		file_id = frappe.db.get_value("File", {"file_url": src.split("?")[0]}, "name")
		return frappe.get_doc("File", file_id).get_content() if file_id else None
	return None


def _stored(file_id: str, url: str) -> bytes:
	from onedesk.one_storage import store

	if store.is_stored(url):
		return store.get(store.key_of(url))
	return frappe.get_doc("File", file_id).get_content()


def _fill(fill, colour, fade=None) -> None:
	from pptx.dml.color import RGBColor

	start = rgb(colour)
	end = rgb((fade or {}).get("to"))
	if start and end:
		fill.gradient()
		# a CSS angle (0 up, turning clockwise) as PowerPoint's (0 rightwards, turning the other way)
		fill.gradient_angle = (90 - float((fade or {}).get("angle") or 0)) % 360
		fill.gradient_stops[0].color.rgb = RGBColor(*start)
		fill.gradient_stops[1].color.rgb = RGBColor(*end)
	elif start:
		fill.solid()
		fill.fore_color.rgb = RGBColor(*start)
	else:
		fill.background()


def _background(slide, value) -> None:
	value = (value or "").strip()
	fade = FADE.match(value)
	if fade:
		_fill(slide.background.fill, fade[2], {"to": fade[3], "angle": float(fade[1])})
	elif rgb(value):
		_fill(slide.background.fill, value)


def _turn(element: dict) -> float:
	if element.get("rotation"):
		return float(element["rotation"])
	found = TURN.search(str(element.get("transform") or ""))
	return float(found[1]) if found else 0.0


SHAPES = {
	"rectangle": "RECTANGLE",
	"oval": "OVAL",
	"triangle": "ISOSCELES_TRIANGLE",
	"diamond": "DIAMOND",
	"pentagon": "REGULAR_PENTAGON",
	"star": "STAR_5_POINT",
	"blockArrow": "RIGHT_ARROW",
}


def _box(element: dict) -> tuple[int, int, int, int]:
	from pptx.util import Emu

	width = float(element.get("width") or 100)
	height = float(element.get("height") or 0)
	if not height and element.get("type") == "text":
		said = paragraphs(element.get("content") or "")
		sizes = [max([run.get("size") or 24 for run in one["runs"]] or [24]) for one in said]
		height = sum(size * 1.5 for size in sizes) or 36
	return Emu(round(float(element.get("left") or 0) * EMU)), Emu(round(float(element.get("top") or 0) * EMU)), Emu(round(width * EMU)), Emu(round((height or 1) * EMU))


def _drawn(slide, element: dict) -> bool:
	"""One element as PowerPoint's own piece; False when PowerPoint has nothing like it."""
	from pptx.dml.color import RGBColor
	from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
	from pptx.util import Emu, Pt

	kind = element.get("type")
	left, top, width, height = _box(element)
	if kind == "text":
		shape = slide.shapes.add_textbox(left, top, width, height)
		_words_into(shape.text_frame, element.get("content") or "", element.get("dir"))
	elif kind == "shape" and element.get("shapeType") == "line":
		stroke = float(element.get("strokeWidth") or 1)
		middle = (float(element.get("left") or 0) + float(element.get("width") or 0) / 2, float(element.get("top") or 0) + stroke / 2)
		turn = math.radians(float(element.get("rotation") or 0))
		half = (float(element.get("width") or 0) / 2 * math.cos(turn), float(element.get("width") or 0) / 2 * math.sin(turn))
		ends = [round((middle[0] - half[0]) * EMU), round((middle[1] - half[1]) * EMU), round((middle[0] + half[0]) * EMU), round((middle[1] + half[1]) * EMU)]
		shape = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, *(Emu(one) for one in ends))
		if rgb(element.get("strokeColor")):
			shape.line.color.rgb = RGBColor(*rgb(element.get("strokeColor")))
		shape.line.width = Pt(stroke * POINT)
		return not element.get("points")
	elif kind == "shape" and element.get("shapeType") in SHAPES:
		kind_of = SHAPES[element["shapeType"]]
		if kind_of == "RECTANGLE" and float(element.get("borderRadius") or 0) > 0:
			kind_of = "ROUNDED_RECTANGLE"
		shape = slide.shapes.add_shape(getattr(MSO_SHAPE, kind_of), left, top, width, height)
		if kind_of == "ROUNDED_RECTANGLE":
			shape.adjustments[0] = min(0.5, float(element["borderRadius"]) / max(1.0, min(float(element.get("width") or 1), float(element.get("height") or 1))))
		_fill(shape.fill, element.get("fillColor"), element.get("fade"))
		if rgb(element.get("strokeColor")) and float(element.get("strokeWidth") or 0) > 0:
			shape.line.color.rgb = RGBColor(*rgb(element.get("strokeColor")))
			shape.line.width = Pt(float(element["strokeWidth"]) * POINT)
		else:
			shape.line.fill.background()
		if element.get("content"):
			_words_into(shape.text_frame, element["content"], element.get("dir"))
	elif kind == "image":
		picture = _content(element.get("src"))
		if not picture:
			return False
		shape = slide.shapes.add_picture(io.BytesIO(picture), left, top, width, height)
	elif kind == "video":
		movie = _content(element.get("src"))
		if not movie:
			return False
		poster = _content(element.get("poster"))
		kind_of = "video/webm" if str(element.get("src")).lower().endswith(".webm") else "video/mp4"
		shape = slide.shapes.add_movie(io.BytesIO(movie), left, top, width, height, poster_frame_image=io.BytesIO(poster) if poster else None, mime_type=kind_of)
	elif kind == "table":
		from onedesk.one_slide import play

		rows = re.findall(r"<tr>(.*?)</tr>", play._table(element.get("content")), re.S)
		cells = [[re.sub(r"<br>", "\n", cell) for cell in re.findall(r"<t[dh]>(.*?)</t[dh]>", row, re.S)] for row in rows]
		if not cells or not cells[0]:
			return False
		count = max(len(row) for row in cells)
		shape = slide.shapes.add_table(len(cells), count, left, top, width, Emu(max(int(height), len(cells) * 40 * EMU))).table
		for r, row in enumerate(cells):
			for c, said in enumerate(row):
				shape.cell(r, c).text = frappe.utils.html2text(said).strip() if "<" in said else frappe.utils.html.unescape(said)
		return True
	else:
		return False
	turn = _turn(element)
	if turn:
		shape.rotation = turn
	return not (element.get("css") or element.get("blur"))


def build(name: str) -> tuple[bytes, list[int]]:
	"""The presentation as a .pptx, and the numbers of the slides that lost
	something PowerPoint has nothing like."""
	from pptx import Presentation as Deck
	from pptx.util import Emu

	from onedesk.one_slide import api, master

	doc = frappe.get_doc(api.PRESENTATION, name)
	width, height = api.frame(name)
	deck = Deck()
	deck.slide_width, deck.slide_height = Emu(width * EMU), Emu(height * EMU)
	blank = deck.slide_layouts[6]
	rows = master.under(name, [{"elements": row.elements, "hide_master": row.get("hide_master")} for row in doc.slides])
	lost = []
	for number, (row, kept) in enumerate(zip(doc.slides, rows, strict=True), start=1):
		slide = deck.slides.add_slide(blank)
		_background(slide, row.background)
		elements = [one for one in json.loads(kept["elements"] or "[]") if isinstance(one, dict) and not one.get("hidden")]
		whole = True
		for element in sorted(elements, key=lambda one: one.get("zIndex") or 0):
			try:
				whole = _drawn(slide, element) and whole
			except Exception:
				frappe.log_error(title="PowerPoint: an element was left out")
				whole = False
		if row.notes:
			slide.notes_slide.notes_text_frame.text = row.notes
		if not whole:
			lost.append(number)
	out = io.BytesIO()
	deck.save(out)
	return out.getvalue(), lost


@frappe.whitelist(methods=["POST"])
def export(name: Annotated[str, "The presentation."]) -> dict:
	"""The presentation as a PowerPoint file beside it in OneCloud, or on its
	record, and which slides lost something PowerPoint has nothing like."""
	from onedesk.one_slide import api, paper

	item = api._may(name, "read")
	content, lost = build(name)
	made = paper.beside(item, f"{item['file_name']}.pptx", content)
	return {**made, "lost": lost}
