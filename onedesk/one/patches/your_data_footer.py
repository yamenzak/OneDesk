"""Your Data and the Privacy Policy at the foot of every public page, and
erpnext's "Powered by ERPNext" gone from it (brand.py). A link the workspace
already has is left as it is."""

import frappe

from onedesk.one.brand import DEFAULTS


def execute():
	settings = frappe.get_single("Website Settings")
	had = {one.url for one in settings.footer_items}
	for one in DEFAULTS["Website Settings"]["footer_items"]:
		if one["url"] not in had:
			settings.append("footer_items", one)
	if not (settings.footer_powered or "").strip():
		settings.footer_powered = DEFAULTS["Website Settings"]["footer_powered"]
	settings.save(ignore_permissions=True)
