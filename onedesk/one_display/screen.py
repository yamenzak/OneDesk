"""The channel builder (stage 7 of docs/ONESLIDE.md): a widget collection
edited in OneSlide's editor. Its backdrop is a one-slide presentation kept on
the collection; when the editor loads it, the collection's widgets join that
slide as `widget` elements, and when it saves, they leave it again as the
collection's rows. Called through the one_slide_loaded and one_slide_saving
hooks, so OneSlide knows nothing of widgets."""

import json
from typing import Annotated

import frappe
from frappe import _
from frappe.utils import cint, flt

from onedesk.one_display import layout, sizes

DOCTYPE = "Widget Collection"
WIDGET = "widget"
ABOVE = 1000
ROW = ("widget_type", "label", "source", "mapping", "settings", "shown", "from_time", "to_time")


def frame(collection) -> tuple[int, int]:
	return sizes.editor(collection)


@frappe.whitelist(methods=["POST"])
def backdrop(collection: Annotated[str, "The widget collection."]) -> dict:
	"""The presentation a collection is edited as, made the first time."""
	from onedesk.one_slide import api

	doc = frappe.get_doc(DOCTYPE, collection)
	doc.check_permission("write")
	held = doc.backdrop and frappe.db.get_value("File", doc.backdrop, "file_url")
	name = held and api.presentation_of(held)
	if name and frappe.db.exists(api.PRESENTATION, name):
		return {"presentation": name}
	file = api.make_with(f"@records/{DOCTYPE}/{doc.name}", _("{0} Screen").format(doc.collection_name or doc.name), [{"background": doc.background, "elements": []}])
	doc.db_set("backdrop", file)
	return {"presentation": api.presentation_of(frappe.db.get_value("File", file, "file_url"))}


def _of(item: dict):
	name = frappe.db.get_value(DOCTYPE, {"backdrop": item.get("name")}, "name") if item.get("name") else None
	return frappe.get_doc(DOCTYPE, name) if name else None


def loaded(doc: dict, item: dict) -> None:
	"""one_slide_loaded: a backdrop's one slide, with the widgets on it."""
	collection = _of(item)
	if not collection:
		return
	said = layout.get(collection.name)
	wide, high = frame(collection)
	doc["screen"] = {key: said[key] for key in ("name", "screen_size", "writable", "types", "sources")}
	# the frame the editor lays the screen out on (frontend/src/slide/shim/frame.js)
	doc["screen"]["frame"] = {"w": wide, "h": high}
	slides = (doc.get("slides") or [])[:1]
	if not slides:
		return
	first = slides[0]
	elements = [one for one in _parsed(first.get("elements")) if one.get("type") != WIDGET]
	for row in said["widgets"]:
		elements.append(
			{
				"id": f"w-{row['id']}",
				"type": WIDGET,
				"name": row.get("label") or "",
				"left": round(flt(row["x"]) / 100 * wide, 2),
				"top": round(flt(row["y"]) / 100 * high, 2),
				"width": round(flt(row["w"]) / 100 * wide, 2),
				"height": round(flt(row["h"]) / 100 * high, 2),
				"zIndex": ABOVE + cint(row.get("layer")),
				"widget": {"id": row["id"], **{key: row.get(key) for key in ROW}},
			}
		)
	first["elements"] = json.dumps(elements)
	first["background"] = collection.background or _brand()
	doc["slides"] = slides


def saving(name: str, item: dict, slides: list) -> list:
	"""one_slide_saving: the widgets written to the collection, and the
	backdrop's one slide without them."""
	collection = _of(item)
	if not collection or not slides:
		return slides
	first = dict(slides[0])
	elements = _parsed(first.get("elements"))
	wide, high = frame(collection)
	placed = sorted((one for one in elements if one.get("type") == WIDGET), key=lambda one: flt(one.get("zIndex")))
	widgets = []
	for layer, one in enumerate(placed, start=1):
		kept = one.get("widget") or {}
		widgets.append(
			{
				**{key: kept.get(key) for key in ROW},
				"id": kept.get("id"),
				"label": one.get("name") or kept.get("label") or "",
				"x": _percent(one.get("left"), wide),
				"y": _percent(one.get("top"), high),
				"w": _percent(one.get("width"), wide, least=0.5),
				"h": _percent(one.get("height"), high, least=0.5),
				"layer": layer,
				"shown": kept.get("shown") or "Always",
			}
		)
	ground = first.get("background") or ""
	layout.save(collection.name, widgets, background="" if ground == _brand() else ground)
	first["elements"] = json.dumps([one for one in elements if one.get("type") != WIDGET])
	return [first]


def _brand() -> str:
	"""The business's colour, which an empty background shows on a screen."""
	from onedesk.one_slide import convert

	company = frappe.db.get_default("company")
	return convert.colour(frappe.db.get_value("Company", company, "one_brand_colour") if company else "")


def _percent(value, of: int, least: float = -50) -> float:
	return round(min(max(flt(value) / of * 100, least), 150), 3)


def _parsed(value) -> list:
	if isinstance(value, list):
		return [one for one in value if isinstance(one, dict)]
	try:
		said = json.loads(value or "[]")
	except ValueError:
		return []
	return [one for one in said if isinstance(one, dict)] if isinstance(said, list) else []


def rows(one: dict) -> list | None:
	"""one_slide_rows: a presentation's `rows` source, a Display Source's rows
	as words, for chips on a screen's backdrop; None for a source not ours."""
	from onedesk.one_display import sources

	name = one.get("source")
	if one.get("kind") != "rows" or not name:
		return None
	if not frappe.db.exists(sources.DOCTYPE, name) or not frappe.has_permission(sources.DOCTYPE, "read", doc=name):
		return []
	fields = {field["fieldname"] for field in layout.fields(name)}
	return [row for row in sources.read(name, fields) if isinstance(row, dict)]


def drawn(collection, edge: int | None = None) -> dict | None:
	"""The backdrop as a screen draws it under the widgets: its one slide's
	elements, media sealed and nothing hidden, on the screen's own frame."""
	from onedesk.one_slide import api, play

	url = collection.backdrop and frappe.db.get_value("File", collection.backdrop, "file_url")
	name = url and api.presentation_of(url)
	if not name or not frappe.db.exists(api.PRESENTATION, name):
		return None
	slides = play.for_screen(name, 10, edge=edge)
	elements = slides[0]["slide"]["elements"] if slides else []
	if not elements:
		return None
	wide, high = frame(collection)
	said = {"width": wide, "height": high, "bare": 1, "elements": elements}
	# what it is, apart from the words its chips are filled with: a screen
	# rebuilds when this changes, and only redraws the backdrop when a chip does
	said["shape"] = f"{name}:{frappe.db.get_value(api.PRESENTATION, name, 'modified')}:{edge or ''}"
	said["live"] = 1 if frappe.db.get_value(api.PRESENTATION, name, "sources") not in (None, "", "[]") else 0
	return said
