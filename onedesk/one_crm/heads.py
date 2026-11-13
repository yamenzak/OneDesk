"""What a lead's and a deal's page say above their fields. See one/head.py.

The figures are record.py's `overview`, worked out once per request.
"""

from urllib.parse import quote

import frappe
from frappe import _, _lt
from frappe.utils import flt, formatdate, get_datetime, getdate, now_datetime, today
from frappe.utils.caching import request_cache

from onedesk.one import head
from onedesk.one import stages as steps
from onedesk.one.company import company_currency
from onedesk.one_crm import capture, chain, record, stages
from onedesk.one_crm.next import OWNER

WHEN = "{when}"


@request_cache
def _said(doctype: str, name: str) -> dict:
	return record.overview(doctype, name)


def lasted(start, end=None) -> str:
	"""How long, not when: "under an hour", "5 hours", "12 days". Pure over
	the two moments."""
	hours = int((get_datetime(end or now_datetime()) - get_datetime(start)).total_seconds() // 3600)
	if hours < 1:
		return _("under an hour")
	if hours < 24:
		return _("an hour") if hours == 1 else _("{0} hours").format(hours)
	days = hours // 24
	return _("a day") if days == 1 else _("{0} days").format(days)


def days(count) -> str:
	"""A number of days as a person says it: "a day", "5 days", "under a day"."""
	whole = round(count or 0)
	if whole < 1:
		return _("under a day")
	return _("a day") if whole == 1 else _("{0} days").format(whole)


def value(doc):
	said = _said(doc.doctype, doc.name)
	return {
		"label": _("Opportunity Amount · {0}%").format(round(said["probability"])),
		"value": head.money(said["value"], said["currency"], 0),
		"meter": {"value": said["probability"], "of": 100},
	}


def stage(doc):
	said = _said(doc.doctype, doc.name)
	if doc.status in ("Converted", "Lost"):
		named = said["stage"] or doc.status
		return {"label": _(named), "value": _("on {0}").format(formatdate(said["since"]))}
	stayed = lasted(said["since"])
	usual = said.get("usual")
	return {
		"label": _(named) if (named := said["stage"]) else _("Sales Stage"),
		"value": _("for {0} · usually {1}").format(stayed, days(usual))
		if usual is not None
		else _("for {0}").format(stayed),
		"tone": "waiting" if said.get("long") else None,
		"meter": {
			"value": int((now_datetime() - get_datetime(said["since"])).total_seconds() // 86400),
			"of": usual,
		}
		if usual
		else None,
	}


def closes(doc):
	said = _said(doc.doctype, doc.name)
	if not said.get("closing"):
		return None
	late = said["open"] and getdate(said["closing"]) < getdate(today())
	return {"value": formatdate(said["closing"]), "tone": "alarm" if late else None}


def quotation(doc):
	found = _said(doc.doctype, doc.name).get("quotation")
	if not found:
		return None
	return {
		"value": _("{0} · {1}").format(_(found.status), head.money(found.grand_total, found.currency, 0)),
		"route": f"/desk/quotation/{found.name}",
	}


@request_cache
def _went(name: str) -> frappe._dict:
	return chain.follow([name])[name]


def _late(invoice) -> bool:
	return "Overdue" in (invoice.status or "")


def progress(doc):
	"""Where the sale stands past the opportunity: quoted, ordered, billed and
	paid, as ERPNext's papers say, on a track. Stopped while it is on hold or
	once it is lost."""
	went = _went(doc.name)
	quotes = [one for one in went.quotations if one.docstatus == 1]
	orders = [one for one in went.orders if one.docstatus == 1]
	bills = [one for one in went.invoices if one.docstatus == 1]
	owed = sum(chain.owed(one) for one in bills)
	billed = bool(orders) and all(flt(one.per_billed) >= 100 for one in orders)
	paid = bool(bills) and owed <= 0
	late = any(_late(one) for one in bills)
	held = doc.sales_stage in stages.held()
	return steps.track(
		doc.opportunity_from == "Lead" and steps.step(_("Lead"), "done"),
		steps.step(_("Opportunity"), "done", formatdate(doc.transaction_date)),
		steps.step(_("Quotation"), steps.at(bool(quotes), bool(went.quotations)), _(quotes[0].status) if quotes else ""),
		steps.step(_("Sales Order"), steps.at(bool(orders), bool(went.orders))),
		steps.step(_("Billed"), steps.at(billed, bool(bills)), steps.share(orders[0].per_billed) if orders and not billed else ""),
		steps.step(_("Paid"), steps.at(paid, bool(bills), late), _("{0} owed").format(head.money(owed, company_currency(doc.get("company")), 0)) if owed > 0 else ""),
		stopped=doc.status == "Lost" or held,
	)


def said(doc):
	"""Where the sale stands, in a sentence, once there is something to say
	past the band: lost, on hold, quoted, or won and how far its money got."""
	if doc.status == "Lost":
		reasons = [_(one.lost_reason) for one in doc.lost_reasons or []]
		text = _("Lost: {0}.").format(", ".join(reasons)) if reasons else _("Lost.")
		return {"text": text, "colour": "gray"}
	if doc.sales_stage in stages.held():
		return {"text": _("On hold, out of the pipeline until it moves again."), "colour": "gray"}
	went = _went(doc.name)
	orders = [one for one in went.orders if one.docstatus == 1]
	if doc.status == "Converted" or orders:
		bills = [one for one in went.invoices if one.docstatus == 1]
		if not orders:
			return {"text": _("Won."), "colour": "green"}
		if not bills:
			return {"text": _("Won and ordered; nothing is billed yet."), "colour": "blue"}
		owed = sum(chain.owed(one) for one in bills)
		if owed <= 0:
			return {"text": _("Won, billed and paid in full."), "colour": "green"}
		if any(_late(one) for one in bills):
			return {"text": _("Won and billed; {0} is still owed, and some of it is late.").format(head.money(owed, company_currency(doc.get("company")), 0)), "colour": "red"}
		return {"text": _("Won and billed; {0} is still owed.").format(head.money(owed, company_currency(doc.get("company")), 0)), "colour": "orange"}
	quotes = [one for one in went.quotations if one.docstatus == 1 and one.status in ("Open", "Replied")]
	if quotes and quotes[0].valid_till:
		if getdate(quotes[0].valid_till) < getdate(today()):
			return {"text": _("Quotation {0} ran out on {1}.").format(quotes[0].name, formatdate(quotes[0].valid_till)), "colour": "orange"}
		return {"text": _("Quotation {0} is with them until {1}.").format(quotes[0].name, formatdate(quotes[0].valid_till)), "colour": "blue"}
	return None


def of_customer(doc):
	"""A customer's open opportunities and what they are worth, opening them."""
	from onedesk.one_crm import measure
	from onedesk.one_crm.next import OPEN

	if not frappe.has_permission("Opportunity", "read"):
		return None
	found = measure.deals({"opportunity_from": "Customer", "party_name": doc.name, "status": ["in", OPEN["Opportunity"]]})
	if not found:
		return None
	statuses = frappe.as_json(["in", list(OPEN["Opportunity"])], indent=None)
	return {
		"value": _("{0} open · {1}").format(len(found), head.money(sum(measure.value(one) for one in found), company_currency(), 0)),
		"route": f"/desk/opportunity?opportunity_from=Customer&party_name={doc.name}&status={statuses}",
	}


def came_in(doc):
	return {"value": WHEN, "when": str(_said(doc.doctype, doc.name)["since"])}


def reply(doc):
	said = _said(doc.doctype, doc.name)
	if said.get("first_reply"):
		return {
			"label": _("First Reply"),
			"value": _("after {0}").format(lasted(said["since"], said["first_reply"])),
		}
	if said["open"]:
		return {"label": _("Waiting For a Reply"), "value": lasted(said["since"]), "tone": "waiting"}
	return None


def made_deals(doc):
	found = _said(doc.doctype, doc.name)["deals"]
	if not found["count"]:
		return None
	return {
		"value": _("{0} open of {1}").format(found["open"], found["count"]),
		"route": f"/desk/opportunity?opportunity_from=Lead&party_name={doc.name}",
	}


def next_step(doc):
	said = _said(doc.doctype, doc.name)
	if not said["open"]:
		return None
	step, on = said["next"]["step"], said["next"]["on"]
	if not step and not on:
		return {"value": _("None planned"), "tone": "waiting"}
	ahead = on and getdate(on) > getdate(today())
	return {
		"label": _("Next Step") + (f" · {formatdate(on)}" if ahead else f" · {WHEN}" if on else ""),
		"value": step or _("Next Step"),
		"when": str(on) if on and not ahead else None,
		"tone": "alarm" if on and get_datetime(on) < now_datetime() else None,
	}


def contact(doc):
	said = _said(doc.doctype, doc.name)
	last = said.get("contact")
	if not last:
		return {
			"label": _("Last Contact"),
			"value": _("None yet"),
			"tone": "waiting" if said["open"] else "quiet",
		}
	return {
		"label": _("Last Call") if last["kind"] == "Call" else _("Last Email"),
		"value": WHEN,
		"when": str(last["at"]),
		"route": f"/desk/{frappe.scrub(last['doctype']).replace('_', '-')}/{last['name']}",
	}


def source(doc):
	return _said(doc.doctype, doc.name).get("source") or None


def deliver_by(doc):
	"""A sales order's earliest promised day for what has still to go out, in
	red once it has passed. Once all is delivered, or the order is closed,
	the day it was promised."""
	open_ = doc.docstatus == 1 and doc.status not in ("Closed", "On Hold", "Completed")
	waiting = [row.delivery_date for row in doc.items if row.delivery_date and flt(row.delivered_qty) < flt(row.qty)]
	if not open_ or not waiting:
		return formatdate(doc.delivery_date) if doc.delivery_date else None
	day = min(getdate(one) for one in waiting)
	if day < getdate(today()):
		return {"value": _("Late since {0}").format(formatdate(day)), "tone": "alarm"}
	return formatdate(day)


def valid(doc):
	"""How long a quotation holds, said as run out, in red, while the customer
	still has it to answer."""
	if not doc.get("valid_till"):
		return None
	if doc.docstatus == 1 and doc.status in ("Open", "Replied", "Expired") and getdate(doc.valid_till) < getdate(today()):
		return {"value": _("Ran out on {0}").format(formatdate(doc.valid_till)), "tone": "alarm"}
	return formatdate(doc.valid_till)


def deal_of(doc):
	"""The opportunity a quotation answers, opening it."""
	deal = doc.get("opportunity")
	if not deal or not frappe.has_permission("Opportunity", "read", doc=deal):
		return None
	title = frappe.db.get_value("Opportunity", deal, "title") or deal
	return {"value": title, "route": f"/desk/opportunity/{quote(deal, safe='')}"}


def next_visit(doc):
	"""A maintenance schedule's next visit still to make, red once it is due,
	or that every visit is made."""
	if doc.docstatus != 1:
		return None
	waiting = sorted(getdate(row.scheduled_date) for row in doc.get("schedules") or [] if row.completion_status != "Fully Completed" and row.scheduled_date)
	if not waiting:
		return {"value": _("All made"), "tone": "quiet"} if doc.get("schedules") else None
	return {"value": formatdate(waiting[0]), "tone": "alarm" if waiting[0] < getdate(today()) else None}


def visits_made(doc):
	"""How many of a schedule's visits are made, of how many."""
	rows = doc.get("schedules") or []
	if not rows:
		return None
	made = sum(1 for row in rows if row.completion_status == "Fully Completed")
	return {"value": _("{0} of {1}").format(made, len(rows)), "meter": {"value": made, "of": len(rows)}}


def met_with(doc):
	"""Who an appointment is with, by their name, opening them."""
	if not doc.get("appointment_with") or not doc.get("party"):
		return None
	shown = frappe.get_meta(doc.appointment_with).get_title_field()
	name = frappe.db.get_value(doc.appointment_with, doc.party, shown) if frappe.has_permission(doc.appointment_with, "read", doc=doc.party) else None
	return {"value": name or doc.party, "route": f"/desk/{frappe.scrub(doc.appointment_with).replace('_', '-')}/{doc.party}"}


MEASURES = {
	"crm.met_with": met_with,
	"crm.next_visit": next_visit,
	"crm.visits_made": visits_made,
	"crm.valid": valid,
	"crm.deal_of": deal_of,
	"crm.value": value,
	"crm.progress": progress,
	"crm.said": said,
	"crm.of_customer": of_customer,
	"crm.stage": stage,
	"crm.closes": closes,
	"crm.quotation": quotation,
	"crm.came_in": came_in,
	"crm.reply": reply,
	"crm.deals": made_deals,
	"crm.next_step": next_step,
	"crm.contact": contact,
	"crm.source": source,
	"crm.deliver_by": deliver_by,
}


VERBS = {
	"crm.take": {
		"doctypes": list(OWNER),
		"label": lambda doc: _("Take This Lead") if doc.doctype == "Lead" else _("Take This Opportunity"),
		"when": lambda doc: not doc.get(OWNER[doc.doctype]) and bool(frappe.has_permission(doc.doctype, "write", doc)),
		"fields": [],
		"run": lambda doc: capture.take(doc.doctype, doc.name) or _("It is yours."),
	},
}


HEADS = [
	{
		"doctype": "Customer",
		"band": [
			{"label": _lt("Overdue"), "source": "Measure", "measure": "party.overdue"},
			{"label": _lt("Last Sales Invoice"), "source": "Measure", "measure": "party.last_bill"},
			{
				"label": _lt("Open Orders"),
				"source": "Count",
				"of_doctype": "Sales Order",
				"filters": [
					["customer", "=", "{{ doc.name }}"],
					["docstatus", "=", 1],
					["status", "not in", ["Completed", "Closed"]],
				],
				"route": '/desk/sales-order?customer={{ doc.name }}&docstatus=1&status=["not in",["Completed","Closed"]]',
				"hide_empty": 1,
			},
			{"label": _lt("Opportunity"), "source": "Measure", "measure": "crm.of_customer"},
		],
		"charts": [{"chart": "party.billed"}],
	},
	{
		"doctype": "Opportunity",
		"sentences": [{"measure": "crm.said"}],
		"band": [
			{"label": _lt("Progress"), "source": "Measure", "measure": "crm.progress"},
			{"label": _lt("Opportunity Amount"), "source": "Measure", "measure": "crm.value"},
			{"label": _lt("Sales Stage"), "source": "Measure", "measure": "crm.stage"},
			{"label": _lt("Next Step"), "source": "Measure", "measure": "crm.next_step"},
			{"label": _lt("Last Contact"), "source": "Measure", "measure": "crm.contact"},
			{"label": _lt("Closes"), "source": "Measure", "measure": "crm.closes"},
			{"label": _lt("Quotation"), "source": "Measure", "measure": "crm.quotation"},
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Source"), "source": "Measure", "measure": "crm.source"},
		],
		"verbs": [{"verb": "crm.take"}],
	},
	{
		"doctype": "Quotation",
		"band": [
			{"label": _lt("Grand Total"), "source": "Measure", "measure": "order.total"},
			{"label": _lt("Valid Till"), "source": "Measure", "measure": "crm.valid"},
			{"label": _lt("Opportunity"), "source": "Measure", "measure": "crm.deal_of"},
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
		],
	},
	{
		"doctype": "Sales Order",
		"band": [
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Total"), "source": "Measure", "measure": "order.total"},
			{"label": _lt("Deliver By"), "source": "Measure", "measure": "crm.deliver_by"},
			{
				"label": _lt("Delivered"),
				"source": "Field",
				"field": "per_delivered",
				"shown_when": [["docstatus", "=", 1]],
			},
			{
				"label": _lt("Billed"),
				"source": "Field",
				"field": "per_billed",
				"shown_when": [["docstatus", "=", 1]],
			},
		],
	},
	{
		"doctype": "Contract",
		"band": [
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Signed On"), "source": "Field", "field": "signed_on"},
			{"label": _lt("Ends"), "source": "Field", "field": "end_date"},
		],
	},
	{
		"doctype": "Warranty Claim",
		"band": [
			{"label": _lt("Warranty / AMC Status"), "source": "Field", "field": "warranty_amc_status"},
			{"label": _lt("Warranty Expiry Date"), "source": "Field", "field": "warranty_expiry_date"},
			{"label": _lt("Resolution Date"), "source": "Field", "field": "resolution_date"},
		],
	},
	{
		"doctype": "Maintenance Schedule",
		"band": [
			{"label": _lt("Next Visit"), "source": "Measure", "measure": "crm.next_visit"},
			{"label": _lt("Visits Made"), "source": "Measure", "measure": "crm.visits_made"},
		],
	},
	{
		"doctype": "Appointment",
		"band": [
			{"label": _lt("Scheduled Time"), "source": "Field", "field": "scheduled_time"},
			{"label": _lt("Appointment With"), "source": "Measure", "measure": "crm.met_with"},
		],
	},
	{
		"doctype": "Email Campaign",
		"band": [
			{"label": _lt("Start Date"), "source": "Field", "field": "start_date"},
			{"label": _lt("End Date"), "source": "Field", "field": "end_date"},
			{"label": _lt("Recipient"), "source": "Field", "field": "recipient"},
		],
	},
	{
		"doctype": "Lead",
		"band": [
			{"label": _lt("Came In"), "source": "Measure", "measure": "crm.came_in"},
			{"label": _lt("First Reply"), "source": "Measure", "measure": "crm.reply"},
			{"label": _lt("Next Step"), "source": "Measure", "measure": "crm.next_step"},
			{"label": _lt("Last Contact"), "source": "Measure", "measure": "crm.contact"},
			{"label": _lt("Opportunity"), "source": "Measure", "measure": "crm.deals"},
			{"label": _lt("Source"), "source": "Measure", "measure": "crm.source"},
		],
		"verbs": [{"verb": "crm.take"}],
	},
]
