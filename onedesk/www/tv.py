"""The page a TV opens: /tv. It pairs, then shows its channel (one_display/
screens.py). Written for old TV browsers: one plain page, no framework, and a
script that runs on Chromium 53."""

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
	context.words_json = json.dumps(
		{
			"pair": _("Pair this screen"),
			"how": _("In OneDisplay, open Display Screen, choose Add Display Screen and enter this code."),
			"serving": _("Now Serving"),
			"counter": _("Counter"),
			"waiting": _("Waiting"),
			"nobody": _("Nobody is being served yet."),
			"take": _("Take a ticket"),
			"your": _("Your ticket"),
			"ahead": _("{0} ahead of you"),
			"offline": _("Offline"),
			"sound": _("Press OK to turn on sound"),
			"busy": _("Something went wrong. Try again."),
		}
	).replace("<", "\\u003c")
	return context
