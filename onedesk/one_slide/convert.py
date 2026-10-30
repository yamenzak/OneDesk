"""A designed slide, as OneDisplay's designer and OneAI's `display_design`
wrote it (blocks placed in percent of a 1920 by 1080 screen), redrawn as a
slide of Suite's elements on its 960 by 540 canvas. OneAI designs a slide
this way (`ai.design`), and stage 5 of docs/ONESLIDE.md turns every designed
slide a playlist holds into a presentation with it. Pure but for the QR code.
"""

import html
import math
import re
import uuid

WIDE, HIGH = 960, 540
SCREEN = 1920
COLOUR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
FONTS = {"sans": "Inter", "serif": "Georgia", "mono": "Courier Prime", "condensed": "Anton"}
SHAPES = {"ellipse": "oval", "arrow": "blockArrow"}
ALIGN = {"start": "left", "center": "center", "end": "right", "justify": "justify"}


def slide(design: dict) -> dict:
	"""`{"background", "elements"}` for one Suite slide. A portrait design
	stands in the middle of the wide slide at its own shape."""
	design = design if isinstance(design, dict) else {}
	portrait = design.get("orientation") == "Portrait"
	box = _box(portrait)
	elements = []
	if _file(design.get("image")):
		elements.append(_picture({"src": design["image"], "x": 0, "y": 0, "w": 100, "h": 100}, box))
		dim = _number(design.get("dim"), 0, 0, 0.9)
		if dim:
			elements.append(_shape({"shape": "rectangle", "fill": "#000000", "opacity": dim, "x": 0, "y": 0, "w": 100, "h": 100}, box))
	for one in design.get("blocks") or []:
		if not isinstance(one, dict):
			continue
		made = {"text": _text, "shape": _shape, "image": _picture, "qr": _qr}.get(one.get("kind"))
		if made:
			elements.append(made(one, box))
	for z, element in enumerate(elements, start=1):
		element["zIndex"] = z
	return {"background": _background(design), "elements": elements}


def _box(portrait: bool) -> dict:
	if not portrait:
		return {"left": 0, "top": 0, "width": WIDE, "height": HIGH, "scale": WIDE / SCREEN}
	width = HIGH * 9 / 16
	return {"left": (WIDE - width) / 2, "top": 0, "width": width, "height": HIGH, "scale": width / 1080}


def _number(value, default, least, most):
	try:
		number = float(value)
	except (TypeError, ValueError):
		return default
	return default if number != number else min(max(number, least), most)


def colour(value, default="") -> str:
	"""A colour as Suite keeps one: eight hex digits."""
	value = (value or "").strip() if isinstance(value, str) else ""
	if not COLOUR.match(value):
		return default
	digits = value[1:]
	if len(digits) == 3:
		digits = "".join(one * 2 for one in digits)
	return f"#{digits.upper()}{'' if len(digits) == 8 else 'FF'}"


def _background(design: dict) -> str:
	ground = colour(design.get("background"), "#0E6E8CFF")
	second = colour(design.get("background2"))
	if not second:
		return ground
	return f"linear-gradient({int(_number(design.get('angle'), 180, 0, 360))}deg, {ground}, {second})"


def _file(value) -> bool:
	return isinstance(value, str) and value.startswith(("/files/", "/private/files/", "/api/method/onedesk.one_slide.api.media?id="))


def _placed(one: dict, box: dict) -> dict:
	"""Where a block stands, in the slide's pixels, and what every element
	takes from it alike."""
	x, y = _number(one.get("x"), 10, -100, 200), _number(one.get("y"), 10, -100, 200)
	w, h = _number(one.get("w"), 40, 0.2, 300), _number(one.get("h"), 20, 0.2, 300)
	placed = {
		"id": uuid.uuid4().hex[:9],
		"left": round(box["left"] + x / 100 * box["width"], 2),
		"top": round(box["top"] + y / 100 * box["height"], 2),
		"width": round(w / 100 * box["width"], 2),
		"height": round(h / 100 * box["height"], 2),
		"opacity": round(_number(one.get("opacity"), 1, 0, 1) * 100),
	}
	if one.get("name"):
		placed["name"] = str(one["name"])[:140]
	for flag in ("hidden", "locked"):
		if one.get(flag) in (1, True, "1"):
			placed[flag] = True
	blur = _number(one.get("blur"), 0, 0, 60) * box["scale"]
	if blur:
		placed["blur"] = round(blur, 1)
	if one.get("css"):
		placed["css"] = str(one["css"])[:2000]
	return placed


def _turned(element: dict, one: dict) -> dict:
	rotation = _number(one.get("rotate"), 0, -360, 360)
	if rotation:
		element["rotation"] = rotation
	return element


def _shadow(element: dict, one: dict, box: dict) -> dict:
	shade = colour(one.get("shadow_colour"))
	if not shade:
		return element
	across, down = _number(one.get("shadow_x"), 0, -200, 200), _number(one.get("shadow_y"), 12, -200, 200)
	size = max(element.get("width") or 1, 1)
	element.update(
		shadowColor=shade[:7] + "FF",
		shadowOpacity=round(int(shade[7:9], 16) / 255 * 100),
		shadowBlur=round(_number(one.get("shadow_blur"), 40, 0, 300) * box["scale"] / size * 100, 2),
		shadowOffset=round(math.hypot(across, down) * box["scale"] / size * 100, 2),
		shadowAngle=round(math.degrees(math.atan2(down, across))),
	)
	return element


