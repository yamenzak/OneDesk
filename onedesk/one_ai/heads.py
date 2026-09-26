"""What OneAI's own records say above their fields. See one/head.py.

A proposal is read-only and carries two verbs, which is the whole design: one
somebody could edit before applying no longer says what the model suggested.
It opens on where it stands and what that means. An action's setting opens on
what the action runs on, so that anything added reads as added.
"""

import frappe
from frappe import _, _lt
from frappe.utils import escape_html

from onedesk.one_ai import run

#: Where a proposal stands, in a word and a colour.
SAYS = {
	"Proposed": ("orange", _lt("Waiting for you")),
	"Applied": ("green", _lt("Done")),
	"Refused": ("grey", _lt("Refused")),
	"Stale": ("red", _lt("Out of date")),
}


def proposal_state(doc):
	if doc.is_new() or not doc.state:
		return None
	colour, word = SAYS.get(doc.state, ("grey", doc.state))
	return {"label": str(word), "colour": colour}


def proposal_said(doc):
	if doc.is_new():
		return None
	if doc.state == "Stale":
		return {
			"text": _("{0} changed after this was suggested, so it no longer applies.").format(doc.record),
			"colour": "red",
		}
	if doc.state == "Applied" and doc.get("applied_doc"):
		return {"text": _("Done. It wrote {0}.").format(doc.applied_doc), "colour": "green"}
	if doc.state == "Proposed":
		return {
			"text": _(
				"Nothing has happened yet. It is checked against your own permissions when you apply it."
			),
			"colour": "blue",
		}
	return None


def action_runs_on(doc):
	"""What the action runs on, and that anything added below is added."""
	if not doc.get("action"):
		return None
	asked = frappe.db.get_value("AI Action", doc.action, ["label", "capability"], as_dict=True)
	if not asked:
		return None
	return {
		"text": _(
			"{0} runs on a model that can do {1}. Anything added below is added to the instruction it already carries, and never replaces it."
		).format(asked.label, (asked.capability or "").lower()),
		"colour": "blue",
	}


def _asks(text: str):
	return lambda doc: [
		{"fieldtype": "HTML", "fieldname": "what", "options": f"<p>{escape_html(str(text))}</p>"}
	]


def _applied(doc, **_values):
	out = run.apply(doc.name) or {}
	return _("Done. It wrote {0}.").format(out["record"]) if out.get("record") else None


MEASURES = {
	"proposal.state": proposal_state,
	"proposal.said": proposal_said,
	"action.runs_on": action_runs_on,
}

VERBS = {
	# Whose decision it is, the server checks (proposals._mine).
	"proposal.apply": {
		"doctypes": ["AI Proposal"],
		"label": lambda doc: _("Apply"),
		"when": lambda doc: not doc.is_new() and doc.state == "Proposed",
		"fields": _asks(_lt("Do this now, as you?")),
		"run": _applied,
	},
	"proposal.refuse": {
		"doctypes": ["AI Proposal"],
		"label": lambda doc: _("Refuse"),
		"when": lambda doc: not doc.is_new() and doc.state == "Proposed",
		"fields": _asks(_lt("Say no to this?")),
		"run": lambda doc, **_values: run.refuse(doc.name) and None,
	},
}

HEADS = [
	{
		"doctype": "AI Proposal",
		"indicators": [{"label": _lt("State"), "measure": "proposal.state"}],
		"sentences": [{"measure": "proposal.said"}],
		"verbs": [{"verb": "proposal.apply", "primary": 1}, {"verb": "proposal.refuse"}],
	},
	{
		"doctype": "AI Action Setting",
		"sentences": [{"measure": "action.runs_on"}],
		"redraw_on": ["action"],
	},
]
