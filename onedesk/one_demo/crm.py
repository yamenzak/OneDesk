"""The pipeline: leads from every source at every stage of being worked, deals
in every stage from New to Lost and in three currencies, the calls made on
them, the next step each is waiting on, and the quotations sent, accepted
and turned down."""

import frappe
from frappe.utils import add_days, add_to_date, date_diff, get_datetime, getdate, now_datetime, today

from onedesk.one_demo.base import ago, ahead, as_user, make, save, tag, wh

SALES = "omar@one.test"
ESTIMATOR = "samir@one.test"

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
			_answered_after(lead.name, hours=1 + len(first) % 6)

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
				if stage == "Won":
					_ordered(quote.name)
				if stage == "Lost":
					quote.declare_enquiry_lost([{"lost_reason": _lost_reason()}], [], "Went with a cheaper local supplier.")
		_convert("Lucy")
		_last_year()
		_marketing()
	_from_the_form()


FORM = (
	("Priya", "Nair", "Nair Interiors", "priya@nairinteriors.example", "We need a quote for frameless shower screens in six flats."),
	("Khalid", "Al Suwaidi", "Suwaidi Villas", "khalid@suwaidi.example", "Following up on the villa windows my brother asked about."),
)


def _from_the_form():
	"""Leads as the web form makes them: no owner, the Website source, and the
	second flagged as maybe the same as a lead we have."""
	for first, last, company, email, said in FORM:
		if frappe.db.exists("Lead", {"email_id": email}):
			continue
		frappe.flags.in_web_form = True
		try:
			lead = frappe.get_doc(
				{"doctype": "Lead", "first_name": first, "last_name": last, "company_name": company, "email_id": email}
			).insert(ignore_permissions=True)
		finally:
			frappe.flags.in_web_form = False
		tag(lead)
		lead.add_comment("Comment", said)


def _ordered(quotation):
	"""Won: the quotation ordered through ERPNext's Make Sales Order, which
	converts the deal, and One moves it to Won (one_crm/stages.py)."""
	from erpnext.selling.doctype.quotation.mapper import make_sales_order

	order = make_sales_order(quotation)
	order.delivery_date = ahead(30)
	order.set_warehouse = wh("Finished Goods")
	for row in order.items:
		row.delivery_date, row.warehouse = order.delivery_date, wh("Finished Goods")
	save(order, submit=True)


def _customer(name):
	"""A customer of last year's who is not among the masters, made as the
	deal that won them would have."""
	if not frappe.db.exists("Customer", name):
		make({"doctype": "Customer", "customer_name": name, "customer_group": "Commercial", "territory": "Dubai"})


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


LAST_YEAR = (
	("Bayview tower lobby doors", "Bayview Developments", SALES, "Existing Customer", 11, 40, "Won", 72000, None, "Paid"),
	("Palm Interiors office partitions", "Palm Interiors", ESTIMATOR, "Reference", 10, 25, "Lost", 28000, "Price", None),
	("Gulf Properties façade survey", "Gulf Properties REIT", SALES, "Exhibition", 9, 35, "Won", 54000, None, "Paid"),
	("Mansour & Sons warehouse glazing", "Mansour & Sons", SALES, "Existing Customer", 8, 30, "Lost", 120000, "Went With a Competitor", None),
	("Aisha Rahman villa shower screens", "Aisha Rahman", ESTIMATOR, "Walk In", 7, 14, "Won", 9500, None, "Paid"),
	("Marina Hotels spa partitions", "Marina Hotels Group", SALES, "Existing Customer", 6, 45, "Lost", 66000, "Timing", None),
	("Osei Builders site office windows", "Osei Builders", ESTIMATOR, "Cold Calling", 5, 20, "Won", 18000, None, "Billed"),
	("Bayview show apartment", "Bayview Developments", SALES, "Existing Customer", 4, 21, "Lost", 34000, "No Budget", None),
	("Tran Retail shopfront", "Tran Retail", SALES, "Website", 3, 18, "Won", 26000, None, "Ordered"),
	("Gulf Properties car park screens", "Gulf Properties REIT", ESTIMATOR, "Reference", 2, 28, "Lost", 47000, "Price", None),
)

