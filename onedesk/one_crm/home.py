"""OneCRM's Home (page/onecrm): what needs the reader today, and everything in
OneCRM with what it is for. The story beside it is story.py.

Today is the reader's own day, as the workspace's My Day was: their open
opportunities and leads whose next step is due or missing, the leads nobody
has taken, their opportunities past the day they were to close, quotations
running out this week, and drafts left.
"""

import frappe
from frappe import _lt
from frappe.utils import add_days, get_datetime, getdate, now_datetime, nowdate

from onedesk.one_crm import measure
from onedesk.one_crm import next as next_step

FEW = 5

WEEK = 7

GROUPS = (
	("pipeline", _lt("Sales Pipeline")),
	("sales", _lt("Selling")),
	("campaigns", _lt("Campaign")),
	("support", _lt("Support")),
	("reports", _lt("Reports")),
	("setup", _lt("Setup")),
)
REPORT_SECTIONS = (
	("pipeline", _lt("Sales Pipeline")),
	("leads", _lt("Lead")),
	("sales", _lt("Selling")),
	("customers", _lt("Customer")),
	("support", _lt("Support")),
)
REPORT_TOPICS = {
	"Opportunity Forecast": "pipeline",
	"Won and Lost": "pipeline",
	"Time in Sales Stage": "pipeline",
	"First Response Time for Opportunity": "pipeline",
	"Lead Sources": "leads",
	"Lead Owner Efficiency": "leads",
	"Lead Conversion Time": "leads",
	"Prospects Engaged But Not Converted": "leads",
	"Campaign Efficiency": "leads",
	"Sales Analytics": "sales",
	"Quotation Trends": "sales",
	"Lost Quotations": "sales",
	"Sales Order Analysis": "sales",
	"Sales Order Trends": "sales",
	"Sales Person-wise Transaction Summary": "sales",
	"Territory-wise Sales": "sales",
	"Item-wise Sales History": "sales",
	"Address And Contacts": "customers",
	"Inactive Customers": "customers",
	"Customer Acquisition and Loyalty": "customers",
	"Customers Without Any Sales Transactions": "customers",
	"Issue Summary": "support",
	"Issue Analytics": "support",
	"First Response Time for Issues": "support",
	"Support Hour Distribution": "support",
	"Maintenance Schedules": "support",
}
SETUP_SECTIONS = (
	("settings", _lt("Settings")),
	("selling", _lt("Selling")),
	("lists", _lt("Lists")),
	("terms", _lt("Pricing")),
	("support", _lt("Support")),
	("calls", _lt("Telephony")),
)
SETUP_TOPICS = {
	"CRM Settings": "settings",
	"Selling Settings": "settings",
	"Appointment Booking Settings": "settings",
	"Web Form": "settings",
	"Sales Stage": "selling",
	"Sales Person": "selling",
	"Assignment Rule": "selling",
	"Sales Partner": "selling",
	"UTM Source": "lists",
	"Opportunity Lost Reason": "lists",
	"Opportunity Type": "lists",
	"Competitor": "lists",
	"Territory": "lists",
	"Customer Group": "lists",
	"Industry Type": "lists",
	"Market Segment": "lists",
	"Price List": "terms",
	"Pricing Rule": "terms",
	"Terms and Conditions": "terms",
	"Sales Taxes and Charges Template": "terms",
	"Promotional Scheme": "terms",
	"Party Specific Item": "terms",
	"Support Settings": "support",
	"Service Level Agreement": "support",
	"Issue Type": "support",
	"Issue Priority": "support",
	"Telephony Call Type": "calls",
	"Incoming Call Settings": "calls",
	"Voice Call Settings": "calls",
	"Communication Medium": "calls",
}

