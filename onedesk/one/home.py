"""One's Home: what only One sees across the apps. The approvals waiting on
the reader, the announcements, what is new, and for administrators the
workspace at a glance and what in it needs them.

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
	"""What OneAI and the agents did for the reader that waits on them."""
	from onedesk.one_ai.reading import act

	return act.waiting()


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
	"""Home, for whoever is reading: what only One sees across the apps. The
	approvals waiting on them from every app, the announcements running,
	the files someone has asked them for (OneCloud's file requests), the
	apps with a version they have not seen, and for an administrator
	the workspace at a glance and what in it needs them. A task, a meeting
	or a document is its own app's, on that app's home."""
	approvals = _approvals()
	return {
		"approvals": [{**one, "since": str(one["since"])} for one in approvals[:LISTED]],
		"waiting": len(approvals),
		"announcements": _announcements(),
		"asked": _asked(),
		"news": news(),
		"glance": glance(),
		"needs": attention(),
		"administers": roles.administers(),
	}


def _asked() -> list[dict]:
	from onedesk.one_hr import own
	from onedesk.one_cloud import file_requests

	return file_requests.asked_of(own.addresses_of())


def _announcements() -> list[dict]:
	from onedesk.one import announcements

	return announcements._running()


def news() -> list[dict]:
	"""The apps the reader has whose newest version they have not opened,
	each with that version's title (UpdateCenter); an app turned off or out
	of the reader's reach is not theirs (versions.for_boot marks it off)."""
	from onedesk.one import ready, versions

	said = []
	for module, one in versions.for_boot().items():
		if not one["unseen"] or one.get("off"):
			continue
		newest = next(iter(ready.shown(module)), None)
		said.append(
			{
				"module": module,
				"version": one["version"],
				"title": _(newest["title"]) if newest and newest.get("title") else "",
			}
		)
	return said


def glance() -> list[dict]:
	"""The workspace in four numbers, for an administrator: people against
	seats, the apps turned on, storage against its limit and OneAI's credits
	left. Read from the workspace's copy of its account. Empty for anybody
	else."""
	if not roles.administers():
		return []
	from onedesk.one import apps, people
	from onedesk.account_center.heads import size

	held = frappe.get_single("Workspace Account")
	offered = [one for one in apps.offered() if not one.get("needs")]
	seats = int(held.seats or 0)
	used = people.seats_used()
	said = [
		{
			"key": "people",
			"title": _("People"),
			"value": str(used),
			"note": _("of {0} seats").format(seats) if seats else "",
			"bar": min(100, round(100 * used / seats)) if seats else None,
			"route": "/desk/one?center=account&at=people",
		},
		{
			"key": "apps",
			"title": _("Apps"),
			"value": str(sum(1 for one in offered if one["on"])),
			"note": _("of {0}").format(len(offered)),
		},
	]
	if flt(held.storage_limit):
		said.append(
			{
				"key": "storage",
				"title": _("Storage"),
				"value": size(held.storage_bytes),
				"note": _("of {0}").format(size(held.storage_limit)),
				"bar": min(100, round(100 * flt(held.storage_bytes) / flt(held.storage_limit))),
				"route": "/desk/one?center=account&at=plan",
			}
		)
	if apps.ai_on():
		said.append(
			{
				"key": "credits",
				"title": _("Credits"),
				"value": frappe.utils.fmt_money(flt(held.credits_balance), precision=0).strip(),
				"note": _("{0} used a month").format(frappe.utils.fmt_money(flt(held.credits_month), precision=0).strip())
				if flt(held.credits_month)
				else "",
				"route": "/desk/one?center=account&at=plan",
			}
		)
	return said


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
				"what": _("Credits are running low"),
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
	"""The reader's day across the apps (OneAI's my_day): tasks due or late,
	meetings, documents and suggestions waiting, approvals, and for an
	administrator what needs them, with the first few tasks."""
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