LAST_YEARS_LEADS = (
	("Omar", "Haddad", "Haddad Contracting", "omar@haddad.example", "Exhibition", 11, "Do Not Contact", None),
	("Grace", "Lim", "Lim Dental", "grace@limdental.example", "Website", 10, "Do Not Contact", None),
	("Rashid", "Al Nuaimi", None, "rashid.nuaimi@example.com", "Walk In", 9, "Do Not Contact", None),
	("Mei", "Chen", "Chen Boutique", "mei@chenboutique.example", "Website", 8, "Do Not Contact", None),
	("Tom", "Barker", "Barker Homes", "tom@barkerhomes.example", "Advertisement", 7, "Do Not Contact", None),
	("Layal", "Saab", "Saab Architects", "layal@saabarch.example", "Reference", 6, "Do Not Contact", None),
	("Ivan", "Petrov", "Petrov Logistics", "ivan@petrovlog.example", "Cold Calling", 5, "Do Not Contact", None),
	("Hiba", "Mansoori", "Mansoori Clinics", "hiba@mansoori.example", "Website", 4, "Do Not Contact", None),
	("Sam", "Okafor", "Okafor Foods", "sam@okafor.example", "Campaign", 3, "Replied", 9),
	("Nadia", "Aziz", None, "nadia.aziz@example.com", "Website", 2, "Interested", None),
	("Peter", "Novak", "Novak Interiors", "peter@novak.example", "Exhibition", 1, "Lead", 4),
)


def _last_year():
	"""A year of selling before today: opportunities won and lost month by
	month, the won ones ordered, billed and paid as far as each got, and the
	leads that came in, each dated on its own day."""
	from erpnext.crm.doctype.opportunity.mapper import make_quotation
	from erpnext.selling.doctype.quotation.mapper import make_sales_order

	from onedesk.one_demo.base import dated
	from onedesk.one_demo.selling import _deliver, _pay

	for first, last, company, email, source, months, status, step in LAST_YEARS_LEADS:
		if frappe.db.exists("Lead", {"email_id": email}):
			continue
		lead = make(
			{
				"doctype": "Lead",
				"first_name": first,
				"last_name": last,
				"company_name": company,
				"email_id": email,
				"utm_source": source,
				"lead_owner": SALES,
				"territory": "Dubai",
				"one_next_step": "Call to see if the project is going ahead" if step else None,
				"one_next_on": add_to_date(now_datetime(), days=step, hours=1) if step else None,
			}
		)
		if status != "Lead":
			frappe.db.set_value("Lead", lead.name, "status", status, update_modified=False)
		_back("Lead", lead.name, ago(months * 30 + len(first)))

	for title, customer, owner, source, months, took, outcome, amount, reason, got in LAST_YEAR:
		if frappe.db.exists("Opportunity", {"title": title}):
			continue
		_customer(customer)
		opened = ago(months * 30)
		closed = add_days(opened, took)
		deal = make(
			{
				"doctype": "Opportunity",
				"title": title,
				"opportunity_from": "Customer",
				"party_name": customer,
				"opportunity_owner": owner,
				"utm_source": source,
				"sales_stage": "New",
				"transaction_date": opened,
				"currency": "AED",
				"opportunity_amount": amount,
				"expected_closing": closed,
			}
		)
		for passed in _stages_to(outcome):
			deal.reload()
			deal.sales_stage = passed
			deal.save()
		quote = make_quotation(deal.name)
		dated(quote, add_days(closed, -7), "transaction_date")
		quote.append("items", {"item_code": "SVC-INST", "qty": round(amount / 180), "rate": 180})
		quote.valid_till = add_days(closed, 20) if outcome == "Lost" else None
		quote = save(quote, submit=True)
		if outcome == "Lost":
			quote.declare_enquiry_lost([{"lost_reason": reason}], [], "")
		else:
			order = make_sales_order(quote.name)
			dated(order, closed, "transaction_date")
			order.delivery_date = add_days(closed, 30)
			for row in order.items:
				row.delivery_date = order.delivery_date
			order = save(order, submit=True)
			frappe.db.set_value("Quotation", quote.name, "valid_till", add_days(closed, 20), update_modified=False)
			_deliver(order, add_days(closed, 5))
			if got in ("Billed", "Paid"):
				invoice = _billed(order.name, add_days(closed, 7))
				if got == "Paid":
					_pay(invoice, add_days(closed, 30))
		_dated_moves(deal.name, opened, closed)


def _billed(order: str, date):
	from erpnext.selling.doctype.sales_order.mapper import make_sales_invoice

	from onedesk.one_demo.base import dated

	invoice = make_sales_invoice(order)
	dated(invoice, date)
	invoice.due_date = add_days(date, 30)
	for row in invoice.get("payment_schedule") or []:
		row.due_date = invoice.due_date
	return save(invoice, submit=True)


