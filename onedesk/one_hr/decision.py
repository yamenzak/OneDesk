"""Somebody answered, and the document says who.

Two doctypes in the Time group are asked for and then answered by a person:
`Attendance Request` and `Shift Request`. HRMS's whole approval for both is that
an Employee has no `submit` grant and HR does, so the decision happens and
nothing records that it was one — no name, no date, no note, and for one of them
no way at all to say no.

What they share is here: who may answer, the three fields that say who did, and
the permission rule. What they do not share stays in their own modules, because
the two verdicts are genuinely different shapes — a shift request carries
HRMS's own `status` and is submitted either way, and an attendance request has
no status field and a turned-down one stays a draft.

**Who may answer is the `submit` grant and nothing else.** Not a role name: a
workspace that has given approvals to its own Department Head role has already
answered that question in the permission table, and a second list of who may
approve is a second answer that will disagree with the first.
"""

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
