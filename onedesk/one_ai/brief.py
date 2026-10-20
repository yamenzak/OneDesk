"""A summary at the top of a customer, supplier, opportunity and project:
marked due by what happens to it, written hourly at most once a day, from
facts gathered here in one call. A field in the head, never a comment.
README, brief.py.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, flt, get_first_day, getdate, now_datetime, nowdate, strip_html

ACTION = "brief"

BRIEF, ON, DUE = "one_ai_brief", "one_ai_brief_on", "one_ai_brief_due"

#: The records that carry one, and what the workspace switch calls them.
BRIEFS = ("Customer", "Supplier", "Opportunity", "Project")

#: The record types turned off, as a system default.
OFF = "one_ai_briefs_off"

#: Characters kept, and how long a summary stands before it may be written again.
MOST = 600
DAY = 1

#: Records written in one hourly run, whatever is due.
AN_HOUR = 40

MAILS, COMMENTS, ITEMS = 5, 5, 5


def on(doctype: str) -> bool:
	"""Whether OneAI writes this record type's summary in this workspace."""
	from onedesk.one import apps

	return doctype in BRIEFS and apps.ai_on() and doctype not in _off()


def _off() -> list[str]:
	try:
		return [one for one in json.loads(frappe.db.get_default(OFF) or "[]") if one in BRIEFS]
	except ValueError:
		return []


@frappe.whitelist(methods=["POST"])
def switch(doctype: str, on: int | str) -> list[str]:
	"""Turn one record type's summaries on or off; the types now off."""
	from onedesk.one import roles

	roles.require()
	if doctype not in BRIEFS:
		frappe.throw(_("{0} has no OneAI summary.").format(doctype))
	off = [one for one in _off() if one != doctype] + ([] if frappe.utils.cint(on) else [doctype])
	frappe.db.set_default(OFF, json.dumps(off))
	return off


def settings() -> list[dict]:
	"""Each record type, whether it is on, and how many carry a summary."""
	return [
		{
			"doctype": doctype,
			"label": _(doctype),
			"on": doctype not in _off(),
			"written": frappe.db.count(doctype, {BRIEF: ["is", "set"]}),
		}
		for doctype in BRIEFS
	]


def _one(field: str):
	return lambda doc: [doc.get(field)]


def _party(kind: str):
	return lambda doc: [doc.party] if doc.get("party_type") == kind else []


def _quoted(doc) -> list:
	return [doc.party_name] if doc.get("quotation_to") == "Customer" else []


def _mailed(kind: str):
	def found(doc) -> list:
		named = [doc.reference_name] if doc.get("reference_doctype") == kind else []
		return named + [one.link_name for one in doc.get("timeline_links") or [] if one.link_doctype == kind]

	return found


def _timed(doc) -> list:
	return [doc.get("parent_project"), *(row.project for row in doc.get("time_logs") or [])]


def _inspected(doc) -> list:
	if doc.get("reference_type") in ("Purchase Receipt", "Purchase Invoice") and doc.get("reference_name"):
		return [frappe.db.get_value(doc.reference_type, doc.reference_name, "supplier")]
	return []


#: What marks a record due: for each kind of record saved, submitted or
#: cancelled, the records it is about and how to find them.
WATCHED = {
	"Sales Invoice": {"Customer": _one("customer"), "Project": _one("project")},
	"Sales Order": {"Customer": _one("customer"), "Project": _one("project")},
	"Delivery Note": {"Customer": _one("customer")},
	"Quotation": {"Customer": _quoted, "Opportunity": _one("opportunity")},
	"Purchase Invoice": {"Supplier": _one("supplier")},
	"Purchase Order": {"Supplier": _one("supplier")},
	"Purchase Receipt": {"Supplier": _one("supplier")},
	"Supplier Quotation": {"Supplier": _one("supplier")},
	"Quality Inspection": {"Supplier": _inspected},
	"Payment Entry": {"Customer": _party("Customer"), "Supplier": _party("Supplier")},
	"Issue": {"Customer": _one("customer")},
	"Task": {"Project": _one("project")},
	"Timesheet": {"Project": _timed},
	"Opportunity": {"Opportunity": _one("name")},
	"Communication": {kind: _mailed(kind) for kind in BRIEFS},
}


def touched(doc, method=None) -> None:
	"""on_update, on_submit and on_cancel of every record: mark what it is
	about due. A draft saved is not news; a submitted one is."""
	about = WATCHED.get(doc.doctype)
	if not about or (method == "on_update" and doc.meta.is_submittable):
		return
	if doc.doctype == "Communication" and doc.get("communication_type") != "Communication":
		return
	for kind, find in about.items():
		if not on(kind):
			continue
		for name in {one for one in find(doc) if one}:
			if frappe.db.exists(kind, name):
				frappe.db.set_value(kind, name, DUE, 1, update_modified=False)


