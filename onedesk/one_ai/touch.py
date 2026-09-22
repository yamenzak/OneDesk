"""The field tools, and the badge on what OneAI wrote.

**One path, not two.** The control beside a prose field opens the same panel as
the launcher, pointed at that field. What comes back is an `AI Proposal` of kind
Edit — the same card, the same Apply — so "help me write this" and an agentic
edit are one thing to trust rather than two. The difference is only where Apply
lands: with the form open, the text goes *into the form*, beside whatever the
person has typed and not saved, and they save it the way they save anything.
A server-side save there would either lose their edits or be refused as stale.

**The badge is a comparison, not a flag.** `AI Touch` holds what was written.
The form is handed the fields that still say it, and the badge shows while they
do. A person's edit makes them differ and the badge is simply no longer true —
without a hook on every doctype's write path, and without anybody having to
remember to clear it.

Text is compared as text: tags stripped and whitespace collapsed, because a
Text Editor wraps what it is given in its own markup and would otherwise differ
from what was written the moment it was drawn.
"""

import json

import frappe
from frappe.utils import get_datetime, strip_html_tags

#: Where the control goes: fields somebody writes prose in.
WRITES = ("Small Text", "Text", "Long Text", "Text Editor", "Markdown Editor")

#: Where a badge can go: anything OneAI can set that a person reads as words.
TEXTS = ("Data", *WRITES, "HTML Editor")

#: What the model is shown of the field it is writing. A field is prose, not a
#: document; past this the question is about something else.
MOST_SHOWN = 8000


def same(one, other) -> bool:
	return _words(one) == _words(other)


def _words(value) -> str:
	return " ".join(strip_html_tags(str(value or "")).split())


def target(field: dict | str | None) -> dict | None:
	"""The field a question is about, checked against the doctype's own meta.

	Anything the browser says is a claim: a field that is not on the doctype, or
	is not prose, is no target at all and the question is asked as an ordinary
	one.
	"""
	if isinstance(field, str):
		field = frappe.parse_json(field) if field.strip() else None
	if not isinstance(field, dict):
		return None
	doctype = (field.get("doctype") or "").strip()
	fieldname = (field.get("fieldname") or "").strip()
	if not doctype or not fieldname or not frappe.db.exists("DocType", doctype):
		return None
	df = frappe.get_meta(doctype).get_field(fieldname)
	if not df or df.fieldtype not in WRITES:
		return None
	return {
		"doctype": doctype,
		"name": (field.get("name") or "").strip(),
		"fieldname": fieldname,
		"fieldtype": df.fieldtype,
		"label": df.label or fieldname,
		"value": str(field.get("value") or "")[:MOST_SHOWN],
	}


def told(field: dict) -> str:
	"""What the model is told about the field it is writing.

	The field's current text comes from the browser, not from the record: it is
	what the person has in front of them, typed and perhaps not saved, and it is
	theirs to send. Nothing here reads the record.
	"""
	where = (
		f"the {field['doctype']} record {field['name']}"
		if field["name"]
		else f"a new {field['doctype']} that is not saved yet"
	)
	shape = (
		"Markdown is fine; it is shown formatted."
		if field["fieldtype"] in ("Text Editor", "Markdown Editor")
		else "Plain text only, no markdown: it is shown exactly as written."
	)
	now = field["value"].strip() or "(empty)"
	return (
		f"The reader is writing the {field['label']} field ({field['fieldname']}) of {where}. "
		f"It holds this now:\n---\n{now}\n---\n"
		"Answer with only the new text for this field: no preamble, no quotation marks, "
		f"no explanation of what changed. {shape}"
	)


def written(field: dict, said: str) -> str:
	"""The model's answer as the field stores it."""
	said = (said or "").strip()
	if said.startswith("```") and said.endswith("```"):
		said = said.strip("`").split("\n", 1)[-1].strip()
	if field["fieldtype"] == "Text Editor":
		from frappe.utils import md_to_html

		return md_to_html(said)
	return said


def wrote(doctype: str, record: str, changes: dict, proposal: str | None = None) -> None:
	"""Remember what was written into a saved record's prose fields."""
	if not record:
		return
	meta = frappe.get_meta(doctype)
	for fieldname, value in (changes or {}).items():
		df = meta.get_field(fieldname)
		if not df or df.fieldtype not in TEXTS or not _words(value):
			continue
		held = frappe.db.get_value(
			"AI Touch", {"for_doctype": doctype, "record": record, "fieldname": fieldname}
		)
		row = frappe.get_doc("AI Touch", held) if held else frappe.new_doc("AI Touch")
		row.update(
			{
				"for_doctype": doctype,
				"record": record,
				"fieldname": fieldname,
				"value": value,
				"proposal": proposal,
				"touched_by": frappe.session.user,
			}
		)
		# Written as a side effect of something the person was already allowed
		# to do — `took` and `apply` checked their permission on the record — and
		# a person holds no permission on this table at all.
		row.save(ignore_permissions=True)


def onload(doc, method=None) -> None:
	"""The fields that still say what OneAI wrote, handed to the form."""
	if doc.doctype == "AI Touch" or doc.is_new():
		return
	rows = frappe.get_all(
		"AI Touch",
		filters={"for_doctype": doc.doctype, "record": doc.name},
		fields=["fieldname", "value"],
	)
	still = {row.fieldname: row.value for row in rows if same(doc.get(row.fieldname), row.value)}
	if still:
		doc.set_onload("ai_touched", still)


def forget(doc, method=None) -> None:
	if doc.doctype == "AI Touch":
		return
	frappe.db.delete("AI Touch", {"for_doctype": doc.doctype, "record": doc.name})


def took(proposal: str) -> dict:
	"""Apply a suggested edit into an open form rather than onto the record.

	The same checks as `proposals.apply` — whose it is, that it is still open,
	that this person may write that record or create one — and then it is marked
	applied and the text handed back for the form to set. Saving is the
	person's, in the form, where everything else they typed is.
	"""
	from onedesk.one_ai import proposals

	entry = frappe.get_doc("AI Proposal", proposal)
	proposals._mine(entry)
	if entry.state in proposals.SETTLED:
		frappe.throw(frappe._("{0} was already {1}.").format(proposal, entry.state.lower()))
	if entry.kind != "Edit":
		frappe.throw(frappe._("Only a suggested change can be applied in the form."))
	proposals._allowed("Edit", entry.for_doctype, entry.record or None)

	changes = json.loads(entry.changes or "{}")
	wrote(entry.for_doctype, entry.record, changes, entry.name)
	proposals._done(entry, entry.record or "")
	return {"proposal": entry.name, "record": entry.record, "changes": changes}


def landed(proposal: str, record: str) -> dict:
	"""A suggestion taken into a new document, now that the document is saved.

	Only counted if the record was made after the text was taken and still says
	it — so a form that was abandoned and another record opened in its place
	does not collect a badge it never had.
	"""
	entry = frappe.get_doc("AI Proposal", proposal)
	if entry.applied_by != frappe.session.user or entry.state != "Applied" or entry.record:
		return {}
	held = frappe.get_doc(entry.for_doctype, record)
	held.check_permission("read")
	if entry.applied_on and get_datetime(held.creation) < get_datetime(entry.applied_on):
		return {}

	changes = json.loads(entry.changes or "{}")
	kept = {key: value for key, value in changes.items() if same(held.get(key), value)}
	wrote(entry.for_doctype, record, kept, entry.name)
	entry.db_set({"record": record, "applied_doc": record})
	return kept

