"""A letter head's top, drawn from the company. docs/DESK-COVERAGE.md, stage 3.

frappe keeps a letter head's top as HTML, and ERPNext's own reads the
company's logo, name, address and contacts from the document as it prints. A
workspace's letter head may hold no template (print_html.letter_head_html),
so its top is drawn here instead: one of PRESETS, from what Workspace >
General keeps (the logo, the name, the company's own address, its phone,
email, website and tax ID, and its Brand Colour), showing what the
administrator ticked. The choice is kept on the letter head (`one_top`), and
the top is drawn again whenever the company or its address changes (`redraw`),
so a printed page always says what General says now.

A top written by hand, in frappe's builder, stays as it was written: editing
a drawn top there makes it hand-written (`draw`).
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


def apply(doc) -> None:
	"""Letter Head validate, before anything checks the top: a drawn top is drawn
	now; one the person changed by hand in the builder is theirs from then on."""
	if not doc.get("one_top"):
		return
	before = doc.get_doc_before_save()
	if (
		before
		and before.get("one_top") == doc.one_top
		and any(doc.get(key) != before.get(key) for key in ("source", "content", "image"))
	):
		doc.one_top = None
		return
	doc.one_top = json.dumps(settings(doc.one_top))
	doc.source = "HTML"
	doc.content = draw(doc.one_top)


def redraw(doc=None, method=None) -> None:
	"""Company or Address on_update: every drawn top says what General says now."""
	if doc is not None and doc.doctype == "Address" and not doc.get("is_your_company_address"):
		return
	details = None
	for name in frappe.get_all("Letter Head", filters={"one_top": ["is", "set"]}, pluck="name"):
		head = frappe.get_doc("Letter Head", name)
		details = details or company()
		drawn = draw(head.one_top, details)
		if drawn != head.content:
			head.flags.one_redrawn = True
			head.save(ignore_permissions=True)


@frappe.whitelist()
def presets(settings_of: str | dict | None = None) -> list[dict]:
	"""Every preset drawn from the company, for the letter head window to show."""
	from onedesk.one import roles

	roles.require()
	details = company()
	said = settings(settings_of)
	return [
		{"preset": key, "label": str(label), "html": draw({**said, "preset": key}, details)}
		for key, label in PRESETS.items()
	]