def due() -> int:
	"""Hourly: write the summaries due, each at most once a day."""
	from onedesk.one import account

	if not account.configured():
		return 0
	since = add_days(now_datetime(), -DAY)
	done = 0
	for kind in BRIEFS:
		if not on(kind):
			continue
		names = frappe.db.sql(
			f"""select name from `tab{kind}` where `{DUE}` = 1 and (`{ON}` is null or `{ON}` < %s)
			order by modified desc limit %s""",
			(since, AN_HOUR - done),
		)
		for (name,) in names:
			write(kind, name)
			frappe.db.commit()
			done += 1
		if done >= AN_HOUR:
			break
	return done


def later(doctype: str, name: str) -> None:
	frappe.enqueue(
		"onedesk.one_ai.brief.write",
		queue="long",
		job_id=f"one-ai-brief::{doctype}::{name}",
		deduplicate=True,
		enqueue_after_commit=True,
		doctype=doctype,
		name=name,
	)


def write(doctype: str, name: str) -> str | None:
	"""Gather what is known about one record, ask once, and keep the answer."""
	from onedesk.one_ai import run

	was = frappe.session.user
	frappe.set_user("Administrator")
	try:
		facts = FACTS[doctype](name)
		said = run.once(ACTION, asked(doctype, facts), reference=name)
	except Exception:
		frappe.log_error(title=f"OneAI could not summarise {doctype} {name}", reference_doctype=doctype, reference_name=name)
		return None
	finally:
		frappe.set_user(was)
	brief = short(strip_html(said or ""))
	if not brief:
		return None
	frappe.db.set_value(doctype, name, {BRIEF: brief, ON: now_datetime(), DUE: 0}, update_modified=False)
	frappe.publish_realtime(
		"doc_update",
		{"doctype": doctype, "name": name, "modified": str(frappe.db.get_value(doctype, name, "modified"))},
		doctype=doctype,
		docname=name,
		after_commit=True,
	)
	return brief


def asked(doctype: str, facts: dict) -> str:
	"""What the model is handed: the kind of record, the facts, the language."""
	language = frappe.db.get_single_value("System Settings", "language") or "en"
	called = frappe.db.get_value("Language", language, "language_name") or language
	return (
		f"Summarise this {doctype.lower()} for whoever opens it next. Today is {nowdate()}. Write in {called}.\n\n"
		+ json.dumps(facts, ensure_ascii=False, default=str)
	)


