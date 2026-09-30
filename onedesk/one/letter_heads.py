"""A letter head's top and foot, drawn from the company. docs/DESK-COVERAGE.md, stage 3.

frappe keeps a letter head's top as HTML, and ERPNext's own reads the
company's logo, name, address and contacts from the document as it prints. A
workspace's letter head may hold no template (print_html.letter_head_html),
so its top is drawn here instead: one of PRESETS, from what Workspace >
General keeps (the logo, the name, the company's own address, its phone,
email, website and tax ID, and its Brand Colour), showing what the
administrator ticked. The choice is kept on the letter head (`one_top`), and
the top is drawn again whenever the company or its address changes (`redraw`),
so a printed page always says what General says now.

The foot is drawn the same way, from FEET (`one_foot`, `draw_foot`). It carries
no page number: that is the print format's own (Print Format's Page Number),
which frappe draws on every page.

A top or foot written by hand, in frappe's builder, stays as it was written:
editing a drawn one there makes it hand-written (`apply`).
"""

import json
import re

import frappe
from frappe import _, _lt
from frappe.utils import cint, escape_html

#: The ways a top is laid out, in the order they are offered.
PRESETS = {
	"classic": _lt("Classic"),
	"centred": _lt("Centred"),
	"banner": _lt("Banner"),
	"minimal": _lt("Minimal"),
	"details": _lt("Logo and Details"),
	"logo": _lt("Logo Only"),
}

#: The ways a foot is laid out, in the order they are offered.
FEET = {
	"centred": _lt("Centred"),
	"split": _lt("Two Sides"),
	"band": _lt("Band"),
}

#: What a new foot shows.
FOOT_FIRST = ("name", "address", "phone", "email", "website")

#: How long a foot's note may be.
NOTE = 200

#: What a top may show beside the logo, in the order it is written.
SHOWN = {
	"name": _lt("Name"),
	"address": _lt("Address"),
	"phone": _lt("Phone"),
	"email": _lt("Email"),
	"website": _lt("Website"),
	"tax_id": _lt("Tax ID"),
}

#: What a new top shows.
SHOWN_FIRST = ("name", "address", "phone", "email", "website")

#: How the company is reached, and the icon each is shown with.
CONTACTS = (("phone", "phone"), ("email", "mail"), ("website", "globe"))

#: A colour as General's control writes one.
COLOUR = re.compile(r"^#[0-9a-fA-F]{3,8}$")

#: The colour a top has when General has none.
INK = "#111827"
MUTED = "#6b7280"

#: So a band of colour prints as it shows.
EXACT = "-webkit-print-color-adjust:exact;print-color-adjust:exact;"


def settings(raw) -> dict:
	"""A top's settings, as kept on the letter head, with what is missing filled."""
	said = raw if isinstance(raw, dict) else (frappe.parse_json(raw) if raw else None) or {}
	preset = said.get("preset") if said.get("preset") in PRESETS else "classic"
	shown = [one for one in (said.get("show") or SHOWN_FIRST) if one in SHOWN]
	return {
		"preset": preset,
		"show": shown,
		"logo_height": min(max(cint(said.get("logo_height")) or 60, 24), 160),
		# The line in the Brand Colour under the top, which every preset may leave out.
		"line": 1 if cint(said.get("line", 1)) else 0,
		"align": (said.get("align") or "left").lower()
		if (said.get("align") or "").lower() in ("left", "center", "right")
		else "left",
	}


def foot_settings(raw) -> dict:
	"""A foot's settings, as kept on the letter head, with what is missing filled."""
	said = raw if isinstance(raw, dict) else (frappe.parse_json(raw) if raw else None) or {}
	return {
		"preset": said.get("preset") if said.get("preset") in FEET else "centred",
		"show": [one for one in (said.get("show") or FOOT_FIRST) if one in SHOWN],
		# A line of the workspace's own, such as "Thank you for your business."
		"note": " ".join(str(said.get("note") or "").split())[:NOTE],
		"line": 1 if cint(said.get("line", 1)) else 0,
	}


