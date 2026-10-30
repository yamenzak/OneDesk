"""Number and List are words on a screen now (D4 of SCRATCHPAD.md). A figure
or a list from a Display Source is a text in the screen's editor whose
chips the source fills (one_slide/data.py, a `rows` source), styled like
any text, so there is no widget to learn for it. This writes the old
widgets as such texts on a collection's backdrop, for the patch that moves
them and for the demo."""

import json
import re

import frappe

from onedesk.one_display import screen, sizes

FIELD = re.compile(r"\{([a-z0-9_]+)\}")
SCREEN_HIGH = 1080


def key_for(source: str, taken: set) -> str:
	"""A chip's key for a source, as data.KEY allows, once each. Pure."""
	base = re.sub(r"[^a-z0-9]+", "_", (source or "data").lower()).strip("_")[:24] or "data"
	base = base if base[0].isalpha() else f"x{base}"[:24]
	key, n = base, 2
	while key in taken:
		key, n = f"{base}_{n}", n + 1
	taken.add(key)
	return key


def chipped(template: str, key: str, row: int | None = None) -> str:
	"""`{field}` in a widget's mapping as a chip of that source: of its first
	row, or of row `row`. Pure."""
	at = f"{row}." if row else ""
	return FIELD.sub(lambda m: "{" + f"{key}.{at}{m[1]}" + "}", template or "")


def number(key: str, mapping: dict, label: str, box: tuple) -> list[dict]:
	"""A figure, large, with what it counts under it, where the widget was. Pure."""
	x, y, w, h = box
	tall = h / 100 * SCREEN_HIGH
	value = chipped(mapping.get("value") or "{value}", key)
	said = [{"kind": "text", "x": x, "y": y, "w": w, "text": value, "size": round(tall * 0.5), "weight": 700, "colour": "#FFFFFF", "line": 1}]
	words = chipped(mapping.get("label") or "", key) or label
	if words:
		said.append({"kind": "text", "x": x, "y": y + h * 0.62, "w": w, "text": words, "size": round(tall * 0.16), "weight": 500, "colour": "#FFFFFF", "line": 1.1})
	return said


def listed(key: str, mapping: dict, heading: str, rows: int, box: tuple) -> list[dict]:
	"""A heading and one line for each row a list may hold, where it was. Pure."""
	x, y, w, h = box
	tall = h / 100 * SCREEN_HIGH
	lines = max(1, min(rows or 6, 12))
	# a line and a half for each row and the heading, with room for one to wrap
	size = round(min(tall / (lines + 3) / 1.45, 40))
	said = []
	if heading:
		said.append({"kind": "text", "x": x, "y": y, "w": w, "text": heading.upper(), "size": round(size * 0.6), "weight": 600, "spacing": 0.15, "colour": "#FFFFFF"})
	title, under = mapping.get("title") or "", mapping.get("subtitle") or mapping.get("value") or ""
	body = "\n".join(
		" · ".join(part for part in (chipped(title, key, n), chipped(under, key, n)) if part) for n in range(1, lines + 1)
	)
	said.append({"kind": "text", "x": x, "y": y + (h * 0.12 if heading else 0), "w": w, "text": body, "size": size, "weight": 500, "colour": "#FFFFFF", "line": 1.45})
	return said


def onto(collection: str, blocks: list[dict], sources: list[dict]) -> None:
	"""The blocks drawn as texts on the collection's backdrop, behind its
	widgets, and their sources added to the backdrop's."""
	from onedesk.one_slide import api, convert, data

	doc = frappe.get_doc("Widget Collection", collection)
	name = screen.backdrop(collection)["presentation"]
	held = frappe.get_doc(api.PRESENTATION, name)
	wide, high = sizes.editor(doc)
	drawn = convert.slide({"blocks": blocks}, wide, high)["elements"]
	slide = held.slides[0]
	kept = json.loads(slide.elements or "[]")
	lowest = min([one.get("zIndex") or 1 for one in kept] or [1])
	for at, one in enumerate(drawn):
		one["zIndex"] = lowest + at
	slide.elements = json.dumps(kept + drawn)
	known = data.cleaned(held.sources)
	held.sources = json.dumps(data.cleaned(known + [one for one in sources if one["key"] not in {k["key"] for k in known}]))
	held.save(ignore_permissions=True)


def widget_blocks(rows: list) -> tuple[list[dict], list[dict]]:
	"""Old Number and List rows as blocks and the sources their chips read."""
	taken, keys, blocks, sources = set(), {}, [], []
	for row in rows:
		settings = json.loads(row.settings or "{}") if isinstance(row.settings, str) else row.settings or {}
		mapping = json.loads(row.mapping or "{}") if isinstance(row.mapping, str) else row.mapping or {}
		if not row.source:
			continue
		if row.source not in keys:
			keys[row.source] = key_for(row.source, taken)
			sources.append({"key": keys[row.source], "kind": "rows", "source": row.source, "limit": 12})
		box = (row.x or 0, row.y or 0, row.w or 20, row.h or 20)
		if row.widget_type == "Number":
			blocks += number(keys[row.source], mapping, settings.get("label") or "", box)
		else:
			blocks += listed(keys[row.source], mapping, settings.get("heading") or "", int(settings.get("rows") or 6), box)
	return blocks, sources
