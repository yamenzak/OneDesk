"""What this site is called, and what it wears.

Site data rather than app code: these are what a tenant edits, so this writes
the defaults a fresh site starts with and never touches them again.
"""

import frappe

LOGO = "/assets/onedesk/images/one.svg"

DEFAULTS = {
	"Website Settings": {
		"app_name": "One",
		"app_logo": LOGO,
		"favicon": LOGO,
		"splash_image": LOGO,
		"footer_powered": " ",
		"footer_items": [
			{"label": "Your Data", "url": "/your-data"},
			{"label": "Privacy Policy", "url": "/legal/privacy"},
		],
	},
	"Navbar Settings": {"app_logo": LOGO},
	"System Settings": {"disable_standard_email_footer": 1, "time_format": "HH:mm"},
}


def apply() -> None:
	for doctype, values in DEFAULTS.items():
		settings = frappe.get_single(doctype)
		for field, value in values.items():
			settings.set(field, value)
		settings.flags.ignore_mandatory = True
		settings.save(ignore_permissions=True)


MARK_OF = {"OneCloud": "onestorage", "OneWriter": "onedoc", "OneWorkbook": "onesheet"}


def mark(app: str) -> str | None:
	"""The mark drawn beside an app's name (brand/): One's own for what every
	app shares, none for the workspace's rules. Pure."""
	if not app:
		return "one"
	if not app.startswith("One"):
		return None
	return MARK_OF.get(app, app.lower())
