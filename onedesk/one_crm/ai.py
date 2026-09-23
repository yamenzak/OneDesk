"""What OneAI can do in OneCRM.

The tools and suggestions this module adds to the panel, named in `hooks.py`.
The rules are OneAI's: a read runs as the person asking, and anything that
would write is a card somebody approves. What this module adds is what sales
knows — that a deal is an Opportunity, what a deal's history is made of, when
a deal has gone quiet, and when a person is already a lead.

**The model reads the history; the record keeps it.** `deal_facts` and
`lead_facts` hand over the page's own answers (`record.overview`) and the
timeline — mail, calls, comments and stage moves, oldest first — so a summary,
a next step or a follow-up is written from what was said rather than from the
fields. Nothing the model writes becomes history until somebody approves it.

**A call written up is a Call Log**, the same record the Log a Call dialog
makes, so it counts as the last time anybody spoke to them and times the first
reply. A next step is its own card: one card per suggestion, and a person may
want the call and not the step.

**A business card becomes a lead only if the person is not one already.**
`add_lead` runs capture's own match: the same email is refused and said, a
matching phone or business name is written on the card as a possible
duplicate, as the web form would have flagged it.
"""

from typing import Annotated

import frappe
from frappe import _, _lt
from frappe.utils import add_days, cint, flt, get_datetime, getdate, now_datetime, today

from onedesk.one_ai import files, proposals
from onedesk.one_crm import capture, measure, record, stages
from onedesk.one_crm import next as next_step

#: What the panel offers, by doctype or workspace, when it opens on one. The
#: keys are OneHR's; see `one_hr/ai.py`.
SUGGESTIONS = {
	"Opportunity": [
		{
			"label": _lt("Where does this deal stand?"),
			"ask": _lt("Where does this deal stand? Say in a few lines what it is, how far it has got, what "
			"was said last and by whom, and what should happen next."),
			"can": "read",
			"view": "Form",
		},
		{
			"label": _lt("Suggest the next step"),
			"ask": _lt("From this deal's history, suggest its next step and the day to do it by."),
			"can": "write",
			"view": "Form",
			"expects": "plan_next_step",
		},
		{
			"label": _lt("Write up a call"),
			"ask": _lt("I have just spoken to them on the phone. Ask me what was said, then write it up as a "
			"call on this deal and suggest the next step it leads to."),
			"can": "write",
			"view": "Form",
		},
		{
			"label": _lt("Draft a follow-up"),
			"ask": _lt("Draft a short follow-up email to them from this deal's history: what was said last, "
			"what we agreed, and the one thing we are asking for. Plain words, no sales talk."),
			"can": "read",
			"view": "Form",
		},
		{
			"label": _lt("Which deals have gone quiet?"),
			"ask": _lt("Which open deals have gone quiet: nobody has spoken to them for two weeks and nothing "
			"is planned?"),
			"can": "read",
			"view": "List",
		},
		{
			"label": _lt("Why are we losing deals?"),
			"ask": _lt("Why have we lost deals this year?"),
			"can": "read",
			"view": "List",
		},
	],
	"Lead": [
		{
			"label": _lt("Draft a reply"),
			"ask": _lt("Draft a short first reply to this lead that answers what they asked, and proposes one "
			"next step. Plain words, no sales talk."),
			"can": "read",
			"view": "Form",
		},
		{
			"label": _lt("Suggest the next step"),
			"ask": _lt("From this lead's history, suggest its next step and the day to do it by."),
			"can": "write",
			"view": "Form",
			"expects": "plan_next_step",
		},
		{
			"label": _lt("Write up a call"),
			"ask": _lt("I have just spoken to them on the phone. Ask me what was said, then write it up as a "
			"call on this lead and suggest the next step it leads to."),
			"can": "write",
			"view": "Form",
		},
		{
			"label": _lt("Add leads from business cards"),
			"ask": _lt("Add a lead from each of these business cards."),
			"file": True,
			"can": "create",
			"view": "List",
			"expects": "add_lead",
		},
		{
			"label": _lt("Add a lead from a signature"),
			"ask": _lt("I will paste an email signature. Add the person in it as a lead."),
			"can": "create",
			"view": "List",
		},
		{
			"label": _lt("Which leads are waiting on us?"),
			"ask": _lt("Which open leads are waiting on us: nobody has spoken to them for a week and nothing "
			"is planned?"),
			"can": "read",
			"view": "List",
		},
	],
	"workspace:OneCRM": [
		{
			"label": _lt("Which deals have gone quiet?"),
			"ask": _lt("Which open deals have gone quiet: nobody has spoken to them for two weeks and nothing "
			"is planned?"),
			"doctype": "Opportunity",
			"can": "read",
		},
		{
			"label": _lt("Why are we losing deals?"),
			"ask": _lt("Why have we lost deals this year?"),
			"doctype": "Opportunity",
			"can": "read",
		},
		{
			"label": _lt("Add leads from business cards"),
			"ask": _lt("Add a lead from each of these business cards."),
			"file": True,
			"doctype": "Lead",
			"can": "create",
			"expects": "add_lead",
		},
	],
}

