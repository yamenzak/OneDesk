"""OneCRM's part of the integration suite (one_demo/check.py runs it):
leads, opportunities, quotations and Home as their people read them, and the
one ability."""

import frappe
from frappe.utils import add_days, add_to_date, flt, getdate, now_datetime, today

from onedesk.one import story as stories
from onedesk.one_demo.base import as_user
from onedesk.one_demo.checking import CENTS, check


@check
def onecrm_leads_and_deals_as_omar_works_them():
	"""Omar's pipeline figures and board, a deal's and a lead's overview, a
	call logged and a step done, a lead from the web form taken, a lead that
	is not the same person cleared and one that is merged, and what OneAI
	reads and suggests on the way."""
	from onedesk.one_crm import agent, board, capture, next, record, story

	deal = frappe.db.get_value("Opportunity", {"title": "Webb Hotel lobby curtain wall"})
	lead = frappe.db.get_value("Lead", {"email_id": "hamad@suwaidi.example"})
	priya = frappe.db.get_value("Lead", {"email_id": "priya@nairinteriors.example"})
	khalid = frappe.db.get_value("Lead", {"email_id": "khalid@suwaidi.example"})
	with as_user("omar@one.test"):
		figures = story.read()["cards"]
		assert figures["pipeline"]["value"] > figures["weighted"]["value"] > 0, figures
		assert figures["rate"]["value"] == 50.0, "two won and two lost in the last 90 days"
		stages = board.worth()["stages"]
		assert sum(one["value"] for one in stages.values()) >= figures["pipeline"]["value"], stages
		assert record.overview("Opportunity", deal)["next"]
		assert record.overview("Lead", lead)
		called = record.log_call("Opportunity", deal, "Outgoing", "Answered", 6, "Agreed to send the drawings by Thursday.")
		assert frappe.db.exists("Dynamic Link", {"parenttype": "Call Log", "parent": called, "link_name": deal})
		next.done("Opportunity", deal, "Review the drawings", str(add_days(today(), 3)) + " 10:00:00")
		assert frappe.db.get_value("Opportunity", deal, "one_next_step") == "Review the drawings"
		assert frappe.db.exists("Comment", {"reference_name": deal, "content": ["like", "%Ask for the drawings%"]})

		next.settle()
		assert not frappe.db.get_value("Lead", priya, "lead_owner"), "the web form gives a lead no owner, and an update leaves it so"
		capture.take("Lead", priya)
		assert frappe.db.get_value("Lead", priya, "lead_owner") == "omar@one.test"
		assert frappe.db.get_value("Lead", khalid, "one_duplicate_of") == lead
		capture.not_duplicate(khalid)
		assert not frappe.db.get_value("Lead", khalid, "one_duplicate_of")
		again = frappe.get_doc({"doctype": "Lead", "first_name": "Priya", "last_name": "Nair", "company_name": "Nair Interiors", "email_id": "p.nair@gmail.example"}).insert()
		assert again.one_duplicate_of == priya
		assert capture.merge(again.name, priya) == priya and not frappe.db.exists("Lead", again.name)

		assert agent.crm_facts("Opportunity", deal)["history"]
		assert agent.crm_facts("Lead", lead)["history"]
		assert agent.crm_facts("Customer", deal).get("error"), "only a deal or a lead"
		assert "quiet" in agent.gone_quiet("Opportunity") and "quiet" in agent.gone_quiet("Lead")
		lost = agent.why_we_lose()
		assert lost["won"] == 6 and lost["lost"] == 6, "a year of selling, and this month's"
		assert [one["reasons"] for one in lost["deals"] if one["deal"] == "Iqbal Clinics reception"] == [["Price"]], lost
		assert agent.add_lead("Hamad Al Suwaidi", "hamad@suwaidi.example").get("error"), "a lead we have is not suggested twice"
		assert agent.add_lead("Joanna Pike", "joanna@pike.example", "Pike Hotels").get("state") == "Proposed"
		assert agent.plan_next_step("Opportunity", deal, "Call to agree the price", str(add_days(today(), 2))).get("state") == "Proposed"
		assert agent.write_up_call("Lead", lead, "Wants the villa windows quoted by the end of the month.").get("state") == "Proposed"