def company() -> dict:
	"""What General keeps about the company, as a top shows it."""
	from onedesk.one import settings as workspace

	held = workspace._company()
	if not held:
		return {"name": "", "colour": INK, "address": []}
	address = workspace._company_address(held)
	place = []
	if address:
		place = [
			address.address_line1,
			address.address_line2,
			", ".join(one for one in (address.city, address.state, address.pincode) if one),
			address.country,
		]
	colour = held.get("one_brand_colour") or ""
	return {
		"name": held.company_name,
		"logo": held.company_logo,
		"address": [one for one in place if one],
		"phone": held.phone_no,
		"email": held.email,
		"website": held.website,
		"tax_id": held.tax_id,
		"colour": colour if COLOUR.match(colour) else INK,
	}


def draw(raw, details: dict | None = None) -> str:
	"""A top's HTML: its preset, from the company, showing what was ticked."""
	said = settings(raw)
	details = details or company()
	shown = set(said["show"])
	colour = details.get("colour") or INK
	e = lambda value: escape_html(str(value or ""))  # noqa: E731

	def logo(align: str = "left") -> str:
		if not details.get("logo"):
			return ""
		height = said["logo_height"]
		# Its width said outright: a printed page sizes a picture in a table cell
		# to the cell, not to the picture.
		ratio = _ratio(details["logo"])
		width = f"width:{round(height * ratio)}px;" if ratio else "width:auto;"
		return (
			f'<img src="{e(details["logo"])}" alt="{e(details.get("name"))}" '
			f'style="height:{height}px;{width}max-width:100%;display:inline-block">'
		)

	name = e(details.get("name")) if "name" in shown else ""
	address = [e(one) for one in details.get("address") or []] if "address" in shown else []
	# The tax ID on a line of its own: beside the contacts it wraps.
	tax = f"{e(_('Tax ID'))} {e(details['tax_id'])}" if "tax_id" in shown and details.get("tax_id") else ""
	small = f"font-size:11px;line-height:1.5;color:{MUTED};"
	rule = (
		f'<div style="height:2px;background:{colour};margin-top:12px;{EXACT}"></div>' if said["line"] else ""
	)

	# Each detail after its icon in the colour: the contacts on one line, kept
	# whole each, the address and the tax ID each on theirs.
	def icon(name: str, tint: str | None = None) -> str:
		return (
			f'<img src="{_icon(name, tint or colour)}" alt="" '
			'style="width:11px;height:11px;display:inline-block;vertical-align:-1px;margin-right:4px">'
		)

	gap = '<span style="display:inline-block;width:12px"></span>'
	contacts = [
		f'<span style="white-space:nowrap">{icon(glyph)}{e(details.get(key))}</span>'
		for key, glyph in CONTACTS
		if key in shown and details.get(key)
	]
	reach = gap.join(contacts)
	taxed = f"{icon('receipt')}{tax}" if tax else ""
	where = f"{icon('map-pin')}{', '.join(address)}" if address else ""

	preset = said["preset"]
	if preset == "logo":
		return f'<div style="text-align:{said["align"]}">{logo()}</div>{rule}'

	if preset == "centred":
		return (
			'<div style="text-align:center">'
			+ (f"<div>{logo()}</div>" if details.get("logo") else "")
			+ (
				f'<div style="font-size:18px;font-weight:700;color:{colour};margin-top:8px">{name}</div>'
				if name
				else ""
			)
			+ (f'<div style="{small}">{where}</div>' if where else "")
			+ (f'<div style="{small}">{reach}</div>' if reach else "")
			+ (f'<div style="{small}">{taxed}</div>' if taxed else "")
			+ "</div>"
			+ rule
		)

	if preset == "banner":
		return (
			f'<div style="background:{colour};color:#ffffff;padding:16px 20px;border-radius:6px;{EXACT}">'
			'<div style="display:table;width:100%">'
			f'<div style="display:table-cell;vertical-align:middle;text-align:left">{logo()}</div>'
			'<div style="display:table-cell;vertical-align:middle;text-align:right">'
			+ (f'<div style="font-size:20px;font-weight:700">{name}</div>' if name else "")
			+ (
				f'<div style="font-size:11px;opacity:0.85">{icon("map-pin", "#ffffff")}{", ".join(address)}</div>'
				if address
				else ""
			)
			+ "</div></div></div>"
			+ (
				f'<div style="{small}text-align:right;margin-top:6px">'
				+ "<br>".join(one for one in (reach, taxed) if one)
				+ "</div>"
				if reach or taxed
				else ""
			)
			+ rule
		)

	if preset == "minimal":
		# The logo, when there is one, beside the name, both over a line in the colour.
		mark = (
			f'<span style="display:inline-block;vertical-align:middle;margin-right:10px">{logo()}</span>'
			if details.get("logo")
			else ""
		)
		return (
			f'<div style="display:table;width:100%;{f"border-bottom:2px solid {colour}" if said["line"] else ""}">'
			'<div style="display:table-cell;vertical-align:bottom;text-align:left;padding-bottom:8px">'
			+ mark
			+ (
				f'<span style="display:inline-block;vertical-align:middle;font-size:18px;font-weight:700;color:{colour}">{name}</span>'
				if name
				else ""
			)
			+ "</div>"
			f'<div style="display:table-cell;vertical-align:bottom;padding-bottom:8px;text-align:right;{small}">'
			+ "<br>".join(one for one in (where, reach, taxed) if one)
			+ "</div></div>"
		)

	if preset == "details":
		# The logo, and beside it the name with the address under it; how to reach
		# the company on the right, each line after its icon.
		def line(glyph: str, text: str) -> str:
			return (
				'<div style="display:table;margin-bottom:3px">'
				'<div style="display:table-cell;width:17px;vertical-align:top;padding-top:2px">'
				f'<img src="{_icon(glyph, colour)}" alt="" style="width:11px;height:11px;display:block">'
				f'</div><div style="display:table-cell;vertical-align:top;white-space:nowrap">{text}</div></div>'
			)

		reached = "".join(
			line(glyph, e(details.get(key))) for key, glyph in CONTACTS if key in shown and details.get(key)
		) + (line("receipt", tax) if tax else "")
		held = (
			f'<div style="font-size:18px;font-weight:700;color:{colour}">{name}</div>' if name else ""
		) + (f'<div style="{small}color:#374151;margin-top:2px">{where}</div>' if where else "")
		return (
			'<div style="display:table;width:100%">'
			'<div style="display:table-cell;vertical-align:middle;text-align:left">'
			'<div style="display:table">'
			+ (
				f'<div style="display:table-cell;vertical-align:middle;padding-right:12px">{logo()}</div>'
				if details.get("logo")
				else ""
			)
			+ f'<div style="display:table-cell;vertical-align:middle">{held}</div>'
			"</div></div>"
			+ (
				'<div style="display:table-cell;vertical-align:middle;text-align:right">'
				f'<div style="display:inline-table;text-align:left;{small}color:#374151">{reached}</div></div>'
				if reached
				else ""
			)
			+ "</div>"
			+ rule
		)

	# Classic: the logo on the left, the company on the right, a line under both.
	left = logo() or (
		f'<div style="font-size:20px;font-weight:700;color:{colour}">{name}</div>' if name else ""
	)
	right = (
		(
			f'<div style="font-size:15px;font-weight:700;color:{colour}">{name}</div>'
			if name and details.get("logo")
			else ""
		)
		+ "".join(f"<div>{icon('map-pin') if not n else ''}{one}</div>" for n, one in enumerate(address))
		+ (f"<div>{reach}</div>" if reach else "")
		+ (f"<div>{taxed}</div>" if taxed else "")
	)
	return (
		'<div style="display:table;width:100%">'
		f'<div style="display:table-cell;vertical-align:middle;text-align:left;width:50%">{left}</div>'
		f'<div style="display:table-cell;vertical-align:middle;text-align:right;{small}color:#374151">{right}</div>'
		"</div>" + rule
	)


