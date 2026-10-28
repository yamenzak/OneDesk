"""What a record Intake makes still needs, asked of OneAI from the document.

While Intake writes a new record (`filling`), `before_insert` asks for its name
and `before_save` for every required field still empty, once each.
"""

import json
from contextlib import contextmanager

import frappe

from onedesk.one_ai import kind

FILL = "intake_fill"

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
	said = frappe.db.get_value("Reading", reading, ["title", "summary", "text"], as_dict=True) or {}
	already = {
		key: value
		for key, value in doc.as_dict(no_default_fields=True).items()
		if value not in (None, "", 0) and not isinstance(value, list | dict)
	}
	return _asked(doc.doctype, asked, already, {"title": said.get("title"), "summary": said.get("summary"), "text": said.get("text")}, reading)


def _asked(doctype: str, asked: list[dict], already: dict, document: dict, reference: str) -> dict:
	"""The model's values for `asked`, from a document's text."""
	from onedesk.one_ai import run
	from onedesk.one_hr.hiring import read

	text = json.dumps(
		{"kind": doctype, "needs": asked, "already": already, "document": {**document, "text": (document.get("text") or "")[:MOST]}},
		default=str,
	)
	try:
		out = read(run.once(FILL, text, reference=reference))
	except Exception:
		frappe.clear_messages()
		frappe.log_error(title=f"OneAI could not fill {doctype}")
		return {}
	return (out or {}).get("values") or {}


def from_file(doctype: str, fields: list[dict], name: str, content: bytes, already: dict, reference: str) -> dict:
	"""What a file says for `fields` of a `doctype` row, read now rather
	than kept: a file requested with a number and dates beside it
	(one_storage/file_requests.guess). Only the fields asked, as given."""
	from onedesk.one_ai.reading import read as reader
	from onedesk.one_ai.reading import vision

	try:
		said = reader.read(name, content)
		if said.needs == "eyes":
			said.text = "\n\n".join(vision.see(name, content, reader.extension(name), 2, reference)["pages"])
	except Exception:
		frappe.clear_messages()
		frappe.log_error(title=f"OneAI could not read {name}")
		return {}
	if not (said.text or "").strip():
		return {}
	asked = [{"fieldname": one["fieldname"], "label": one["label"], "fieldtype": one["fieldtype"], **({"options": one["options"]} if one.get("options") else {})} for one in fields]
	wanted = {one["fieldname"] for one in fields}
	return {key: value for key, value in _asked(doctype, asked, already, {"text": said.text}, reference).items() if key in wanted and value not in (None, "")}
