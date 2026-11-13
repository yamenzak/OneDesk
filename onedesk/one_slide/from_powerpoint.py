"""A PowerPoint file as a presentation, the other way from powerpoint.build:
OneCloud's Open on a .pptx makes a presentation beside it from PowerPoint's
pieces (AGENTS.md, PowerPoint)."""

import html
import io
import json
import math
import uuid

import frappe
from frappe import _
from lxml import etree

from onedesk.one_slide.powerpoint import EMU, MASTER, POINT, SHAPES

SUFFIXES = (".pptx", ".ppsx")
DRAWN = {value: key for key, value in SHAPES.items()} | {"ROUNDED_RECTANGLE": "rectangle", "STAR_5_POINT": "star"}
SPACE = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
THEMED = {
	"TEXT_1": "dk1",
	"BACKGROUND_1": "lt1",
	"TEXT_2": "dk2",
	"BACKGROUND_2": "lt2",
	"DARK_1": "dk1",
	"LIGHT_1": "lt1",
	"DARK_2": "dk2",
	"LIGHT_2": "lt2",
	**{f"ACCENT_{n}": f"accent{n}" for n in range(1, 7)},
	"HYPERLINK": "hlink",
}
SCHEMED = {"tx1": "dk1", "bg1": "lt1", "tx2": "dk2", "bg2": "lt2"}
TITLE_SIZE, BODY_SIZE, PLAIN_SIZE = 44, 24, 18


def theme_colours(deck) -> dict:
	"""The deck's theme colours by name (dk1, accent1, …), as #RRGGBB."""
	from pptx.opc.constants import RELATIONSHIP_TYPE as RT

	try:
		theme = etree.fromstring(deck.slide_master.part.part_related_by(RT.THEME).blob)
	except (KeyError, etree.XMLSyntaxError):
		return {}
	out = {}
	for slot in theme.iterfind(".//a:clrScheme/*", SPACE):
		name = etree.QName(slot).localname
		found = slot.find("a:srgbClr", SPACE)
		system = slot.find("a:sysClr", SPACE)
		value = found.get("val") if found is not None else system.get("lastClr") if system is not None else None
		if value:
			out[name] = "#" + value.upper()
	return out


def colour(color, theme: dict) -> str | None:
	"""A python-pptx colour as #RRGGBB, its theme's when it names one."""
	try:
		kind = color.type
	except (AttributeError, TypeError):
		return None
	if kind is None:
		return None
	try:
		if kind == 1:
			return f"#{color.rgb}"
		if kind == 2:
			return theme.get(THEMED.get(color.theme_color.name, ""))
	except (AttributeError, KeyError, TypeError, ValueError):
		return None
	return None


def _filled(fill, theme: dict) -> str | None:
	try:
		if fill.type == 1:
			return colour(fill.fore_color, theme)
	except (AttributeError, TypeError, NotImplementedError):
		return None
	return None


def styled(shape, ref: str, theme: dict) -> str | None:
	"""The theme colour a shape's own style gives its fill, line or words
	(fillRef, lnRef, fontRef), which python-pptx leaves unread."""
	found = shape._element.find(f"{{http://schemas.openxmlformats.org/presentationml/2006/main}}style/a:{ref}/a:schemeClr", SPACE)
	if found is None:
		return None
	name = found.get("val") or ""
	return theme.get(SCHEMED.get(name, name))


def _px(emu) -> float:
	return round((emu or 0) / EMU, 2)


def _default_size(shape) -> float:
	if not shape.is_placeholder:
		return PLAIN_SIZE
	kind = str(shape.placeholder_format.type or "")
	return TITLE_SIZE if "TITLE" in kind and "SUB" not in kind else BODY_SIZE


def _run(run, size: float, theme: dict, ink: str | None = None) -> str:
	text = html.escape(run.text or "")
	if not text:
		return ""
	font = run.font
	style = [f"font-size: {round(((font.size.pt if font.size else size)) / POINT)}px"]
	if colour(font.color, theme) or ink:
		style.append(f"color: {colour(font.color, theme) or ink}")
	if font.name:
		style.append(f"font-family: {html.escape(font.name)}")
	if font.bold:
		text = f"<strong>{text}</strong>"
	if font.italic:
		text = f"<em>{text}</em>"
	if font.underline:
		text = f"<u>{text}</u>"
	return f'<span style="{"; ".join(style)}">{text}</span>'


def _bulleted(paragraph) -> bool:
	props = paragraph._p.pPr
	if props is None:
		return False
	return props.find("{%s}buChar" % SPACE["a"]) is not None or props.find("{%s}buAutoNum" % SPACE["a"]) is not None


ALIGNED = {1: "left", 2: "center", 3: "right", 4: "justify"}


