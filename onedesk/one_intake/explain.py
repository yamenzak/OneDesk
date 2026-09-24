"""Explain this letter, and write the answer to it (docs/INTAKE.md §16.3).

**Explain** in the Intake panel asks OneAI, once, what a document means in
plain words in the reader's own language, what they have to do and by when,
and for a letter, a reply in the letter's own language. For a contract with a
last day to cancel, **Write the cancellation** asks for the cancellation
letter instead, to reach them by that day.

It is the one Intake call a person starts, so it is kept: the same document
explained again in the same language costs nothing, and **Again** asks anew.
Whoever may open the file or the message may ask; nobody else learns it
exists.
"""

import json

import frappe
from frappe import _

from onedesk.one_intake import search

EXPLAIN = "intake_explain"

#: What of a long document the model is shown.
MOST_TEXT = 30_000


def readable(name: str):
	"""The Reading, for somebody who may open what it was read from."""
	doc = frappe.get_doc("Reading", name)
	root = search.root_of(doc.as_dict())
	if not (search.files_of(root) or search.messages_of(root)):
		frappe.throw(_("That is no longer here."), frappe.DoesNotExistError)
	return doc


@frappe.whitelist(methods=["POST"])
def explain(reading: str, cancel: int = 0, again: int = 0) -> dict:
	"""The document explained in the reader's language, what to do, and a
	reply or a cancellation letter in the letter's language."""
	doc = readable(reading)
	language = frappe.local.lang or "en"
	purpose = "cancel" if int(cancel) else "explain"
	held = json.loads(doc.explained or "{}")
	key = f"{purpose}:{language}"
	if held.get(key) and not int(again):
		return held[key]
	said = _ask(doc, language, purpose)
	if not said:
		frappe.throw(_("OneAI could not explain this document just now. Try again in a moment."))
	said = shaped(said)
	held[key] = said
	doc.db_set("explained", json.dumps(held, ensure_ascii=False), update_modified=False)
	return said


def shaped(said: dict) -> dict:
	"""What the model answered, cut to what the panel draws. Pure."""
	todo = [
		{"what": str(one.get("what") or "")[:200], "by": one.get("by") or None}
		for one in (said.get("todo") or [])[:8]
		if isinstance(one, dict) and one.get("what")
	]
	return {
		"explanation": str(said.get("explanation") or "")[:3000],
		"todo": todo,
		"reply": str(said.get("reply") or "")[:6000],
		"reply_language": str(said.get("reply_language") or "")[:8],
	}


def prompt(doc: dict, language: str, purpose: str, cancel_by: str | None) -> str:
	"""What the model is asked. Pure."""
	facts = {
		"kind": doc.get("kind"),
		"summary": doc.get("summary"),
		"issued": str(doc.get("issued_on") or "") or None,
		"number": doc.get("number"),
		"dates": [{"date": str(one.get("date") or ""), "what": one.get("what"), "about": one.get("about"), "rule": one.get("rule")} for one in doc.get("dates") or []],
		"notice": doc.get("notice_period"),
	}
	ask = (
		f"Write the letter cancelling this contract at the earliest date it allows; it must arrive by {cancel_by}."
		if purpose == "cancel" and cancel_by
		else "Write the letter cancelling this contract at the earliest date it allows."
		if purpose == "cancel"
		else "Write a short reply if the document is a letter someone expects an answer to, else leave the reply empty."
	)
	return (
		f"The reader's language: {language}.\n{ask}\n"
		f"What was already read from it: {json.dumps(facts, ensure_ascii=False, default=str)}\n\n"
		f"The document:\n{(doc.get('text') or '')[:MOST_TEXT]}"
	)


def _ask(doc, language: str, purpose: str) -> dict | None:
	from onedesk.one_ai import run
	from onedesk.one_hr.hiring import read

	cancel_by = _cancel_by(doc) if purpose == "cancel" else None
	return read(run.once(EXPLAIN, prompt(doc.as_dict(), language, purpose, cancel_by), reference=doc.name))


def _cancel_by(doc) -> str | None:
	"""The last day to cancel, from the Contract Intake made for this reading."""
	contract = frappe.db.get_value("Intake Action", {"reading": doc.name, "target_doctype": "Contract", "level": "Done"}, "target_name")
	return str(frappe.db.get_value("Contract", contract, "one_cancel_by") or "") or None if contract else None