@check
def onecrm_home_tells_how_selling_is_going():
	"""Omar's Home: a year of selling month by month, the funnel following
	opportunities to their quotations, orders, invoices and payments as
	ERPNext links them, the pipeline by stage adding up to its value, every
	lost one under a reason, Today listing only steps that are set and due,
	and every row of the directory opening something that exists."""
	from onedesk.one_crm import home, measure, story

	with as_user("omar@one.test"):
		told = story.read()
		said = home.read()
		cards = told["cards"]
		assert set(cards) == {"leads", "pipeline", "weighted", "won", "rate", "average"}, set(cards)
		assert len(cards["won"]["series"]) == stories.MONTHS and sum(1 for one in cards["won"]["series"] if one) >= 5, cards["won"]
		alive = sum(measure.value(one) for one in measure.deals(measure.alive()))
		assert abs(cards["pipeline"]["value"] - alive) < 0.01
		staged = sum(one["value"] for one in told["pipeline"]["stages"] if not one["held"])
		assert abs(staged - alive) < 0.01, (staged, alive)
		funnel = {one["step"]: one["count"] for one in told["sales"]["funnel"]}
		assert list(funnel) == list(story.FUNNEL), funnel
		assert funnel["Opportunity"] >= funnel["Quotation"] >= funnel["Sales Order"] >= funnel["Sales Invoice"] >= funnel["Paid"] >= 1, funnel
		lost = sum(1 for one in measure.closed().values() if one.outcome == "Lost" and one.on >= getdate(told["months"][0]))
		assert sum(one["count"] for one in told["pipeline"]["lost"]) >= lost, told["pipeline"]["lost"]
		due = said["needs"]["opportunities"]["rows"] + said["needs"]["leads"]["rows"]
		assert due and all(one["on"] for one in due), due
		for row in said["everything"]:
			kind = "DocType" if row["kind"] == "List" else row["kind"]
			assert frappe.db.exists(kind, row["target"]), row
		from onedesk.one_ai import chat, suggest

		offered = [one["label"] for one in suggest.for_page({"page": "onecrm"})]
		assert "Why are we losing opportunities?" in offered, offered
		assert "OneCRM's Home" in chat._page({"page": "onecrm"})


@check
def onecrm_an_opportunity_says_where_its_sale_went():
	"""An opportunity's head follows the sale past the deal: Bayview's paid
	in full and green with every step done, Osei's billed and owing late in
	red, Tran's ordered and not billed, Iqbal's lost with its reason, Harbour
	on hold with nothing under way; and a customer's page counts what it may
	still buy."""
	from onedesk.one import head
	from onedesk.one_crm import heads

	record = frappe.get_doc("Record Head", "Opportunity")

	def said(title):
		return head.said(frappe.get_doc("Opportunity", {"title": title}), record)

	with as_user("omar@one.test"):
		paid = said("Bayview tower lobby doors")
		assert paid["sentence"] == {"text": "Won, billed and paid in full.", "colour": "green"}, paid["sentence"]
		assert [one["state"] for one in paid["band"][0]["steps"]] == ["done"] * 5, paid["band"][0]
		owing = said("Osei Builders site office windows")
		assert owing["sentence"]["colour"] == "red" and owing["band"][0]["steps"][-1]["state"] == "late", owing
		ordered = said("Tran Retail shopfront")
		assert ordered["sentence"]["text"] == "Won and ordered; nothing is billed yet.", ordered["sentence"]
		lost = said("Iqbal Clinics reception")
		assert lost["sentence"] == {"text": "Lost: Price.", "colour": "gray"}, lost["sentence"]
		assert lost["band"][0]["steps"][0]["label"] == "Lead", lost["band"][0]
		held = said("Harbour Logistics depot doors")
		assert not any(one["state"] in ("now", "late") for one in held["band"][0]["steps"]), held["band"][0]
		crescent = heads.of_customer(frappe.get_doc("Customer", "Crescent Schools"))
		assert crescent and crescent["value"].startswith("1 open"), crescent


