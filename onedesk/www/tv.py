"""The page a TV opens: /tv. It pairs, then plays its channel (one_display/
screens.py, programme.py). Written for old TV browsers: one plain page, no
framework, and a script that runs on Chromium 53.

/tv?preview=<channel> plays a channel for somebody signed in to the desk,
without pairing: the channel's Preview, and the layout editor's with
&collection=<collection>&embed=1."""

import json
import re
from pathlib import Path

import frappe
from frappe import _
from frappe.sessions import get_csrf_token

from onedesk.one_display import screens

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.csrf_token = get_csrf_token() if frappe.session.user != "Guest" else ""
	context.lang = frappe.local.lang or "en"
	context.rtl = context.lang in ("ar", "he", "fa", "ur")
	preview = frappe.form_dict.get("preview")
	collection = frappe.form_dict.get("collection")
	# /radio is this page playing a sound zone and showing nothing (hooks.py website_route_rules)
	context.radio = frappe.local.request.path.rstrip("/").endswith("/radio") if getattr(frappe.local, "request", None) else False
	context.preview_json = json.dumps(
		{"channel": preview or None, "collection": collection, "embed": bool(frappe.form_dict.get("embed"))}
		if (preview or collection) and frappe.session.user != "Guest"
		else None
	).replace("<", "\\u003c")
	# Where the socket that wakes a screen is: the site's own address, or the
	# socket server's port on a development bench (frappe's socketio_client).
	context.socket_json = json.dumps(
		{"port": frappe.conf.socketio_port if frappe._dev_server else None, "site": frappe.local.site}
	)
	brand = screens._brand()
	context.accent = brand["colour"] if re.fullmatch(r"#[0-9a-fA-F]{6}", brand.get("colour") or "") else "#2563eb"
	context.mark = _mark()
	context.words_json = json.dumps(
		{
			"pair": _("Connect this radio") if context.radio else _("Connect this screen"),
			"scan": _("Or scan with your phone"),
			"where": brand["name"],
			"host": frappe.utils.get_url().split("://", 1)[-1],
			"done": _("Connected"),
			"how": _("Open Screens in OneDisplay, add a screen and enter this code."),
			"silent": _("Nothing playing"),
			"counter": _("Counter"),
			"waiting": _("Waiting"),
			"queued": _("{0} waiting"),
			"now": _("Now"),
			"next": _("Next"),
			"open": _("Open now"),
			"closed": _("Closed now"),
			"network": _("Network"),
			"password": _("Password"),
			"nobody": _("No ticket is being served."),
			"your": _("Your ticket"),
			"ahead": _("{0} ahead of you"),
			"sound": _("Press OK to enable sound"),
			"busy": _("The ticket could not be taken. Try again."),
		}
	).replace("<", "\\u003c")
	return context


def _mark() -> str:
	"""OneDisplay's mark from brand/, drawn inline with ids of its own."""
	svg = (Path(frappe.get_app_path("onedesk")).parent / "brand" / "onedisplay.svg").read_text()
	svg = re.sub(r'\s(width|height)="\d+"', "", svg, count=2)
	return svg.replace('id="', 'id="pm-').replace("url(#", "url(#pm-")
