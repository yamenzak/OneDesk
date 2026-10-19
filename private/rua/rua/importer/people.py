"""Rua's people: employees under their branch and position, paid basic and
allowance from the month the import runs in, their leave as approved Leave
Applications, their papers as Employee Documents with One's types, and the
few letters the old app made final.

Payroll has no history: the old app kept no payslips worth booking, so pay
starts with the first payroll run in One. A leave the old app gave no type
is Annual Leave, allocated enough to cover what was taken.
"""

import frappe
from frappe.utils import add_days, cint, flt, get_first_day, getdate, today

from rua.importer.base import clean
from rua.setup import STRUCTURE

EMPLOYEE = "RUA Employee"
LEAVE = "RUA Leave"
DOCUMENT = "RUA Document"
LETTER = "RUA Letter"
HOLIDAYS = "Rua Holidays"
ANNUAL = "Annual Leave"
LEAVE_YEARS = ("2025-01-01", "2026-12-31")
PAPERS = (
	("emirates id", "Emirates ID"),
	("passpor", "Passport"),
	("medical", "Medical Fitness"),
	("daman", "Health Insurance"),
	("insurance", "Health Insurance"),
	("residence visa", "Residence Permit"),
	("visa", "Visa"),
	("labour card", "Labour Card"),
	("labor card", "Labour Card"),
	("work permit", "Work Permit"),
	("driving", "Driving Licence"),
)
COMPANY_PAPERS = (
	"licence",
	"license",
	"registration",
	"registartion",
	"certificate",
	"establishment",
	"esttablishment",
	"tawtheeq",
	"civil defence",
	"employees list",
	"stamp",
	"supplier card",
	"authorization",
)


def run(run_):
	holidays(run_)
	for old in run_.docs(EMPLOYEE):
		employee(run_, old)
	frappe.db.commit()
	leave(run_)
	for old in run_.docs(DOCUMENT):
		if old.get("source_doctype") == EMPLOYEE:
			paper(run_, old)
	letters(run_)


def holidays(run_):
	"""Sundays off, which is the one day the old roll-call never has."""
	if not frappe.db.exists("Holiday List", HOLIDAYS):
		doc = frappe.get_doc(
			{
				"doctype": "Holiday List",
				"holiday_list_name": HOLIDAYS,
				"from_date": "2023-01-01",
				"to_date": f"{getdate(today()).year}-12-31",
				"weekly_off": "Sunday",
			}
		)
		doc.get_weekly_off_dates()
		doc.insert(ignore_permissions=True)
	from onedesk.one import holidays as held

	if not held.assignments(run_.company):
		doc = frappe.new_doc("Holiday List Assignment")
		doc.update(
			{
				"holiday_list": HOLIDAYS,
				"applicable_for": "Company",
				"assigned_to": run_.company,
				"from_date": "2023-01-01",
			}
		)
		doc.insert(ignore_permissions=True)
		doc.submit()
	if not frappe.db.get_value("Company", run_.company, "default_holiday_list"):
		frappe.db.set_value("Company", run_.company, "default_holiday_list", HOLIDAYS)


def master(doctype, field, value):
	value = clean(value)
	if not value:
		return None
	if not frappe.db.exists(doctype, value):
		frappe.get_doc({"doctype": doctype, field: value}).insert(ignore_permissions=True)
	return value


def employee(run_, old):
	name = run_.made(EMPLOYEE, old["name"], "Employee")
	if not name:
		words = clean(old.get("employee_name")).split(" ", 1) or [old["name"]]
		doc = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": words[0] or old["name"],
				"last_name": words[1] if len(words) > 1 else None,
				"gender": old.get("gender") or "Male",
				"date_of_birth": old.get("date_of_birth"),
				"date_of_joining": old.get("joining_date") or str(getdate(old.get("creation"))),
				"status": "Active",
				"company": run_.company,
				"branch": master("Branch", "branch", old.get("branch")),
				"designation": master("Designation", "designation_name", old.get("position")),
				"cell_number": clean(old.get("phone")) or None,
				"personal_email": clean(old.get("email")).lower() or None,
				"holiday_list": HOLIDAYS,
			}
		)
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True, set_name=old["name"])
		name = run_.remember(EMPLOYEE, old["name"], "Employee", doc.name)
		if not old.get("date_of_birth") or not old.get("joining_date"):
			run_.note(
				"To Check", "Employee", name, "The old app had no date of birth or joining date: fill them in"
			)
	paid(run_, old, name)


