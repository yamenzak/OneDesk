"""What OneStudio's records say above their fields. See one/head.py.

An extension opens on whether it is on, what it does, and whether it has run
into mistakes lately; its one verb turns it on or off, which is the only
thing anybody here changes on it.
"""

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
		return {
			"text": _("This workspace does not run extensions on the server yet. Ask us to turn them on."),
			"colour": "orange",
		}
	return {"text": doc.explanation, "colour": "blue"} if doc.explanation else None


def extension_mistakes(doc):
	if doc.is_new() or doc.runs != extensions.ON_SERVER:
		return None
	count = ai._recent_mistakes(doc.name)
	return {"value": str(count), "tone": "alarm" if count else None}


def _switch(doc, on: bool):
	doc.enabled = int(on)
	doc.save()
	return _("Turned on.") if on else _("Turned off.")


MEASURES = {
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
	"extension.off": {
		"doctypes": [extensions.EXTENSION],
		"label": lambda doc: _("Turn Off"),
		"when": lambda doc: not doc.is_new() and bool(doc.enabled),
		"run": lambda doc, **_values: _switch(doc, False),
	},
}

HEADS = [
	{
		"doctype": extensions.EXTENSION,
		"indicators": [{"label": _lt("State"), "measure": "extension.state"}],
		"sentences": [{"measure": "extension.said"}],
		"band": [{"label": _lt("Mistakes This Week"), "source": "Measure", "measure": "extension.mistakes"}],
		"verbs": [{"verb": "extension.on", "primary": 1}, {"verb": "extension.off"}],
	},
]
