"""The workspace's own name, logo and colour, set once in One's
ControlCenter › Branding and kept in frappe's own fields where frappe has
one; the shell, the sign-in page, the installed app and mails read them
(onedesk/one_interface/AGENTS.md, The workspace's identity)."""

import json
import re

import frappe

from onedesk.one import brand
from onedesk.one_studio import letter_heads

ONES = brand.DEFAULTS["Website Settings"]

LOGO_FIELDS = {"Website Settings": ("app_logo", "favicon", "splash_image"), "Navbar Settings": ("app_logo",)}

HEX = re.compile(r"#[0-9a-fA-F]{6}")

DARK_PAGE = (23, 23, 23)


def name() -> str | None:
	"""The name the workspace gave itself, or None for One's own."""
	said = (frappe.db.get_single_value("Website Settings", "app_name") or "").strip()
	return said if said and said != ONES["app_name"] else None


def logo() -> str | None:
	"""The logo the workspace gave itself, or None for One's own."""
	said = (frappe.db.get_single_value("Website Settings", "app_logo") or "").strip()
	return said if said and said != ONES["app_logo"] else None


def colour() -> str | None:
	"""The workspace company's Brand Colour, or None for One's own accent."""
	company = frappe.defaults.get_global_default("company")
	said = frappe.get_cached_value("Company", company, "one_brand_colour") if company else None
	return said if HEX.fullmatch(said or "") else None


def shades(colour: str | None) -> dict | None:
	"""What the shell draws a colour in, for each theme, each readable where
	it stands. In light the main button is the colour itself with white or
	ink on it (the letter heads' rule, `letter_heads.on`), and the accent
	and the focus ring are the colour darkened until it reads on white
	(`letter_heads.readable`). In dark all three are the colour lifted
	until it reads on the dark page (`lifted`), with ink on it. None for
	One's own. Pure."""
	if not colour or not HEX.fullmatch(colour):
		return None
	return {
		"colour": colour,
		"ink": letter_heads.on(colour),
		"accent": letter_heads.readable(colour),
		"dark": lifted(colour),
		"dark_ink": letter_heads.INK,
	}


def lifted(colour: str) -> str:
	"""The colour mixed toward white until it stands out by WCAG's 4.5 to 1
	from a dark page (frappe-ui's darkest surface, #171717) and from the ink
	written on it. Pure."""
	rgb = letter_heads._rgb(colour)
	ink = letter_heads._rgb(letter_heads.INK)
	for _step in range(40):
		if min(_apart(rgb, DARK_PAGE), _apart(rgb, ink)) >= 4.5:
			break
		rgb = tuple(min(255, round(one + (255 - one) * 0.1)) for one in rgb)
	return "#{:02x}{:02x}{:02x}".format(*rgb)


def _apart(one, other) -> float:
	light, dark = sorted((letter_heads._luminance(one), letter_heads._luminance(other)), reverse=True)
	return (light + 0.05) / (dark + 0.05)


def boot() -> dict:
	"""What the desk draws the workspace's identity from (chrome.js `brand`)."""
	return {
		"name": name(),
		"logo": logo(),
		"favicon": frappe.db.get_single_value("Website Settings", "favicon") or ONES["favicon"],
		"shades": shades(colour()),
	}


def save(values: dict) -> bool:
	"""Write the name and the logo set in Branding into frappe's own
	fields; an emptied one goes back to One's. A logo uploaded as a private
	file is made public, since the sign-in page and the installed app show
	it to somebody not signed in. Whether anything changed."""
	changed = False
	if "app_name" in values:
		wanted = (values.get("app_name") or "").strip() or ONES["app_name"]
		changed |= _write("Website Settings", {"app_name": wanted})
	if "app_logo" in values:
		wanted = _public((values.get("app_logo") or "").strip()) or ONES["app_logo"]
		for doctype, fields in LOGO_FIELDS.items():
			changed |= _write(doctype, dict.fromkeys(fields, wanted))
	return changed


def _write(doctype: str, wanted: dict) -> bool:
	settings = frappe.get_single(doctype)
	if all((settings.get(field) or "") == value for field, value in wanted.items()):
		return False
	settings.update(wanted)
	settings.flags.ignore_mandatory = True
	settings.save(ignore_permissions=True)
	return True


def _public(url: str) -> str:
	if not url.startswith("/private/"):
		return url
	held = frappe.db.get_value("File", {"file_url": url}, "name")
	if not held:
		return url
	file = frappe.get_doc("File", held)
	file.is_private = 0
	file.save(ignore_permissions=True)
	return file.file_url


@frappe.whitelist(allow_guest=True, methods=["GET"])
@frappe.read_only()
def manifest():
	"""The installed app's manifest: the workspace's name and logo, else
	One's, opening on the desk, in the workspace's colour."""
	from werkzeug.wrappers import Response

	said = boot()
	icon = said["logo"] or ONES["app_logo"]
	shown = said["name"] or ONES["app_name"]
	body = {
		"name": shown,
		"short_name": shown,
		"start_url": "/desk",
		"scope": "/",
		"display": "standalone",
		"icons": [{"src": icon, "sizes": "any", "type": _type(icon)}],
	}
	if said["shades"]:
		body["theme_color"] = said["shades"]["colour"]
	return Response(json.dumps(body), mimetype="application/manifest+json", headers={"Cache-Control": "public, max-age=300"})


def _type(url: str) -> str:
	import mimetypes

	return mimetypes.guess_type(url.split("?")[0])[0] or "image/png"