@check
def onecrm_campaigns_prospects_and_meetings():
	"""What Omar's Campaign and Selling groups list: each campaign counts the
	leads it brought in Campaign Efficiency, the mail campaign says where it
	is by its dates (a week's mailing made with the demo has ended since), the prospect holds its lead, and the meeting booked
	with Marcus is on Omar's own calendar, not everyone's."""
	from frappe.desk.query_report import run

	with as_user("omar@one.test"):
		rows = run("Campaign Efficiency", {"from_date": str(add_days(today(), -400)), "to_date": today()})["result"]
		counted = {row["utm_campaign"]: row["lead_count"] for row in rows}
		assert counted.get("Dubai Design Week 2026") == 2 and counted.get("Hotel Refit Mailer") == 2, rows
		mailing = frappe.get_all("Email Campaign", filters={"recipient": "Hotel Owners"}, fields=["status", "end_date"])
		ended = mailing and getdate(mailing[0].end_date) < getdate(today())
		assert mailing and mailing[0].status in (("Completed",) if ended else ("Scheduled", "In Progress")), mailing
		assert frappe.get_all("Prospect Lead", filters={"parent": "Erdem Towers"}, pluck="lead_name")
		meeting = frappe.get_all("Appointment", filters={"customer_email": "marcus@webbhosp.example"}, fields=["calendar_event"])
		assert meeting and meeting[0].calendar_event, meeting
		event = frappe.get_doc("Event", meeting[0].calendar_event)
		assert event.event_type == "Private" and event.owner == "omar@one.test", (event.event_type, event.owner)


@check
def onecrm_a_next_step_come_due_is_told_once():
	"""A step come due on Omar's opportunity reaches him as Next Step Due, in
	its words, once however often the scheduler looks."""
	from unittest.mock import patch

	from onedesk.one_crm import tell

	deal = frappe.db.get_value("Opportunity", {"title": "Nordlicht second showroom"})
	frappe.db.set_value("Opportunity", deal, {"one_next_step": "Send the workshop agenda", "one_next_on": add_to_date(now_datetime(), minutes=-1)})
	told = []
	with patch("onedesk.one.notify.notify", side_effect=lambda name, users, **said: told.append((name, users, said))):
		tell.due()
		tell.due()
	told = [one for one in told if one[2]["record"] == ("Opportunity", deal)]
	assert [(name, users) for name, users, _said in told] == [("Next Step Due", "omar@one.test")], told
	assert told[0][2]["step"] == "Send the workshop agenda" and told[0][2]["title"] == "Nordlicht second showroom", told


@check
def onecrm_what_was_quoted_is_ordered_delivered_and_invoiced_price_for_price():
	"""What a customer was quoted is what they ordered, were sent and were
	invoiced, price for price, and a window sent back is credited at what it
	sold for."""
	wrong = []
	for child, link, source in (
		("Sales Order Item", "quotation_item", "Quotation Item"),
		("Delivery Note Item", "so_detail", "Sales Order Item"),
		("Sales Invoice Item", "so_detail", "Sales Order Item"),
		("Sales Invoice Item", "dn_detail", "Delivery Note Item"),
	):
		for row in frappe.db.sql(
			f"""select row.parent, row.item_code, row.rate, src.rate as was from `tab{child}` row
			join `tab{source}` src on src.name = row.{link} where row.docstatus = 1 and row.{link} is not null""",
			as_dict=True,
		):
			if abs(flt(row.rate) - flt(row.was)) > CENTS:
				wrong.append((child, row.parent, row.item_code, row.rate, row.was))
	for credit in frappe.get_all("Sales Invoice", filters={"is_return": 1, "docstatus": 1}, fields=["name", "return_against"]):
		for row in frappe.get_doc("Sales Invoice", credit.name).items:
			sold = frappe.db.get_value("Sales Invoice Item", {"parent": credit.return_against, "item_code": row.item_code}, "rate")
			if abs(flt(row.rate) - flt(sold)) > CENTS:
				wrong.append(("credit", credit.name, row.item_code, row.rate, sold))
	assert not wrong, wrong[:5]


@check
def onecrm_merging_leads_is_an_ability():
	"""Merge Duplicate Leads starts with the Sales Manager alone: a Sales
	User's merge is refused before anything is read."""
	from onedesk.one_crm import capture

	assert capture.merges("omar@one.test") and not capture.merges("samir@one.test")
	with as_user("samir@one.test"):
		try:
			capture.merge("CRM-LEAD-ONE", "CRM-LEAD-TWO")
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("a Sales User merged two leads")


