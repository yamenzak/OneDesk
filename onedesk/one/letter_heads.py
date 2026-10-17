"""A letter head's top and foot, drawn from the company.

A workspace's letter head may hold no template, so its top and foot are drawn
here from what Workspace > General keeps, and drawn again when that changes.
"""

import json
import re

import frappe
from frappe import _, _lt
from frappe.utils import cint, escape_html

#: The ways a top is laid out, in the order they are offered.
PRESETS = {
	"classic": _lt("Classic"),
	"details": _lt("Columns"),
	"ledger": _lt("Ledger"),
	"strip": _lt("Strip"),
	"masthead": _lt("Masthead"),
	"centred": _lt("Centred"),
	"window": _lt("Window"),
	"accent": _lt("Accent"),
	"wordmark": _lt("Wordmark"),
	"minimal": _lt("Minimal"),
	"banner": _lt("Tinted"),
	"band": _lt("Band"),
	"logo": _lt("Logo Only"),
}

#: The ways a foot is laid out, in the order they are offered.
FEET = {
	"centred": _lt("Centred"),
	"split": _lt("Two Sides"),
	"strip": _lt("Fact Strip"),
	"legal": _lt("Legal"),
	"accent": _lt("Accent"),
	"corner": _lt("Corner"),
	"spread": _lt("Spread"),
	"above": _lt("Logo Above"),
	"band": _lt("Tinted"),
}

#: What a foot may show: what a top may, and a small logo before it.
FOOT_SHOWN = {"logo": _lt("Logo")}

#: What a new foot shows: a quiet line, since the top already says the rest.
FOOT_FIRST = ("phone", "website", "tax_id")

#: How tall the logo in a foot is, in pixels.
FOOT_LOGO = 20

#: How long a foot's note may be.
NOTE = 200

#: The settings a header is drawn with.
TOP_KEYS = ("preset", "show", "logo_height", "align", "line")

#: What a top may show beside the logo, in the order it is written.
SHOWN = {
	"name": _lt("Name"),
	"address": _lt("Address"),
	"phone": _lt("Phone"),
	"email": _lt("Email"),
	"website": _lt("Website"),
	"tax_id": _lt("Tax ID"),
}

#: What a new top shows. The name only when ticked: a logo usually says it, and
#: with no logo the name is the top's headline whatever is ticked.
SHOWN_FIRST = ("address", "phone", "email", "website")

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
		# The line in the Brand Colour under the top: off unless asked for, since
		# the room under the top already sets it apart.
		"line": 1 if cint(said.get("line", 0)) else 0,
		"align": (said.get("align") or "left").lower()
		if (said.get("align") or "").lower() in ("left", "center", "right")
		else "left",
	}


def foot_settings(raw) -> dict:
	"""A foot's settings, as kept on the letter head, with what is missing filled."""
	said = raw if isinstance(raw, dict) else (frappe.parse_json(raw) if raw else None) or {}
	return {
		"preset": said.get("preset") if said.get("preset") in FEET else "centred",
		"show": [one for one in (said.get("show") or FOOT_FIRST) if one in SHOWN or one in FOOT_SHOWN],
		# A line of the workspace's own, such as "Thank you for your business."
		"note": " ".join(str(said.get("note") or "").split())[:NOTE],
		"line": 1 if cint(said.get("line", 0)) else 0,
	}


def company() -> dict:
	"""What General keeps about the company, as a top shows it."""
	from onedesk.one import settings as workspace

	held = workspace._company()
	if not held:
		return {"name": "", "colour": INK, "address": [], "street": "", "locality": ""}
	address = workspace._company_address(held)
	street = locality = ""
	if address:
		street = ", ".join(one for one in (address.address_line1, address.address_line2) if one)
		locality = ", ".join(
			one
			for one in (" ".join(one for one in (address.city, address.pincode) if one), address.state, address.country)
			if one
		)
	colour = held.get("one_brand_colour") or ""
	return {
		"name": held.company_name,
		"logo": held.company_logo,
		"address": [one for one in (street, locality) if one],
		"street": street,
		"locality": locality,
		"phone": held.phone_no,
		"email": held.email,
		"website": held.website,
		"tax_id": held.tax_id,
		# A UAE company's tax number is its TRN, and its papers call it that.
		"tax_label": "TRN" if held.country == "United Arab Emirates" else "Tax ID",
		"colour": colour if COLOUR.match(colour) else INK,
	}