#: What each record type is called when talking to a person.
CALLED = {"Lead": "lead", "Opportunity": "deal"}

#: The most history handed over for one record, newest kept.
MOST_EVENTS = 40

#: How much of one mail, call or comment is handed over.
MOST_WORDS = 600

#: The most open records looked through for "gone quiet".
MOST_OPEN = 300


def workspace() -> str:
	"""For the `one_ai_workspace` hook: what a deal is here, and the stages in
	order, because the person says "deal" and "Proposal" and the records say
	Opportunity and a Sales Stage."""
	names = [
		f"{one.name} ({cint(one.one_probability)}%)"
		for one in stages.stages()
		if (one.one_outcome or "Open") == "Open" and one.one_position
	]
	said = "What people here call a deal is an Opportunity record, and a lead is a Lead."
	if names:
		said += " The open sales stages, in order, are " + ", ".join(names) + "."
	return said


# ----------------------------------------------------------------- reading


def deal_facts(deal: Annotated[str, "The deal's id, such as CRM-OPP-2026-00001."]) -> dict:
	"""Everything about one deal a person would read before deciding what to do:
	what it is worth, its stage and for how long, its next step, the last time
	anybody spoke to them, its quotation, and its history — mail, calls,
	comments and stage moves, oldest first."""
	return _facts("Opportunity", deal)


def lead_facts(lead: Annotated[str, "The lead's id, such as CRM-LEAD-2026-00001."]) -> dict:
	"""Everything about one lead a person would read before deciding what to do:
	who they are, what they asked, where they came from, how long they have
	waited, its next step, and its history — mail, calls and comments, oldest
	first."""
	return _facts("Lead", lead)


def _facts(doctype: str, name: str) -> dict:
	if not frappe.db.exists(doctype, name):
		return {"error": f"There is no {CALLED[doctype]} {name!r}."}
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	said = {
		"id": doc.name,
		"called": doc.get("title") or doc.name,
		"status": doc.status,
		"owner": doc.get(next_step.OWNER[doctype]),
		"page": record.overview(doctype, name),
		"history": history(doctype, name),
	}
	if doctype == "Opportunity":
		said.update(
			party={"type": doc.opportunity_from, "name": doc.party_name, "contact": doc.contact_person},
			items=[{"item": row.item_name or row.item_code, "qty": row.qty, "amount": row.amount} for row in doc.items],
			lost=[row.lost_reason for row in doc.lost_reasons] or None,
		)
	else:
		said.update(
			person=doc.lead_name,
			business=doc.company_name,
			job_title=doc.job_title,
			email=doc.email_id,
			phone=doc.mobile_no or doc.phone,
			asked=_plain(doc.get("one_message")),
			duplicate_of=doc.get("one_duplicate_of"),
		)
	return said