def words(frame, size: float, theme: dict, ink: str | None = None, align: str | None = None) -> str:
	"""A text frame as the editor's HTML: paragraphs with their alignment,
	bullets as a list, runs with their size, colour, font and weight."""
	out, listed = [], False
	for paragraph in frame.paragraphs:
		said = "".join(_run(run, size, theme, ink) for run in paragraph.runs) or "<br>"
		aligned = ALIGNED.get(int(paragraph.alignment)) if paragraph.alignment is not None else align
		block = f'<p style="text-align: {aligned}">{said}</p>' if aligned else f"<p>{said}</p>"
		bullet = _bulleted(paragraph) and said != "<br>"
		if bullet and not listed:
			out.append("<ul>")
		if not bullet and listed:
			out.append("</ul>")
		listed = bullet
		out.append(f"<li>{block}</li>" if bullet else block)
	if listed:
		out.append("</ul>")
	return "".join(out)


def _table(table) -> str:
	rows = []
	for row in table.rows:
		cells = "".join(f"<td>{html.escape(cell.text or '').replace(chr(10), '<br>')}</td>" for cell in row.cells)
		rows.append(f"<tr>{cells}</tr>")
	return f"<table>{''.join(rows)}</table>"


def _unfilled(shape) -> bool:
	"""Whether the shape says nothing of its fill, so its style decides."""
	try:
		return shape.fill.type is None
	except (AttributeError, TypeError, NotImplementedError):
		return False


def _shape_kind(shape) -> str | None:
	try:
		return DRAWN.get(shape.auto_shape_type.name) if shape.shape_type == 1 else None
	except (AttributeError, ValueError, NotImplementedError):
		return None


def element(shape, theme: dict, keep, offset=(0, 0, 1, 1)) -> dict | None:
	"""One PowerPoint shape as one of the editor's elements, or None when
	the editor has nothing like it (a chart, SmartArt, a video)."""
	dx, dy, sx, sy = offset
	box = {
		"id": str(uuid.uuid4()),
		"left": round(dx + _px(shape.left) * sx, 2),
		"top": round(dy + _px(shape.top) * sy, 2),
		"width": round(_px(shape.width) * sx, 2),
		"height": round(_px(shape.height) * sy, 2),
	}
	if shape.rotation:
		box["rotation"] = round(shape.rotation, 2)
	if getattr(shape, "has_table", False) and shape.has_table:
		return {**box, "type": "table", "content": _table(shape.table)}
	if shape.shape_type == 13 or (shape.is_placeholder and hasattr(shape, "image")):
		try:
			picture = shape.image
		except (AttributeError, ValueError):
			return None
		return {**box, "type": "image", "src": keep(f"{shape.name or 'Picture'}.{picture.ext}", picture.blob)}
	if getattr(shape, "begin_x", None) is not None:
		stroke = max(1, round(shape.line.width.pt / POINT) if shape.line.width else 1)
		x1, y1 = dx + _px(shape.begin_x) * sx, dy + _px(shape.begin_y) * sy
		x2, y2 = dx + _px(shape.end_x) * sx, dy + _px(shape.end_y) * sy
		length = math.hypot(x2 - x1, y2 - y1)
		box.update(left=round((x1 + x2) / 2 - length / 2, 2), top=round((y1 + y2) / 2 - stroke / 2, 2), width=round(length, 2), height=stroke)
		box.pop("rotation", None)
		turn = round(math.degrees(math.atan2(y2 - y1, x2 - x1)), 2)
		if turn:
			box["rotation"] = turn
		return {**box, "type": "shape", "shapeType": "line", "strokeWidth": stroke, "strokeColor": (colour(shape.line.color, theme) or "#000000") + "FF"}
	text = shape.text_frame.text.strip() if getattr(shape, "has_text_frame", False) and shape.has_text_frame else ""
	kind = _shape_kind(shape)
	fill = (_filled(shape.fill, theme) or (styled(shape, "fillRef", theme) if _unfilled(shape) else None)) if kind else None
	if kind and (fill or not text):
		drawn = {**box, "type": "shape", "shapeType": kind, "fillColor": (fill + "FF") if fill else "#00000000"}
		try:
			stroke = colour(shape.line.color, theme) if shape.line.fill.type == 1 else None if shape.line.fill.type is not None else styled(shape, "lnRef", theme)
		except (AttributeError, TypeError):
			stroke = None
		if stroke:
			drawn.update(strokeColor=stroke + "FF", strokeWidth=max(1, round(shape.line.width.pt / POINT) if shape.line.width else 1))
		if shape.auto_shape_type.name == "ROUNDED_RECTANGLE":
			drawn["borderRadius"] = round(min(box["width"], box["height"]) * 0.17)
		if text:
			drawn["content"] = words(shape.text_frame, _default_size(shape), theme, styled(shape, "fontRef", theme), "center")
		return drawn
	if text:
		return {**box, "type": "text", "content": words(shape.text_frame, _default_size(shape), theme)}
	return None