EVERYTHING = (
	("pipeline", _lt("Lead"), "DocType", "Lead", _lt("Somebody who got in touch, or somebody you want to reach.")),
	("pipeline", _lt("Opportunity"), "DocType", "Opportunity", _lt("A sale you are working on, what it is worth and how far it has got.")),
	("pipeline", _lt("Prospect"), "DocType", "Prospect", _lt("A business you want to sell to, with its people.")),
	("pipeline", _lt("Customer"), "DocType", "Customer", _lt("Who has bought, or is about to.")),
	("pipeline", _lt("Contact"), "DocType", "Contact", _lt("The people at your customers and prospects.")),
	("pipeline", _lt("Appointment"), "DocType", "Appointment", _lt("A meeting booked with a lead or a customer.")),
	("pipeline", _lt("Contract"), "DocType", "Contract", _lt("What a customer signs, and until when.")),
	("pipeline", _lt("Call Log"), "DocType", "Call Log", _lt("Every call made and taken, and who it was with.")),
	("sales", _lt("Quotation"), "DocType", "Quotation", _lt("A price sent to a lead or a customer.")),
	("sales", _lt("Sales Order"), "DocType", "Sales Order", _lt("A quotation the customer said yes to.")),
	("sales", _lt("Sales Invoice"), "DocType", "Sales Invoice", _lt("What a sales order is billed with, in OneBook.")),
	("sales", _lt("Blanket Order"), "DocType", "Blanket Order", _lt("A price agreed for a year of orders.")),
	("campaigns", _lt("Campaign"), "DocType", "Campaign", _lt("Where a lead came from, to count what each campaign brought.")),
	("campaigns", _lt("Email Campaign"), "DocType", "Email Campaign", _lt("Mail sent to a lead or a contact on a schedule.")),
	("campaigns", _lt("Email Group"), "DocType", "Email Group", _lt("A list of addresses a newsletter goes to.")),
	("support", _lt("Issue"), "DocType", "Issue", _lt("A customer's complaint or question, until it is resolved.")),
	("support", _lt("Warranty Claim"), "DocType", "Warranty Claim", _lt("Something sold that broke, and whether the warranty covers it.")),
	("support", _lt("Maintenance Schedule"), "DocType", "Maintenance Schedule", _lt("The visits promised to keep what a customer bought working.")),
	("support", _lt("Maintenance Visit"), "DocType", "Maintenance Visit", _lt("A visit to a customer, and the work done.")),
	("reports", _lt("Opportunity Forecast"), "Report", "Opportunity Forecast", _lt("What the open opportunities will bring in, month by month.")),
	("reports", _lt("Won and Lost"), "Report", "Won and Lost", _lt("Opportunities won and lost, and the win rate.")),
	("reports", _lt("Time in Sales Stage"), "Report", "Time in Sales Stage", _lt("How long opportunities stay in each stage, and take to win.")),
	("reports", _lt("First Response Time for Opportunity"), "Report", "First Response Time for Opportunity", _lt("How fast opportunities were first answered.")),
	("reports", _lt("Lead Sources"), "Report", "Lead Sources", _lt("Which sources bring leads that turn into sales.")),
	("reports", _lt("Lead Owner Efficiency"), "Report", "Lead Owner Efficiency", _lt("What each lead owner turned into opportunities and sales.")),
	("reports", _lt("Lead Conversion Time"), "Report", "Lead Conversion Time", _lt("How long a lead took to become a customer.")),
	("reports", _lt("Prospects Engaged But Not Converted"), "Report", "Prospects Engaged But Not Converted", _lt("Leads spoken to often that have not bought.")),
	("reports", _lt("Campaign Efficiency"), "Report", "Campaign Efficiency", _lt("What each campaign brought in leads, opportunities and sales.")),
	("reports", _lt("Sales Analytics"), "Report", "Sales Analytics", _lt("Orders by customer, item or territory, month by month."), {"doc_type": "Sales Order"}),
	("reports", _lt("Quotation Trends"), "Report", "Quotation Trends", _lt("What was quoted, period against period.")),
	("reports", _lt("Lost Quotations"), "Report", "Lost Quotations", _lt("Quotations lost, and why.")),
	("reports", _lt("Sales Order Analysis"), "Report", "Sales Order Analysis", _lt("Each order line: delivered, billed, and what is late.")),
	("reports", _lt("Sales Order Trends"), "Report", "Sales Order Trends", _lt("What was ordered, period against period.")),
	("reports", _lt("Sales Person-wise Transaction Summary"), "Report", "Sales Person-wise Transaction Summary", _lt("What each salesperson sold.")),
	("reports", _lt("Territory-wise Sales"), "Report", "Territory-wise Sales", _lt("Opportunities, quotations, orders and invoices by territory.")),
	("reports", _lt("Item-wise Sales History"), "Report", "Item-wise Sales History", _lt("Every item sold, to whom and when.")),
	("reports", _lt("Address And Contacts"), "Report", "Address And Contacts", _lt("Every customer's addresses and people.")),
	("reports", _lt("Inactive Customers"), "Report", "Inactive Customers", _lt("Customers who have not ordered for a while.")),
	("reports", _lt("Customer Acquisition and Loyalty"), "Report", "Customer Acquisition and Loyalty", _lt("New customers against returning ones, month by month.")),
	("reports", _lt("Customers Without Any Sales Transactions"), "Report", "Customers Without Any Sales Transactions", _lt("Customers who have never been billed.")),
	("reports", _lt("Issue Summary"), "Report", "Issue Summary", _lt("Issues opened, replied to and resolved, by who handled them.")),
	("reports", _lt("Issue Analytics"), "Report", "Issue Analytics", _lt("Issues by customer, type or priority, month by month.")),
	("reports", _lt("First Response Time for Issues"), "Report", "First Response Time for Issues", _lt("How fast issues were first answered.")),
	("reports", _lt("Support Hour Distribution"), "Report", "Support Hour Distribution", _lt("The hours of the day issues come in.")),
	("reports", _lt("Maintenance Schedules"), "Report", "Maintenance Schedules", _lt("Every visit due, by customer and item.")),
	("setup", _lt("CRM Settings"), "DocType", "CRM Settings", _lt("How leads, opportunities and quotations work.")),
	("setup", _lt("Selling Settings"), "DocType", "Selling Settings", _lt("How quotations, orders and prices work.")),
	("setup", _lt("Appointment Booking Settings"), "DocType", "Appointment Booking Settings", _lt("When customers may book a meeting, and with whom.")),
	("setup", _lt("Get in Touch Form"), "DocType", "Web Form", _lt("The website form that makes a lead."), {"name": "get-in-touch"}),
	("setup", _lt("Sales Stage"), "DocType", "Sales Stage", _lt("The stages an opportunity moves through, and their probability.")),
	("setup", _lt("Sales Person"), "DocType", "Sales Person", _lt("Who sells, and the team they are in.")),
	("setup", _lt("Assignment Rule"), "DocType", "Assignment Rule", _lt("How new leads are shared out."), {"document_type": "Lead"}),
	("setup", _lt("Sales Partner"), "DocType", "Sales Partner", _lt("Who sells for you, on commission.")),
	("setup", _lt("Lead Source"), "List", "UTM Source", _lt("Where a lead or an opportunity came from.")),
	("setup", _lt("Opportunity Lost Reason"), "List", "Opportunity Lost Reason", _lt("Why an opportunity or a quotation is lost.")),
	("setup", _lt("Opportunity Type"), "DocType", "Opportunity Type", _lt("Sales, support, maintenance: what an opportunity is for.")),
	("setup", _lt("Competitor"), "DocType", "Competitor", _lt("Who else a customer is talking to.")),
	("setup", _lt("Territory"), "List", "Territory", _lt("The places you sell in.")),
	("setup", _lt("Customer Group"), "List", "Customer Group", _lt("Kinds of customer, each with its price list and terms.")),
	("setup", _lt("Industry Type"), "List", "Industry Type", _lt("The industry a lead or a customer is in.")),
	("setup", _lt("Market Segment"), "List", "Market Segment", _lt("The part of the market a lead or a customer is in.")),
	("setup", _lt("Price List"), "DocType", "Price List", _lt("The prices you sell at, one list per currency or customer group.")),
	("setup", _lt("Pricing Rule"), "DocType", "Pricing Rule", _lt("A discount or price for some customers, items or quantities.")),
	("setup", _lt("Terms and Conditions"), "DocType", "Terms and Conditions", _lt("The terms a quotation and an order carry.")),
	("setup", _lt("Sales Taxes and Charges Template"), "DocType", "Sales Taxes and Charges Template", _lt("The taxes a sale carries.")),
	("setup", _lt("Promotional Scheme"), "DocType", "Promotional Scheme", _lt("A promotion with tiers of discount or free items.")),
	("setup", _lt("Party Specific Item"), "DocType", "Party Specific Item", _lt("The only items a customer or supplier is offered.")),
	("setup", _lt("Support Settings"), "DocType", "Support Settings", _lt("When issues close by themselves, and what the help page shows.")),
	("setup", _lt("Service Level Agreement"), "DocType", "Service Level Agreement", _lt("How fast an issue must be answered and resolved, by priority.")),
	("setup", _lt("Issue Type"), "List", "Issue Type", _lt("Kinds of issue, such as a fault or a question.")),
	("setup", _lt("Issue Priority"), "List", "Issue Priority", _lt("How urgent an issue is.")),
	("setup", _lt("Telephony Call Type"), "DocType", "Telephony Call Type", _lt("What a call was about.")),
	("setup", _lt("Incoming Call Settings"), "DocType", "Incoming Call Settings", _lt("Who answers calls to a number, on which days and hours.")),
	("setup", _lt("Voice Call Settings"), "DocType", "Voice Call Settings", _lt("Whether a person takes calls, and what callers hear.")),
	("setup", _lt("Communication Medium"), "DocType", "Communication Medium", _lt("A phone line, mailbox or chat customers reach you on, and who answers it when.")),
)


