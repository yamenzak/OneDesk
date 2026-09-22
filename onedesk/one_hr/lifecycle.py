"""Two things that refuse the first onboarding a workspace submits.

**The holiday list.**

`Employee Boarding Controller.get_holiday_list` decides which days the boarding
tasks may not land on:

	if self.employee:
		return get_holiday_list_for_employee(self.employee, as_on=self.boarding_begins_on)
	else:
		if not self.holiday_list:
			frappe.throw(_("Please set the Holiday List."), frappe.MandatoryError)

An Employee Onboarding is for somebody who **is not an employee yet** — creating
them is what the record is for, and `make_employee` is what does it. So
`self.employee` is empty on every onboarding that has not been completed, and it
falls to `self.holiday_list`, a field on the document that nothing fills: not
the form script, not `validate`, not the template the activities came from. The
company's `default_holiday_list` is sitting right there, correctly set by the
setup wizard, and is never consulted.

Employee Separation takes the other branch and works, because the person leaving
is an employee and `get_holiday_list_for_employee` falls back to their company
on its own. So it is an asymmetry rather than a decision.

This is the fifth instance of the fault this audit keeps finding — after
`leave_balance`, the two benefit ceilings, the expense claim's cost centre and
the appointment letter's terms — and the worst of them, because the other four
were filled by a form script and this one is filled by nothing at all.

**The project it starts on the wrong day.** Past that, `on_submit` makes a
Project for the boarding and a Task per activity:

	"expected_start_date": self.date_of_joining
	if self.doctype == "Employee Onboarding"
	else self.resignation_letter_date,

while every task starts from `add_days(self.boarding_begins_on, activity.begin_on)`.
Onboarding *is* the work done before somebody joins — the contract, the laptop,
the induction — so `boarding_begins_on` is earlier than `date_of_joining` on any
realistic record, and ERPNext's own Task guard then refuses the first task:

	TASK-2026-00003's Expected Start Date cannot be before PROJ-0002's

The project is given the day the person arrives, which is when onboarding
*ends*. A boarding project starts no later than its first task, so that is what
`task` below settles, and only for a project a boarding document owns.
"""

import frappe
from frappe.utils import getdate

#: Where the answer already is. `Company.default_holiday_list` is what
#: `get_holiday_list_for_employee` itself falls back to for somebody who has one.
COMPANY_FIELD = "default_holiday_list"


def onboarding(doc, method=None) -> None:
	if doc.holiday_list or doc.employee or not doc.company:
		return
	doc.holiday_list = frappe.db.get_value("Company", doc.company, COMPANY_FIELD)


#: The two documents that own a boarding project. A Task in either one's project
#: is a boarding activity; a Task anywhere else is OneProject's and is left alone.
BOARDINGS = ("Employee Onboarding", "Employee Separation")


def task(doc, method=None) -> None:
	"""A boarding project starts no later than the first activity in it."""
	if not doc.project or not doc.exp_start_date:
		return
	starts = frappe.db.get_value("Project", doc.project, "expected_start_date")
	if not starts or getdate(doc.exp_start_date) >= getdate(starts):
		return
	if not any(frappe.db.exists(boarding, {"project": doc.project}) for boarding in BOARDINGS):
		return
	frappe.db.set_value("Project", doc.project, "expected_start_date", doc.exp_start_date)


def result(doc, method=None) -> None:
	"""How many people a Training Result covers.

	The list was `HR-TRR-2026-00001 · Working at Height, October` and the event
	twice, because `training_event` is both the title field and a list column.
	Who it is about is in `employees`, a child table, which cannot be a column.
	"""
	doc.one_people = len(doc.employees or [])
