"""Which project a document Intake reads is for (one_intake/money.py).

A supplier's bill for the villa's glass says "Villa Al Barsha" somewhere: in
its reference, a line, the delivery address. Booked with no project, it was
missing from the project's **Cost** until somebody set it by hand. Intake now
asks `named` which open project the document names, and the bill it drafts,
and each of its lines, carry it.

A name only counts whole, ignoring case, and only one project may be named:
a bill naming two is left for a person, as one naming none is. A name inside
a longer one that is also named ("Villa" and "Villa Windows") is the longer.
"""

import re

import frappe

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