@frappe.whitelist()
def read() -> dict:
	"""What needs the reader, and the directory, as the reader may see them."""
	return {
		"needs": needs_you(),
		"groups": [{"key": key, "label": str(label)} for key, label in GROUPS],
		"sections": {
			"reports": [{"key": key, "label": str(label)} for key, label in REPORT_SECTIONS],
			"setup": [{"key": key, "label": str(label)} for key, label in SETUP_SECTIONS],
		},
		"everything": directory(),
	}


def _kept(rows: list) -> dict:
	return {"rows": rows[:FEW], "count": len(rows)}


def needs_you() -> dict:
	"""The reader's own open opportunities and leads, due or unplanned; leads
	nobody has taken; their opportunities past closing; quotations running
	out; and drafts left more than a day."""
	return {
		"opportunities": _kept(_steps("Opportunity", due=True)),
		"leads": _kept(_steps("Lead", due=True)),
		"unplanned": _kept(_steps("Opportunity", due=False) + _steps("Lead", due=False)),
		"unclaimed": _kept(_unclaimed()),
		"closing": _kept(_closing()),
		"expiring": _kept(_expiring()),
		"drafts": drafts(),
	}


TITLE = {"Lead": ("lead_name", "company_name"), "Opportunity": ("title", "customer_name")}