#: What a company's tax number is called on its papers (company), for translation.
TAX_LABELS = (_lt("TRN"), _lt("Tax ID"))

#: The company's details in the order a reader looks for them, after the name.
REACH = ("phone", "email", "website")

#: Between details on one line.
DOT = '<span style="color:#d1d5db;padding:0 6px">·</span>'

#: How light a tint of the Brand Colour a band is, out of one.
TINT = 0.07

#: A detail's size and colour, and a faint rule's.
SMALL = f"font-size:9.5px;line-height:1.6;color:{MUTED};"
FAINT = "#eef0f3"


def _rgb(colour: str) -> tuple[int, int, int]:
	hexed = colour.lstrip("#")
	if len(hexed) in (3, 4):
		hexed = "".join(one * 2 for one in hexed[:3])
	return tuple(int(hexed[i : i + 2], 16) for i in (0, 2, 4))


def _luminance(rgb) -> float:
	def channel(value: int) -> float:
		value /= 255
		return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

	r, g, b = (channel(one) for one in rgb)
	return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(rgb) -> float:
	"""Against white."""
	return 1.05 / (_luminance(rgb) + 0.05)


def readable(colour: str) -> str:
	"""The Brand Colour as text on white: itself, or darkened until it reads
	(WCAG's 4.5 to 1), so a yellow brand still prints a name that can be read.
	A line or a band keeps the colour as it is. Pure."""
	try:
		rgb = _rgb(colour)
	except ValueError:
		return INK
	for _step in range(40):
		if _contrast(rgb) >= 4.5:
			break
		rgb = tuple(int(one * 0.9) for one in rgb)
	return "#{:02x}{:02x}{:02x}".format(*rgb)


def on(colour: str) -> str:
	"""Text on the Brand Colour: white, or ink on a light one. Pure."""
	try:
		return "#ffffff" if _contrast(_rgb(colour)) >= 3 else INK
	except ValueError:
		return "#ffffff"


def tint(colour: str, share: float = TINT) -> str:
	"""The Brand Colour mixed into white, for a band text sits on. Pure."""
	try:
		rgb = _rgb(colour)
	except ValueError:
		return "#f9fafb"
	return "#{:02x}{:02x}{:02x}".format(*(round(255 - (255 - one) * share) for one in rgb))


def initials(name: str) -> str:
	"""Two letters for a company with no logo: Sahara Glass & Aluminium is SG. Pure."""
	words = [one for one in (name or "").replace("&", " ").split() if one[:1].isalnum()]
	return "".join(one[0] for one in words[:2]).upper()


def _cell(content: str, style: str = "") -> str:
	return f'<div style="display:table-cell;{style}">{content}</div>'


def _row(*cells: str, style: str = "") -> str:
	return f'<div style="display:table;width:100%;{style}">{"".join(cells)}</div>'


def _lines(*rows: str) -> str:
	return "".join(f"<div>{one}</div>" for one in rows if one)


def _label(text: str, colour: str | None = None) -> str:
	"""A fact's small capital label, grey or in the colour."""
	return (
		'<div style="font-size:7.5px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;'
		f'color:{colour or "#9ca3af"};margin-bottom:3px">{text}</div>'
	)


def _facts(details: dict, shown: set) -> dict:
	"""What the company says, escaped, each only when ticked and kept."""
	e = lambda value: escape_html(str(value or ""))  # noqa: E731
	address = "address" in shown
	return {
		"street": e(details.get("street")) if address else "",
		"locality": e(details.get("locality")) if address else "",
		"where": e(", ".join(details.get("address") or [])) if address else "",
		**{key: e(details.get(key)) if key in shown and details.get(key) else "" for key in REACH},
		"tax_label": e(_(details.get("tax_label") or "Tax ID")),
		"tax_id": e(details.get("tax_id")) if "tax_id" in shown and details.get("tax_id") else "",
	}


