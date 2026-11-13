"""What OneAI's own records say above their fields. See one/head.py.

A proposal is read-only and carries two verbs, which is the whole design: one
somebody could edit before applying no longer says what the model suggested.
It opens on where it stands and what that means.
"""

from frappe import _, _lt
from frappe.utils import escape_html, pretty_date

from onedesk.one import registry
from onedesk.one_ai import brief, run

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


def _asks(text: str):
	return lambda doc: [
		{"fieldtype": "HTML", "fieldname": "what", "options": f"<p>{escape_html(str(text))}</p>"}
	]


def _applied(doc, **_values):
	out = run.apply(doc.name) or {}
	return _("Done. It wrote {0}.").format(out["record"]) if out.get("record") else None


def summary(doc):
	"""OneAI's summary, or what it waits for, while summaries are on here."""
	if doc.is_new() or not (doc.get(brief.BRIEF) or brief.on(doc.doctype)):
		return None
	if not doc.get(brief.BRIEF):
		return {
			"text": _("{0} Summary").format(registry.name("one_ai")),
			"lines": [_("{0} writes one here when something happens, such as an invoice, a payment or a mail.").format(registry.name("one_ai"))],
			"colour": "blue",
		}
	return {
		"text": _("{0} Summary").format(registry.name("one_ai")),
		"lines": [doc.get(brief.BRIEF), _("Written {0}.").format(pretty_date(doc.get(brief.ON)))],
		"colour": "blue",
	}


def _summarisable(doc) -> bool:
	from onedesk.one import account, apps

	return not doc.is_new() and apps.ai_on() and account.configured()


def _summarise(doc, **_values):
	brief.later(doc.doctype, doc.name)
	return _("{0} is writing it. It shows here in a minute.").format(registry.name("one_ai"))


NOTICES = {
	"oneai.summary": {"doctypes": list(brief.BRIEFS), "said": summary, "verbs": ["oneai.summarise"]},
}


MEASURES = {
	"proposal.state": proposal_state,
	"proposal.said": proposal_said,
}

VERBS = {
	"oneai.summarise": {
		"doctypes": list(brief.BRIEFS),
		"label": lambda doc: _("Summarise Again") if doc.get(brief.BRIEF) else _("Summarise Now"),
		"when": _summarisable,
		"run": _summarise,
	},
	"proposal.apply": {
		"doctypes": ["AI Proposal"],
		"label": lambda doc: _("Approve"),
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
]