def _dated_moves(deal: str, opened, closed):
	"""Each stage move on the day it happened, spread from the day the
	opportunity came in to the day it closed; the opportunity itself moves
	with its date when the demo is settled (history.py)."""
	moves = frappe.get_all(
		"Milestone",
		filters={"reference_type": "Opportunity", "reference_name": deal},
		pluck="name",
		order_by="creation asc",
	)
	span = max(date_diff(closed, opened), 1)
	for i, name in enumerate(moves):
		day = add_days(opened, round(span * i / max(len(moves) - 1, 1)))
		_back("Milestone", name, day)


def _answered_after(lead: str, hours: int) -> None:
	"""The demo makes a lead and calls it in the same second; a real first
	call comes some hours later, and Lead Sources measures that wait."""
	made = frappe.db.get_value("Lead", lead, "creation")
	frappe.db.set_value("Lead", lead, "one_first_reply_at", add_to_date(made, hours=hours), update_modified=False)


def _back(doctype: str, name: str, day):
	"""A record made today, moved back to `day`, the time of day kept, with
	its versions."""
	when = f"{getdate(day)} {get_datetime(frappe.db.get_value(doctype, name, 'creation')).time()}"
	frappe.db.set_value(doctype, name, {"creation": when, "modified": when}, update_modified=False)
	frappe.db.sql(
		"update `tabVersion` set creation = %(w)s, modified = %(w)s where ref_doctype = %(t)s and docname = %(n)s",
		{"w": when, "t": doctype, "n": name},
	)


CAMPAIGNS = (
	("Dubai Design Week 2026", "Our stand at Design Week.", ("peter@novak.example", "omar@haddad.example")),
	("Hotel Refit Mailer", "Mail to hotel owners planning a refit.", ("marcus@webbhosp.example", "sam@okafor.example")),
)


def _marketing():
	"""Where leads came from and what is sent to them: two campaigns with the
	leads each brought in, an email group of hotel owners, a mail campaign to
	it, a prospect with its leads, and a meeting booked with a lead."""
	for name, about, emails in CAMPAIGNS:
		if not frappe.db.exists("Campaign", {"campaign_name": name}):
			make({"doctype": "Campaign", "campaign_name": name, "description": about})
		for email in emails:
			lead = frappe.db.get_value("Lead", {"email_id": email})
			if lead:
				frappe.db.set_value("Lead", lead, "utm_campaign", name, update_modified=False)
	if not frappe.db.exists("Email Template", "Hotel Refit"):
		with as_user("Administrator"):
			make(
				{
					"doctype": "Email Template",
					"name": "Hotel Refit",
					"subject": "Glazing for your refit",
					"response": "<p>We fit curtain walls, partitions and doors for hotels while they stay open.</p>",
				}
			)
	campaign = frappe.db.get_value("Campaign", {"campaign_name": "Hotel Refit Mailer"})
	planned = frappe.get_doc("Campaign", campaign)
	if not planned.campaign_schedules:
		for days in (0, 7):
			planned.append("campaign_schedules", {"send_after_days": days, "email_template": "Hotel Refit"})
		planned.save()
	if not frappe.db.exists("Email Group", "Hotel Owners"):
		make({"doctype": "Email Group", "title": "Hotel Owners"})
		for email in CAMPAIGNS[1][2]:
			make({"doctype": "Email Group Member", "email_group": "Hotel Owners", "email": email})
	if not frappe.db.exists("Email Campaign", {"campaign_name": campaign}):
		make(
			{
				"doctype": "Email Campaign",
				"campaign_name": campaign,
				"email_campaign_for": "Email Group",
				"recipient": "Hotel Owners",
				"start_date": today(),
				"sender": SALES,
			}
		)
	yusuf = frappe.db.get_value("Lead", {"email_id": "yusuf@erdem.example"})
	if yusuf and not frappe.db.exists("Prospect", "Erdem Towers"):
		make(
			{
				"doctype": "Prospect",
				"company_name": "Erdem Towers",
				"industry": frappe.db.get_value("Lead", yusuf, "industry"),
				"territory": "Dubai",
				"prospect_owner": SALES,
				"no_of_employees": "51-200",
				"leads": [{"lead": yusuf}],
			}
		)
	marcus = frappe.db.get_value("Lead", {"email_id": "marcus@webbhosp.example"})
	if marcus and not frappe.db.exists("Appointment", {"party": marcus}):
		make(
			{
				"doctype": "Appointment",
				"customer_name": "Marcus Webb",
				"customer_email": "marcus@webbhosp.example",
				"scheduled_time": f"{add_days(today(), 2)} 11:00:00",
				"status": "Open",
				"appointment_with": "Lead",
				"party": marcus,
				"customer_details": "Walk the lobby with Samir to measure for the curtain wall.",
			}
		)
