"""A project asks its team how it is going, and keeps what they say.

ERPNext has the parts: **Collect Progress** on a project, how often and when,
the subject and message of the ask; a **Project Update** for each ask; the
answers as rows on it; and a summary of yesterday's answers mailed to the team
(`send_project_status_email_to_users`). The asking and the collecting did not
work, and this replaces those two:

- **It only asked by email, and only where there was mail.** With no outgoing
  account the ask raised, rolled back its Project Update, and nothing was
  asked. `ask` makes the Project Update, tells each member in One (a
  notification that opens the project), and mails them as well where mail can
  go.
- **It asked too often.** Hourly asked every hour of the day, its window
  tested with `or`; Twice Daily asked in two hours running. `due` asks once a
  day, twice at the two times, or once on the day of the week. Hourly is taken
  off the choices: a status note every hour is not a status note.
- **An answer could only be an email reply**, and was read back every hour and
  added again each time, and only on the day it was asked. `post` is **Post
  Update** on the project's page, which answers today's ask or, with none,
  makes one; `answered` takes an email reply once, when it arrives, whatever
  the day.
- **The answers were kept out of sight** on the Project Update. `timeline`
  puts each one in the project's activity, under who wrote it.

The daily summary is still ERPNext's, sent only where mail can go (`sum_up`).
"""

from datetime import time

import frappe
from frappe import _
from frappe.utils import escape_html, get_time, now_datetime, nowdate, nowtime
from frappe.utils.html_utils import sanitize_html

#: ERPNext's jobs this replaces: the three askers and the collector, and the
#: summary, which sum_up now runs where mail can go.
REPLACED = (
	"erpnext.projects.doctype.project.project.hourly_reminder",
	"erpnext.projects.doctype.project.project.project_status_update_reminder",
	"erpnext.projects.doctype.project.project.collect_project_status",
	"erpnext.projects.doctype.project.project.send_project_status_email_to_users",
)

#: When an ask with no time set goes out.
MORNING = time(9, 0)

FIELDS = ("frequency", "first_email", "second_email", "daily_time_to_send", "day_to_send", "weekly_time_to_send")


def settle(*_args) -> None:
	"""Stop ERPNext's own asking and collecting. A stopped job survives migrate."""
	for method in REPLACED:
		job = frappe.db.exists("Scheduled Job Type", {"method": method})
		if job and not frappe.db.get_value("Scheduled Job Type", job, "stopped"):
			frappe.db.set_value("Scheduled Job Type", job, "stopped", 1)


def ask() -> None:
	"""Hourly: ask every project that is due."""
	now = now_datetime()
	for project in frappe.get_all(
		"Project", filters={"collect_progress": 1, "status": "Open"}, fields=["name", *FIELDS]
	):
		asked = frappe.db.count("Project Update", {"project": project.name, "date": now.date()})
		if due(project, now.time(), now.strftime("%A"), asked):
			_ask(project.name)


def due(settings: dict, now: time, weekday: str, asked: int) -> bool:
	"""Whether a project's team is to be asked now, given how many times it
	was asked today. Pure."""

	def at(field):
		value = settings.get(field)
		return get_time(value) if value else MORNING

	frequency = settings.get("frequency")
	if frequency == "Daily":
		return not asked and now >= at("daily_time_to_send")
	if frequency == "Twice Daily":
		return (not asked and now >= at("first_email")) or (asked == 1 and now >= at("second_email"))
	if frequency == "Weekly":
		return not asked and weekday == settings.get("day_to_send") and now >= at("weekly_time_to_send")
	return False


def _ask(project: str) -> None:
	from erpnext.setup.doctype.holiday_list.holiday_list import is_holiday

	doc = frappe.get_doc("Project", project)
	people = [row.user for row in doc.users if row.user and frappe.db.get_value("User", row.user, "enabled")]
	if not people or is_holiday(doc.holiday_list):
		return
	update = frappe.get_doc(
		{"doctype": "Project Update", "project": project, "sent": 0, "date": nowdate(), "time": nowtime()}
	).insert(ignore_permissions=True)
	subject = doc.subject or _("How is {0} going?").format(doc.project_name)
	for user in people:
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": user,
				"type": "Alert",
				"document_type": "Project",
				"document_name": project,
				"subject": subject,
				"email_content": doc.message or _("Post your update on the project's page."),
			}
		).insert(ignore_permissions=True)
	if _mail():
		frappe.sendmail(
			recipients=[frappe.db.get_value("User", user, "email") for user in people],
			subject=subject,
			message=doc.message or _("Reply to this email with your update."),
			reference_doctype="Project Update",
			reference_name=update.name,
			reply_to=frappe.db.get_value("Email Account", {"enable_incoming": 1, "default_incoming": 1}, "email_id"),
		)