def _text(one: dict, box: dict) -> dict:
	element = _placed(one, box)
	scale = box["scale"]
	words = str(one.get("text") or "")[:2000]
	if one.get("upper") in (1, True, "1"):
		words = words.upper()
	style = "; ".join(
		[
			f"color: {colour(one.get('colour'), '#FFFFFFFF')}",
			f"font-size: {round(_number(one.get('size'), 96, 8, 600) * scale)}px",
			f"font-family: {FONTS.get(one.get('font'), 'Inter')}",
			f"font-weight: {int(_number(one.get('weight'), 700, 100, 900))}",
			f"letter-spacing: {round(_number(one.get('spacing'), 0, -0.1, 0.6) * _number(one.get('size'), 96, 8, 600) * scale, 2)}px",
		]
	)
	align = ALIGN.get(one.get("align"), "left")
	paragraphs = []
	for line in words.split("\n"):
		said = html.escape(line) or "<br>"
		if one.get("italic") in (1, True, "1"):
			said = f"<em>{said}</em>"
		if one.get("underline") in (1, True, "1"):
			said = f"<u>{said}</u>"
		paragraphs.append(f'<p style="text-align: {align};"><span style="{style}">{said}</span></p>')
	line = _number(one.get("line"), 1.15, 0.6, 3)
	element.update(
		type="text",
		content="".join(paragraphs),
		lineHeight=line,
		editorMetadata={"lineHeight": line},
		transform=f"rotate({_number(one.get('rotate'), 0, -360, 360)}deg)" if one.get("rotate") else "none",
		transformOrigin="center center" if one.get("rotate") else "top left",
	)
	element.pop("height", None)
	looks = []
	fill = colour(one.get("fill"))
	if fill:
		second = colour(one.get("fill2"))
		paint = f"linear-gradient({int(_number(one.get('angle'), 180, 0, 360))}deg, {fill}, {second})" if second else fill
		looks.append(f"background: {paint}")
	padding = _number(one.get("padding"), 0, 0, 400) * scale
	if padding:
		looks.append(f"padding: {round(padding)}px")
	stroke = _number(one.get("stroke"), 0, 0, 200) * scale
	if stroke:
		looks.append(f"border: {round(stroke, 1)}px {one.get('stroke_style') or 'solid'} {colour(one.get('stroke_colour'), '#FFFFFFFF')}")
	radius = _number(one.get("radius"), 0, 0, 960) * scale
	if radius:
		looks.append(f"border-radius: {round(radius)}px")
	shade = colour(one.get("shadow_colour"))
	if shade:
		looks.append(
			f"text-shadow: {round(_number(one.get('shadow_x'), 0, -200, 200) * scale)}px "
			f"{round(_number(one.get('shadow_y'), 12, -200, 200) * scale)}px "
			f"{round(_number(one.get('shadow_blur'), 40, 0, 300) * scale)}px {shade}"
		)
	if looks:
		element["css"] = "; ".join(filter(None, [element.get("css"), *looks]))
	return element


def _shape(one: dict, box: dict) -> dict:
	element = _turned(_placed(one, box), one)
	kind = SHAPES.get(one.get("shape"), one.get("shape") if one.get("shape") in ("rectangle", "triangle", "diamond", "star", "line") else "rectangle")
	stroke = round(_number(one.get("stroke"), 0, 0, 200) * box["scale"], 1)
	element.update(
		type="shape",
		shapeType=kind,
		fillColor=colour(one.get("fill"), "#FFFFFF33"),
		strokeColor=colour(one.get("stroke_colour"), "#FFFFFFFF"),
		strokeWidth=stroke,
		strokeStyle=one.get("stroke_style") if one.get("stroke_style") in ("dashed", "dotted") else "solid",
		borderRadius=round(_number(one.get("radius"), 0, 0, 960) * box["scale"]) if kind == "rectangle" else 0,
	)
	if kind == "line":
		element.update(strokeColor=colour(one.get("fill"), element["strokeColor"]), strokeWidth=max(stroke, element["height"]), markerStart="none", markerEnd="none")
		element["height"] = element["strokeWidth"]
	second = colour(one.get("fill2"))
	if second and kind != "line":
		element["fade"] = {"to": second, "angle": int(_number(one.get("angle"), 180, 0, 360))}
	return _shadow(element, one, box)


def _picture(one: dict, box: dict) -> dict:
	element = _turned(_placed(one, box), one)
	element.update(
		type="image",
		src=one["src"] if _file(one.get("src")) else "",
		borderRadius=round(_number(one.get("radius"), 0, 0, 960) * box["scale"]),
		borderWidth=round(_number(one.get("stroke"), 0, 0, 200) * box["scale"], 1),
		borderColor=colour(one.get("stroke_colour"), "#FFFFFFFF"),
		borderStyle=(one.get("stroke_style") or "solid") if one.get("stroke") else "none",
	)
	return _shadow(element, one, box)


def _qr(one: dict, box: dict) -> dict:
	"""A QR code is a picture of one, drawn now: Suite has no QR element."""
	import base64

	from onedesk.one_display.programme import _qr as drawn

	element = _picture({**one, "src": ""}, box)
	link = str(one.get("link") or "")[:1000]
	if link:
		element["src"] = "data:image/svg+xml;base64," + base64.b64encode(drawn(link).encode()).decode()
		element["name"] = element.get("name") or link[:140]
	return element
