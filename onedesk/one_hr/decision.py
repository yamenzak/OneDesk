"""Somebody answered, and the document says who."""

import frappe
from frappe import _
from frappe.utils import now_datetime

#: The three fields both of them carry, added as custom fields on each.
SIGNED = ("one_decided_by", "one_decided_on", "one_note")


def may_decide(doc) -> None:
	if not frappe.has_permission(doc.doctype, "submit", doc=doc):
		frappe.throw(
			_("Only somebody who can approve these may answer this one."), frappe.PermissionError
		)


def carry(doc, field: str, verdict: str) -> None:
	"""The verdict One's own Approve or Reject sets, kept through the save.
	frappe puts back any field the person may not write at its level, and the
	approver a record names often holds no HR role, so a Reject came back as
	unanswered and the submit then read it as a yes. `kept` sets it again."""
	doc.set(field, verdict)
	doc.flags.one_verdict = (field, verdict)


def kept(doc, method=None) -> None:
	"""before_validate, which runs after frappe's reset: the verdict `carry`
	set, back on the record."""
	if doc.flags.get("one_verdict"):
		field, verdict = doc.flags.one_verdict
		doc.set(field, verdict)


def sign(doc, note=None) -> None:
	"""Stamp the decision onto a document that is about to be saved."""
	doc.one_decided_by = frappe.session.user
	doc.one_decided_on = now_datetime()
	if note is not None:
		doc.one_note = note or ""


def signed(note=None) -> dict:
	"""The same three, as something `db_set` can take."""
	return {
		"one_decided_by": frappe.session.user,
		"one_decided_on": now_datetime(),
		"one_note": note or "",
	}
