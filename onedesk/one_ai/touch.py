"""The field tools, and the badge on what OneAI wrote.

One path, not two: opening the panel from a text field the reader was just
in (public/js/one_ai/oneai.js, justLeft) makes the same card any other edit makes. The badge shows while the field still says what `AI Touch` holds.
"""

import json

import frappe
from frappe.utils import cint, flt, get_datetime, strip_html_tags

WRITES = ("Small Text", "Text", "Long Text", "Text Editor", "Markdown Editor")

TEXTS = ("Data", *WRITES, "HTML Editor")

# Every field OneAI sets is marked, not only prose: a date, an amount or a
# customer it filled is as much its as a paragraph it wrote.
UNMARKED = (
	"Section Break",
	"Column Break",
	"Tab Break",
	"HTML",
	"Button",
	"Heading",
	"Image",
	"Fold",
	"Table",
	"Table MultiSelect",
	"Password",
	"Read Only",
)

NUMBERS = ("Currency", "Float", "Int", "Percent", "Rating", "Duration")

MOST_SHOWN = 8000

EMAIL = ("Communication", "content")

MOST_QUOTED = 6000


def same(one, other, fieldtype: str | None = None) -> bool:
	"""Whether a field still says what was written: as numbers for a number,
	so 100 and "100.0" are one value, and as text otherwise."""
	if fieldtype in NUMBERS:
		return flt(one) == flt(other)
	if fieldtype == "Check":
		return cint(one) == cint(other)
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
	said = {
		"doctype": doctype,
		"name": (field.get("name") or "").strip(),
		"fieldname": fieldname,
		"fieldtype": df.fieldtype,
		"label": df.label or fieldname,
		"value": str(field.get("value") or "")[:MOST_SHOWN],
	}
	if (doctype, fieldname) == EMAIL and field.get("email") and not said["name"]:
		said["email"] = {
			"subject": str(field.get("subject") or "")[:300],
			"to": str(field.get("to") or "")[:500],
			"quoted": str(field.get("quoted") or "")[:MOST_QUOTED],
		}
	return said


def told(field: dict) -> str:
	"""What the model is told about the field it is writing.

	The field's current text comes from the browser, not from the record: it is
	what the person has in front of them, typed and perhaps not saved, and it is
	theirs to send. Nothing here reads the record.
	"""
	if field.get("email"):
		return _email(field)
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


def _email(field: dict) -> str:
	"""What the model is told when the reader is writing an email."""
	email = field["email"]
	now = field["value"].strip() if _words(field["value"]) else "(nothing yet)"
	said = "The reader is writing an email in the email window"
	if email["to"]:
		said += f", to {email['to']}"
	if email["subject"]:
		said += f', subject "{email["subject"]}"'
	said += f". What they have written so far:\n---\n{now}\n---\n"
	if email["quoted"]:
		said += f"It replies to this message, which is not yours to change:\n---\n{email['quoted']}\n---\n"
	return said + (
		"Answer with only the new text of their email: greeting, body and closing, in the language they "
		"wrote in unless they ask for another. No signature (their own is kept below what you write), no "
		"subject line, no preamble, no quotation marks, no explanation of what changed. Markdown is fine; it "
		"is shown formatted."
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
	"""Remember what OneAI put into a saved record's fields, so each shows the
	mark while it still says that."""
	if not record:
		return
	meta = frappe.get_meta(doctype)
	for fieldname, value in (changes or {}).items():
		df = meta.get_field(fieldname)
		if not df or df.fieldtype in UNMARKED or value in (None, "") or isinstance(value, (list, dict)):
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
				"value": str(value),
				"proposal": proposal,
				"touched_by": frappe.session.user,
			}
		)
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
	meta = doc.meta
	still = {
		row.fieldname: doc.get(row.fieldname)
		for row in rows
		if same(doc.get(row.fieldname), row.value, (meta.get_field(row.fieldname) or {}).get("fieldtype"))
	}
	if still:
		doc.set_onload("ai_touched", still)
	made = frappe.db.get_value(
		"AI Proposal",
		{"kind": "Create", "state": "Applied", "for_doctype": doc.doctype, "applied_doc": doc.name},
		["name", "applied_by", "applied_on"],
		as_dict=True,
	)
	if made:
		doc.set_onload(
			"ai_made",
			{"by": frappe.utils.get_fullname(made.applied_by), "on": str(made.applied_on or "")},
		)


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
