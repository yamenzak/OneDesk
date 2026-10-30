"""A presentation's size, and slides drawn for one size redrawn for another
(AGENTS.md, Size). Every position and size follows its own axis; type,
borders and corners follow the smaller of the two, so words never grow past
their box. `frontend/src/slide/shim/resize.js` is the same rule in the
editor, for a layout inserted from a template of another size."""

import json
import re
from typing import Annotated

import frappe
from frappe import _

#: The sizes New Presentation and Slide Size offer, as `shim/frame.js` lists them.
SIZES = {
	"wide": (960, 540),
	"standard": (960, 720),
	"a4": (1123, 794),
	"a4-portrait": (794, 1123),
	"square": (960, 960),
	"tall": (540, 960),
}
LEAST, MOST = 200, 4000
FONT = re.compile(r"(font-size|letter-spacing):\s*(-?[\d.]+)px")


def size(width, height) -> tuple[int, int]:
	"""A size a presentation may be: whole pixels, neither side below 200 nor
	above 4000, and 960 by 540 when nothing sensible was asked. Pure."""
	try:
		width, height = int(float(width)), int(float(height))
	except (TypeError, ValueError):
		return SIZES["wide"]
	if width <= 0 or height <= 0:
		return SIZES["wide"]
	return (min(max(width, LEAST), MOST), min(max(height, LEAST), MOST))


def scaled(elements: list, sx: float, sy: float) -> list:
	"""The elements redrawn `sx` across and `sy` down. Pure."""
	least = min(sx, sy)
	out = []
	for one in elements or []:
		if not isinstance(one, dict):
			continue
		one = dict(one)
		for key, by in (("left", sx), ("top", sy), ("width", sx), ("height", sy)):
			if isinstance(one.get(key), int | float):
				one[key] = round(one[key] * by, 2)
		for key in ("borderWidth", "strokeWidth", "borderRadius", "blur"):
			if isinstance(one.get(key), int | float):
				one[key] = round(one[key] * least, 2)
		if isinstance(one.get("points"), list):
			one["points"] = [
				{**point, "x": round(point.get("x", 0) * sx, 2), "y": round(point.get("y", 0) * sy, 2)}
				for point in one["points"]
				if isinstance(point, dict)
			]
		if one.get("type") == "text" and isinstance(one.get("content"), str):
			one["content"] = FONT.sub(lambda m: f"{m[1]}: {round(float(m[2]) * least, 2)}px", one["content"])
		out.append(one)
	return out


def refit(rows, before: tuple[int, int], after: tuple[int, int]) -> None:
	"""Slide rows (anything with `elements` as JSON) redrawn from one size to
	another, in place."""
	if before == after:
		return
	sx, sy = after[0] / before[0], after[1] / before[1]
	for row in rows:
		elements = json.loads(row.get("elements") or "[]") if isinstance(row.get("elements"), str) else row.get("elements")
		row["elements"] = json.dumps(scaled(elements or [], sx, sy))


@frappe.whitelist(methods=["POST"])
def resize(
	name: Annotated[str, "The presentation."],
	width: Annotated[int, "The new width in pixels."],
	height: Annotated[int, "The new height in pixels."],
) -> dict:
	"""Make every slide another size, its contents redrawn to fit. What it
	was is kept as a version first, so it can be undone from Version
	History."""
	from onedesk.one_slide import api, guides, versions

	api._may(name, "write")
	doc = frappe.get_doc(api.PRESENTATION, name)
	before = api.frame(name)
	after = size(width, height)
	if before == after:
		return {"width": after[0], "height": after[1]}
	versions.keep_now(doc, _("Before changing the size"))
	doc.guides = json.dumps(guides.scaled(doc.guides, before, after))
	_redrawn(doc, before, after)
	from onedesk.one_slide import master

	if master.of(name):
		redrawn(master.of(name), before, after)
	return {"width": after[0], "height": after[1]}


def redrawn(name: str, before: tuple[int, int], after: tuple[int, int]) -> None:
	"""A presentation's slides redrawn at another size and kept, with no
	version: a master, whose presentation keeps the version."""
	from onedesk.one_slide import api

	_redrawn(frappe.get_doc(api.PRESENTATION, name), before, after)


def _redrawn(doc, before: tuple[int, int], after: tuple[int, int]) -> None:
	rows = [row.as_dict() for row in doc.slides]
	refit(rows, before, after)
	for row, drawn in zip(doc.slides, rows, strict=True):
		row.elements = drawn["elements"]
	doc.width, doc.height = after
	doc.save(ignore_permissions=True)