def _row(doctype: str, one) -> dict:
	name, party = TITLE[doctype]
	return {
		"doctype": doctype,
		"name": one.name,
		"title": one.get(name) or one.get(party) or one.name,
		"party": one.get(party) if one.get(name) else None,
		"step": one.one_next_step,
		"on": str(one.one_next_on) if one.one_next_on else None,
		"late": bool(one.one_next_on) and get_datetime(one.one_next_on) < now_datetime(),
	}


def _steps(doctype: str, due: bool) -> list[dict]:
	"""The reader's open ones whose next step is due by tonight, the latest
	first; or, with due False, the ones with none."""
	if not frappe.has_permission(doctype, "read"):
		return []
	filters = [
		[next_step.OWNER[doctype], "=", frappe.session.user],
		["status", "in", next_step.OPEN[doctype]],
		["one_next_on", "is", "set" if due else "not set"],
		["company", "=", measure.company()],
	]
	if due:
		filters.append(["one_next_on", "<=", f"{nowdate()} 23:59:59"])
	rows = frappe.get_list(
		doctype,
		filters=filters,
		fields=["name", *TITLE[doctype], "one_next_step", "one_next_on"],
		order_by="one_next_on asc, modified desc",
		limit_page_length=0,
	)
	return [_row(doctype, one) for one in rows]


def _unclaimed() -> list[dict]:
	"""Open leads nobody owns, the newest first: everybody's to take."""
	if not frappe.has_permission("Lead", "read"):
		return []
	rows = frappe.get_list(
		"Lead",
		filters={"lead_owner": ["is", "not set"], "status": ["in", next_step.OPEN["Lead"]], "company": measure.company()},
		fields=["name", *TITLE["Lead"], "one_next_step", "one_next_on", "creation", "utm_source"],
		order_by="creation desc",
		limit_page_length=0,
	)
	return [{**_row("Lead", one), "since": str(one.creation), "source": one.utm_source} for one in rows]