def draw(raw, details: dict | None = None) -> str:
	"""A top's HTML: its preset, from the company, showing what was ticked.

	The Brand Colour is a line, a label, the name or a band, and every detail
	quiet grey. A company with no logo is its initials in the colour beside its
	name. Laid out in display:table, since frappe's print style stretches a
	picture across a table cell."""
	said = settings(raw)
	details = details or company()
	shown = set(said["show"])
	colour = details.get("colour") or INK
	ink = readable(colour)
	e = lambda value: escape_html(str(value or ""))  # noqa: E731
	f = _facts(details, shown)
	has_logo = bool(details.get("logo"))
	# The name beside the logo only when ticked: a logo usually says it.
	name = e(details.get("name")) if "name" in shown or not has_logo else ""
	reach = [f[key] for key in REACH if f[key]]
	tax = f"{f['tax_label']} {f['tax_id']}" if f["tax_id"] else ""
	rule = (
		f'<div style="height:2px;background:{colour};margin-top:16px;{EXACT}"></div>'
		if said["line"]
		else '<div style="height:20px"></div>'
	)

	def logo(height: int | None = None) -> str:
		if not has_logo:
			return ""
		height = height or said["logo_height"]
		# Its width said outright: a printed page sizes a picture to its box.
		ratio = _ratio(details["logo"])
		width = f"width:{round(height * ratio)}px;" if ratio else "width:auto;"
		return (
			f'<img src="{e(details["logo"])}" alt="{e(details.get("name"))}" '
			f'style="height:{height}px;{width}max-width:100%;display:inline-block;vertical-align:middle">'
		)

	def monogram(box: int = 44) -> str:
		"""The company's initials on its colour, and its name beside them."""
		return (
			'<div style="display:inline-table">'
			+ _cell(
				f'<div style="width:{box}px;height:{box}px;border-radius:{round(box * 0.22)}px;background:{colour};'
				f"color:{on(colour)};font-size:{round(box * 0.38)}px;font-weight:700;line-height:{box}px;"
				f'text-align:center;{EXACT}">{e(initials(details.get("name")))}</div>',
				"vertical-align:middle",
			)
			+ (
				_cell(
					name,
					f"vertical-align:middle;padding-left:12px;font-size:{15 if box > 32 else 13}px;"
					"font-weight:600;letter-spacing:-0.01em;color:#111827;text-align:left",
				)
				if name
				else ""
			)
			+ "</div>"
		)

	def identity(box: int = 44, height: int | None = None) -> str:
		"""The logo, with the name under it when ticked, or the monogram."""
		if not has_logo:
			return monogram(box)
		return logo(height) + (
			f'<div style="font-size:11px;font-weight:600;color:#111827;margin-top:8px">{name}</div>' if name else ""
		)

	def fact(label: str, body: str, tinted: bool = False, style: str = "") -> str:
		return (
			_cell(_label(label, ink if tinted else None) + f'<div style="{SMALL}color:#374151">{body}</div>', style)
			if body
			else ""
		)

	where = _lines(f["street"], f["locality"])
	preset = said["preset"]

	if preset == "logo":
		return f'<div style="text-align:{said["align"]}">{identity()}</div>{rule}'

	if preset == "details":
		# Columns: the identity left; the address and how to reach the company
		# in columns at right, each under a quiet label.
		columns = fact(_("Address"), where, style="vertical-align:top;padding-left:26px") + fact(
			_("Contact"), _lines(*reach), style="vertical-align:top;padding-left:26px;white-space:nowrap"
		) + fact(f["tax_label"], f["tax_id"], style="vertical-align:top;padding-left:26px;white-space:nowrap")
		return (
			_row(
				_cell(identity(), "vertical-align:top"),
				_cell(f'<div style="display:inline-table;text-align:left">{columns}</div>', "vertical-align:top;text-align:right"),
			)
			+ rule
		)

	if preset == "ledger":
		# The identity left; the facts two by two at right, under labels in the colour.
		cells = [
			one
			for one in (
				fact(_("Address"), where, True, "vertical-align:top;padding:0 0 8px 24px"),
				fact(_("Phone"), f["phone"], True, "vertical-align:top;padding:0 0 8px 24px;white-space:nowrap"),
				fact(_("Email"), f["email"], True, "vertical-align:top;padding:0 0 8px 24px;white-space:nowrap"),
				fact(f["tax_label"], f["tax_id"], True, "vertical-align:top;padding:0 0 8px 24px;white-space:nowrap"),
			)
			if one
		]
		grid = "".join(
			f'<div style="display:table-row">{"".join(cells[n : n + 2])}</div>' for n in range(0, len(cells), 2)
		)
		return (
			_row(
				_cell(identity(), "vertical-align:middle"),
				_cell(f'<div style="display:inline-table;text-align:left">{grid}</div>', "vertical-align:middle;text-align:right"),
			)
			+ rule
		)

	if preset == "strip":
		# The identity on its own, then every fact in a strip across the page.
		strip = (
			fact(_("Address"), where, style="vertical-align:top;padding-right:14px;width:34%")
			+ fact(_("Phone"), f["phone"], style="vertical-align:top;padding-right:14px;white-space:nowrap")
			+ fact(_("Email"), f["email"], style="vertical-align:top;padding-right:14px;white-space:nowrap")
			+ fact(_("Web"), f["website"], style="vertical-align:top;padding-right:14px;white-space:nowrap")
			+ fact(f["tax_label"], f["tax_id"], style="vertical-align:top;white-space:nowrap")
		)
		return (
			f"<div>{identity()}</div>"
			+ (
				f'<div style="margin-top:18px;padding:10px 0;border-top:1px solid {FAINT};border-bottom:1px solid {FAINT}">'
				f"{_row(strip)}</div>"
				if strip
				else ""
			)
			+ rule
		)

	if preset == "masthead":
		# The identity centred over three equal columns of facts.
		columns = [
			(_("Address"), where),
			(_("Contact"), _lines(f["phone"], f["email"])),
			(f["tax_label"] if f["tax_id"] else _("Web"), _lines(f["tax_id"], f["website"])),
		]
		cells = "".join(
			_cell(_label(label, ink) + f'<div style="{SMALL}">{body}</div>', "vertical-align:top;text-align:center")
			for label, body in columns
			if body
		)
		return (
			f'<div style="text-align:center;margin-bottom:16px">{identity()}</div>'
			+ (
				f'<div style="border-top:1px solid {FAINT};padding-top:12px">{_row(cells, style="table-layout:fixed")}</div>'
				if cells
				else ""
			)
			+ rule
		)

	if preset == "centred":
		return (
			f'<div style="text-align:center"><div>{identity()}</div>'
			f'<div style="{SMALL}margin-top:10px">{_lines(DOT.join(one for one in (f["street"], f["locality"]) if one), DOT.join([*reach, tax] if tax else reach))}</div>'
			"</div>" + rule
		)

	if preset == "window":
		# Everything at top right, the left free for the address a letter goes to.
		return (
			f'<div style="text-align:right"><div>{identity(36, 40)}</div>'
			f'<div style="{SMALL}margin-top:10px">{_lines(f["street"], f["locality"], DOT.join(reach), tax)}</div>'
			"</div>" + rule
		)

	if preset == "accent":
		# A short bar in the colour over the identity; the facts in two columns at right.
		bar = f'<div style="width:36px;height:4px;border-radius:2px;background:{colour};margin-bottom:14px;{EXACT}"></div>'
		right = (
			_cell(f'<div style="{SMALL}">{where}</div>', "vertical-align:bottom;text-align:right")
			+ _cell(
				f'<div style="{SMALL}">{_lines(*reach, tax)}</div>',
				"vertical-align:bottom;text-align:right;padding-left:24px;white-space:nowrap;width:1%",
			)
		)
		return (
			_row(
				_cell(bar + identity(), "vertical-align:bottom"),
				_cell(_row(right), "vertical-align:bottom;width:62%"),
			)
			+ rule
		)

	if preset == "wordmark":
		# The name set large and spaced, or the logo; every fact on one line under it.
		mark = (
			logo()
			if has_logo
			else f'<div style="font-size:20px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:{ink}">{e(details.get("name"))}</div>'
		)
		return (
			f"<div>{mark}</div>"
			+ f'<div style="{SMALL}margin-top:10px">{DOT.join(one for one in (f["where"], *reach, tax) if one)}</div>'
			+ rule
		)

	if preset == "minimal":
		# One quiet line: the name or a small logo, and how to reach the company.
		left = logo(36) if has_logo and not name else f'<span style="font-size:12px;font-weight:600;color:{ink}">{name}</span>'
		return (
			f'<div style="padding-bottom:10px;{f"border-bottom:1px solid {colour};" if said["line"] else ""}">'
			+ _row(
				_cell(left, "vertical-align:baseline"),
				_cell(f'<span style="{SMALL}">{DOT.join([*reach, tax] if tax else reach)}</span>', "vertical-align:baseline;text-align:right"),
			)
			+ "</div>"
		)

	if preset == "banner":
		# Tinted: the company on its Brand Colour's faintest tint.
		return (
			f'<div style="background:{tint(colour)};border-radius:6px;padding:20px 24px;{EXACT}">'
			+ _row(
				_cell(identity(), "vertical-align:middle"),
				_cell(f'<div style="{SMALL}">{_lines(f["street"], f["locality"], DOT.join(reach), tax)}</div>', "vertical-align:middle;text-align:right"),
			)
			+ "</div>"
			+ rule
		)

	if preset == "band":
		# A band in the colour, the name or the logo on it, the facts under it.
		text = on(colour)
		mark = (
			f'<span style="display:inline-block;background:#ffffff;border-radius:6px;padding:6px 10px">{logo(32)}</span>'
			if has_logo
			else f'<span style="font-size:16px;font-weight:600;color:{text}">{e(details.get("name"))}</span>'
		)
		return (
			f'<div style="background:{colour};border-radius:6px;padding:16px 20px;{EXACT}">'
			+ _row(
				_cell(mark, "vertical-align:middle"),
				_cell(
					f'<div style="font-size:9.5px;line-height:1.6;color:{text}">{_lines(f["phone"], f["email"])}</div>',
					"vertical-align:middle;text-align:right",
				),
			)
			+ "</div>"
			+ f'<div style="{SMALL}margin-top:8px">{DOT.join(one for one in (f["where"], f["website"], tax) if one)}</div>'
			+ rule
		)

	# Classic: the identity on the left, the company stacked on the right.
	return (
		_row(
			_cell(identity(), "vertical-align:middle"),
			_cell(f'<div style="{SMALL}">{_lines(f["street"], f["locality"], DOT.join(reach), tax)}</div>', "vertical-align:middle;text-align:right"),
		)
		+ rule
	)