def paid(run_, old, name):
	"""Basic as the assignment's base and the allowance as its variable,
	from the first day of this month or the day they joined."""
	if not flt(old.get("basic")) and not flt(old.get("allowance")):
		return
	if frappe.db.exists("Salary Structure Assignment", {"employee": name, "docstatus": 1}):
		return
	joined = frappe.db.get_value("Employee", name, "date_of_joining")
	start = max(getdate(get_first_day(today())), getdate(joined))
	doc = frappe.get_doc(
		{
			"doctype": "Salary Structure Assignment",
			"employee": name,
			"salary_structure": STRUCTURE,
			"company": run_.company,
			"from_date": start,
			"base": flt(old.get("basic")),
			"variable": flt(old.get("allowance")),
			"currency": run_.currency,
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()


def leave(run_):
	if not frappe.db.exists("Leave Type", ANNUAL):
		frappe.get_doc(
			{
				"doctype": "Leave Type",
				"leave_type_name": ANNUAL,
				"include_holiday": 1,
				"is_carry_forward": 1,
			}
		).insert(ignore_permissions=True)
	taken = {}
	for old in run_.docs(LEAVE):
		if old.get("leave_date") and old.get("return_date"):
			days = (getdate(old["return_date"]) - getdate(old["leave_date"])).days
			taken[old.get("employee")] = taken.get(old.get("employee"), 0) + max(days, 1)
	for old_employee, days in taken.items():
		name = run_.made(EMPLOYEE, old_employee, "Employee")
		if not name or frappe.db.exists(
			"Leave Allocation", {"employee": name, "leave_type": ANNUAL, "docstatus": 1}
		):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Leave Allocation",
				"employee": name,
				"leave_type": ANNUAL,
				"from_date": max(
					getdate(LEAVE_YEARS[0]), getdate(frappe.db.get_value("Employee", name, "date_of_joining"))
				),
				"to_date": LEAVE_YEARS[1],
				"new_leaves_allocated": max(60, days),
			}
		)
		doc.insert(ignore_permissions=True)
		doc.submit()
	for old in run_.docs(LEAVE):
		application(run_, old)


def application(run_, old):
	if run_.made(LEAVE, old["name"], "Leave Application"):
		return
	name = run_.made(EMPLOYEE, old.get("employee"), "Employee")
	if not name or not old.get("leave_date"):
		run_.note("Left Out", None, None, f"{old['name']}: a leave with no employee or no dates")
		return
	back = getdate(old.get("return_date") or old["leave_date"])
	ends = max(getdate(old["leave_date"]), add_days(back, -1))
	doc = frappe.get_doc(
		{
			"doctype": "Leave Application",
			"employee": name,
			"leave_type": ANNUAL,
			"from_date": old["leave_date"],
			"to_date": ends,
			"posting_date": old["leave_date"],
			"status": "Approved",
			"company": run_.company,
			"follow_via_email": 0,
		}
	)
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True, set_name=old["name"])
	doc.submit()
	run_.remember(LEAVE, old["name"], "Leave Application", doc.name)


def kind(said):
	said = clean(said).lower()
	for word, kind_ in PAPERS:
		if word in said:
			return kind_
	return None


def company_paper(said):
	said = clean(said).lower()
	return any(word in said for word in COMPANY_PAPERS) and kind(said) != "Driving Licence"


def paper(run_, old):
	"""An employee's paper as a row on them; one of the company's own (its
	licences, registrations) goes with its files in files.py; anything else
	is kept as a file on the employee there too."""
	if run_.made(DOCUMENT, old["name"], "Employee Document"):
		return
	name = run_.made(EMPLOYEE, old.get("for_docname"), "Employee")
	type_ = kind(old.get("document_name"))
	if not name or not type_ or company_paper(old.get("document_name")):
		return
	doc = frappe.get_doc("Employee", name)
	row = doc.append(
		"one_documents",
		{
			"document_type": type_,
			"number": clean(old.get("document_number")) or None,
			"issued_on": old.get("issue_date"),
			"expires_on": old.get("expiry_date"),
			"place_of_issue": clean(old.get("place_of_issue")) or None,
		},
	)
	doc.flags.ignore_mandatory = True
	doc.save(ignore_permissions=True)
	run_.remember(DOCUMENT, old["name"], "Employee Document", row.name)


def letters(run_):
	"""The letters the old app made final, each on the employee it was for.
	Drafts and templates were never sent and stay behind: new letters are
	HRMS's own records with One's prints."""
	people = {}
	for old in run_.docs(EMPLOYEE):
		made = run_.made(EMPLOYEE, old["name"], "Employee")
		if made:
			people[clean(old.get("employee_name")).lower()] = made
	left = 0
	for old in run_.docs(LETTER):
		if old.get("status") != "Final" or cint(old.get("is_template")):
			left += 1
			continue
		if run_.made(LETTER, old["name"], "Employee Letter"):
			continue
		who = whose(people, old)
		if not who:
			run_.note(
				"Left Out", None, None, f"{old['name']}: a final letter for nobody the import could find"
			)
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Employee Letter",
				"employee": who,
				"kind": "Other",
				"addressed_to": clean(old.get("to")) or None,
				"purpose": clean(old.get("subject") or old.get("title")) or None,
				"letter_date": old.get("date"),
				"body": old.get("content") or "",
			}
		)
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True, set_name=old["name"])
		doc.submit()
		run_.remember(LETTER, old["name"], "Employee Letter", doc.name)
	if left:
		run_.note("Left Out", None, None, f"{left} letters that were drafts or templates, never sent")


def whose(people, old):
	"""The employee a letter was for: its signee, or the one person named in
	it. Pure over the names given."""
	signee = clean(old.get("signee")).lower()
	if signee in people:
		return people[signee]
	words = set(signee.split())
	best = [name for full, name in people.items() if len(words & set(full.split())) >= 2]
	if len(best) == 1:
		return best[0]
	text = clean(frappe.utils.strip_html(old.get("content") or "")).lower()
	found = [name for full, name in people.items() if full and full in text]
	return found[0] if len(found) == 1 else None
