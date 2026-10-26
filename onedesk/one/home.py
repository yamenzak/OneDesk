"""One's Home: what is waiting for the reader today, and for administrators,
what in the workspace needs them.

Every number on it is counted here for whoever is reading, when Home is
drawn, and never kept. The page is the island `onedesk.one_home`
(frontend/src/one/Home.vue) on the page `one`.
"""

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, flt, getdate, today

from onedesk.one import roles

LISTED = 5


def _tasks() -> list:
	from onedesk.one_task import mine

	return [one for group in mine.tasks() if group["key"] in ("overdue", "today") for one in group["tasks"]]


def tasks_due() -> int:
	"""Tasks given to the reader that are due today or late (OneTask's My Tasks)."""
	return len(_tasks())


def _meetings() -> list[dict]:
	from onedesk.one_calendar import events

	day = getdate(today())
	return sorted(events.mine(day, day), key=lambda one: (not one["all_day"], one["start"]))


def meetings_today() -> int:
	"""What is on the reader's own calendar today (OneCalendar)."""
	return len(_meetings())


def intake_waiting() -> int:
	"""Documents OneAI read that wait for the reader."""
	from onedesk.one_ai.reading import inbox

	return inbox.counts()["waiting"]


def suggestions_waiting() -> int:
	"""OneAI's cards the reader has not yet approved or refused."""
	return frappe.db.count("AI Proposal", {"asked_by": frappe.session.user, "state": "Proposed"})


APPROVALS = (
	(
		"Leave Application",
		lambda user: {"leave_approver": user, "status": "Open", "docstatus": 0},
		"employee_name",
	),
	(
		"Expense Claim",
		lambda user: {"expense_approver": user, "approval_status": "Draft", "docstatus": 0},
		"employee_name",
	),
	("Workflow Action", lambda user: {"status": "Open"}, "reference_name"),
)


def _approvals() -> list[dict]:
	"""Leave and expense claims waiting on the reader as their approver, and
	approval steps their roles take, oldest first."""
	user = frappe.session.user
	found = []
	for doctype, wanted, title in APPROVALS:
		if not frappe.db.exists("DocType", doctype) or not frappe.has_permission(doctype, "read"):
			continue
		for one in frappe.get_list(
			doctype, filters=wanted(user), fields=["name", "creation", f"{title} as title"], limit=500
		):
			found.append(
				{"doctype": doctype, "name": one.name, "title": one.title or one.name, "since": one.creation}
			)
	return sorted(found, key=lambda one: one["since"])


def approvals_waiting() -> int:
	return len(_approvals())


@frappe.whitelist(methods=["GET"])
@frappe.read_only()
def read() -> dict:
	"""Home, for whoever is reading: how much waits for them in each app they
	have, the first few of each, and for an administrator what in the
	workspace needs them. An app the workspace turned off is left out."""
	from onedesk.one import apps

	off = set(apps.hidden())
	tasks = _tasks()
	meetings = _meetings()
	approvals = _approvals()
	counts = {
		"tasks": None if "OneTask" in off else len(tasks),
		"meetings": None if "OneCalendar" in off else len(meetings),
		"documents": intake_waiting() if apps.intake_on() else None,
		"suggestions": suggestions_waiting() if apps.ai_on() else None,
		"approvals": len(approvals),
	}
	return {
		"counts": {key: value for key, value in counts.items() if value is not None},
		"tasks": [
			{
				"name": one.name,
				"subject": one.subject,
				"due": str(one.due) if one.due else None,
				"project": one.project_title,
			}
			for one in tasks[:LISTED]
		]
		if counts["tasks"] is not None
		else [],
		"meetings": [
			{
				"doctype": one["doctype"],
				"name": one["name"],
				"title": one["title"],
				"start": str(one["start"]),
				"end": str(one["end"]) if one["end"] else None,
				"all_day": one["all_day"],
			}
			for one in meetings[:LISTED]
		]
		if counts["meetings"] is not None
		else [],
		"approvals": [{**one, "since": str(one["since"])} for one in approvals[:LISTED]],
		"needs": attention(),
		"administers": roles.administers(),
	}


