"""Intake as an inbox: what OneAI did, and what waits for you (docs/INTAKE.md §4).

**Intake** in the rail, under the bell and the clock, opens two boxes that
work like a mailbox, one line per document:

- **Done**: documents OneAI acted on and nothing waits for. Open one to read
  what it made and changed, field by field, and undo any of it.
- **Waiting**: documents with something a person has to decide — a proposal
  the auditor was unsure of or could not apply, or something done that the
  auditor thinks is wrong. Apply, dismiss, undo or keep.

What a person has opened is remembered per person with Frappe's own
`track_seen`, so a document is unread for you until you open it, whoever else
has, and is unread again when OneAI does something new with it. The rail
shows how many wait for you.

You see the documents read for you. An administrator of the workspace may
also look at everybody's, except what is medical, about pay or personal.
"""

from typing import Annotated

import frappe
from frappe import _

#: What only the person it was read for sees, administrators included.
PRIVATE = ("Medical", "Pay", "Personal")

#: A page of one box.
PAGE = 40

WAITS = "(a.level = 'Proposed' or (a.level = 'Done' and a.audit = 'Wrong'))"


def _scope(everyone: bool) -> tuple[str, dict]:
	from onedesk.one.roles import administers

	me = frappe.session.user
	if everyone and administers():
		return "(r.on_behalf_of = %(me)s or ifnull(r.sensitivity, '') not in %(private)s)", {"me": me, "private": PRIVATE}
	return "r.on_behalf_of = %(me)s", {"me": me}


def _box(box: str) -> str:
	"""Which documents a box holds. A document is in one box only."""
	waiting = f"exists (select 1 from `tabIntake Action` a where a.reading = r.name and {WAITS})"
	if box == "waiting":
		return waiting
	return f"exists (select 1 from `tabIntake Action` a where a.reading = r.name and a.level = 'Done') and not {waiting}"


@frappe.whitelist()
@frappe.read_only()
def listing(
	box: Annotated[str, "done or waiting"] = "waiting",
	everyone: Annotated[int, "An administrator's view of everybody's documents."] = 0,
	start: Annotated[int, "Where the page starts."] = 0,
) -> dict:
	"""One page of a box, newest first."""
	scope, values = _scope(bool(int(everyone)))
	rows = frappe.db.sql(
		f"""select r.name, r.title, r.kind, r.summary, r.on_behalf_of, r._seen, r.verdict,
			(select max(a.modified) from `tabIntake Action` a where a.reading = r.name) as happened,
			(select count(*) from `tabIntake Action` a where a.reading = r.name and a.level = 'Done') as done,
			(select count(*) from `tabIntake Action` a where a.reading = r.name and {WAITS}) as waiting
		from `tabReading` r
		where {scope} and {_box(box)}
		order by happened desc limit %(most)s offset %(start)s""",
		{**values, "most": PAGE + 1, "start": int(start)},
		as_dict=True,
	)
	me = frappe.session.user
	items = [
		{
			"name": row.name,
			"title": row.title or _(row.kind or "Document"),
			"kind": _(row.kind) if row.kind else None,
			"summary": row.summary,
			"when": row.happened,
			"done": row.done,
			"waiting": row.waiting,
			"unread": me not in frappe.parse_json(row._seen or "[]"),
			"person": frappe.utils.get_fullname(row.on_behalf_of) if row.on_behalf_of != me else None,
		}
		for row in rows[:PAGE]
	]
	return {"items": items, "more": len(rows) > PAGE}


@frappe.whitelist()
@frappe.read_only()
def counts() -> dict:
	"""For the rail: how many documents wait for you, and how many in either
	box you have not opened."""
	scope, values = _scope(False)
	like = f'%"{frappe.session.user}"%'
	waiting, unread = frappe.db.sql(
		f"""select
			sum({_box("waiting")}),
			sum(ifnull(r._seen, '') not like %(like)s and exists (select 1 from `tabIntake Action` a where a.reading = r.name and a.level in ('Done', 'Proposed')))
		from `tabReading` r where {scope}""",
		{**values, "like": like},
	)[0]
	return {"waiting": int(waiting or 0), "unread": int(unread or 0)}