def history(doctype: str, name: str) -> list[dict]:
	"""Mail, calls, comments and stage moves on one record, oldest first, the
	newest MOST_EVENTS of them. What the record's own timeline shows to anybody
	who may read the record, which the caller has checked."""
	events = []
	for one in frappe.get_all(
		"Communication",
		filters={"reference_doctype": doctype, "reference_name": name, "communication_type": "Communication"},
		fields=["communication_date", "sent_or_received", "sender", "subject", "content"],
		order_by="communication_date desc",
		limit_page_length=MOST_EVENTS,
	):
		events.append(
			{
				"at": one.communication_date,
				"what": "Email sent" if one.sent_or_received == "Sent" else "Email received",
				"who": one.sender,
				"said": _plain(f"{one.subject or ''}: {one.content or ''}"),
			}
		)
	for one in frappe.get_all(
		"Comment",
		filters={"reference_doctype": doctype, "reference_name": name, "comment_type": "Comment"},
		fields=["creation", "comment_email", "content"],
		order_by="creation desc",
		limit_page_length=MOST_EVENTS,
	):
		events.append({"at": one.creation, "what": "Comment", "who": one.comment_email, "said": _plain(one.content)})
	calls = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Call Log", "link_doctype": doctype, "link_name": name},
		pluck="parent",
	)
	for one in frappe.get_all(
		"Call Log",
		filters={"name": ["in", calls or [""]]},
		fields=["start_time", "type", "status", "duration", "summary", "employee_user_id"],
		order_by="start_time desc",
		limit_page_length=MOST_EVENTS,
	):
		events.append(
			{
				"at": one.start_time,
				"what": f"{one.type} call, {one.status}, {cint(one.duration) // 60} min",
				"who": one.employee_user_id,
				"said": _plain(one.summary),
			}
		)
	if doctype == "Opportunity":
		for one in frappe.get_all(
			"Milestone",
			filters={"reference_type": doctype, "reference_name": name, "track_field": "sales_stage"},
			fields=["creation", "value", "owner"],
			order_by="creation desc",
			limit_page_length=MOST_EVENTS,
		):
			events.append({"at": one.creation, "what": f"Moved to {one.value}", "who": one.owner})
	events.sort(key=lambda one: get_datetime(one["at"]))
	return events[-MOST_EVENTS:]


def _plain(html) -> str:
	said = " ".join(frappe.utils.strip_html_tags(str(html or "")).split())
	return said if len(said) <= MOST_WORDS else said[: MOST_WORDS - 1].rsplit(" ", 1)[0] + "…"


def gone_quiet(
	record_type: Annotated[str, "Opportunity for deals, Lead for leads."] = "Opportunity",
	days: Annotated[int, "How long without a word counts as quiet. Two weeks for deals, one for leads."] | None = None,
) -> dict:
	"""The open deals or leads nobody has spoken to for a while and that have
	nothing planned: no next step, or one whose day has passed. Only the ones
	the person asking may see."""
	if record_type not in next_step.OPEN:
		return {"error": "Ask about Opportunity (deals) or Lead (leads)."}
	days = cint(days) or (14 if record_type == "Opportunity" else 7)
	owner = next_step.OWNER[record_type]
	fields = ["name", "title", "status", owner, "one_next_step", "one_next_on", "creation"]
	if record_type == "Opportunity":
		fields += ["sales_stage", "opportunity_amount", "currency"]
	now = now_datetime()
	found = []
	for one in frappe.get_list(
		record_type,
		filters={"status": ["in", next_step.OPEN[record_type]]},
		fields=fields,
		order_by="creation asc",
		limit_page_length=MOST_OPEN,
	):
		last = record.last_contact(record_type, one.name)
		spoke = last["at"] if last else None
		if not quiet(spoke or one.creation, one.one_next_on, now, days):
			continue
		row = {
			"id": one.name,
			"called": one.title,
			"owner": one.get(owner),
			"last_spoken": str(spoke) if spoke else None,
			"next_step": one.one_next_step,
			"next_on": str(one.one_next_on) if one.one_next_on else None,
		}
		if record_type == "Opportunity":
			row.update(stage=one.sales_stage, value=flt(one.opportunity_amount), currency=one.currency)
		found.append(row)
	return {
		"days": days,
		"quiet": found,
		"next": "Answer as a short list, the most valuable or the longest quiet first: each line the "
		"record, how long since anybody spoke to them, and whose it is. Say plainly if there are none.",
	}


