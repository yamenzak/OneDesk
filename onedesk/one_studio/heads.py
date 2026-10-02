"""What OneStudio's records say above their fields. See one/head.py.

An extension opens on whether it is on, what it does, and whether it has run
into errors lately; its one verb turns it on or off, which is the only
thing anybody here changes on it.
"""

import frappe
from frappe import _, _lt

from onedesk.one_studio import ai, extensions


def extension_state(doc):
	if doc.is_new():
		return None
	if doc.enabled:
		return {"label": _("On"), "colour": "green"}
	if doc.review == "Refused":
		return {"label": _("Refused by Review"), "colour": "red"}
	if doc.runs == extensions.ON_SERVER and not extensions.runs_server_scripts():
		return {"label": _("Cannot Run Here"), "colour": "orange"}
	return {"label": _("Off"), "colour": "grey"}


def extension_said(doc):
	if doc.is_new():
		return None
	if doc.review == "Refused":
		return {"text": _("The review refused it: {0}").format(doc.review_note or ""), "colour": "red"}
	if doc.runs == extensions.ON_SERVER and not extensions.runs_server_scripts():
		# What it does still comes first: the form leaves the explanation to
		# the head unless the review refused it.
		return {
			"text": " ".join(
				filter(
					None,
					[
						doc.explanation,
						_(
							"It cannot run here yet: this workspace does not run extensions on the server. Ask us to turn them on."
						),
					],
				)
			),
			"colour": "orange",
		}
	return {"text": doc.explanation, "colour": "blue"} if doc.explanation else None


def extension_mistakes(doc):
	if doc.is_new():
		return None
	count = ai._recent_mistakes(doc.name)
	return {"value": str(count), "tone": "alarm" if count else None}


def _switch(doc, on: bool):
	doc.enabled = int(on)
	doc.save()
	return _("Turned on.") if on else _("Turned off.")


def _mended(doc):
	from onedesk.one_studio import mend

	return mend.start(doc)


def record_type_said(doc):
	if doc.is_new() or not doc.description:
		return None
	return {"text": doc.description, "colour": "blue"}


def record_type_records(doc):
	if doc.is_new() or not frappe.db.exists("DocType", doc.record_doctype):
		return None
	return {
		"value": str(frappe.db.count(doc.record_doctype)),
		"route": f"/desk/{frappe.scrub(doc.record_doctype).replace('_', '-')}",
	}


MEASURES = {
	"record_type.said": record_type_said,
	"record_type.records": record_type_records,
	"extension.state": extension_state,
	"extension.said": extension_said,
	"extension.mistakes": extension_mistakes,
}

VERBS = {
	"extension.on": {
		"doctypes": [extensions.EXTENSION],
		"label": lambda doc: _("Turn On"),
		"when": lambda doc: not doc.is_new() and not doc.enabled and doc.review == "Passed",
		"run": lambda doc, **_values: _switch(doc, True),
	},
	"extension.mend": {
		"doctypes": [extensions.EXTENSION],
		"label": lambda doc: _("Mend With OneAI"),
		"when": lambda doc: not doc.is_new() and ai._recent_mistakes(doc.name) > 0,
		"run": lambda doc, **_values: _mended(doc),
	},
	"extension.off": {
		"doctypes": [extensions.EXTENSION],
		"label": lambda doc: _("Turn Off"),
		"when": lambda doc: not doc.is_new() and bool(doc.enabled),
		"run": lambda doc, **_values: _switch(doc, False),
	},
}

HEADS = [
	{
		"doctype": "Record Type",
		"sentences": [{"measure": "record_type.said"}],
		"band": [{"label": _lt("Records"), "source": "Measure", "measure": "record_type.records"}],
	},
	{
		"doctype": extensions.EXTENSION,
		"indicators": [{"label": _lt("State"), "measure": "extension.state"}],
		"sentences": [{"measure": "extension.said"}],
		"band": [
			{"label": _lt("Errors in the Last 7 Days"), "source": "Measure", "measure": "extension.mistakes"}
		],
		"verbs": [
			{"verb": "extension.on", "primary": 1},
			{"verb": "extension.off"},
			{"verb": "extension.mend"},
		],
	},
]