@frappe.whitelist()
def item(name: Annotated[str, "The Reading."]) -> dict:
	"""One document as the reading pane draws it, marked as seen by you."""
	from onedesk.one_intake import panel

	doc = _readable(name)
	said = panel.described(name)
	said["route"] = _route(doc)
	said["person"] = frappe.utils.get_fullname(doc.on_behalf_of) if doc.on_behalf_of != frappe.session.user else None
	doc.add_seen()
	return said


@frappe.whitelist(methods=["POST"])
def keep(action: Annotated[str, "The Intake Action the auditor doubted."]) -> dict:
	"""A person keeps what the auditor thought wrong."""
	from onedesk.one_intake import act

	row = frappe.get_doc("Intake Action", action)
	act._may_decide(row)
	row.db_set("audit", "Kept")
	return {"audit": "Kept"}


@frappe.whitelist(methods=["POST"])
def seen_all(box: Annotated[str, "done or waiting"] = "done") -> int:
	"""Every document in a box marked as seen by you."""
	scope, values = _scope(False)
	names = frappe.db.sql_list(f"select r.name from `tabReading` r where {scope} and {_box(box)}", values)
	for name in names:
		frappe.get_doc("Reading", name).add_seen()
	return len(names)


def _readable(name: str):
	from onedesk.one.roles import administers

	doc = frappe.get_doc("Reading", name)
	mine = doc.on_behalf_of == frappe.session.user
	if not mine and not (administers() and (doc.sensitivity or "") not in PRIVATE):
		frappe.throw(_("That is no longer here."), frappe.DoesNotExistError)
	return doc


def _route(doc) -> str | None:
	"""Where the document itself opens: its file in OneCloud, or its message."""
	if doc.source_doctype == "File" and doc.source_name:
		folder = frappe.db.get_value("File", doc.source_name, "folder")
		return f"/app/onecloud?node={frappe.utils.quote(folder or '')}&file={frappe.utils.quote(doc.source_name)}"
	if doc.source_doctype == "Communication" and doc.source_name:
		thread = frappe.db.get_value("Communication", doc.source_name, "one_thread") or doc.source_name
		return f"/app/onemail?thread={frappe.utils.quote(thread)}"
	return None


# ------------------------------------------------------------------ after OneAI acts


def fresh(name: str) -> None:
	"""OneAI did something new with a document: it is unread again for
	everybody, and the person's rail is told."""
	frappe.db.set_value("Reading", name, "_seen", "[]", update_modified=False)
	person = frappe.db.get_value("Reading", name, "on_behalf_of")
	if person:
		frappe.publish_realtime("intake_inbox", {"reading": name}, user=person, after_commit=True)


def tell(name: str) -> None:
	"""Once the auditor has had its say: if anything still waits for the
	person, one notification saying so, pointing at their Waiting box."""
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	reading = frappe.db.get_value("Reading", name, ["name", "title", "on_behalf_of", "change"], as_dict=True)
	if not reading or not reading.on_behalf_of or reading.change == "Nothing New":
		return
	waiting = frappe.db.sql(f"select count(*) from `tabIntake Action` a where a.reading = %s and {WAITS}", name)[0][0]
	email = frappe.db.get_value("User", reading.on_behalf_of, "email")
	if not waiting or not email:
		return
	subject = (
		_("{0} things OneAI read in {1} need a look.").format(waiting, frappe.bold(reading.title or ""))
		if waiting > 1
		else _("One thing OneAI read in {0} needs a look.").format(frappe.bold(reading.title or ""))
	)
	enqueue_create_notification(
		[email],
		{
			"type": "Alert",
			"document_type": "Reading",
			"document_name": name,
			"subject": subject,
			"from_user": "oneai@one.invalid",
			"link": f"/app/intake?box=waiting&reading={name}",
		},
		dedupe_on=["document_type", "document_name"],
	)