def draw_foot(raw, details: dict | None = None) -> str:
	"""A foot's HTML: its preset, from the company, showing what was ticked, with
	the note when there is one."""
	said = foot_settings(raw)
	details = details or company()
	shown = set(said["show"])
	colour = details.get("colour") or INK
	e = lambda value: escape_html(str(value or ""))  # noqa: E731
	small = f"font-size:10px;line-height:1.6;color:{MUTED};"
	gap = '<span style="display:inline-block;width:12px"></span>'

	def icon(name: str, tint: str | None = None) -> str:
		return (
			f'<img src="{_icon(name, tint or colour)}" alt="" '
			'style="width:10px;height:10px;display:inline-block;vertical-align:-1px;margin-right:4px">'
		)

	def details_of(tint: str | None = None) -> tuple[str, str, str, str]:
		name = f'<span style="font-weight:700;color:{tint or INK}">{e(details.get("name"))}</span>'
		address = details.get("address") or []
		return (
			name if "name" in shown and details.get("name") else "",
			f"{icon('map-pin', tint)}{e(', '.join(address))}" if "address" in shown and address else "",
			gap.join(
				f'<span style="white-space:nowrap">{icon(glyph, tint)}{e(details.get(key))}</span>'
				for key, glyph in CONTACTS
				if key in shown and details.get(key)
			),
			f'<span style="white-space:nowrap">{icon("receipt", tint)}{e(_("Tax ID"))} {e(details["tax_id"])}</span>'
			if "tax_id" in shown and details.get("tax_id")
			else "",
		)

	note = f'<span style="font-style:italic">{e(said["note"])}</span>' if said["note"] else ""
	rule = (
		f'<div style="height:2px;background:{colour};margin-bottom:8px;{EXACT}"></div>'
		if said["line"]
		else ""
	)

	def under(align: str) -> str:
		return f'<div style="margin-top:4px;text-align:{align};{small}">{note}</div>' if note else ""

	preset = said["preset"]
	if preset == "band":
		name, where, reach, taxed = details_of("#ffffff")
		lines = [
			gap.join(one for one in (name, where) if one),
			gap.join(one for one in (reach, taxed) if one),
		]
		band = "".join(f"<div>{one}</div>" for one in lines if one)
		return (
			f'<div style="background:{colour};color:#ffffff;padding:8px 16px;border-radius:4px;'
			f'text-align:center;font-size:10px;line-height:1.7;{EXACT}">{band}</div>'
			if band
			else ""
		) + under("center")

	name, where, reach, taxed = details_of()
	if preset == "split":
		left = "<br>".join(one for one in (name, where) if one)
		right = "<br>".join(one for one in (reach, taxed) if one)
		return (
			rule + f'<div style="display:table;width:100%;{small}color:#374151">'
			f'<div style="display:table-cell;vertical-align:top;text-align:left">{left}</div>'
			f'<div style="display:table-cell;vertical-align:top;text-align:right">{right}</div></div>'
			+ under("left")
		)

	# Centred: the company on one line, how to reach it on the next, then the note.
	lines = [
		gap.join(one for one in (name, where) if one),
		gap.join(one for one in (reach, taxed) if one),
		note,
	]
	return rule + (
		f'<div style="text-align:center;{small}color:#374151">'
		+ "".join(f"<div>{one}</div>" for one in lines if one)
		+ "</div>"
	)


