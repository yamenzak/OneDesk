"""What this site is called, and what it wears.

Site data rather than app code: these are what a tenant edits, so this writes
the defaults a fresh site starts with and never touches them again.

Two doctypes because two readers. `Website Settings.app_name` titles the desk,
the login page and every system email, and its `app_logo` is what
`get_app_logo` reads first — the navbar, the login page, the password reset,
the OAuth consent. The desktop screen asks `Navbar Settings.app_logo` instead
and falls back to frappe's own hook, so that one has to be written as well.

`footer_powered` is here for a third reason: a portal page left alone says
**Powered by ERPNext** at the foot, which is erpnext's default and which a
customer signing up to One should never be shown. Found on `/start`. An
empty one is not enough, because frappe's footer treats empty as unset and
draws erpnext's line anyway; a space draws nothing. The mails had the same
line, "Sent via ERPNext", which System Settings' `disable_standard_email_footer`
leaves out.

`footer_items` puts Your Data and the Privacy Policy at the foot of every
public page, the sign-in page included, so somebody who is not a user finds
where to ask for their data (one/privacy_public.py). frappe's own footer
links, so a workspace can change or add to them in Website Settings.
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
		settings.save(ignore_permissions=True)