def _closing() -> list[dict]:
	"""The reader's open opportunities whose Expected Closing Date has passed,
	the longest past first."""
	if not frappe.has_permission("Opportunity", "read"):
		return []
	day = getdate(nowdate())
	rows = frappe.get_list(
		"Opportunity",
		filters={
			"opportunity_owner": frappe.session.user,
			"status": ["in", next_step.OPEN["Opportunity"]],
			"expected_closing": ["<", day],
			"company": measure.company(),
		},
		fields=["name", *TITLE["Opportunity"], "one_next_step", "one_next_on", "expected_closing"],
		order_by="expected_closing asc",
		limit_page_length=0,
	)
	return [
		{
			**_row("Opportunity", one),
			"closing": str(one.expected_closing),
			"days": (day - getdate(one.expected_closing)).days,
		}
		for one in rows
	]


def _expiring() -> list[dict]:
	"""Open quotations whose Valid Till falls this week, the soonest first."""
	if not frappe.has_permission("Quotation", "read"):
		return []
	day = getdate(nowdate())
	rows = frappe.get_list(
		"Quotation",
		filters={
			"docstatus": 1,
			"status": ["in", ["Open", "Replied"]],
			"valid_till": ["between", [day, add_days(day, WEEK - 1)]],
			"company": measure.company(),
		},
		fields=["name", "party_name", "customer_name", "valid_till", "grand_total", "currency"],
		order_by="valid_till asc",
		limit_page_length=0,
	)
	return [
		{
			"name": one.name,
			"party": one.customer_name or one.party_name,
			"valid_till": str(one.valid_till),
			"days": (getdate(one.valid_till) - day).days,
			"grand_total": one.grand_total,
			"currency": one.currency,
		}
		for one in rows
	]


DRAFTS = (
	("Quotation", _lt("Quotation")),
	("Sales Order", _lt("Sales Order")),
)


def drafts() -> list[dict]:
	"""For each kind of paper, how many drafts the reader left more than a day
	ago."""
	out = []
	for doctype, label in DRAFTS:
		if not frappe.has_permission(doctype, "read"):
			continue
		count = len(
			frappe.get_list(
				doctype,
				filters={
					"docstatus": 0,
					"owner": frappe.session.user,
					"modified": ["<", add_days(nowdate(), -1)],
					"company": measure.company(),
				},
				pluck="name",
				limit_page_length=0,
			)
		)
		if count:
			out.append({"doctype": doctype, "label": str(label), "count": count})
	return out


def _may(kind: str, target: str) -> bool:
	"""Whether the reader may open it. A report declutter switched off, or one
	over records the reader may not read, refuses when opened, so neither is
	offered."""
	if kind in ("DocType", "List"):
		return bool(frappe.has_permission(target, "read"))
	if not frappe.db.exists(kind, target):
		return False
	doc = frappe.get_cached_doc(kind, target)
	if kind == "Report":
		if doc.disabled or (doc.ref_doctype and not frappe.has_permission(doc.ref_doctype, "report")):
			return False
	return bool(doc.is_permitted())


LAST_MONTH = ("Issue Summary", "Issue Analytics", "Support Hour Distribution")


def _filters(target: str, filters: list) -> dict | None:
	"""A row's own filters, and the last thirty days for the support reports:
	two of them start from a year default erpnext no longer writes, so they
	opened asking for dates, and the third opened on today alone."""
	said = dict(filters[0]) if filters else {}
	if target in LAST_MONTH:
		said.update(from_date=add_days(nowdate(), -30), to_date=nowdate())
	return said or None


def directory() -> list[dict]:
	"""Everything in OneCRM the reader may open, with what it is for."""
	return [
		{
			"group": group,
			"label": str(label),
			"kind": kind,
			"target": target,
			"filters": _filters(target, filters),
			"about": str(about),
			"topic": {"reports": REPORT_TOPICS, "setup": SETUP_TOPICS}.get(group, {}).get(target),
		}
		for group, label, kind, target, about, *filters in EVERYTHING
		if _may(kind, target)
	]