def quiet(spoke, next_on, now, days: int) -> bool:
	"""Whether a record has gone quiet: nobody has spoken to them for `days`
	days (counting from when it came in if nobody ever has) and nothing is
	planned — no next step, or one whose time has passed. Pure."""
	if next_on and get_datetime(next_on) >= now:
		return False
	return get_datetime(spoke) <= add_days(now, -days)


def why_we_lose(
	from_date: Annotated[str, "The first day of the period, as YYYY-MM-DD. A year ago if not said."] | None = None,
	to_date: Annotated[str, "The last day, as YYYY-MM-DD. Today if not said."] | None = None,
) -> dict:
	"""Every deal lost over a period, with the reasons picked and what was
	written about it, what it was worth, where it came from, the competitor if
	one was named, and how many were won over the same days. Read it to answer
	why deals are lost — then group what was said into the few reasons behind
	it."""
	end = getdate(to_date) if to_date else getdate(today())
	start = getdate(from_date) if from_date else add_days(end, -365)
	shut = {name: one for name, one in measure.closed().items() if start <= one.on <= end}
	seen = {
		one.name: one
		for one in measure.deals({"name": ["in", list(shut) or [""]]}, fields=("title", "order_lost_reason"))
	}
	lost = [name for name, one in shut.items() if one.outcome == "Lost" and name in seen]
	reasons = _rows("Opportunity Lost Reason Detail", "lost_reason", lost)
	rivals = _rows("Competitor Detail", "competitor", lost)
	said = [
		{
			"deal": seen[name].title or name,
			"lost_on": str(shut[name].on),
			"value": measure.value(seen[name]),
			"source": seen[name].utm_source,
			"stage_before": stages.last_open(name),
			"reasons": reasons.get(name, []),
			"competitors": rivals.get(name, []),
			"written": _plain(seen[name].order_lost_reason) or None,
		}
		for name in lost
	]
	return {
		"period": {"from": str(start), "to": str(end)},
		"won": sum(1 for name, one in shut.items() if one.outcome == "Won" and name in seen),
		"lost": len(said),
		"deals": said,
		"next": "Answer as a short list, one line per reason, most common first: the reason, how many "
		"deals and what they were worth, and a few words from what was written. Keep separate reasons "
		"separate, and say so if a stage or a source keeps coming up. Say plainly if there are too few "
		"to call anything a pattern.",
	}


def _rows(doctype: str, field: str, deals: list[str]) -> dict[str, list[str]]:
	held = {}
	for row in frappe.get_all(
		doctype,
		filters={"parenttype": "Opportunity", "parent": ["in", deals or [""]]},
		fields=["parent", field],
		order_by="idx asc",
	):
		held.setdefault(row.parent, []).append(row[field])
	return held


# -------------------------------------------------------------- suggesting


def add_lead(
	person: Annotated[str, "The person's full name, as printed."],
	email: Annotated[str, "Their email address, as printed."] | None = None,
	business: Annotated[str, "The business they work for, as printed."] | None = None,
	job_title: Annotated[str, "Their job title, as printed."] | None = None,
	mobile: Annotated[str, "Their mobile number, as printed."] | None = None,
	phone: Annotated[str, "Their office number, as printed."] | None = None,
	website: Annotated[str, "Their website, as printed."] | None = None,
	city: Annotated[str, "The city in their address."] | None = None,
	card_file: Annotated[str, "The file name of the business card this person is from."] | None = None,
) -> dict:
	"""Suggest a lead from a business card or an email signature. Call it once
	per person. Copy what is printed; leave out what is not.

	Nothing is added until somebody approves the card; the business card goes
	on the lead when they do.
	"""
	address = (email or "").strip().lower()
	if address and not frappe.utils.validate_email_address(address):
		return {"error": f"{email!r} is not an email address. Read it again, or leave it out."}
	if not (person or "").strip():
		return {"error": "A lead needs the person's name."}
	values = {
		"lead_name": person.strip(),
		"email_id": address,
		"company_name": (business or "").strip(),
		"job_title": (job_title or "").strip(),
		"mobile_no": (mobile or "").strip(),
		"phone": (phone or "").strip(),
		"website": (website or "").strip(),
		"city": (city or "").strip(),
		"lead_owner": frappe.session.user,
	}
	same = capture.matches(frappe._dict(values))
	already = next((one for one in same if one["on"] == "email" and one["doctype"] == "Lead"), None)
	if already:
		return {
			"error": f"{person} ({address}) is already a lead: {already['name']}. "
			"Say so rather than adding them twice."
		}
	why = None
	if same:
		kind, other, by = same[0]["doctype"], same[0]["name"], same[0]["on"]
		values.update(one_duplicate_type=kind, one_duplicate_of=other, one_duplicate_on=by)
		why = _("Maybe the same as {0} {1}, by {2}.").format(_(kind), other, _(by))
	held = files.uploaded(card_file, person)
	card = proposals.propose(
		"Create",
		"Lead",
		changes={key: value for key, value in values.items() if value},
		why=why,
		files=[held] if held else [],
	)
	return {"proposal": card, "state": "Proposed"}


