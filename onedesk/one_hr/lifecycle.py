"""Two things that refuse the first onboarding a workspace submits."""

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


#: The Project Type of a boarding project. OneProject's Projects and Project
#: Tree leave it out: somebody's first week is not a piece of client work.
BOARDING = "Employee Boarding"


def typed(doc, method=None) -> None:
	"""Employee Onboarding and Employee Separation on_update: the project HRMS
	made for the checklist is typed as a boarding."""
	if doc.get("project") and not frappe.db.get_value("Project", doc.project, "project_type"):
		_boarding()
		frappe.db.set_value("Project", doc.project, "project_type", BOARDING, update_modified=False)


def settle_boardings(*_args) -> None:
	"""The boarding projects made before they were typed."""
	for boarding in BOARDINGS:
		for project in frappe.get_all(boarding, filters={"project": ["is", "set"]}, pluck="project"):
			if not frappe.db.get_value("Project", project, "project_type"):
				_boarding()
				frappe.db.set_value("Project", project, "project_type", BOARDING, update_modified=False)


def _boarding() -> None:
	if not frappe.db.exists("Project Type", BOARDING):
		frappe.get_doc({"doctype": "Project Type", "project_type": BOARDING}).insert(ignore_permissions=True)


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
