"""What a model suggested, and the person who decides whether it happens.

**A model cannot write.** What it can do is put a card in front of somebody —
this record, these fields, that value — and the doing happens afterwards, in a
request a person made by pressing Apply, down the same path they would have
taken by hand.

The split is not a formality. A tool that saves is a tool that saves on a
model's say-so, and the failure mode is not a wrong field: it is a wrong
*record*, at the end of a chain of lookups nobody read. A person between the
asking and the doing also puts the diff in front of them while they decide.

**Permissions are checked twice and never bypassed.** Once when the proposal is
written, so a model cannot suggest something the asker could not do; and again
when it is applied, as an ordinary insert, save or delete by whoever pressed the
button. There is no `ignore_permissions` in this file and there is not going to
be one.

**An edit that would overwrite somebody else's is refused.** A proposal carries
the record's `modified` from when it was written; if the record has moved since,
the proposal is stale and says so. Applying it anyway would be a model's diff
quietly undoing a person's.
"""

import json

import frappe
from frappe.utils import now_datetime

from onedesk.one_ai import touch

#: What is done and cannot be done again. Everything else is still a decision.
SETTLED = ("Applied", "Refused", "Stale")

#: How much of a record is quoted back on the card. A proposal is read by a
#: person in a hurry, and forty fields is a diff nobody checks.
MOST_FIELDS = 40


def propose(
	kind: str,
	doctype: str,
	changes: dict | None = None,
	record: str | None = None,
	why: str | None = None,
	reference: str | None = None,
) -> str:
	"""Write down what a model suggested, having checked the asker may do it.

	The check is real and happens now: `has_permission` for the verb, on the
	actual document where there is one, so a proposal to edit a record this
	person cannot edit is refused at the point it is suggested rather than at
	the point somebody presses a button.
	"""
	changes = _plain(changes or {})
	held = _allowed(kind, doctype, record)

	entry = frappe.get_doc(
		{
			"doctype": "AI Proposal",
			"kind": kind,
			"for_doctype": doctype,
			"record": record,
			"state": "Proposed",
			"asked_by": frappe.session.user,
			"said": _said(kind, doctype, record, changes),
			"why": why,
			"changes": frappe.as_json(changes),
			"was": frappe.as_json(_was(held, changes)) if held else None,
			"modified_then": str(held.modified) if held else None,
			"reference": reference,
		}
	)
	entry.insert()
	return entry.name


def apply(proposal: str) -> dict:
	"""Do it, as the person who pressed the button and with their permissions.

	An ordinary insert, save or delete. Nothing here is done on the model's
	authority, and nothing here runs as anybody but the caller.
	"""
	entry = frappe.get_doc("AI Proposal", proposal)
	_mine(entry)
	if entry.state in SETTLED:
		frappe.throw(frappe._("{0} was already {1}.").format(proposal, entry.state.lower()))

	changes = json.loads(entry.changes or "{}")
	if entry.kind == "Create":
		made = frappe.get_doc({"doctype": entry.for_doctype, **changes})
		if entry.for_doctype == "File":
			made.ai_generated = 1
		made.insert()
		touch.wrote(entry.for_doctype, made.name, changes, entry.name)
		return _done(entry, made.name)

	if entry.kind == "Edit" and not entry.record:
		frappe.throw(frappe._("This is for a document that is not saved yet. Apply it from its form."))

	held = frappe.get_doc(entry.for_doctype, entry.record)
	if entry.modified_then and str(held.modified) != entry.modified_then:
		entry.db_set("state", "Stale")
		frappe.throw(
			frappe._("{0} has changed since this was suggested, so it no longer applies.").format(
				entry.record
			)
		)

	if entry.kind == "Delete":
		held.delete()
		return _done(entry, entry.record)

	if entry.kind == "Move":
		# The workflow's own transition, which checks the role it is allowed to
		# and writes the state change and its log entry. Not a `db_set` on the
		# state field, which would move the record without any of that.
		from frappe.model.workflow import apply_workflow

		apply_workflow(held, changes.get("action"))
		return _done(entry, held.name)

	held.update(changes)
	held.save()
	touch.wrote(entry.for_doctype, held.name, changes, entry.name)
	return _done(entry, held.name)


