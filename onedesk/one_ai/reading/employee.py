"""OneAI as an employee: after the planners, OneAI looks things up as
the person it reads for and acts through the one door, with five tools.
Each act is marked, undoable, checked against that person's permissions,
and waits in the inbox below the workspace's floor. README, employee.py.
"""

import json
from typing import Annotated

import frappe
from frappe.utils import cint, getdate, strip_html_tags

from onedesk.one_ai.reading import act, guard

ACTION = "intake_act"

#: What the model may read with: the chat's own, as the person.
LOOKS = (
	"find_by_meaning",
	"search_everywhere",
	"find_records",
	"list_records",
	"read_record",
	"about_record",
	"describe_type",
	"count_records",
	"find_documents",
)

SURE = Annotated[int, "How sure you are, 0 to 100. Below the workspace's floor it waits for a person instead."]

LINES, ASKS = 20, 10


def think(name: str) -> None:
	"""The agent's pass over one understood reading, after the planners."""
	from onedesk.one import account, apps
	from onedesk.one_ai import run

	reading = frappe.get_doc("Reading", name)
	if not _worth(reading) or not apps.intake_on() or not account.configured():
		return
	asked = told(reading)
	if guard.holds(reading, asked):
		return
	was = frappe.session.user
	frappe.flags.one_intake_reading = reading.name
	frappe.flags.one_ai_tools = {fn.__name__: fn for fn in HANDS}
	frappe.set_user(reading.on_behalf_of)
	try:
		run.ask(
			ACTION,
			asked,
			reference=reading.name,
			only=[*LOOKS, *(fn.__name__ for fn in HANDS)],
			nudges=False,
		)
	finally:
		frappe.set_user(was)
		frappe.flags.one_ai_tools = None
		frappe.flags.one_intake_reading = None


def _worth(reading) -> bool:
	"""Real, current, ordinary, and read for somebody: history, a copy and a
	personal document are left to the planners."""
	return (
		reading.state == "Understood"
		and reading.on_behalf_of
		and not cint(reading.history)
		and reading.verdict in ("Action", "Information")
		and reading.sensitivity in (None, "", "Ordinary")
		and not reading.copy_of
	)


def told(reading) -> str:
	"""The reading as the model is shown it, and what was already done."""
	structured = json.loads(reading.structured or "{}")
	mail = structured.get("mail") or {}
	said = {
		"document": {
			"title": reading.title,
			"kind": reading.kind,
			"summary": reading.summary,
			"number": reading.number,
			"issued_on": str(reading.issued_on or "") or None,
			"amount": reading.gross,
			"currency": reading.currency,
			"language": reading.language,
		},
		"came_as": {key: mail.get(key) for key in ("from_name", "from_email", "to", "cc", "subject", "date", "direction") if mail.get(key)}
		or {"file": reading.source_name},
		"parties": [
			{
				"role": one.role,
				"name": one.party_name,
				"person": bool(one.is_person),
				"job_title": one.job_title,
				"email": one.email,
				"phone": one.phone,
				"is": f"{one.matched_doctype} {one.matched_name}" if one.matched_name else None,
			}
			for one in reading.parties
			if not one.ours
		],
		"references": [{"kind": one.kind, "value": one.value} for one in reading.get("refs") or []],
		"asks": [{"what": one.what, "detail": one.detail, "by": str(one.by_date or "") or None} for one in reading.asks[:ASKS]],
		"lines": [{"text": one.text, "qty": one.qty, "amount": one.amount} for one in reading.lines[:LINES]],
		"text": strip_html_tags(reading.text or "")[:6000],
		"already_done": [
			f"{one.level}: {one.kind} {one.target_doctype} {one.target_name or ''}".strip()
			for one in frappe.get_all(
				"Reading Action",
				filters={"reading": reading.name},
				fields=["kind", "target_doctype", "target_name", "level"],
				order_by="creation asc",
			)
		],
		"today": str(getdate()),
	}
	return json.dumps(said, ensure_ascii=False, default=str)


def _reading():
	name = frappe.flags.one_intake_reading
	if not name:
		frappe.throw("This tool only works while OneAI reads a document.")
	return frappe.get_doc("Reading", name)


def _done(action: act.Action) -> dict:
	"""Hand an action to the door, and say what happened to it."""
	reading = _reading()
	action.key = f"{reading.key[:80]}|agent|{action.kind}|{action.doctype}|{action.name or ''}|{_digest(action.values)}"
	made = act.apply(action, reading)
	row = frappe.db.get_value("Reading Action", made, ["level", "target_name", "why"], as_dict=True) if made else None
	if not row:
		return {"state": "Not done", "why": "There is nobody this document is read for."}
	return {
		"state": {"Done": "Done", "Proposed": "Waiting for a person", "Refused": "Refused"}.get(row.level, row.level),
		"record": row.target_name,
		**({"why": row.why} if row.why else {}),
	}


