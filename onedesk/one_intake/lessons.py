"""Lessons: what people take back, remembered (docs/INTAKE.md §10).

Undoing something OneAI did, dismissing what it proposed, deleting a record it
made and moving a file it filed back are each kept as an **Intake Lesson**,
with the party and the kind of document that led to it. Two things follow:

- the next document from that party is read with its lessons, so the model
  is told "last time, people took back the supplier OneAI made";
- **three** lessons alike (the same party, the same kind of document, the
  same thing done to the same doctype) and OneAI stops doing it by itself:
  the door proposes it instead, saying why. Deleting the lessons in the
  Intake Lesson list lets it act again.
"""

import json

import frappe
from frappe import _

#: How many lessons alike before OneAI asks rather than acts.
RULE = 3

#: What a model is told of a party's lessons, at most.
MOST_TOLD = 8


def learn(row, what: str) -> None:
	"""Remember that a person took an Intake Action back."""
	reading = frappe.db.get_value("Reading", row.reading, ["kind", "party_doctype", "party_name"], as_dict=True) if row.reading else None
	if not reading or not reading.party_name:
		return
	frappe.get_doc(
		{
			"doctype": "Intake Lesson",
			"what": what,
			"action_kind": row.kind,
			"target_doctype": row.target_doctype,
			"kind": reading.kind,
			"party_doctype": reading.party_doctype,
			"party_name": reading.party_name,
			"action": row.name,
			"reading": row.reading,
			"by": frappe.session.user,
			"said": _said(row),
		}
	).insert(ignore_permissions=True)


def _said(row) -> str:
	after = json.loads(row.after or "{}")
	shown = {key: value for key, value in after.items() if key not in ("name",)}
	return f"{row.kind} {row.target_doctype} {row.target_name or ''} {json.dumps(shown, ensure_ascii=False, default=str)[:300]}".strip()


def times(reading, action) -> int:
	"""How many times people took back this very kind of thing for this party."""
	if not reading.get("party_name"):
		return 0
	return frappe.db.count(
		"Intake Lesson",
		{
			"party_doctype": reading.get("party_doctype"),
			"party_name": reading.get("party_name"),
			"kind": reading.get("kind") or "",
			"action_kind": action.kind,
			"target_doctype": action.doctype,
		},
	)


def told(party_doctype: str | None, party_name: str | None) -> str:
	"""A party's lessons, as the model reading its next document is told them."""
	if not party_name:
		return ""
	rows = frappe.get_all(
		"Intake Lesson",
		filters={"party_doctype": party_doctype, "party_name": party_name},
		fields=["what", "kind", "said"],
		order_by="creation desc",
		limit=MOST_TOLD,
	)
	if not rows:
		return ""
	lines = [f"- {row.what}: {row.said} (from a {row.kind or 'document'})" for row in rows]
	return "Earlier, people corrected what OneAI did with this party's documents:\n" + "\n".join(lines)


# ------------------------------------------------------------------ what a person does


def deleted(doc, method=None) -> None:
	"""on_trash: a person deleting a record OneAI made, which is a lesson."""
	from onedesk.one_intake import mark

	if doc.doctype not in mark.marked_doctypes() or frappe.flags.one_intake_writing or not mark.is_marked(doc.doctype, doc.name):
		return
	held = frappe.db.get_value("Intake Action", {"target_doctype": doc.doctype, "target_name": doc.name, "kind": "Create", "level": "Done"}, "name")
	if held:
		row = frappe.get_doc("Intake Action", held)
		row.db_set({"level": "Undone", "undone_by": frappe.session.user})
		learn(row, "Deleted")


def moved(doc, method=None) -> None:
	"""File on_update: a person moving a file OneAI filed somewhere else."""
	if frappe.flags.one_intake_writing or doc.is_new() or doc.is_folder:
		return
	before = doc.get_doc_before_save()
	if not before:
		return
	if before.folder != doc.folder:
		held = frappe.db.get_value("Intake Action", {"target_doctype": "File", "target_name": doc.name, "kind": "Move", "level": "Done"}, "name")
		if held:
			_moved_back(held)
	if (before.attached_to_doctype, before.attached_to_name) != (doc.attached_to_doctype, doc.attached_to_name) and before.attached_to_name:
		held = frappe.db.get_value(
			"Intake Action",
			{"target_doctype": before.attached_to_doctype, "target_name": before.attached_to_name, "kind": "Attach", "level": "Done", "after": ["like", f'%"file": "{doc.name}"%']},
			"name",
		)
		if held:
			_moved_back(held)


def _moved_back(name: str) -> None:
	row = frappe.get_doc("Intake Action", name)
	row.db_set({"level": "Undone", "undone_by": frappe.session.user})
	learn(row, "Moved Back")


def rule_says(reading, action) -> str | None:
	"""Why the door should ask rather than act, when people have taken this
	back often enough."""
	count = times(reading, action)
	if count >= RULE:
		return _("People took this back {0} times before for this party.").format(count)
	return None
