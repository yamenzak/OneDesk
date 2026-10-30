"""The page a TV opens: /tv. It pairs, then plays its channel (one_display/
screens.py, programme.py). Written for old TV browsers: one plain page, no
framework, and a script that runs on Chromium 53.

/tv?preview=<channel> plays a channel for somebody signed in to the desk,
without pairing: the channel's Preview, and the layout editor's with
&collection=<collection>&embed=1."""

import json

import frappe
from frappe import _
from frappe.sessions import get_csrf_token

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.csrf_token = get_csrf_token() if frappe.session.user != "Guest" else ""
	context.lang = frappe.local.lang or "en"
	context.rtl = context.lang in ("ar", "he", "fa", "ur")
	preview = frappe.form_dict.get("preview")
	collection = frappe.form_dict.get("collection")
	context.preview_json = json.dumps(
		{"channel": preview or None, "collection": collection, "embed": bool(frappe.form_dict.get("embed"))}
		if (preview or collection) and frappe.session.user != "Guest"
		else None
	).replace("<", "\\u003c")
	context.words_json = json.dumps(
		{
			"pair": _("Pair this screen"),
			"how": _("In OneDisplay, open Display Screen, choose Add Display Screen and enter this code."),
			"counter": _("Counter"),
			"waiting": _("Waiting"),
			"nobody": _("Nobody is being served yet."),
			"your": _("Your ticket"),
			"ahead": _("{0} ahead of you"),
			"sound": _("Press OK to turn on sound"),
			"busy": _("The ticket could not be taken. Try again."),
		}
	).replace("<", "\\u003c")
	return context
