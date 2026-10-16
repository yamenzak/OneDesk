"""Telling people about tasks (notifications/one_task/)."""

import frappe
from frappe import _
from frappe.utils import formatdate, get_fullname, getdate, nowdate

from onedesk.one import notify
from onedesk.one_task.capture import DONE


def given(doc, method=None) -> None:
	"""Notification Log before_insert: frappe's line for a task given, in ours."""
	if doc.type != "Assignment" or doc.document_type != "Task" or not doc.document_name:
		return
	if _completed(doc):
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
	_say(doc, "Task Given", subject, message)


def _say(doc, kind: str, subject: str, message: str) -> None:
	# frappe's before_insert has already copied its own line into the title the
	# bell shows (title, description), so ours goes there too.
	doc.update(
		{
			"type": kind,
			"subject": subject,
			"title": subject,
			"email_content": message or None,
			"description": message or None,
		}
	)


def _completed(doc) -> bool:
	"""A task completed closes every assignment on it (erpnext's
	close_all_assignments), and frappe tells each other assignee theirs was
	"removed". Said as what happened: Task Done."""
	task = frappe.db.get_value(
		"Task", doc.document_name, ["subject", "status", "project", "exp_end_date"], as_dict=True
	)
	if not task or task.status != "Completed" or doc.for_user == doc.from_user:
		return False
	if not frappe.db.get_value("Notification Type", "Task Done", "enabled"):
		return False
	lang = frappe.db.get_value("User", doc.for_user, "language") or frappe.db.get_single_value(
		"System Settings", "language"
	)
	subject, message = notify.render(
		"Task Done",
		{
			"who": get_fullname(doc.from_user),
			"task": task.subject,
			"project": _facts(task)["project"],
			"facts": _facts(task)["facts"],
		},
		lang,
	)
	_say(doc, "Task Done", subject, message)
	return True


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
		facts=_facts(doc)["project"].lstrip(" ·"),
	)


def changed(doc, method=None) -> None:
	"""Task on_update: a task ready, sent for review, or moved, told to its people."""
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_import or frappe.flags.in_patch:
		return
	if doc.is_template:
		return
	if doc.status in DONE and doc.has_value_changed("status"):
		for name in set(
			frappe.get_all(
				"Task Depends On", filters={"task": doc.name, "parenttype": "Task"}, pluck="parent"
			)
		):
			_ready(name, doc.subject)
	if doc.status == "Pending Review" and doc.has_value_changed("status"):
		people = _others({*_gave(doc.name), doc.owner})
		if people:
			notify.notify(
				"Pending Review",
				people,
				record=("Task", doc.name),
				who=get_fullname(frappe.session.user),
				task=doc.subject,
				**_facts(doc),
			)
	before = doc.get_doc_before_save()
	if (
		before
		and before.status == "Pending Review"
		and doc.status not in DONE
		and doc.status != "Pending Review"
	):
		people = _others(_given(doc.name))
		if people:
			notify.notify(
				"Sent Back",
				people,
				record=("Task", doc.name),
				who=get_fullname(frappe.session.user),
				task=doc.subject,
				project=_facts(doc)["project"],
				facts=_facts(doc)["project"].lstrip(" ·"),
			)
	if before and doc.exp_end_date and _day(before.exp_end_date) != _day(doc.exp_end_date):
		people = _others(_given(doc.name))
		if people:
			notify.notify(
				"Due Date Changed",
				people,
				record=("Task", doc.name),
				who=get_fullname(frappe.session.user),
				task=doc.subject,
				due=formatdate(doc.exp_end_date),
				was=_(" · was {0}").format(formatdate(before.exp_end_date)) if before.exp_end_date else "",
				project=_facts(doc)["project"],
				facts=" · ".join(
					one
					for one in (
						_("Was {0}").format(formatdate(before.exp_end_date)) if before.exp_end_date else "",
						_facts(doc)["project"].lstrip(" ·"),
					)
					if one
				),
			)


def _ready(name: str, done: str) -> None:
	"""A task waiting on one just done: Task Ready when nothing it waits on is open."""
	task = frappe.db.get_value(
		"Task",
		name,
		["name", "subject", "project", "status", "owner", "exp_start_date", "exp_end_date"],
		as_dict=True,
	)
	if not task or task.status in DONE:
		return
	waits = frappe.get_all("Task Depends On", filters={"parent": name, "parenttype": "Task"}, pluck="task")
	if frappe.db.exists("Task", {"name": ["in", waits], "status": ["not in", DONE]}):
		return
	people = _others(set(_given(name)) or {task.owner})
	if people:
		notify.notify(
			"Task Ready", people, record=("Task", name), task=task.subject, done=done, **_facts(task)
		)


def _others(people) -> list[str]:
	"""A task's people, but whoever made the change."""
	return sorted(one for one in people if one and one not in ("Administrator", "Guest", frappe.session.user))


def _given(task: str) -> list[str]:
	"""Whoever the task is given to: its open assignments."""
	return frappe.get_all(
		"ToDo",
		filters={"reference_type": "Task", "reference_name": task, "status": "Open"},
		pluck="allocated_to",
	)


def _gave(task: str) -> list[str]:
	"""Whoever gave the task to somebody."""
	return frappe.get_all(
		"ToDo",
		filters={"reference_type": "Task", "reference_name": task, "status": ["!=", "Cancelled"]},
		pluck="assigned_by",
	)


def _day(value) -> str | None:
	return str(getdate(value)) if value else None


def _facts(task) -> dict:
	"""When a task is due and its project, each led by a dot so either may be
	left out: " · 5 Oct 2026 · Website Relaunch"."""
	from onedesk.one_task.mine import due

	day = due(task)
	title = frappe.db.get_value("Project", task.project, "project_name") if task.get("project") else None
	due = _("Due {0}").format(formatdate(day)) if day else ""
	project = (title or task.project) if task.get("project") else ""
	return {
		"due": f" · {due}" if due else "",
		"project": f" · {project}" if project else "",
		# Both on one line, for the mail: "Due 5 Oct 2026 · Website Relaunch".
		"facts": " · ".join(one for one in (due, project) if one),
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
		for user in frappe.parse_json(one._assign or "[]") or []:
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


def commented(doc, method=None) -> None:
	"""Comment after_insert: a comment on a task, told to its people, but the
	commenter and whoever it mentions (frappe tells them as a Mention)."""
	if doc.comment_type != "Comment" or doc.reference_doctype != "Task" or not doc.reference_name:
		return
	from frappe.desk.notifications import extract_mentions

	task = frappe.db.get_value("Task", doc.reference_name, ["subject", "owner"], as_dict=True)
	if not task:
		return
	mentioned = set(extract_mentions(doc.content) or [])
	people = [
		one
		for one in _others({*_given(doc.reference_name), *_gave(doc.reference_name), task.owner})
		if one not in mentioned and one != doc.comment_email
	]
	if people:
		notify.notify(
			"Comment on Your Task",
			people,
			record=("Task", doc.reference_name),
			who=doc.comment_by or get_fullname(frappe.session.user),
			task=task.subject,
			comment=frappe.utils.strip_html(doc.content or "")[:400],
		)
