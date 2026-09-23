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
from frappe.utils import now_datetime, strip_html_tags

from onedesk.one_ai import touch

#: What is done and cannot be done again. Everything else is still a decision.
SETTLED = ("Applied", "Refused", "Stale")

#: How much of a record is quoted back on the card. A proposal is read by a
#: person in a hurry, and forty fields is a diff nobody checks.
MOST_FIELDS = 40

#: Rows a suggestion may carry in one child table. An expense claim is its rows
#: — but twenty is a stack of receipts somebody reads, and a hundred is a table
#: nobody does.
MOST_ROWS = 20


def propose(
	kind: str,
	doctype: str,
	changes: dict | None = None,
	record: str | None = None,
	why: str | None = None,
	reference: str | None = None,
	files: list[str] | None = None,
) -> str:
	"""Write down what a model suggested, having checked the asker may do it.

	The check is real and happens now: `has_permission` for the verb, on the
	actual document where there is one, so a proposal to edit a record this
	person cannot edit is refused at the point it is suggested rather than at
	the point somebody presses a button.
	"""
	changes = _plain(changes or {}, doctype)
	if kind in ("Create", "Edit") and frappe.db.exists("DocType", doctype):
		changes = _understood(doctype, changes)
	held = _allowed(kind, doctype, record)
	if kind == "Create":
		_ready(doctype, changes)

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
			"files": frappe.as_json(list(files or [])) if files else None,
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
		_attach(entry, made.name)
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
	_attach(entry, held.name)
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


def _ready(doctype: str, changes: dict) -> None:
	"""Refuse a new record now that frappe would refuse at Approve.

	Frappe's own checks on a document that is never saved: links resolved and
	their fetched fields filled, then the doctype's own `validate` — which is
	where HRMS says a leave needs an approver and where Expense Claim sets its
	exchange rate — inside a savepoint that is always rolled back, then what is
	required and still empty. A model told "Leave Approver is missing" asks the
	person; a card that fails when they press Approve teaches them the cards do
	not work.
	"""
	meta = frappe.get_meta(doctype)
	unknown = [key for key in changes if not meta.has_field(key) and key not in frappe.model.default_fields]
	doc = frappe.new_doc(doctype)
	doc.update(changes)
	rows = [doc, *(row for table in doc.meta.get_table_fields() for row in doc.get(table.fieldname) or [])]

	bad, wrong = [], set()
	for one in rows:
		invalid, _cancelled = one.get_invalid_links()
		# frappe's own words for each: "Leave Type: Holiday Leave".
		bad += [f"Could not find {said}" for _field, _value, said in invalid]
		wrong |= {(one, field) for field, _value, _said in invalid}

	muted = frappe.flags.mute_messages
	frappe.db.savepoint(READY)
	frappe.flags.mute_messages = True
	try:
		for one in rows:
			one._fix_numeric_types()  # as insert does
		doc.run_method("before_validate")
		doc.run_method("validate")
	except frappe.ValidationError as refused:
		bad.append(strip_html_tags(str(refused)).strip())
	except Exception:
		# Something a controller did not expect of a record with no name yet:
		# not the model's mistake, and Approve will say it if it is real.
		pass
	finally:
		frappe.flags.mute_messages = muted
		frappe.db.rollback(save_point=READY)

	missing = []
	for one in rows:
		for fieldname, _msg in one._get_missing_mandatory_fields():
			if fieldname in ("parent", "parenttype") or (one, fieldname) in wrong:
				continue  # a row's parent is set on save; a wrong link is said above
			missing.append(f"{one.meta.get_label(fieldname)} ({fieldname})")
	if missing:
		bad.insert(0, "Still needed: " + ", ".join(dict.fromkeys(missing)))
	if unknown:
		# The model's own guess at a field name, said back so it can correct
		# itself in one step instead of asking the person what a field is called.
		bad.insert(0, f"{doctype} has no field {', '.join(unknown)}. Its fields: {', '.join(fields_of(meta))}")
	if bad:
		frappe.throw(
			". ".join(one.rstrip(".") for one in dict.fromkeys(bad))
			+ ". "
			# Said to the model, not to a person: it asks them, in their language.
			+ "Correct what you can from what the person already said and suggest it again; ask them only for what they have not said.",
			frappe.MandatoryError,
		)


