"""OneInterface's part of the integration suite (one_demo/check.py runs it):
the review stamps reach the desk only on a dev site, and every screen named
as passed is one frappe can route to."""

from unittest.mock import patch

import frappe

from onedesk.one_demo.checking import check


@check
def stamps_reach_only_a_dev_site():
	"""The boot carries the stamps on a site in developer mode or marked
	one_dev, and nothing at all anywhere else (one_interface/stamps.py)."""
	from onedesk.one_interface import stamps

	with patch.dict(frappe.conf, {"developer_mode": 0, "one_dev": 0}):
		assert stamps.for_boot() == {}
	with patch.dict(frappe.conf, {"developer_mode": 0, "one_dev": 1}):
		said = stamps.for_boot()
		assert said["dev"] == 1 and said["passed"] is stamps.PASSED
	for screen in stamps.PASSED:
		kind, _, name = screen.partition("/")
		if kind in ("Form", "List", "Tree"):
			assert frappe.db.exists("DocType", name), screen


@check
def the_shell_wears_the_workspaces_identity():
	"""The demo's owner set its logo and Brand Colour in One's ControlCenter ›
	Branding: frappe's own fields hold the logo, so the sign-in page, the tab
	and the splash show it; the desk, the installed app and mails read the
	same setting; a name set and emptied again goes back to One's own
	(one_interface/identity.py)."""
	import json

	from onedesk.one import brand, control, notify
	from onedesk.one_demo.base import COMPANY
	from onedesk.one_demo.people import BRAND
	from onedesk.one_interface import identity

	assert identity.logo() == BRAND["app_logo"], identity.logo()
	assert frappe.db.get_single_value("Navbar Settings", "app_logo") == BRAND["app_logo"]
	assert frappe.db.get_single_value("Website Settings", "favicon") == BRAND["app_logo"]
	assert frappe.db.get_value("Company", COMPANY, "one_brand_colour") == BRAND["one_brand_colour"]
	said = identity.boot()
	assert said["shades"]["colour"] == BRAND["one_brand_colour"] and said["shades"]["dark"] != BRAND["one_brand_colour"], said
	mail = notify.one_mail_brand()
	assert mail["logo"].endswith(BRAND["app_logo"]) and mail["colour"] == BRAND["one_brand_colour"], mail
	shown = control._general("branding")["values"]
	assert shown["app_logo"] == BRAND["app_logo"] and shown["app_name"] == "", shown

	manifest = json.loads(identity.manifest().get_data())
	assert manifest["icons"][0]["src"] == BRAND["app_logo"] and manifest["theme_color"] == BRAND["one_brand_colour"], manifest
	assert manifest["name"] == brand.DEFAULTS["Website Settings"]["app_name"], manifest

	try:
		control._save_general({"app_name": "Sahara Glass"})
		assert identity.name() == "Sahara Glass" and identity.boot()["name"] == "Sahara Glass"
		assert frappe.db.get_single_value("System Settings", "app_name") == "Sahara Glass"
		assert notify.one_mail_brand()["name"] == "Sahara Glass"
		assert json.loads(identity.manifest().get_data())["name"] == "Sahara Glass"
	finally:
		control._save_general({"app_name": ""})
	assert identity.name() is None
	assert frappe.db.get_single_value("Website Settings", "app_name") == brand.DEFAULTS["Website Settings"]["app_name"]
