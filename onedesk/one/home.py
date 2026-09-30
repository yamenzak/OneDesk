"""One's Home: what is waiting for the reader today, and for administrators,
what in the workspace needs them.

Home is frappe's `One` workspace, and every number on it is a frappe
`Number Card` of type Custom: a method here that counts for whoever is
reading, with where a click goes (`route`, `route_options`). Each counts
through `frappe.get_list` or the product's own reader, so it is exactly what
the reader may open. The administrators' part is a `Custom HTML Block`
limited to their role, filled by `attention`, and it hides itself when
nothing needs them.

Nothing here is kept: each number is asked when Home is drawn.
"""

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, flt, getdate, today

from onedesk.one import roles


def _card(value: int, route: list, route_options: dict | None = None) -> dict:
	return {
		"value": int(value or 0),
		"fieldtype": "Int",
		"route": route,
		"route_options": route_options or {},
	}


@frappe.whitelist()
@frappe.read_only()
def tasks_due(filters=None) -> dict:
	"""Tasks given to the reader that are due today or late (OneTask's My Tasks)."""
	from onedesk.one_task import mine

	groups = {one["key"]: len(one["tasks"]) for one in mine.tasks()}
	return _card(groups.get("overdue", 0) + groups.get("today", 0), ["my-tasks"])


@frappe.whitelist()
@frappe.read_only()
def meetings_today(filters=None) -> dict:
	"""What is on the reader's own calendar today (OneCalendar)."""
	from onedesk.one_calendar import events

	day = getdate(today())
	return _card(len(events.mine(day, day)), ["onecalendar"])


@frappe.whitelist()
@frappe.read_only()
def intake_waiting(filters=None) -> dict:
	"""Documents OneIntake read that wait for the reader."""
	from onedesk.one_intake import inbox

	return _card(inbox.counts()["waiting"], ["intake"], {"box": "waiting"})


@frappe.whitelist()
@frappe.read_only()
def suggestions_waiting(filters=None) -> dict:
	"""OneAI's cards the reader has not yet approved or refused."""
	count = frappe.db.count("AI Proposal", {"asked_by": frappe.session.user, "state": "Proposed"})
	return _card(count, ["List", "AI Proposal"], {"asked_by": frappe.session.user, "state": "Proposed"})


#: What waits on the reader's approval: the doctype, and its filters for them.
APPROVALS = (
	("Leave Application", lambda user: {"leave_approver": user, "status": "Open", "docstatus": 0}),
	("Expense Claim", lambda user: {"expense_approver": user, "approval_status": "Draft", "docstatus": 0}),
	# A step of an approval the workspace set (one/approvals.py) that one of the
	# reader's roles takes; frappe's own permission query keeps it to those.
	("Workflow Action", lambda user: {"status": "Open"}),
)


@frappe.whitelist()
@frappe.read_only()
def approvals_waiting(filters=None) -> dict:
	"""Leave and expense claims waiting on the reader as their approver, and
	approval steps their roles take. A click opens the list with the most."""
	user = frappe.session.user
	counted = []
	for doctype, wanted in APPROVALS:
		if not frappe.db.exists("DocType", doctype) or not frappe.has_permission(doctype, "read"):
			continue
		counted.append(
			(
				len(frappe.get_list(doctype, filters=wanted(user), pluck="name", limit=500)),
				doctype,
				wanted(user),
			)
		)
	if not counted:
		return _card(0, ["List", "Leave Application"])
	most = max(counted, key=lambda one: one[0])
	return _card(sum(one[0] for one in counted), ["List", most[1]], most[2])


# ------------------------------------------------------------------ administrators


@frappe.whitelist()
@frappe.read_only()
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
			"route": "/desk/settings?section=mail",
		}
		for email in broken
	]


def _account() -> list[dict]:
	from onedesk.one import account, settings

	held = frappe.get_single("Workspace Account")
	said = []
	for row in held.get("domains") or []:
		# A name still waiting for its DNS is not a fault yet; one Cloudflare
		# has a problem with is (one_admin/hosts.py, standing).
		if row.get("problem") and not row.get("given"):
			said.append(
				{
					"what": _("{0} is not working").format(row.domain),
					"detail": row.get("problem") or _("The workspace does not open at it yet."),
					"route": "/desk/workspace-settings?section=domains",
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
				"route": "/desk/workspace-settings?section=plan",
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
					"route": "/desk/workspace-settings?section=plan",
				}
			)
	seats = int(held.seats or 0)
	if seats and settings.seats_used() >= seats:
		said.append(
			{
				"what": _("Every seat is taken"),
				"detail": _("Nobody else can be invited until somebody is turned off or seats are added."),
				"route": "/desk/workspace-settings?section=plan",
			}
		)
	if flt(held.owing):
		said.append(
			{
				"what": _("A payment is overdue"),
				"detail": _("Pay it from Payment Method so the workspace stays open."),
				"route": "/desk/workspace-settings?section=plan",
			}
		)
	return said


#: How close to its last day the holiday list must be for Home to say so.
HOLIDAYS_WARN = 60


def _holidays() -> list[dict]:
	from onedesk.one import holidays

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
			"route": "/desk/workspace-settings?section=holidays",
		}
	]


# ------------------------------------------------------------------ OneAI


def my_day() -> dict:
	"""Everything Home counts for the reader, and for an administrator what
	needs them, with the first few of each where they are listed."""
	from onedesk.one_task import mine

	late = [
		{"task": one.subject, "due": str(one.due) if one.due else None, "project": one.project_title}
		for group in mine.tasks()
		if group["key"] in ("overdue", "today")
		for one in group["tasks"][:5]
	]
	return {
		"tasks_due_or_late": tasks_due()["value"],
		"first_tasks": late,
		"meetings_today": meetings_today()["value"],
		"documents_waiting_in_oneintake": intake_waiting()["value"],
		"oneai_suggestions_waiting": suggestions_waiting()["value"],
		"approvals_waiting": approvals_waiting()["value"],
		"workspace_needs_you": [{"what": one["what"], "detail": one["detail"]} for one in attention()],
	}
