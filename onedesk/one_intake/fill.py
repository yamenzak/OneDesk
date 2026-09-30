"""What a record Intake makes still needs, asked of OneAI from the document.

A planner fills the fields it knows a kind by: a task's subject and dates, a
bill's supplier and lines. What else the kind requires is the workspace's to
decide, and it changes: a required field added on the Customize page, a kind
Numbering names by one of its fields, or one whose name a person types. None
of that is in the planner, so without this the save fails and the action is
refused.

So while Intake writes a new record (`filling`, from act._write), two hooks
on every kind ask the model, once each, for what is still `missing`
(one_ai/kind.py), from the document and nothing else:

- `before_insert`, before frappe names the record: its name, when the kind is
  named by a field or typed by whoever makes it;
- `before_save`, after the kind's own validate has filled what it fills: every
  required field still empty.

A value the document does not give is left empty, and frappe then refuses the
record as it always would, with its own words, so the action waits for a
person. Only the record Intake is making is touched, never one its flow makes
on the way, and never outside Intake's write.
"""

import json
from contextlib import contextmanager

import frappe

from onedesk.one_ai import kind

#: The AI action that fills a record's missing fields from a document.
FILL = "intake_fill"

#: How much of a document the model is shown.
MOST = 12000


@contextmanager
def filling(reading: str, doctype: str):
	"""While Intake makes one record of `doctype` for a reading."""
	was = frappe.flags.one_intake_fill
	frappe.flags.one_intake_fill = {"reading": reading, "doctype": doctype}
	try:
		yield
	finally:
		frappe.flags.one_intake_fill = was


def _mine(doc) -> dict | None:
	said = frappe.flags.one_intake_fill
	if said and doc.doctype == said["doctype"] and doc.is_new() and not doc.flags.one_filled:
		return said
	return None


def before_insert(doc, method=None) -> None:
	"""The record's name, when the document has to give it."""
	said = _mine(doc)
	if not said:
		return
	named = kind.naming(doc.doctype)
	needs = [one for one in kind.missing(doc) if one[0] in (kind.TYPED, named.get("field"))]
	if needs:
		_fill(doc, needs, said["reading"])


def before_save(doc, method=None) -> None:
	"""Every required field still empty after the kind's own validate."""
	said = _mine(doc)
	if not said:
		return
	needs = [one for one in kind.missing(doc) if one[0] != kind.TYPED and doc.meta.has_field(one[0])]
	if needs:
		_fill(doc, needs, said["reading"])
		doc.flags.one_filled = True


def _fill(doc, needs: list[tuple[str, str]], reading: str) -> None:
	from onedesk.one_ai import proposals

	described = {one["fieldname"]: one for one in kind.fields(doc.meta)}
	asked = []
	for fieldname, label in needs:
		if fieldname == kind.TYPED:
			asked.append(
				{"fieldname": kind.TYPED, "label": label, "about": "the new record's own name, typed"}
			)
		elif fieldname in described:
			asked.append(described[fieldname])
	if not asked:
		return
	values = _ask(doc, asked, reading)
	if not values:
		return
	wanted = {one["fieldname"] for one in asked}
	values = {key: value for key, value in values.items() if key in wanted and value not in (None, "")}
	typed = values.pop(kind.TYPED, None)
	for key, value in proposals._understood(doc.doctype, values).items():
		doc.set(key, value)
	if typed:
		doc.set(kind.TYPED, str(typed).strip()[:140])


def _ask(doc, asked: list[dict], reading: str) -> dict:
	from onedesk.one_ai import run
	from onedesk.one_hr.hiring import read

	said = frappe.db.get_value("Reading", reading, ["title", "summary", "text"], as_dict=True) or {}
	already = {
		key: value
		for key, value in doc.as_dict(no_default_fields=True).items()
		if value not in (None, "", 0) and not isinstance(value, list | dict)
	}
	text = json.dumps(
		{
			"kind": doc.doctype,
			"needs": asked,
			"already": already,
			"document": {
				"title": said.get("title"),
				"summary": said.get("summary"),
				"text": (said.get("text") or "")[:MOST],
			},
		},
		default=str,
	)
	try:
		out = read(run.once(FILL, text, reference=reading))
	except Exception:
		frappe.log_error(title=f"Intake could not fill {doc.doctype}")
		return {}
	return (out or {}).get("values") or {}