@check
def onecrm_riyadh_keeps_its_own_pipeline():
	"""Sahara Glass Saudi's deal and quotation, in riyals, stay out of
	Sahara's board, figures and Home; with Riyadh as Omar's company the board
	is Riyadh's, in riyals; and Omar, limited to Sahara, never lists them."""
	from erpnext import get_company_currency

	from onedesk.one_crm import board, story
	from onedesk.one_demo.base import COMPANY
	from onedesk.one_demo.branch import BRANCH

	deal = frappe.db.get_value("Opportunity", {"company": BRANCH, "title": "Al Olaya Towers Phase 2"})
	quote = frappe.db.get_value("Quotation", {"company": BRANCH, "docstatus": 1})
	assert deal and quote, "the demo's second company has its pipeline (one_demo/branch.py)"
	with as_user("omar@one.test"):
		ours = board.worth()
		assert ours["currency"] == get_company_currency(COMPANY)
		sahara = sum(flt(one.base_opportunity_amount) or flt(one.base_total) for one in frappe.get_all("Opportunity", filters={"company": COMPANY}, fields=["base_opportunity_amount", "base_total"]))
		assert abs(sum(one["value"] for one in ours["stages"].values()) - sahara) < CENTS, "the board added another company's deals"
		assert story.read()["currency"] == get_company_currency(COMPANY)
	frappe.defaults.set_user_default("company", BRANCH, "omar@one.test")
	try:
		with as_user("omar@one.test"):
			theirs = board.worth()
			assert theirs["currency"] == get_company_currency(BRANCH) and theirs["stages"].get("Proposal", {}).get("value", 0) >= 69000, theirs
			assert story.read()["currency"] == get_company_currency(BRANCH)
	finally:
		frappe.defaults.set_user_default("company", COMPANY, "omar@one.test")
	from onedesk.one_crm import stages

	with as_user("omar@one.test"):
		won = frappe.get_doc("Opportunity", deal)
		won.sales_stage = stages.first("Won")
		try:
			won.save()
			raise AssertionError("a deal with no order was won")
		except frappe.ValidationError as e:
			assert "order" in str(e), e
		frappe.get_doc({"doctype": "User Permission", "user": "omar@one.test", "allow": "Company", "for_value": COMPANY}).insert(ignore_permissions=True)
	with as_user("omar@one.test"):
		assert deal not in frappe.get_list("Opportunity", pluck="name", limit_page_length=0)
		assert quote not in frappe.get_list("Quotation", pluck="name", limit_page_length=0)


@check
def onecrm_an_issue_late_for_its_first_answer_is_told():
	"""An open issue whose first answer was due an hour ago and has not come
	is told, once, to the support team when nobody has it."""
	from unittest.mock import patch

	from frappe.utils import add_to_date, now_datetime

	from onedesk.one_crm import tell

	issue = frappe.db.get_value("Issue", {"status": "Open", "first_responded_on": ["is", "not set"]})
	assert issue, "the demo has an open issue nobody answered"
	frappe.db.set_value("Issue", issue, {"response_by": add_to_date(now_datetime(), hours=-1), "_assign": None}, update_modified=False)
	frappe.cache.delete_keys("one_crm:answer_late:")
	told = []
	with patch("onedesk.one.notify.notify", side_effect=lambda name, users, **said: told.append((name, users, said))):
		tell.answers_late()
		tell.answers_late()
	late = [one for one in told if one[0] == "Issue Answer Late"]
	assert len(late) == 1 and set(late[0][1]) == set(tell._support()), told


@check
def onecrm_oneai_lists_the_quotations_still_waiting():
	"""OneAI's quotes_waiting lists the reader's company's open and replied
	quotations, soonest last day first."""
	from onedesk.one_crm import agent

	with as_user("omar@one.test"):
		said = agent.quotes_waiting()["quotations"]
	assert said and all(one["status"] in ("Open", "Replied") for one in said), said
	days = [one["days_left"] for one in said if one["days_left"] is not None]
	assert days == sorted(days), days
