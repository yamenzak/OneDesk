"""What a lead's or a deal's page answers before anybody clicks anything.

A deal is opened to find out what it is worth, how far it has got and for how
long, what happens next, when anybody last spoke to them, and when it should
close. A lead is opened for how long it has waited, where it came from, what
happens next and what it has turned into. Each answer carries where it came
from so the page still links to it.

A call is written down by hand as a Call Log, erpnext's own record of a call,
linked to the lead or deal, so it is on the timeline beside the mail and the
comments, and a later telephony integration writes the same record.
"""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, flt, get_datetime, now_datetime

from onedesk.one_crm import measure
from onedesk.one_crm import next as next_step

#: A call's outcome in the dialog's words, and Call Log's own status for it.
OUTCOME = {"Answered": "Completed", "No Answer": "No Answer", "Busy": "Busy"}


@frappe.whitelist()
@frappe.read_only()
def overview(doctype: Annotated[str, "Lead or Opportunity."], name: str) -> dict:
	if doctype not in next_step.OPEN:
		frappe.throw(_("Only a lead or a deal has an overview."))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	said = {
		"open": doc.status in next_step.OPEN[doctype],
		"next": {"step": doc.one_next_step, "on": doc.one_next_on},
		"contact": last_contact(doctype, name),
		"source": doc.get("utm_source"),
	}
	if doctype == "Opportunity":
		said.update(
			value=flt(doc.opportunity_amount),
			currency=doc.currency,
			probability=flt(doc.probability),
			stage=doc.sales_stage,
			since=stage_since(doc),
			**_usual(doc),
			closing=doc.expected_closing,
			quotation=quotation(name),
		)
	else:
		said.update(
			since=doc.creation,
			deals=deals(name),
			first_reply=doc.one_first_reply_at,
		)
	return said


def _usual(doc) -> dict:
	"""How long deals usually stay in this deal's stage, and whether this one
	has stayed longer. Nothing for a deal that is closed."""
	if doc.status not in next_step.OPEN["Opportunity"]:
		return {"usual": None, "long": False}
	usual = measure.usual_for(doc.sales_stage)
	length = (now_datetime() - get_datetime(stage_since(doc))).total_seconds() / 86400
	return {"usual": usual, "long": measure.stuck(length, usual)}


def stage_since(doc):
	"""When a deal reached the stage it is in: the Milestone that recorded it."""
	reached = frappe.get_all(
		"Milestone",
		filters={
			"reference_type": "Opportunity",
			"reference_name": doc.name,
			"track_field": "sales_stage",
			"value": doc.sales_stage,
		},
		fields=["creation"],
		order_by="creation desc",
		limit=1,
	)
	return reached[0].creation if reached else doc.creation


def last_contact(doctype: str, name: str) -> dict | None:
	"""The latest mail or call with them, whichever is later."""
	mail = frappe.get_all(
		"Communication",
		filters={
			"reference_doctype": doctype,
			"reference_name": name,
			"communication_type": "Communication",
		},
		fields=["name", "communication_date", "sent_or_received"],
		order_by="communication_date desc",
		limit=1,
	)
	calls = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Call Log", "link_doctype": doctype, "link_name": name},
		pluck="parent",
	)
	call = (
		frappe.get_all(
			"Call Log",
			filters={"name": ["in", calls]},
			fields=["name", "start_time", "type", "status"],
			order_by="start_time desc",
			limit=1,
		)
		if calls
		else []
	)
	found = []
	if mail:
		found.append(
			{
				"kind": "Email",
				"at": mail[0].communication_date,
				"doctype": "Communication",
				"name": mail[0].name,
				"way": mail[0].sent_or_received,
			}
		)
	if call:
		found.append(
			{"kind": "Call", "at": call[0].start_time, "doctype": "Call Log", "name": call[0].name, "way": call[0].type}
		)
	return max(found, key=lambda one: one["at"]) if found else None


def quotation(opportunity: str) -> dict | None:
	rows = frappe.get_all(
		"Quotation",
		filters={"opportunity": opportunity, "docstatus": ["<", 2]},
		fields=["name", "status", "grand_total", "currency"],
		order_by="creation desc",
		limit=1,
	)
	return rows[0] if rows else None


def deals(lead: str) -> dict:
	rows = frappe.get_all(
		"Opportunity",
		filters={"opportunity_from": "Lead", "party_name": lead},
		fields=["opportunity_amount", "status"],
	)
	return {
		"count": len(rows),
		"open": sum(1 for row in rows if row.status in next_step.OPEN["Opportunity"]),
		"value": sum(flt(row.opportunity_amount) for row in rows),
	}


@frappe.whitelist(methods=["POST"])
def log_call(
	doctype: Annotated[str, "Lead or Opportunity."],
	name: str,
	direction: Annotated[str, "Outgoing or Incoming."],
	outcome: Annotated[str, "Answered, No Answer or Busy."],
	minutes: int | None = 0,
	summary: str | None = None,
) -> str:
	"""A call written down by hand, as a Call Log on the lead or deal."""
	if doctype not in next_step.OPEN:
		frappe.throw(_("Only a lead or a deal has calls."))
	if direction not in ("Outgoing", "Incoming") or outcome not in OUTCOME:
		frappe.throw(_("A call is Outgoing or Incoming, and Answered, No Answer or Busy."))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	log = frappe.get_doc(call(doc, direction, outcome, minutes, summary))
	# Written by hand, so no telephony popup is owed to anybody.
	log.trigger_call_popup = lambda: None
	log.insert(ignore_permissions=True)
	return log.name


def call(doc, direction: str, outcome: str, minutes=0, summary: str | None = None) -> dict:
	"""A Call Log with them that has just ended, as a dict. The dialog inserts
	it, and OneAI puts it on a card."""
	theirs = phone(doc)
	ended = now_datetime()
	seconds = cint(minutes) * 60 if outcome == "Answered" else 0
	return {
		"doctype": "Call Log",
		"id": frappe.generate_hash(length=12),
		"type": direction,
		"status": OUTCOME[outcome],
		"from": frappe.session.user if direction == "Outgoing" else theirs,
		"to": theirs if direction == "Outgoing" else frappe.session.user,
		"medium": _("Logged by hand"),
		"duration": seconds,
		"start_time": add_to_date(ended, seconds=-seconds),
		"end_time": ended,
		"summary": (summary or "").strip() or None,
		"employee_user_id": frappe.session.user,
		"links": [{"link_doctype": doc.doctype, "link_name": doc.name}],
	}


def phone(doc) -> str:
	for field in ("mobile_no", "phone", "contact_mobile", "contact_phone"):
		if doc.get(field):
			return doc.get(field)
	return doc.get("title") or doc.name


def settle() -> None:
	"""A CRM Note becomes a comment on the timeline, where the rest of what was
	said about a lead or deal already is. The notes tab is hidden, so the rows
	are moved rather than left where nobody sees them."""
	for row in frappe.get_all(
		"CRM Note",
		filters={"parenttype": ["in", list(next_step.OPEN)]},
		fields=["name", "parent", "parenttype", "note", "added_by", "added_on"],
	):
		if (row.note or "").strip():
			comment = frappe.get_doc(
				{
					"doctype": "Comment",
					"comment_type": "Comment",
					"reference_doctype": row.parenttype,
					"reference_name": row.parent,
					"content": row.note,
					"comment_email": row.added_by,
				}
			).insert(ignore_permissions=True)
			if row.added_by:
				comment.db_set({"owner": row.added_by, "creation": row.added_on or comment.creation})
		frappe.db.delete("CRM Note", {"name": row.name})
