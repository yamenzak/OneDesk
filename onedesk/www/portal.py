"""The portal, a frappe-ui app (frontend/portal; one/portal.py). This serves
its page with what it starts with, and sends frappe's list of a kind (/orders)
to its place in it (/portal/orders)."""

import json
from urllib.parse import quote

import frappe
from frappe.sessions import get_csrf_token

from onedesk.one import portal

no_cache = 1


def get_context(context, **dict_params):
	doctype = dict_params.get("doctype") or frappe.form_dict.get("doctype")
	if doctype:
		route = frappe.get_meta(doctype).get("route") or frappe.local.request.path.strip("/")
		_go(f"/portal/{portal.PATHS.get('/' + route, route)}")
	if frappe.session.user == "Guest":
		_go(f"/login?redirect-to={quote(frappe.local.request.full_path.rstrip('?'))}")
	if frappe.get_cached_value("User", frappe.session.user, "user_type") != "Website User":
		_go("/desk")
	context.csrf_token = get_csrf_token()
	frappe.db.commit()  # the token, for a reader whose session has none yet
	context.boot = portal.boot()
	# As a script's text: nothing in it can end the script it is in.
	context.boot_json = json.dumps(context.boot, default=str).replace("<", "\\u003c")
	return context


def _go(where: str):
	frappe.local.flags.redirect_location = where
	raise frappe.Redirect
