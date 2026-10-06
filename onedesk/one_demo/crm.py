"""The pipeline: leads from every source at every stage of being worked, deals
in every stage from New to Lost and in three currencies, the calls made on
them, the next step each is waiting on, and the quotations sent, accepted
and turned down."""

import frappe
from frappe.utils import add_to_date, now_datetime

from onedesk.one_demo.base import ago, ahead, as_user, make, save, tag

SALES = "omar@one.test"
ESTIMATOR = "samir@one.test"

#: first, last, company, email, source, status, owner, next step, in days
LEADS = (
	("Hamad", "Al Suwaidi", "Suwaidi Villas", "hamad@suwaidi.example", "Website", "Lead", SALES, "Call back about the villa windows", 1),
	("Elena", "Petrova", "Petrova Design Studio", "elena@petrova.example", "Reference", "Replied", SALES, "Send the showroom brochure", 2),
	("Kevin", "Osei", "Osei Builders", "kevin@osei.example", "Cold Calling", "Lead", SALES, "First call", -2),
	("Noura", "Al Falasi", None, "noura.falasi@example.com", "Walk In", "Interested", ESTIMATOR, "Site survey of the balcony", 4),
	("Marcus", "Webb", "Webb Hospitality", "marcus@webbhosp.example", "Campaign", "Opportunity", SALES, None, 0),
	("Sana", "Iqbal", "Iqbal Clinics", "sana@iqbalclinics.example", "Website", "Lost Quotation", SALES, None, 0),
	("Diego", "Ramos", "Ramos & Co", "diego@ramos.example", "Exhibition", "Do Not Contact", SALES, None, 0),
	("Fiona", "Clarke", "Clarke Architects", "fiona@clarkearch.example", "Reference", "Quotation", SALES, "Follow up on the quotation", 3),
	("Yusuf", "Erdem", "Erdem Towers", "yusuf@erdem.example", "Advertisement", "Lead", SALES, "Qualify the tower facade", 6),
	("Lucy", "Tran", "Tran Retail", "lucy@tranretail.example", "Website", "Converted", SALES, None, 0),
)

#: title, party (customer or a lead by first name), stage, amount, currency,
#: closing in days, next step, in days
DEALS = (
	("Suwaidi Villas glazing", ("Lead", "Hamad"), "New", 180000, "AED", 60, "Visit the plot with Samir", 3),
	("Webb Hotel lobby curtain wall", ("Lead", "Marcus"), "Qualified", 640000, "AED", 45, "Ask for the drawings", 2),
	("Clarke Architects school façade", ("Lead", "Fiona"), "Proposal", 410000, "AED", 30, "Walk them through the quotation", 1),
	("Crescent Schools classroom windows", ("Customer", "Crescent Schools"), "Negotiation", 96000, "AED", 10, "Agree the payment terms", -1),
	("Acme Holdings New York lobby", ("Customer", "Acme Holdings"), "Proposal", 85000, "USD", 40, "Send the revised quote", 5),
	("Harbour Logistics depot doors", ("Customer", "Harbour Logistics"), "On Hold", 52000, "GBP", 120, "Check in after their budget round", 30),
	("Nordlicht second showroom", ("Customer", "Nordlicht GmbH"), "Qualified", 38000, "EUR", 50, "Plan the design workshop", 7),
	("Marina Hotels pool fence", ("Customer", "Marina Hotels Group"), "Won", 44000, "AED", -20, None, 0),
	("Iqbal Clinics reception", ("Lead", "Sana"), "Lost", 31000, "AED", -35, None, 0),
)


def run(password=None):
	with as_user(SALES):
		leads = {}
		for first, last, company, email, source, status, owner, step, days in LEADS:
			found = frappe.db.get_value("Lead", {"email_id": email})
			if found:
				leads[first] = found
				continue
			if not frappe.db.exists("UTM Source", source):
				tag(frappe.get_doc({"doctype": "UTM Source"}).insert(set_name=source))
			lead = make(
				{
					"doctype": "Lead",
					"first_name": first,
					"last_name": last,
					"company_name": company,
					"email_id": email,
					"mobile_no": f"+97155{abs(hash(email)) % 10000000:07d}",
					"utm_source": source,
					"lead_owner": owner,
					"territory": "Dubai",
					"one_next_step": step,
					"one_next_on": add_to_date(now_datetime(), days=days, hours=2) if step else None,
				}
			)
			if status not in ("Lead", "Opportunity", "Quotation", "Lost Quotation", "Converted"):
				frappe.db.set_value("Lead", lead.name, "status", status)
			leads[first] = lead.name
			from onedesk.one_crm.record import log_call

			log_call("Lead", lead.name, "Outgoing", "Answered" if len(first) % 2 else "No Answer", 4, f"First call with {first}.")

		from erpnext.crm.doctype.opportunity.mapper import make_quotation

		for title, (kind, who), stage, amount, currency, closing, step, days in DEALS:
			if frappe.db.exists("Opportunity", {"title": title}):
				continue
			party = leads[who] if kind == "Lead" else who
			deal = make(
				{
					"doctype": "Opportunity",
					"title": title,
					"opportunity_from": kind,
					"party_name": party,
					"opportunity_owner": SALES,
					"sales_stage": "New",
					"currency": currency,
					"opportunity_amount": amount,
					"expected_closing": ahead(closing) if closing > 0 else ago(-closing),
					"one_next_step": step,
					"one_next_on": add_to_date(now_datetime(), days=days, hours=3) if step else None,
					"items": [{"item_code": "SVC-SURV", "qty": 1, "rate": amount}] if False else [],
				}
			)
			for passed in _stages_to(stage):
				deal.reload()
				deal.sales_stage = passed
				deal.save()
			from onedesk.one_crm.record import log_call

			log_call("Opportunity", deal.name, "Incoming", "Answered", 12, f"{title}: talked through scope and timing.")
			if stage in ("Proposal", "Negotiation", "Won", "Lost"):
				quote = make_quotation(deal.name)
				quote.append("items", {"item_code": "SVC-SURV", "qty": 1, "rate": 900})
				quote.append("items", {"item_code": "WIN-CS12", "qty": max(1, int(amount / 2400 / 3)), "rate": 2400})
				quote.valid_till = ahead(20)
				quote = save(quote, submit=True)
				if stage == "Lost":
					# Turned down: the quotation is lost, and ERPNext loses the deal with it.
					quote.declare_enquiry_lost([{"lost_reason": _lost_reason()}], [], "Went with a cheaper local supplier.")
		_convert("Lucy")


def _convert(first):
	"""A lead who became a customer, through ERPNext's own Create Customer."""
	from erpnext.crm.doctype.lead.mapper import make_customer

	lead = frappe.db.get_value("Lead", {"first_name": first})
	if lead and not frappe.db.exists("Customer", {"lead_name": lead}):
		customer = make_customer(lead)
		customer.customer_group = customer.customer_group or "Commercial"
		customer.territory = customer.territory or "Dubai"
		tag(customer.insert())


def _stages_to(stage):
	order = ("New", "Qualified", "Proposal", "Negotiation")
	if stage in order:
		return order[1 : order.index(stage) + 1]
	if stage == "On Hold":
		return ("Qualified", "On Hold")
	if stage == "Won":
		return ("Qualified", "Proposal", "Negotiation")
	return ("Qualified", "Proposal")


def _lost_reason():
	name = "Price"
	if not frappe.db.exists("Opportunity Lost Reason", name):
		tag(frappe.get_doc({"doctype": "Opportunity Lost Reason", "lost_reason": name}).insert())
	return name
