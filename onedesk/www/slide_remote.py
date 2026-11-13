"""The page a presenter's phone opens from the presenter view's QR code:
/slide-remote?t=<token>. It drives the slides; it reads nothing.
one_deck/remote.py says what the token pairs."""

import json

import frappe
from frappe import _

from onedesk.one_deck import remote

no_cache = 1


def get_context(context):
	context.no_cache = 1
	token = frappe.form_dict.get("t") or ""
	said = remote.paired(token)
	context.gone = not said
	if said:
		context.title = said["title"]
		context.remote = json.dumps(
			{
				"token": token,
				"key": remote.phone_key(token),
				"socket": {"port": frappe.conf.socketio_port if frappe._dev_server else None, "site": frappe.local.site},
				# what remote.js says, in the reader's language
				"words": {
					"slide": _("Slide {0} of {1}"),
					"end": _("End of the presentation"),
					"connected": _("Connected. Waiting for the presenter view…"),
					"connecting": _("Connecting…"),
					"ended": _("This remote has ended"),
					"taken": _("Another phone is already the remote for this screen."),
					"failed": _("Could not connect. Check the phone's connection."),
				},
			}
		)
	return context