def _digest(values: dict) -> str:
	import hashlib

	return hashlib.md5(json.dumps(values or {}, sort_keys=True, default=str).encode()).hexdigest()[:10]


def link_to(
	doctype: Annotated[str, "The type of record the document or message is about, such as Purchase Order or Project."],
	name: Annotated[str, "Its id, as a lookup answered it."],
	sure: SURE,
	why: Annotated[str, "One sentence: what in the document says it is about this record."],
) -> dict:
	"""File the document and its message with a record it is about: the order
	it confirms, the project it reports on, the invoice it chases. It then
	shows on that record's timeline. Use it for every record it is plainly
	about, not only its sender."""
	if not frappe.db.exists(doctype, name):
		frappe.throw(f"There is no {doctype} {name}. Look it up with find_records or find_by_meaning first.")
	carrier = _carrier(_reading())
	if not carrier:
		frappe.throw("This document has no message or file to file with a record.")
	return _done(act.Action("Link", doctype, name, carrier, why=why, confidence=sure / 100))


def _carrier(reading) -> dict | None:
	from onedesk.one_ai.reading import planning

	return planning.carrier(reading)


def make_record(
	doctype: Annotated[str, "The type of record to make."],
	values: Annotated[dict, "Field name to value. Read describe_type first for a type you have not made before."],
	sure: SURE,
	why: Annotated[str, "One sentence: what in the document asks for it."],
) -> dict:
	"""Make a record the document calls for that nobody has made yet: an
	opportunity from a request for a quote, an address or a bank account a
	supplier sent, an issue a customer reported. It is marked as made by
	OneAI and can be undone. Never make what already_done shows."""
	return _done(act.Action("Create", doctype, values=values or {}, why=why, confidence=sure / 100))


def fill_in(
	doctype: Annotated[str, "The type of record."],
	name: Annotated[str, "Its id."],
	values: Annotated[dict, "Field name to the new value: only fields the document says something new about."],
	sure: SURE,
	why: Annotated[str, "One sentence: what in the document says it."],
) -> dict:
	"""Enrich an existing record with what the document says: a phone,
	an address, a tax number, a delivery date an order confirmation gives. An
	empty field is filled; one a person filled waits for them to decide."""
	return _done(act.Action("Update", doctype, name, values=values or {}, why=why, confidence=sure / 100))


def add_comment(
	doctype: Annotated[str, "The type of record."],
	name: Annotated[str, "Its id."],
	text: Annotated[str, "What arrived and what it means for this record, in two sentences at most."],
) -> dict:
	"""Leave a note on a record about what just arrived: "The supplier moved
	delivery to 14 November." Use it when the news matters to people working
	on the record but changes none of its fields."""
	return _done(act.Action("Comment", doctype, name, values={"content": text}, why=text))


def make_task(
	subject: Annotated[str, "What has to be done, as a short instruction."],
	assign_to: Annotated[str, "The user who should do it: the record's owner, its account manager or the person who_handles names."],
	about_doctype: Annotated[str, "The type of record it is about."] | None = None,
	about_name: Annotated[str, "Its id."] | None = None,
	due: Annotated[str, "YYYY-MM-DD, when the document gives a date."] | None = None,
	sure: SURE = 80,
	why: Annotated[str, "One sentence: what in the document asks for it."] | None = None,
) -> dict:
	"""Give somebody a task the document calls for that the planners did not:
	reply to a complaint, approve a change, send a missing document. One task
	per thing to do; never one already_done shows."""
	values = {
		"subject": subject[:140],
		"description": why,
		"exp_end_date": due,
		"assign_to": assign_to,
		"one_about_doctype": about_doctype,
		"one_about": about_name,
	}
	return _done(
		act.Action(
			"Create",
			"Task",
			values={key: value for key, value in values.items() if value},
			why=why or subject,
			confidence=sure / 100,
			flow="onedesk.one_ai.reading.planning.make_task",
		)
	)


def who_handles(
	doctype: Annotated[str, "The type of record."],
	name: Annotated[str, "Its id."],
) -> dict:
	"""Who looks after a record: whoever it is assigned to, its owner, its
	account or project manager. Ask before giving a task about it."""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	said = {
		"assigned_to": json.loads(doc.get("_assign") or "[]"),
		"made_by": doc.owner,
	}
	for field in ("account_manager", "project_manager", "lead_owner", "opportunity_owner", "user_id", "leave_approver", "expense_approver"):
		if doc.meta.has_field(field) and doc.get(field):
			said[field] = doc.get(field)
	if doctype == "Project":
		said["team"] = frappe.get_all("Project User", filters={"parent": name, "parenttype": "Project"}, pluck="user")
	return said


HANDS = (link_to, make_record, fill_in, add_comment, make_task, who_handles)
