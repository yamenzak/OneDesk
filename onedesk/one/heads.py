"""What One's own records say above their fields. See one/head.py.

A News Source says why its last fetch failed and a hidden News Item that it
is hidden. A Second Approval says where it stands and why it asks, and
offers whoever may decide it its kind's one action and Refuse; the payment,
bank account or employee it is about says it waits, with the same action.
"""

import frappe
from frappe import _, _lt
from frappe.utils import get_fullname, pretty_date

from onedesk.one import second


def news_failed(doc):
	"""Why the last fetch failed, until one works."""
	if doc.get("last_error"):
		return {"text": doc.last_error, "colour": "orange"}
	return None


def news_hidden(doc):
	if doc.get("hidden_item"):
		return {"text": _("Hidden. This headline is not shown on the top bar or on screens."), "colour": "gray"}
	return None


STATES = {
	second.WAITING: ("orange", _lt("Waiting")),
	second.APPROVED: ("green", _lt("Approved")),
	second.REFUSED: ("red", _lt("Refused")),
}


def approval_state(doc):
	if doc.is_new() or not doc.status:
		return None
	colour, word = STATES.get(doc.status, ("gray", doc.status))
	return {"label": str(word), "colour": colour}


def approval_said(doc):
	"""Why it asks, and who decided or may decide it."""
	if doc.is_new():
		return None
	lines = (doc.reasons or "").splitlines()
	if doc.status == second.WAITING:
		people = second.deciders(doc)
		text = (
			_("Waiting for {0}.").format(", ".join(get_fullname(one) for one in people))
			if people
			else _("Nobody else may approve this, so {0} approves it alone, with remarks.").format(get_fullname(doc.asked_by))
		)
		return {"text": text, "lines": lines, "colour": "orange"}
	said = _("Approved by {0} {1}.") if doc.status == second.APPROVED else _("Refused by {0} {1}.")
	lines += [doc.remarks] if doc.remarks else []
	return {
		"text": said.format(get_fullname(doc.decided_by), pretty_date(doc.decided_on)),
		"lines": lines,
		"colour": "green" if doc.status == second.APPROVED else "red",
	}


def _remarks(doc) -> list[dict]:
	return [
		{
			"fieldtype": "Small Text",
			"fieldname": "remarks",
			"label": _("Remarks"),
			"reqd": 1 if doc.asked_by == frappe.session.user else 0,
		}
	]


def _waiting_on(doc):
	"""The waiting approval a payment, a bank account or an employee is the
	reference of."""
	name = frappe.db.get_value(
		second.DOCTYPE, {"reference_doctype": doc.doctype, "reference_name": doc.name, "status": second.WAITING}, "name"
	)
	return frappe.get_doc(second.DOCTYPE, name) if name else None


def waiting_here(doc):
	"""On a payment, a bank account or an employee: it waits for a second
	person, and why; or the bank details were refused."""
	if doc.is_new():
		return None
	row = _waiting_on(doc)
	if row:
		return {"text": _("Waiting for a second person to approve it."), "lines": (row.reasons or "").splitlines(), "colour": "orange"}
	if doc.doctype == "Payment Entry":
		if doc.docstatus == 0 and second.held(doc.party_type, doc.party):
			return {"text": _("Payments to {0} wait until their new bank details are approved.").format(doc.party_name or doc.party), "colour": "orange"}
		return None
	party = (doc.party_type, doc.party) if doc.doctype == "Bank Account" else ("Employee", doc.name)
	last = second.held(*party)
	if last and frappe.db.get_value(second.DOCTYPE, last, "status") == second.REFUSED:
		return {"text": _("The new bank details were refused. Nothing is paid until they are changed and approved."), "colour": "red"}
	return None


def _decidable(doc) -> bool:
	row = _waiting_on(doc)
	return bool(row and second.may_decide(row))


HERE = ["Payment Entry", "Bank Account", "Employee"]

NOTICES = {
	"second.waiting": {"doctypes": HERE, "said": waiting_here, "verbs": ["second.approve_here"]},
}


MEASURES = {
	"news.failed": news_failed,
	"news.hidden": news_hidden,
	"approval.state": approval_state,
	"approval.said": approval_said,
}

VERBS = {
	"second.approve": {
		"doctypes": [second.DOCTYPE],
		"label": lambda doc: _(second.APPROVE[doc.kind]),
		"when": lambda doc: not doc.is_new() and second.may_decide(doc),
		"fields": _remarks,
		"run": lambda doc, remarks=None, **_values: second.approve(doc.name, remarks),
	},
	"second.refuse": {
		"doctypes": [second.DOCTYPE],
		"label": lambda doc: _("Refuse"),
		"when": lambda doc: not doc.is_new() and second.may_decide(doc),
		"fields": _remarks,
		"run": lambda doc, remarks=None, **_values: second.refuse(doc.name, remarks),
	},
	"second.approve_here": {
		"doctypes": HERE,
		"label": lambda doc: _(second.APPROVE[_waiting_on(doc).kind]),
		"when": _decidable,
		"fields": lambda doc: _remarks(_waiting_on(doc)),
		"run": lambda doc, remarks=None, **_values: second.approve(_waiting_on(doc).name, remarks),
	},
}

HEADS = [
	{"doctype": "News Source", "sentences": [{"measure": "news.failed"}]},
	{"doctype": "News Item", "sentences": [{"measure": "news.hidden"}]},
	{
		"doctype": "Second Approval",
		"indicators": [{"label": _lt("Status"), "measure": "approval.state"}],
		"sentences": [{"measure": "approval.said"}],
		"band": [
			{"label": _lt("Asked By"), "source": "Field", "field": "asked_by"},
			{"label": _lt("Asked On"), "source": "Field", "field": "asked_on"},
			{"label": _lt("Reference Name"), "source": "Field", "field": "reference_name", "hide_empty": 1},
			{"label": _lt("Amount"), "source": "Field", "field": "amount", "shown_when": [["kind", "=", "Payment"]]},
			{"label": _lt("Records"), "source": "Field", "field": "records", "shown_when": [["kind", "=", "Export"]]},
		],
		"verbs": [{"verb": "second.approve", "primary": 1}, {"verb": "second.refuse"}],
	},
]
