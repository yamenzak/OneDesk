"""Telling people about tasks (one_task/notifications.py).

**A task given.** Giving somebody a task is frappe's assignment, and frappe
writes its own line for it: "Samir assigned a new task Task Write the copy to
you". It is written from deep inside `assign_to.add`, with no switch to turn it
off, so rather than send a second one, `given` says frappe's line in ours as it
is written: the Notification Log becomes a Task Given, with when the task is
due and its project. frappe's line for an assignment taken away is left alone.

**A task done.** ERPNext closes a task's assignments when it is completed, and
frappe tells nobody. `done` tells whoever gave the task, and whoever made it,
unless they completed it themselves.

**The morning.** `today` tells each person what is due that day and what is
late, from the tasks given to them, as My Tasks groups them (mine.py).
"""

import frappe
from frappe import _
from frappe.utils import formatdate, get_fullname, getdate, nowdate

from onedesk.one import notify
from onedesk.one_task.capture import DONE


def given(doc, method=None) -> None:
	"""Notification Log before_insert: frappe's line for a task given, in ours."""
	if doc.type != "Assignment" or doc.document_type != "Task" or not doc.document_name:
		return
	# Only a task given: its assignment is open. Taking one away is frappe's to say.
	if not frappe.db.exists(
		"ToDo",
		{
			"reference_type": "Task",
			"reference_name": doc.document_name,
			"allocated_to": doc.for_user,
			"status": "Open",
		},
	):
		return
	if not frappe.db.get_value("Notification Type", "Task Given", "enabled"):
		return
	task = frappe.db.get_value(
		"Task", doc.document_name, ["subject", "project", "exp_start_date", "exp_end_date"], as_dict=True
	)
	if not task:
		return
	lang = frappe.db.get_value("User", doc.for_user, "language") or frappe.db.get_single_value(
		"System Settings", "language"
	)
	subject, message = notify.render(
		"Task Given", {"who": get_fullname(doc.from_user), "task": task.subject, **_facts(task)}, lang
	)
	doc.update({"type": "Task Given", "subject": subject, "email_content": message or None})


def done(doc, method=None) -> None:
	"""Task on_update: a task completed, told to whoever gave it and made it."""
	if doc.status != "Completed" or not doc.has_value_changed("status"):
		return
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_import or frappe.flags.in_patch:
		return
	gave = frappe.get_all(
		"ToDo",
		filters={"reference_type": "Task", "reference_name": doc.name, "status": ["!=", "Cancelled"]},
		pluck="assigned_by",
	)
	people = {one for one in [*gave, doc.owner] if one and one not in ("Administrator", "Guest")}
	people.discard(frappe.session.user)
	if not people:
		return
	notify.notify(
		"Task Done",
		sorted(people),
		record=("Task", doc.name),
		who=get_fullname(frappe.session.user),
		task=doc.subject,
		project=_facts(doc)["project"],
	)


def _facts(task) -> dict:
	"""When a task is due and its project, each led by a dot so either may be
	left out: " · 5 Oct 2026 · Website Relaunch"."""
	from onedesk.one_task.mine import due

	day = due(task)
	title = frappe.db.get_value("Project", task.project, "project_name") if task.get("project") else None
	return {
		"due": f" · {formatdate(day)}" if day else "",
		"project": f" · {title or task.project}" if task.get("project") else "",
	}


def today() -> None:
	"""Each morning: each person's tasks due that day and late, when there are any."""
	if not frappe.db.get_value("Notification Type", "Today's Tasks", "enabled"):
		return
	from onedesk.one_task.mine import due, when

	day = getdate(nowdate())
	rows = frappe.get_all(
		"Task",
		filters=[["status", "not in", DONE], ["_assign", "is", "set"]],
		or_filters=[["exp_end_date", "<=", nowdate()], ["exp_start_date", "<=", nowdate()]],
		fields=["name", "subject", "exp_start_date", "exp_end_date", "_assign"],
	)
	mine: dict[str, list] = {}
	for one in rows:
		group = when(due(one), day)
		if group not in ("overdue", "today"):
			continue
		for user in frappe.parse_json(one._assign) or []:
			mine.setdefault(user, []).append((group, one))
	if not mine:
		return
	people = frappe.get_all(
		"User",
		filters={"name": ["in", list(mine)], "enabled": 1, "user_type": "System User"},
		fields=["name", "language"],
	)
	fallback = frappe.db.get_single_value("System Settings", "language")
	for person in people:
		if person.name in ("Administrator", "Guest"):
			continue
		lang = person.language or fallback
		said = {"overdue": _("Overdue", lang=lang), "today": _("Today", lang=lang)}
		# Late first, then today's, as My Tasks lists them.
		listed = sorted(mine[person.name], key=lambda pair: (pair[0] != "overdue", due(pair[1])))
		notify.notify(
			"Today's Tasks",
			person.name,
			link="/desk/my-tasks",
			sender="Administrator",
			count=len(listed),
			tasks=_lines([f"{said[group]} · {one.subject}" for group, one in listed]),
		)


def _lines(lines: list[str]):
	"""Lines of text as HTML, each escaped, one to a line."""
	from markupsafe import Markup

	return Markup("<br>").join(lines)