def _mail() -> bool:
	return bool(frappe.db.exists("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}))


def sum_up() -> None:
	"""Daily: ERPNext's summary of yesterday's answers, where mail can go."""
	if _mail():
		from erpnext.projects.doctype.project.project import send_project_status_email_to_users

		send_project_status_email_to_users()


@frappe.whitelist()
@frappe.read_only()
def asked(project: str) -> bool:
	"""Whether the reader is asked for an update on this project today and has
	not given one."""
	frappe.has_permission("Project", "read", project, throw=True)
	user = frappe.session.user
	if not frappe.db.exists("Project User", {"parenttype": "Project", "parent": project, "user": user}):
		return False
	today = frappe.get_all("Project Update", filters={"project": project, "date": nowdate()}, pluck="name")
	if not today:
		return False
	return not frappe.db.exists(
		"Project User", {"parenttype": "Project Update", "parent": ["in", today], "user": user}
	)


@frappe.whitelist(methods=["POST"])
def post(project: str, note: str) -> str:
	"""The reader's update on a project: on today's ask, or on a new one."""
	frappe.has_permission("Project", "read", project, throw=True)
	note = (note or "").strip()
	if not note:
		frappe.throw(_("Write your update first."))
	found = frappe.get_all(
		"Project Update", filters={"project": project, "date": nowdate()}, pluck="name", order_by="creation desc", limit=1
	)
	update = (
		frappe.get_doc("Project Update", found[0])
		if found
		else frappe.get_doc({"doctype": "Project Update", "project": project, "sent": 0, "date": nowdate(), "time": nowtime()})
	)
	_answer(update, frappe.session.user, escape_html(note).replace("\n", "<br>"))
	return update.name


def answered(doc, method=None) -> None:
	"""Communication after_insert: an emailed reply to an ask, taken once."""
	if doc.reference_doctype != "Project Update" or doc.sent_or_received != "Received":
		return
	if doc.communication_type != "Communication":
		return
	user = frappe.db.get_value("User", {"email": doc.sender}, "name")
	if not user:
		return
	from email_reply_parser import EmailReplyParser

	note = frappe.utils.md_to_html(EmailReplyParser.parse_reply(doc.text_content or "") or "") or doc.content
	_answer(frappe.get_doc("Project Update", doc.reference_name), user, note)


def _answer(update, user: str, note: str) -> None:
	"""One row per person on an ask: a second answer replaces the first."""
	who = frappe.db.get_value("User", user, ["full_name", "user_image"], as_dict=True) or {}
	row = next((one for one in update.users if one.user == user), None) or update.append("users", {"user": user})
	row.update({"full_name": who.get("full_name"), "image": who.get("user_image"), "project_status": note})
	update.flags.ignore_permissions = True
	update.save()


def timeline(doctype: str, docname: str) -> list[dict]:
	"""additional_timeline_content for Project: each update in its activity."""
	updates = {
		one.name: one
		for one in frappe.get_all("Project Update", filters={"project": docname}, fields=["name", "date", "time"])
	}
	if not updates:
		return []
	rows = frappe.get_all(
		"Project User",
		filters={"parenttype": "Project Update", "parent": ["in", list(updates)], "project_status": ["is", "set"]},
		fields=["parent", "user", "full_name", "project_status", "modified"],
	)
	return [
		{
			"icon": "message-square",
			"is_card": True,
			"creation": row.modified,
			"content": _("{0} posted an update").format(f"<strong>{escape_html(row.full_name or row.user)}</strong>")
			+ f'<div class="one-update">{sanitize_html(row.project_status)}</div>',
		}
		for row in rows
	]