def plan_next_step(
	record_type: Annotated[str, "Opportunity for a deal, Lead for a lead."],
	name: Annotated[str, "Its id."],
	step: Annotated[str, "What is to be done, as a short line starting with a verb, such as 'Call to agree the price'."],
	on: Annotated[str, "When, as YYYY-MM-DD, or YYYY-MM-DD HH:MM if a time was said."],
) -> dict:
	"""Suggest the next step on a deal or a lead: what is to be done, and by
	when. Read its history first, so the step follows from what was said."""
	if record_type not in next_step.OPEN:
		return {"error": "Only a deal (Opportunity) or a lead (Lead) has a next step."}
	try:
		when = get_datetime(on)
	except Exception:
		return {"error": f"{on!r} is not a date. Give it as YYYY-MM-DD."}
	if not when or when.date() < getdate(today()):
		return {"error": f"{on} has passed. Suggest a day from today on."}
	if len(on.strip()) <= 10:
		# A day with no time said is a day, not midnight: the morning of it.
		when = when.replace(hour=9, minute=0)
	status = frappe.db.get_value(record_type, name, "status")
	if status is None:
		return {"error": f"There is no {CALLED[record_type]} {name!r}."}
	if status not in next_step.OPEN[record_type]:
		return {"error": f"This {CALLED[record_type]} is {status}, so it has no next step."}
	card = proposals.propose(
		"Edit",
		record_type,
		record=name,
		changes={"one_next_step": step.strip()[:140], "one_next_on": str(when.replace(microsecond=0))},
	)
	return {"proposal": card, "state": "Proposed"}


def write_up_call(
	record_type: Annotated[str, "Opportunity for a deal, Lead for a lead."],
	name: Annotated[str, "Its id."],
	summary: Annotated[
		str,
		"What was said, in a few short lines: what they want, what was agreed, and anything promised by "
		"either side. The person's words, tidied; nothing they did not say.",
	],
	direction: Annotated[str, "Outgoing if we called them, Incoming if they called."] = "Outgoing",
	outcome: Annotated[str, "Answered, No Answer or Busy."] = "Answered",
	minutes: Annotated[int, "How long it lasted, if said."] | None = None,
) -> dict:
	"""Suggest a call on a deal or a lead, written up from what the person said
	about it. It lands on the history beside the mail, as a call logged by hand
	would. Suggest the next step it leads to separately, with plan_next_step."""
	if record_type not in next_step.OPEN:
		return {"error": "Only a deal (Opportunity) or a lead (Lead) has calls."}
	if direction not in ("Outgoing", "Incoming") or outcome not in record.OUTCOME:
		return {"error": "direction is Outgoing or Incoming; outcome is Answered, No Answer or Busy."}
	if not frappe.db.exists(record_type, name):
		return {"error": f"There is no {CALLED[record_type]} {name!r}."}
	doc = frappe.get_doc(record_type, name)
	doc.check_permission("write")
	call = record.call(doc, direction, outcome, minutes, summary)
	call.pop("doctype")
	# A card holds plain values; the times are written as the database would.
	call.update(start_time=str(call["start_time"].replace(microsecond=0)), end_time=str(call["end_time"].replace(microsecond=0)))
	return {"proposal": proposals.propose("Create", "Call Log", changes=call), "state": "Proposed"}
