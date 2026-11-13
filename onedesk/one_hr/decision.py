"""Somebody answered, and the document says who."""

import frappe
from frappe import _
from frappe.utils import now_datetime

SIGNED = ("one_decided_by", "one_decided_on", "one_note")


def may_decide(doc) -> None:
	if not frappe.has_permission(doc.doctype, "submit", doc=doc):
		frappe.throw(
			_("Only somebody who can approve these may answer this one."), frappe.PermissionError
		)
	if own(doc):
		frappe.throw(_("Somebody else has to answer your own request."), frappe.PermissionError)


def own(doc) -> bool:
	"""Whether the request is the reader's own. Nobody answers their own: HR
	Settings' two prevent_self switches say so for leave and claims, and One
	holds every other request to the same rule."""
	employee = doc.get("employee")
	return bool(employee) and frappe.db.get_value("Employee", employee, "user_id") == frappe.session.user


def carry(doc, field: str, verdict: str) -> None:
	"""The verdict One's own Approve or Reject sets, kept through the save.
	frappe puts back any field the person may not write at its level, and the
	approver a record names often holds no HR role, so a Reject came back as
	unanswered and the submit then read it as a yes. `kept` sets it again."""
	doc.set(field, verdict)
	doc.flags.one_verdict = (field, verdict)


def answer(doctype: str, name: str, field: str, verdict: str, note, waiting: str) -> None:
	"""One's own Approve or Reject of a request that answering submits (leave,
	a claim, a shift): only somebody who may decide, only while it waits
	(`waiting` says so otherwise), the verdict in `field` carried through the
	save, and the note on it. Submitting signs it."""
	doc = frappe.get_doc(doctype, name)
	may_decide(doc)
	if doc.docstatus != 0:
		frappe.throw(waiting)
	carry(doc, field, verdict)
	doc.one_note = note or ""
	doc.submit()


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
