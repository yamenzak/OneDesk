"""The page a file request's link opens: /r/<token>.

A checklist of the files asked for, each with a place to send it. Everything
it does goes through one_storage/file_requests.py; this only draws.
"""

import frappe
from frappe import _
from frappe.utils import get_fullname

from onedesk.one_storage import file_requests

no_cache = 1

SAID = {
	"sent": lambda: _("Thank you. It has arrived."),
	"kind": lambda: _("That kind of file is not what was asked for."),
	"nothing": lambda: _("Choose a file first."),
	"closed": lambda: _("This request is closed."),
}


def get_context(context):
	context.no_cache = 1
	token = frappe.form_dict.get("token")
	context.token = token
	doc, person = file_requests.live(token)
	if not doc:
		context.gone = True
		return context
	said = frappe.form_dict.get("said") or ""
	context.said = SAID[said]() if said in SAID else None
	context.said_wrong = said in ("kind", "nothing", "closed")
	context.doc = doc
	context.by = get_fullname(doc.owner)
	context.closed = doc.status != "Open"
	context.overdue = file_requests.overdue(doc)
	sent = {}
	for one in doc.uploads:
		if one.email == person.email:
			sent.setdefault(one.item, []).append(frappe.db.get_value("File", one.file, "file_name") or "")
	context.items = [
		{
			"name": one.name,
			"label": one.label,
			"description": one.description,
			"required": one.required,
			"several": one.several,
			"accept": ",".join(f".{ext.strip()}" for ext in (one.accept or "").split(",") if ext.strip()),
			"kinds": one.accept,
			"sent": sent.get(one.label, []),
		}
		for one in doc.items
	]
	context.complete = person.state == "Complete"
	return context