def draw_foot(raw, details: dict | None = None) -> str:
	"""A foot's HTML: its preset, from the company, showing what was ticked,
	with the note under it when there is one."""
	said = foot_settings(raw)
	details = details or company()
	shown = set(said["show"])
	colour = details.get("colour") or INK
	e = lambda value: escape_html(str(value or ""))  # noqa: E731
	f = _facts(details, shown)
	small = f"font-size:8.5px;line-height:1.6;color:{MUTED};"

	def mark(always: bool = False, height: int = FOOT_LOGO) -> str:
		if not details.get("logo") or not (always or "logo" in shown):
			return ""
		ratio = _ratio(details["logo"])
		width = f"width:{round(height * ratio)}px;" if ratio else "width:auto;"
		return (
			f'<img src="{e(details["logo"])}" alt="{e(details.get("name"))}" '
			f'style="height:{height}px;{width}display:inline-block;vertical-align:middle;margin-right:8px">'
		)

	name = (
		f'<span style="font-weight:600;color:#374151">{e(details.get("name"))}</span>'
		if "name" in shown and details.get("name")
		else ""
	)
	reach = [f[key] for key in REACH if f[key]]
	tax = f"{f['tax_label']} {f['tax_id']}" if f["tax_id"] else ""
	everything = [one for one in (name, f["where"], *reach, tax) if one]

	def note(align: str) -> str:
		if not said["note"]:
			return ""
		return f'<div style="margin-top:3px;text-align:{align};{small}color:#9ca3af">{e(said["note"])}</div>'

	rule = (
		f'<div style="height:1px;background:{colour};margin-bottom:8px;{EXACT}"></div>'
		if said["line"]
		else ""
	)

	preset = said["preset"]
	if preset == "band":
		# Tinted: the line on the Brand Colour's faintest tint.
		return (
			f'<div style="background:{tint(colour)};border-radius:4px;padding:8px 14px;text-align:center;{small}{EXACT}">'
			f"{DOT.join(everything)}</div>"
			+ (f'<div style="height:2px;background:{colour};margin-top:6px;{EXACT}"></div>' if said["line"] else "")
			+ note("center")
		)

	if preset == "split":
		# Who the company is on the left; how to reach it on the right.
		left = [one for one in (name, f["where"]) if one] or everything[:1]
		right = [one for one in everything if one not in left]
		return (
			rule
			+ _row(
				_cell(mark() + DOT.join(left), "vertical-align:middle;text-align:left"),
				_cell(DOT.join(right), "vertical-align:middle;text-align:right"),
				style=small,
			)
			+ note("left")
		)

	if preset == "above":
		# The logo centred on its own over the line, whether or not it was ticked.
		return (
			(f'<div style="text-align:center;margin-bottom:6px">{mark(always=True)}</div>' if details.get("logo") else "")
			+ rule
			+ f'<div style="text-align:center;{small}">{DOT.join(everything)}</div>'
			+ note("center")
		)

	if preset == "spread":
		# Each detail in an equal share of the width: the first against the left
		# edge, the last against the right, the rest centred in theirs. The name,
		# with the logo, takes two shares, so it stays on one line.
		named = (mark() + name) if (mark() or name) else ""
		items = [one for one in (named, f["where"], *reach, tax) if one]
		last = len(items) - 1
		shares = len(items) + (1 if named else 0)
		share = lambda n: f"{100 * (2 if named and n == 0 else 1) / shares:.4f}%"  # noqa: E731
		return (
			rule
			+ _row(
				*(
					_cell(
						one,
						f"width:{share(n)};vertical-align:middle;white-space:nowrap;"
						f"text-align:{'left' if n == 0 else 'right' if n == last else 'center'}",
					)
					for n, one in enumerate(items)
				),
				style=f"table-layout:fixed;{small}",
			)
			+ note("center")
		)

	if preset == "strip":
		# Fact Strip: each fact in a column under its quiet label.
		def fact(label: str, body: str, keep: bool = True) -> str:
			return (
				_cell(_label(label) + f"<div>{body}</div>", "vertical-align:top;padding-right:18px;" + ("white-space:nowrap;width:1%" if keep else ""))
				if body
				else ""
			)

		cells = (
			fact(_("Company"), e(details.get("name")) if "name" in shown else "")
			+ fact(_("Address"), _lines(f["street"], f["locality"]), keep=False)
			+ fact(_("Contact"), _lines(*reach))
			+ fact(f["tax_label"], f["tax_id"])
		)
		return (
			f'<div style="border-top:1px solid {colour if said["line"] else FAINT};padding-top:10px;{EXACT}">'
			+ _row(cells, style=small)
			+ "</div>"
			+ note("left")
		)

	if preset == "legal":
		# Who the company is, where it is registered and its tax number, centred.
		return (
			rule
			+ f'<div style="text-align:center;{small}">'
			+ (f"<div>{name}</div>" if name else "")
			+ _lines(DOT.join(one for one in (f["where"], tax) if one), DOT.join(reach))
			+ "</div>"
			+ note("center")
		)

	if preset == "accent":
		# A short bar in the colour over one centred line.
		return (
			f'<div style="width:28px;height:3px;border-radius:2px;background:{colour};margin:0 auto 8px;{EXACT}"></div>'
			+ f'<div style="text-align:center;{small}">{DOT.join(everything)}</div>'
			+ note("center")
		)

	if preset == "corner":
		# The logo or the name in the left corner, the rest on the right.
		left = mark(always=True, height=22) or (
			f'<span style="font-weight:600;color:#374151">{e(details.get("name"))}</span>'
		)
		return (
			rule
			+ _row(
				_cell(left, "vertical-align:middle"),
				_cell(DOT.join(one for one in (f["where"], *reach, tax) if one), "vertical-align:middle;text-align:right"),
				style=small,
			)
			+ note("left")
		)

	# Centred: everything ticked on one line, joined by dots.
	return rule + f'<div style="text-align:center;{small}">{mark()}{DOT.join(everything)}</div>' + note("center")


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


#: An icon asked for by name in a letter head written by hand: [icon:phone], or
#: [icon:phone:#0f766e] for a colour other than the Brand Colour.
ICON = re.compile(r"\[icon:([a-z0-9-]+)(?::(#[0-9a-fA-F]{3,8}))?\]")


def icons_in(html: str | None) -> str | None:
	"""A letter head written by hand, with each [icon:name] it asks for drawn as
	one of frappe's Lucide icons: the same small picture the presets use, since
	HTML written by hand cannot carry the icon itself. A name frappe does not
	ship is left as it was written."""
	if not html or "[icon:" not in html:
		return html
	colour = company().get("colour") or INK

	def one(found: re.Match) -> str:
		name, tint = found.group(1), found.group(2)
		if not _known(name):
			return found.group(0)
		return (
			f'<img src="{_icon(name, tint or colour)}" alt="" '
			'style="width:11px;height:11px;display:inline-block;vertical-align:-1px;margin-right:4px">'
		)

	return ICON.sub(one, html)


def _known(name: str) -> bool:
	_icon(name, INK)
	sprite = frappe.cache.get_value("one_lucide_sprite") or ""
	return f'id="icon-{name}"' in sprite


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
