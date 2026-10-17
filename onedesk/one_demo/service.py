"""After the sale, in OneCRM's Support: issues in every state under a service
level agreement, a warranty claim on the pool fence and the visit that mended
it, a year of glazing maintenance for Bayview with its first visit done, and
the phones, promotions and items only some customers are offered."""

import frappe
from erpnext.maintenance.doctype.maintenance_schedule.maintenance_schedule import (
	make_maintenance_visit as visit_for_schedule,
)
from erpnext.support.doctype.warranty_claim.warranty_claim import make_maintenance_visit as visit_for_claim
from frappe.utils import add_days, add_months, getdate

from onedesk.one_demo.base import COMPANY, as_user, make, once, save, tag, today

SALES = "omar@one.test"
TECHNICIAN = "Tariq Haidar"

#: Each part, in order.
PARTS = (
	"_lists",
	"_agreement",
	"_issues",
	"_warranty",
	"_maintenance",
	"_phones",
	"_offers",
)


def run(password=None):
	for part in PARTS:
		globals()[part]()


def _lists():
	"""The kinds of issue, the technician who visits, and the sales desk."""
	with as_user("Administrator"):
		for kind, about in (
			("Fault", "Something installed is not working."),
			("Question", "A customer wants to know something."),
			("Complaint", "A customer is unhappy with the work or the service."),
		):
			once("Issue Type", {"name": kind}, {"__newname": kind, "description": about})
		once(
			"Sales Person",
			{"sales_person_name": TECHNICIAN},
			{
				"sales_person_name": TECHNICIAN,
				"parent_sales_person": "Sales Team",
				"employee": frappe.db.get_value("Employee", {"user_id": "tariq@one.test"}),
			},
		)
		once(
			"Employee Group",
			{"name": "Sales Desk"},
			{
				"employee_group_name": "Sales Desk",
				"employee_list": [{"employee": frappe.db.get_value("Employee", {"user_id": SALES})}],
			},
		)


def _agreement():
	"""Issues answered within four working hours, eight for a low one."""
	with as_user("Administrator"):
		settings = frappe.get_single("Support Settings")
		if not settings.track_service_level_agreement:
			settings.track_service_level_agreement = 1
			settings.save()
	with as_user(SALES):
		once(
			"Service Level Agreement",
			{"service_level": "Standard"},
			{
				"service_level": "Standard",
				"document_type": "Issue",
				"default_service_level_agreement": 1,
				"enabled": 1,
				"holiday_list": frappe.db.get_value("Company", COMPANY, "default_holiday_list")
				or frappe.db.get_value("Holiday List", {}),
				"default_priority": "Medium",
				"apply_sla_for_resolution": 1,
				"priorities": [
					{"priority": "High", "response_time": 2 * 3600, "resolution_time": 8 * 3600},
					{"priority": "Medium", "response_time": 4 * 3600, "resolution_time": 24 * 3600, "default_priority": 1},
					{"priority": "Low", "response_time": 8 * 3600, "resolution_time": 72 * 3600},
				],
				"support_and_resolution": [
					{"workday": day, "start_time": "08:00:00", "end_time": "17:00:00"}
					for day in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
				],
				"sla_fulfilled_on": [{"status": "Resolved"}, {"status": "Closed"}],
			},
		)


#: subject, customer, raised by, kind, priority, status, what they wrote
ISSUES = (
	("Sliding door hard to open", "Gulf Properties REIT", "maintenance@gulfreit.example", "Fault", "High", "Open", "The lobby's sliding door sticks halfway since the weekend."),
	("Classroom window handle broken", "Crescent Schools", "office@crescent.example", "Fault", "Medium", "Replied", "The handle on the second window in room 4 came off in a teacher's hand."),
	("Cleaning the double glazing", "Palm Interiors", "studio@palminteriors.example", "Question", "Low", "Resolved", "Which cleaner can we use on the new units without marking the coating?"),
	("Installers left packaging behind", "Bayview Developments", "site@bayview.example", "Complaint", "Medium", "Closed", "Crates and wrap were left on level 12 after the curtain wall went in."),
)


def _issues():
	with as_user(SALES):
		for subject, customer, raised_by, kind, priority, status, said in ISSUES:
			if frappe.db.exists("Issue", {"subject": subject}):
				continue
			issue = make(
				{
					"doctype": "Issue",
					"subject": subject,
					"customer": customer,
					"raised_by": raised_by,
					"issue_type": kind,
					"priority": priority,
					"company": COMPANY,
					"description": said,
				}
			)
			if status != "Open":
				issue.reload()
				issue.status = status
				if status in ("Resolved", "Closed"):
					issue.resolution_details = "Answered by phone and in writing."
				issue.save()