#: Layout, not data.
LAYOUT = {"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Heading", "Image", "Fold"}


def _understood(doctype: str, changes: dict) -> dict:
	"""What the model meant, where frappe can say so without guessing.

	A field named by its label — "due_date" for the field labelled Due Date,
	whose name is `date` — is that field. A link given as its record's title —
	"Rania Sabbagh" for a User — is that record, when exactly one record the
	reader may see has that title. Anything less certain is left as it was,
	and `_ready` says what is wrong with it.
	"""
	meta = frappe.get_meta(doctype)
	labelled = {
		frappe.scrub(f.label): f.fieldname for f in meta.fields if f.label and f.fieldtype not in LAYOUT
	}
	meant = {}
	for key, value in changes.items():
		field = key
		if not meta.has_field(key) and key not in frappe.model.default_fields:
			field = labelled.get(frappe.scrub(key), key)
		df = meta.get_field(field)
		if df and df.fieldtype in frappe.model.table_fields and isinstance(value, list):
			value = [_understood(df.options, row) if isinstance(row, dict) else row for row in value]
		elif df and df.fieldtype == "Link" and isinstance(value, str) and value:
			if not frappe.db.exists(df.options, value):
				value = _titled(df.options, value) or value
		meant[field] = value
	return meant


def _titled(doctype: str, said: str) -> str | None:
	"""The one record of a type the reader may see whose title is `said`."""
	meta = frappe.get_meta(doctype)
	title = "full_name" if doctype == "User" else meta.title_field
	if not title or not meta.has_field(title):
		return None
	found = frappe.get_list(doctype, filters={title: said}, pluck="name", limit_page_length=2)
	return found[0] if len(found) == 1 else None


def fields_of(meta, most: int = 80) -> list[str]:
	"""A type's fields as a model can use them: "fieldname (Label)", required
	ones marked, hidden and layout ones left out."""
	return [
		f"{f.fieldname} ({f.label}{', required' if f.reqd else ''})"
		for f in meta.fields
		if f.fieldtype not in LAYOUT and f.fieldtype != "Password" and not f.hidden
	][:most]


#: The savepoint a new record is tried in and rolled back from.
READY = "one_ai_ready"


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


def _plain(changes: dict, doctype: str | None = None) -> dict:
	"""Only what a model may set.

	Plain values, and rows of plain values in the doctype's own child tables.
	A row is allowed because some records are their rows — an expense claim is
	its receipts — and the card draws every row it carries, so it is read before
	anybody presses Approve. A nested document, a table that is not the
	doctype's, or a row holding anything but plain values is dropped.
	"""
	plain = (str, int, float, bool, type(None))
	tables = {}
	if doctype and frappe.db.exists("DocType", doctype):
		tables = {
			df.fieldname: df.options
			for df in frappe.get_meta(doctype).fields
			if df.fieldtype in ("Table", "Table MultiSelect")
		}

	kept = {}
	for key, value in changes.items():
		if isinstance(value, plain):
			kept[key] = value
		elif key in tables and isinstance(value, list):
			allowed = {df.fieldname for df in frappe.get_meta(tables[key]).fields}
			rows = [
				{field: one for field, one in row.items() if field in allowed and isinstance(one, plain)}
				for row in value[:MOST_ROWS]
				if isinstance(row, dict)
			]
			if rows:
				kept[key] = rows
	return kept


def _attach(entry, name: str) -> None:
	"""The files a suggestion was made from, attached to what it made.

	A receipt read into an expense claim belongs on the claim: it is what the
	claim is evidence of. Inserted as the person approving, like the record
	itself, and only once however often this runs.
	"""
	for url in json.loads(entry.get("files") or "[]"):
		if frappe.db.exists(
			"File", {"file_url": url, "attached_to_doctype": entry.for_doctype, "attached_to_name": name}
		):
			continue
		frappe.get_doc(
			{
				"doctype": "File",
				"file_url": url,
				"attached_to_doctype": entry.for_doctype,
				"attached_to_name": name,
				"is_private": 1 if url.startswith("/private/") else 0,
			}
		).insert()


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
