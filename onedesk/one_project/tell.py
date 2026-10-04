"""Telling people about a project (one_project/notifications.py).

**Added to a project.** ERPNext mails each new member its own "Project
Collaboration Invitation", in English, outside the hub. `members.invite`
marks that mail sent, and `added` tells them in ours: on the bell, and by
email or push as they chose, in their language.

**Made its manager.** Nobody was told. `added` tells the new manager too.

**At risk.** Health is somebody's judgement that a project is in trouble
before any figure says so. `health` tells its manager and members when it is
marked At Risk or Off Track; whoever marked it already knows.

**A retainer's month.** On the first of the month, `retainer_months` tells
whoever runs each open retainer that last month isn't invoiced, with its
hours against the allowance. And when a submitted timesheet takes this
month's hours past the allowance, `hours_used` tells them then, while there
is still time to say so to the customer.
"""

import frappe
from frappe.utils import add_months, flt, formatdate, get_first_day, get_fullname, getdate, nowdate

from onedesk.one import notify
from onedesk.one_project import kinds, retainer

#: The health worth telling people about.
WORSE = ("At Risk", "Off Track")


def changed(doc, method=None) -> None:
	"""Project on_update: who was added, who now runs it, and how it is going."""
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_import or frappe.flags.in_patch:
		return
	before = doc.get_doc_before_save()
	added(doc, before)
	health(doc, before)


def added(doc, before) -> None:
	was = {row.user for row in (before.get("users") or [])} if before else set()
	new = sorted({row.user for row in doc.get("users") or []} - was - {"Administrator", "Guest"})
	facts = _facts(doc)
	if new:
		notify.notify("Added to Project", new, record=("Project", doc.name), **facts)
	manager = doc.get("one_manager")
	if (
		manager
		and manager != (before.get("one_manager") if before else None)
		and manager not in ("Administrator", "Guest")
	):
		notify.notify("Made Project Manager", manager, record=("Project", doc.name), **facts)


def health(doc, before) -> None:
	said = doc.get("one_health")
	if said not in WORSE or not before or before.get("one_health") == said:
		return
	people = {row.user for row in doc.get("users") or []} | {doc.get("one_manager")}
	people = sorted(one for one in people if one and one not in ("Administrator", "Guest"))
	if people:
		notify.notify("Project Health", people, record=("Project", doc.name), health=said, **_facts(doc))


def _facts(doc) -> dict:
	"""Who did it, the project, and its customer and end date, each led by a
	dot so either may be left out: " · Mansour & Sons · 3 Nov 2026"."""
	return {
		"who": get_fullname(frappe.session.user),
		"project": doc.project_name,
		"customer": f" · {doc.customer}" if doc.get("customer") else "",
		"due": f" · {formatdate(doc.expected_end_date)}" if doc.get("expected_end_date") else "",
	}


def retainer_months() -> None:
	"""Monthly: each open retainer whose last month isn't invoiced, told to
	whoever runs it."""
	last = add_months(get_first_day(getdate(nowdate())), -1)
	for one in frappe.get_all(
		"Project",
		filters={"one_kind": kinds.RETAINER, "status": "Open", "one_monthly_fee": [">", 0]},
		fields=[
			"name",
			"project_name",
			"customer",
			"one_monthly_hours",
			"one_manager",
			"owner",
			"creation",
			"expected_start_date",
		],
	):
		if get_first_day(getdate(one.expected_start_date or one.creation)) > last:
			continue
		if retainer.invoiced(one.name, last):
			continue
		said = _retainer(one, retainer.logged(one.name, last))
		if said:
			notify.notify("Retainer Month to Invoice", **said)


def hours_used(doc, method=None) -> None:
	"""Timesheet on_submit: a retainer whose hours this month the timesheet
	takes past its allowance."""
	month = get_first_day(getdate(nowdate()))
	here: dict[str, float] = {}
	for row in doc.get("time_logs") or []:
		if row.project and row.from_time and get_first_day(getdate(row.from_time)) == month:
			here[row.project] = here.get(row.project, 0.0) + flt(row.hours)
	if not here:
		return
	for one in frappe.get_all(
		"Project",
		filters={"name": ["in", list(here)], "one_kind": kinds.RETAINER, "one_monthly_hours": [">", 0]},
		fields=["name", "project_name", "customer", "one_monthly_hours", "one_manager", "owner"],
	):
		hours = retainer.logged(one.name, month)
		if hours - here[one.name] < flt(one.one_monthly_hours) <= hours:
			said = _retainer(one, hours)
			if said:
				notify.notify("Retainer Hours Used", **said)


def _retainer(one, hours: float) -> dict | None:
	"""Who to tell about a retainer, and what: its manager, or whoever made it."""
	person = one.one_manager or one.owner
	if not person or person in ("Administrator", "Guest"):
		return None
	return {
		"users": person,
		"record": ("Project", one.name),
		"project": one.project_name,
		"hours": f"{flt(hours, 1):g}",
		"allowance": f"{flt(one.one_monthly_hours, 1):g}",
		"customer": f" · {one.customer}" if one.customer else "",
	}