def _warranty():
	"""The loose pool fence panel, under its warranty, and the visit that
	fixed it."""
	with as_user(SALES):
		claim = once(
			"Warranty Claim",
			{"customer": "Marina Hotels Group", "item_code": "BAL-GL"},
			{
				"status": "Open",
				"complaint_date": add_days(today(), -3),
				"customer": "Marina Hotels Group",
				"item_code": "BAL-GL",
				"warranty_amc_status": "Under Warranty",
				"warranty_expiry_date": add_months(today(), 18),
				"complaint": "A glass panel of the pool fence moves when leaned on.",
				"complaint_raised_by": "Facilities manager",
				"company": COMPANY,
			},
		)
		if frappe.db.exists("Maintenance Visit Purpose", {"prevdoc_docname": claim.name}):
			return
		visit = visit_for_claim(claim.name)
		visit.update({"mntc_date": add_days(today(), -1), "maintenance_type": "Breakdown", "completion_status": "Fully Completed"})
		for row in visit.purposes:
			row.service_person = TECHNICIAN
			row.work_done = "Reset the panel's clamps and sealed the base again."
		visit.customer_feedback = "Solid again, thank you."
		save(visit, submit=True)


def _maintenance():
	"""A year of quarterly glazing checks on Bayview Tower, the first done on
	the day it was due."""
	with as_user(SALES):
		start = getdate(add_days(today(), -120))
		schedule = frappe.db.get_value("Maintenance Schedule", {"customer": "Bayview Developments", "docstatus": 1})
		if not schedule:
			# A schedule's visits point at its item rows, which have names
			# only once it is saved, so it is saved before they are drawn.
			doc = frappe.get_doc(
				{
					"doctype": "Maintenance Schedule",
					"customer": "Bayview Developments",
					"transaction_date": start,
					"company": COMPANY,
					"items": [
						{
							"item_code": "SVC-MAINT",
							"start_date": start,
							"end_date": add_days(add_months(start, 12), -1),
							"periodicity": "Quarterly",
							"no_of_visits": 4,
							"sales_person": TECHNICIAN,
						}
					],
				}
			).insert()
			doc.generate_schedule()
			doc.save()
			doc.submit()
			schedule = tag(doc).name
		if frappe.db.exists("Maintenance Visit", {"maintenance_schedule": schedule}):
			return
		first = frappe.get_all(
			"Maintenance Schedule Detail",
			filters={"parent": schedule},
			fields=["name", "item_code", "scheduled_date"],
			order_by="scheduled_date",
			limit=1,
		)[0]
		visit = visit_for_schedule(schedule, item_name=frappe.db.get_value("Item", first.item_code, "item_name"), s_id=first.name)
		visit.update({"mntc_date": first.scheduled_date, "completion_status": "Fully Completed"})
		for row in visit.purposes:
			row.service_person = TECHNICIAN
			row.work_done = "Checked the seals and drainage on every floor, and cleared two blocked weep holes."
		save(visit, submit=True)


def _phones():
	"""Who answers the sales line, when, and what callers hear."""
	with as_user(SALES):
		for kind in ("Enquiry", "Support", "Follow Up"):
			once("Telephony Call Type", {"name": kind}, {"call_type": kind})
		once(
			"Incoming Call Settings",
			{"name": "Sales Line"},
			{
				"__newname": "Sales Line",
				"call_routing": "Sequential",
				"call_handling_schedule": [
					{"day_of_week": day, "from_time": "08:00:00", "to_time": "17:00:00", "agent_group": "Sales Desk"}
					for day in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
				],
			},
		)
	# Whose settings they are is the administrator's to say (ERPNext keeps the
	# user at a level only the System Manager writes).
	with as_user("Administrator"):
		once(
			"Voice Call Settings",
			{"user": SALES},
			{
				"user": SALES,
				"call_receiving_device": "Computer",
				"greeting_message": "Thank you for calling Sahara Glass & Aluminium.",
				"agent_busy_message": "Everyone is on a call. Please hold.",
				"agent_unavailable_message": "We are closed. Please call again after 8 in the morning.",
			},
		)


def _offers():
	"""Hardware cheaper by the box, and Bayview offered the products alone."""
	with as_user(SALES):
		once(
			"Promotional Scheme",
			{"name": "Hardware by the Box"},
			{
				"__newname": "Hardware by the Box",
				"apply_on": "Item Group",
				"item_groups": [{"item_group": "Hardware"}],
				"selling": 1,
				"company": COMPANY,
				"valid_from": today(),
				"price_discount_slabs": [
					{"min_qty": 10, "max_qty": 49, "rate_or_discount": "Discount Percentage", "discount_percentage": 5, "rule_description": "Five per cent off ten or more"},
					{"min_qty": 50, "rate_or_discount": "Discount Percentage", "discount_percentage": 10, "rule_description": "Ten per cent off fifty or more"},
				],
			},
		)
		once(
			"Party Specific Item",
			{"party": "Bayview Developments"},
			{"party_type": "Customer", "party": "Bayview Developments", "restrict_based_on": "Item Group", "based_on_value": "Products"},
		)