def short(text: str) -> str:
	said = " ".join((text or "").split())
	if len(said) <= MOST:
		return said
	return said[: MOST - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


#: Each side of a party: its invoices, orders, what it delivers on, and the
#: field that names the party on each.
SIDES = {
	"Customer": {
		"party": "customer",
		"invoice": "Sales Invoice",
		"order": "Sales Order",
		"by": "delivery_date",
		"done": "per_delivered",
		"quote": ("Quotation", "party_name"),
	},
	"Supplier": {
		"party": "supplier",
		"invoice": "Purchase Invoice",
		"order": "Purchase Order",
		"by": "schedule_date",
		"done": "per_received",
		"quote": ("Supplier Quotation", "supplier"),
	},
}


def party_facts(doctype: str, name: str) -> dict:
	"""A customer or supplier as somebody about to deal with them would want
	it: what they are worth this year and last, what is owed and overdue,
	orders late or open, what they buy or sell, and what was said lately."""
	side = SIDES[doctype]
	doc = frappe.get_doc(doctype, name)
	today = getdate()
	year = get_first_day(today).replace(month=1)
	last_year = year.replace(year=year.year - 1)
	invoice, party = side["invoice"], side["party"]
	from erpnext import get_default_currency

	currency = get_default_currency()

	def total(start, end) -> float:
		return flt(
			frappe.db.sql(
				f"""select sum(base_grand_total) from `tab{invoice}` where {party} = %s and docstatus = 1
				and is_return = 0 and posting_date >= %s and posting_date < %s""",
				(name, start, end),
			)[0][0]
		)

	owed = frappe.db.sql(
		f"""select count(*), sum(outstanding_amount), sum(if(due_date < %s, outstanding_amount, 0)),
		sum(if(due_date < %s, 1, 0)) from `tab{invoice}`
		where {party} = %s and docstatus = 1 and outstanding_amount > 0""",
		(today, today, name),
	)[0]
	open_orders = frappe.get_all(
		side["order"],
		filters={party: name, "docstatus": 1, "status": ["not in", ["Completed", "Closed", "Cancelled"]]},
		fields=["name", "status", side["by"], "base_grand_total", side["done"], "per_billed"],
		order_by=f"{side['by']} asc",
		limit_page_length=20,
	)
	items = frappe.db.sql(
		f"""select i.item_name, sum(i.qty), sum(i.base_amount) from `tab{invoice} Item` i
		join `tab{invoice}` p on p.name = i.parent
		where p.{party} = %s and p.docstatus = 1 and p.is_return = 0 and p.posting_date >= %s
		group by i.item_name order by sum(i.base_amount) desc limit %s""",
		(name, year, ITEMS),
	)
	quote, quoted_by = side["quote"]
	said = {
		"name": doc.get(f"{party}_name") or name,
		"group": doc.get(f"{party}_group"),
		"country": doc.get("country") or doc.get("territory"),
		"since": str(getdate(doc.creation)),
		"disabled": bool(doc.get("disabled")),
		"on_hold": bool(doc.get("on_hold")),
		"currency": currency,
		"invoiced_this_year": total(year, add_days(today, 1)),
		"invoiced_last_year": total(last_year, year),
		"returns_this_year": frappe.db.count(invoice, {party: name, "docstatus": 1, "is_return": 1, "posting_date": [">=", year]}),
		"unpaid": {"invoices": owed[0], "amount": flt(owed[1]), "overdue_amount": flt(owed[2]), "overdue_invoices": int(owed[3] or 0)},
		"last_invoice": str(
			frappe.db.sql(f"select max(posting_date) from `tab{invoice}` where {party} = %s and docstatus = 1", name)[0][0] or ""
		)
		or None,
		"open_orders": [
			{
				"order": one.name,
				"status": one.status,
				"due": str(one.get(side["by"]) or ""),
				"late": bool(one.get(side["by"]) and getdate(one.get(side["by"])) < today and flt(one.get(side["done"])) < 100),
				"worth": one.base_grand_total,
				"delivered_percent": one.get(side["done"]),
				"billed_percent": one.per_billed,
			}
			for one in open_orders
		],
		"most_this_year": [{"item": one[0], "qty": flt(one[1]), "worth": flt(one[2])} for one in items],
		"open_quotes": frappe.db.count(quote, {quoted_by: name, "docstatus": 1, "status": ["in", ["Open", "Submitted", "Replied"]]}),
	}
	if doctype == "Customer":
		said["open_issues"] = [
			{"subject": one.subject, "status": one.status, "since": str(one.opening_date)}
			for one in frappe.get_all(
				"Issue",
				filters={"customer": name, "status": ["in", ["Open", "Replied", "On Hold"]]},
				fields=["subject", "status", "opening_date"],
				order_by="opening_date desc",
				limit_page_length=5,
			)
		]
	else:
		said["rejected_inspections_this_year"] = frappe.db.sql(
			"""select count(*) from `tabQuality Inspection` q join `tabPurchase Receipt` r
			on q.reference_type = 'Purchase Receipt' and q.reference_name = r.name
			where r.supplier = %s and q.status = 'Rejected' and q.docstatus = 1 and q.report_date >= %s""",
			(name, year),
		)[0][0]
	return {**said, **lately(doctype, name)}


def lately(doctype: str, name: str) -> dict:
	"""The last few mails and comments on a record, newest first."""
	mails = frappe.db.sql(
		"""select c.subject, c.sent_or_received, c.communication_date, c.content from `tabCommunication` c
		where c.communication_type = 'Communication' and (
			(c.reference_doctype = %(kind)s and c.reference_name = %(name)s)
			or exists (select 1 from `tabCommunication Link` l where l.parent = c.name
				and l.link_doctype = %(kind)s and l.link_name = %(name)s))
		order by c.communication_date desc limit %(most)s""",
		{"kind": doctype, "name": name, "most": MAILS},
		as_dict=True,
	)
	comments = frappe.get_all(
		"Comment",
		filters={"reference_doctype": doctype, "reference_name": name, "comment_type": "Comment"},
		fields=["content", "comment_by", "creation"],
		order_by="creation desc",
		limit_page_length=COMMENTS,
	)
	return {
		"mail": [
			{"subject": one.subject, "way": one.sent_or_received, "on": str(one.communication_date), "said": short(strip_html(one.content or ""))[:300]}
			for one in mails
		],
		"comments": [{"by": one.comment_by, "on": str(one.creation), "said": short(strip_html(one.content or ""))[:300]} for one in comments],
	}


def opportunity_facts(name: str) -> dict:
	from onedesk.one_crm import ai

	return ai._facts("Opportunity", name)


def project_facts(name: str) -> dict:
	from onedesk.one_project import ai

	return {**ai.project_facts(name), **lately("Project", name)}


FACTS = {
	"Customer": lambda name: party_facts("Customer", name),
	"Supplier": lambda name: party_facts("Supplier", name),
	"Opportunity": opportunity_facts,
	"Project": project_facts,
}
