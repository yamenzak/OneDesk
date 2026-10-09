"""Which project a document Intake reads is for (one_intake/money.py), and
whether a task about it fits in it (one_intake/plans.py)."""

import re

import frappe
from frappe.utils import getdate

#: Shorter names say too little to go by ("Web", "HQ").
SHORTEST = 5

#: Not a project here: an employee's onboarding or exit checklist.
HR = "Employee Boarding"


def named(text: str) -> str | None:
	"""The one open project whose name the text gives, if exactly one."""
	if not text:
		return None
	projects = frappe.get_all(
		"Project",
		filters=[["status", "=", "Open"], ["project_type", "!=", HR]],
		fields=["name", "project_name"],
	)
	return pick(text, [(one.name, one.project_name) for one in projects])


def pick(text: str, projects: list[tuple[str, str]]) -> str | None:
	"""The project named in `text`, of (name, title) pairs; None for none or
	more than one. Pure."""
	found = [
		(name, title)
		for name, title in projects
		if title
		and len(title.strip()) >= SHORTEST
		and re.search(rf"(?<!\w){re.escape(title.strip())}(?!\w)", text, re.IGNORECASE)
	]
	# A name inside a longer one that is named too is the longer.
	found = [
		one
		for one in found
		if not any(other is not one and one[1].strip().lower() in other[1].strip().lower() for other in found)
	]
	names = {name for name, _title in found}
	return names.pop() if len(names) == 1 else None


def task_in(project: str | None, day) -> str | None:
	"""The project a task Intake makes about a document goes in: the one the
	document names, where the task's day is inside it, as ERPNext asks of any
	task in a project."""
	if not project or not day:
		return project
	ends = frappe.db.get_value("Project", project, "expected_end_date")
	return project if not ends or getdate(day) <= getdate(ends) else None