def refuse(proposal: str) -> dict:
	"""Say no. Kept rather than deleted, because what was suggested is a record."""
	entry = frappe.get_doc("AI Proposal", proposal)
	_mine(entry)
	if entry.state in SETTLED:
		frappe.throw(frappe._("{0} was already {1}.").format(proposal, entry.state.lower()))
	entry.db_set("state", "Refused")
	return {"proposal": entry.name, "state": "Refused"}


def mine(state: str = "Proposed") -> list[dict]:
	"""This person's own proposals, newest first."""
	return frappe.get_list(
		"AI Proposal",
		filters={"state": state},
		fields=["name", "kind", "for_doctype", "record", "said", "why", "creation"],
		order_by="creation desc",
		limit_page_length=50,
	)


def _mine(entry) -> None:
	"""Whose decision this is.

	The person it was written for, or somebody who administers the workspace.
	Not because applying somebody else's would escalate anything — the write is
	checked against the applier's own permissions either way — but because a
	card addressed to one person and answered by another is a conversation
	neither of them had.
	"""
	if entry.asked_by == frappe.session.user:
		return
	from onedesk.one import roles

	roles.require()


def _allowed(kind: str, doctype: str, record: str | None):
	"""The caller's own permission for the verb, checked now.

	`frappe.has_permission` with a document does what the desk does: the role,
	the user permissions, and whatever `has_permission` hooks the doctype
	carries — which is how a proposal about a workspace an operator may not see
	is refused here rather than being written and then failing.
	"""
	verb = {"Create": "create", "Edit": "write", "Delete": "delete", "Move": "write"}.get(kind)
	if not verb:
		frappe.throw(frappe._("{0} is not something that can be proposed.").format(kind))

	held = None
	if kind == "Edit" and not record:
		# A field on a document that is not saved yet — written from the field's
		# own control, and applied into the form. What it asks is to create one.
		verb = "create"
	elif kind != "Create":
		if not record:
			frappe.throw(frappe._("A {0} has to name a record.").format(kind.lower()))
		held = frappe.get_doc(doctype, record)

	if not frappe.has_permission(doctype, ptype=verb, doc=held):
		frappe.throw(
			frappe._("You may not {0} {1}.").format(verb, held.name if held else doctype),
			frappe.PermissionError,
		)
	return held


def _was(held, changes: dict) -> dict:
	"""What the fields being changed hold now, so the card is a diff."""
	return {key: held.get(key) for key in list(changes)[:MOST_FIELDS]}


def _plain(changes: dict) -> dict:
	"""Only what a model may set. A child table or a nested document on a
	model's say-so is a diff nobody reads before pressing a button."""
	return {
		key: value
		for key, value in changes.items()
		if isinstance(value, str | int | float | bool | type(None))
	}


def _said(kind: str, doctype: str, record: str | None, changes: dict) -> str:
	if kind == "Create":
		return frappe._("Create a {0}").format(doctype)
	if kind == "Delete":
		return frappe._("Delete {0}").format(record)
	if kind == "Move":
		return frappe._("{0} on {1}").format(changes.get("action") or "?", record)
	if not record:
		return frappe._("Write {0} on a new {1}").format(", ".join(list(changes)[:3]) or "?", doctype)
	return frappe._("Change {0} on {1}").format(", ".join(list(changes)[:3]) or "?", record)


def _done(entry, name: str) -> dict:
	entry.db_set(
		{
			"state": "Applied",
			"applied_doc": name,
			"applied_by": frappe.session.user,
			"applied_on": now_datetime(),
		}
	)
	return {"proposal": entry.name, "state": "Applied", "record": name}
