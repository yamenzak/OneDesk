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
	# Otherwise every mail ends "Sent via ERPNext" (erpnext's default_mail_footer).
	"System Settings": {"disable_standard_email_footer": 1},
}


def apply() -> None:
	for doctype, values in DEFAULTS.items():
		settings = frappe.get_single(doctype)
		for field, value in values.items():
			settings.set(field, value)
		# On a new site this runs before the setup wizard has asked for
		# System Settings' language and time zone.
		settings.flags.ignore_mandatory = True
		settings.save(ignore_permissions=True)