def attention() -> list[dict]:
	"""What in the workspace needs an administrator now, each with where to
	fix it. Empty for anybody else, and when nothing does. Read from what the
	workspace already keeps: its copy of the account (`Workspace Account`),
	its mailboxes and its holiday list; nothing is asked of the admin site."""
	if not roles.administers():
		return []
	said = []
	said += _mailboxes()
	said += _account()
	said += _holidays()
	return said


def _mailboxes() -> list[dict]:
	broken = frappe.get_all("Email Account", filters={"one_error": ["is", "set"]}, pluck="email_id")
	return [
		{
			"what": _("{0} is not connecting").format(email),
			"detail": _("New mail is not arriving. Reconnect it with its password."),
			"route": "/desk/onemail?settings=mailboxes",
		}
		for email in broken
	]


def _account() -> list[dict]:
	from onedesk.one import account, people

	held = frappe.get_single("Workspace Account")
	said = []
	for row in held.get("domains") or []:
		if row.get("problem") and not row.get("given"):
			said.append(
				{
					"what": _("{0} is not working").format(row.domain),
					"detail": row.get("problem") or _("The workspace does not open at it yet."),
					"route": "/desk/one?center=account&at=domains",
				}
			)
	month = flt(held.credits_month)
	if month and flt(held.credits_balance) < month * account.LOW:
		said.append(
			{
				"what": _("OneAI credits are running low"),
				"detail": _("{0} left, about three days at the rate the workspace uses them.").format(
					frappe.utils.fmt_money(flt(held.credits_balance), precision=0).strip()
				),
				"route": "/desk/one?center=account&at=plan",
			}
		)
	for used, limit, label in (
		(held.storage_bytes, held.storage_limit, _("Storage is nearly full")),
		(held.database_bytes, held.database_limit, _("The database is nearly full")),
	):
		if flt(limit) and flt(used) >= flt(limit) * account.NEARLY_FULL:
			said.append(
				{
					"what": label,
					"detail": _("{0}% used.").format(int(flt(used) / flt(limit) * 100)),
					"route": "/desk/one?center=account&at=plan",
				}
			)
	seats = int(held.seats or 0)
	if seats and people.seats_used() >= seats:
		said.append(
			{
				"what": _("All seats are in use"),
				"detail": _("Disable someone or add seats to invite more people."),
				"route": "/desk/one?center=account&at=plan",
			}
		)
	if flt(held.owing):
		said.append(
			{
				"what": _("A payment is overdue"),
				"detail": _("Pay it from Payment Method so the workspace stays open."),
				"route": "/desk/one?center=account&at=plan",
			}
		)
	return said


HOLIDAYS_WARN = 60


def _holidays() -> list[dict]:
	from onedesk.one_hr import holidays

	now = holidays.in_force()
	if not now or holidays.after(now):
		return []
	end = frappe.db.get_value("Holiday List", now, "to_date")
	left = date_diff(end, today())
	if left > HOLIDAYS_WARN:
		return []
	return [
		{
			"what": _("The holiday list ends on {0}").format(frappe.utils.formatdate(end)),
			"detail": _("From {0} every day counts as a working day. Make next year's list.").format(
				frappe.utils.formatdate(add_days(end, 1))
			),
			"route": "/desk/one?center=settings&module=OneHR&at=holidays",
		}
	]


def my_day() -> dict:
	"""Everything Home counts for the reader, and for an administrator what
	needs them, with the first few of each where they are listed."""
	tasks = _tasks()
	late = [
		{"task": one.subject, "due": str(one.due) if one.due else None, "project": one.project_title}
		for one in tasks[:LISTED]
	]
	return {
		"tasks_due_or_late": len(tasks),
		"first_tasks": late,
		"meetings_today": meetings_today(),
		"documents_waiting_in_oneai": intake_waiting(),
		"oneai_suggestions_waiting": suggestions_waiting(),
		"approvals_waiting": approvals_waiting(),
		"workspace_needs_you": [{"what": one["what"], "detail": one["detail"]} for one in attention()],
	}
