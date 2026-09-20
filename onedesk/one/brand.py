"""What this site is called, and what it wears.

Site data rather than app code: these are what a tenant edits, so this writes
the defaults a fresh site starts with and never touches them again.

Two doctypes because two readers. `Website Settings.app_name` titles the desk,
the login page and every system email, and its `app_logo` is what
`get_app_logo` reads first — the navbar, the login page, the password reset,
the OAuth consent. The desktop screen asks `Navbar Settings.app_logo` instead
and falls back to frappe's own hook, so that one has to be written as well.
"""

import frappe

LOGO = "/assets/onedesk/images/one.svg"

DEFAULTS = {
	"Website Settings": {
		"app_name": "One",
		"app_logo": LOGO,
		"favicon": LOGO,
		"splash_image": LOGO,
	},
	"Navbar Settings": {"app_logo": LOGO},
}


def apply() -> None:
	for doctype, values in DEFAULTS.items():
		settings = frappe.get_single(doctype)
		for field, value in values.items():
			settings.set(field, value)
		settings.save(ignore_permissions=True)