#: Lucide, as frappe ships it to the desk.
SPRITE = ("frappe", "public", "icons", "lucide", "icons.svg")


def _icon(name: str, colour: str) -> str:
	"""One of frappe's Lucide icons, in the colour, as a picture a printed page
	may carry: an inline image, since a letter head holds no markup but HTML's."""
	import base64

	sprite = frappe.cache.get_value("one_lucide_sprite") or ""
	if not sprite:
		with open(frappe.get_app_path(*SPRITE)) as held:
			sprite = held.read()
		frappe.cache.set_value("one_lucide_sprite", sprite)
	found = re.search(rf'<symbol[^>]*id="icon-{re.escape(name)}"[^>]*>(.*?)</symbol>', sprite, re.S)
	drawn = (
		'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
		f'stroke="{colour}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
		f"{found.group(1) if found else ''}</svg>"
	)
	return "data:image/svg+xml;base64," + base64.b64encode(drawn.encode()).decode()


def _ratio(url: str) -> float | None:
	"""A picture's width over its height, read from the file: an SVG's viewBox or
	size, or a picture's pixels. None when it cannot be read."""
	cached = frappe.cache.hget("one_logo_ratio", url)
	if cached is not None:
		return cached or None
	ratio = 0.0
	try:
		content = None
		name = frappe.db.get_value("File", {"file_url": url}, "name")
		if name:
			content = frappe.get_doc("File", name).get_content()
		elif url.startswith("/files/"):
			with open(frappe.get_site_path("public", url.lstrip("/")), "rb") as held:
				content = held.read()
		if isinstance(content, str):
			content = content.encode()
		if content and (content.lstrip()[:5] in (b"<svg ", b"<?xml") or b"<svg" in content[:500]):
			text = content[:2000].decode(errors="ignore")
			box = re.search(r'viewBox="\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)', text)
			size = re.search(r'<svg[^>]*\swidth="([\d.]+)[^"]*"[^>]*\sheight="([\d.]+)', text)
			found = box or size
			if found and float(found.group(2)):
				ratio = float(found.group(1)) / float(found.group(2))
		elif content:
			from io import BytesIO

			from PIL import Image

			width, height = Image.open(BytesIO(content)).size
			ratio = width / height if height else 0.0
	except Exception:
		ratio = 0.0
	frappe.cache.hset("one_logo_ratio", url, ratio)
	return ratio or None


