"""Two things that refuse the first onboarding a workspace submits."""

import frappe
from frappe import _
from frappe.utils import getdate

COMPANY_FIELD = "default_holiday_list"


def onboarding(doc, method=None) -> None:
	if doc.holiday_list or doc.employee or not doc.company:
		return
	doc.holiday_list = frappe.db.get_value("Company", doc.company, COMPANY_FIELD)


BOARDINGS = ("Employee Onboarding", "Employee Separation")


BOARDING = "Employee Boarding"


def typed(doc, method=None) -> None:
	"""Employee Onboarding and Employee Separation on_update: the project HRMS
	made for the checklist is typed as a boarding, and named for whose it is."""
	if doc.get("project") and not frappe.db.get_value("Project", doc.project, "project_type"):
		_boarding()
		frappe.db.set_value("Project", doc.project, "project_type", BOARDING, update_modified=False)
	if doc.get("project"):
		_named(doc.doctype, doc.project, doc.employee_name)


def settle_boardings(*_args) -> None:
	"""The boarding projects made before they were typed or named."""
	for boarding in BOARDINGS:
		for one in frappe.get_all(boarding, filters={"project": ["is", "set"]}, fields=["project", "employee_name"]):
			if not frappe.db.get_value("Project", one.project, "project_type"):
				_boarding()
				frappe.db.set_value("Project", one.project, "project_type", BOARDING, update_modified=False)
			_named(boarding, one.project, one.employee_name)


def _named(boarding: str, project: str, person: str | None) -> None:
	"""HRMS names the project "Employee Onboarding : " and the applicant's
	email, which a task's Project column then says. While it still has their
	name it is "Onboarding: Feras Odeh"; one somebody renamed is left."""
	title = frappe.db.get_value("Project", project, "project_name") or ""
	if not person or not title.startswith(f"{_(boarding)} : "):
		return
	said = _("Onboarding: {0}") if boarding == "Employee Onboarding" else _("Exit: {0}")
	frappe.db.set_value("Project", project, "project_name", said.format(person), update_modified=False)


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