def _walk(shapes, theme: dict, keep, offset=(0, 0, 1, 1)):
	"""Every shape on a slide, a group's in the slide's own place. Yields
	(element or None, shape)."""
	for shape in shapes:
		if shape.shape_type == 6:
			xfrm = shape._element.grpSpPr.find("{%s}xfrm" % SPACE["a"])
			child = xfrm.find("{%s}chOff" % SPACE["a"]) if xfrm is not None else None
			extent = xfrm.find("{%s}chExt" % SPACE["a"]) if xfrm is not None else None
			sx = (shape.width / int(extent.get("cx"))) if extent is not None and int(extent.get("cx")) else 1
			sy = (shape.height / int(extent.get("cy"))) if extent is not None and int(extent.get("cy")) else 1
			cx = int(child.get("x")) if child is not None else 0
			cy = int(child.get("y")) if child is not None else 0
			dx, dy, osx, osy = offset
			inner = (dx + (_px(shape.left) - _px(cx) * sx) * osx, dy + (_px(shape.top) - _px(cy) * sy) * osy, osx * sx, osy * sy)
			yield from _walk(shape.shapes, theme, keep, inner)
			continue
		try:
			yield element(shape, theme, keep, offset), shape
		except Exception:
			yield None, shape


def _background(slide, theme: dict) -> str:
	try:
		if not slide.follow_master_background:
			return _filled(slide.background.fill, theme) or ""
		return _filled(slide.slide_layout.slide_master.background.fill, theme) or ""
	except (AttributeError, TypeError, NotImplementedError):
		return ""


def read(content: bytes, keep, mastered: bool = False) -> tuple[int, int, list[dict], list[int]]:
	"""A .pptx's size in pixels, its slides as the editor keeps them, and the
	numbers of the slides that lost something the editor has nothing like.
	`keep(file_name, bytes)` keeps a picture and answers its address. For a
	presentation with a master, the master's shapes (powerpoint.MASTER) are
	left to the master."""
	from pptx import Presentation as Deck

	deck = Deck(io.BytesIO(content))
	theme = theme_colours(deck)
	slides, lost = [], []
	for number, slide in enumerate(deck.slides, start=1):
		drawn, missed = [], False
		for made, _shape in _walk(slide.shapes, theme, keep):
			if mastered and str(_shape.name or "").startswith(MASTER):
				continue
			if made is None:
				missed = missed or not (getattr(_shape, "has_text_frame", False) and not _shape.text_frame.text.strip())
				continue
			made["zIndex"] = len(drawn) + 1
			drawn.append(made)
		if missed:
			lost.append(number)
		notes = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide and slide.notes_slide.notes_text_frame else ""
		slides.append({"client_id": str(uuid.uuid4()), "background": _background(slide, theme), "elements": drawn, "notes": notes})
	return _px(deck.slide_width), _px(deck.slide_height), slides, lost


def of_file(file: str) -> str | None:
	"""The presentation already made from a PowerPoint File, if it is still there."""
	from onedesk.one_slide import api

	return frappe.db.get_value(api.PRESENTATION, {"from_file": file}, "name")


@frappe.whitelist(methods=["POST"])
def open_file(file: str) -> dict:
	"""The presentation made from a .pptx File, beside it, the first time it
	is opened; afterwards the same one."""
	from onedesk.one_slide import api, play
	from onedesk.one_cloud import api as cloud
	from onedesk.one_cloud import namespace as ns

	item = ns.row(file)
	if not item or item.get("is_folder") or item.get("one_deleted_on") or not ns.may(item, "read"):
		frappe.throw(_("This file cannot be opened."), frappe.PermissionError)
	name = item.get("file_name") or ""
	if not name.lower().endswith(SUFFIXES):
		frappe.throw(_("Only PowerPoint files can be opened as a presentation."))
	held = of_file(file)
	if held and ns.may(api._file(held), "read"):
		return {"presentation": held, "made": False}
	folder = item.get("folder")
	parent = folder if folder and ns.may(ns.row(folder) or {}, "add") else ns.home()
	content = cloud._content(item)
	try:
		from pptx import Presentation as Deck

		Deck(io.BytesIO(content))
	except Exception:
		frappe.throw(_("Could not read {0}.").format(name))
	made = api.make(parent, name.rsplit(".", 1)[0])
	doc = frappe.get_doc(api.PRESENTATION, made["presentation"])
	width, height, slides, lost = read(content, lambda file_name, blob: api.MEDIA + api._kept(doc.name, file_name, blob)["name"])
	doc.width, doc.height, doc.from_file = round(width), round(height), file
	doc.set("slides", [{**one, "background": play.background(one["background"]), "elements": play.cleaned(json.dumps(one["elements"]))} for one in slides])
	doc.save(ignore_permissions=True)
	return {"presentation": doc.name, "made": True, "lost": lost}