#: Each drawn part: its settings field, the fields frappe keeps it in, how it is
#: read, and how it is drawn.
PARTS = (
	("one_top", "source", "content", "image", settings, lambda raw, details=None: draw(raw, details)),
	(
		"one_foot",
		"footer_source",
		"footer",
		"footer_image",
		foot_settings,
		lambda raw, details=None: draw_foot(raw, details),
	),
)


def apply(doc) -> None:
	"""Letter Head validate, before anything checks the top or foot: a drawn one
	is drawn now; one the person changed by hand in the builder is theirs from
	then on."""
	before = doc.get_doc_before_save()
	for field, source, html, image, read, drawn in PARTS:
		if not doc.get(field):
			continue
		if (
			before
			and before.get(field) == doc.get(field)
			and any(doc.get(key) != before.get(key) for key in (source, html, image))
		):
			doc.set(field, None)
			continue
		doc.set(field, json.dumps(read(doc.get(field))))
		doc.set(source, "HTML")
		doc.set(html, drawn(doc.get(field)))


def redraw(doc=None, method=None) -> None:
	"""Company or Address on_update: every drawn top and foot says what General
	says now."""
	if doc is not None and doc.doctype == "Address" and not doc.get("is_your_company_address"):
		return
	details = None
	heads = frappe.get_all(
		"Letter Head", or_filters={"one_top": ["is", "set"], "one_foot": ["is", "set"]}, pluck="name"
	)
	for name in heads:
		head = frappe.get_doc("Letter Head", name)
		details = details or company()
		if any(
			head.get(field) and drawn(head.get(field), details) != head.get(html)
			for field, _source, html, _image, _read, drawn in PARTS
		):
			head.flags.one_redrawn = True
			head.save(ignore_permissions=True)


@frappe.whitelist()
def presets(settings_of: str | dict | None = None, part: str = "top") -> list[dict]:
	"""Every preset of a top or a foot drawn from the company, for the letter
	head window to show."""
	from onedesk.one import roles

	roles.require()
	details = company()
	if part == "foot":
		said = foot_settings(settings_of)
		return [
			{"preset": key, "label": str(label), "html": draw_foot({**said, "preset": key}, details)}
			for key, label in FEET.items()
		]
	said = settings(settings_of)
	return [
		{"preset": key, "label": str(label), "html": draw({**said, "preset": key}, details)}
		for key, label in PRESETS.items()
	]
