"""What OneAI does in OneTask: reads the reader's tasks, suggests a task as a
card, breaks a task into the steps of its checklist, and gives a task to a
colleague as the page's Assign does. A change to a task (done, due another
day, more pressing) is the generic edit_record on the Task, which saves it
as the page does.
"""

from typing import Annotated

import frappe
from frappe import _, _lt
from frappe.utils import get_fullname, getdate

# What OneAI changes in OneTask is a card it suggests (plan_task, plan_steps,
# assign_task and the edit card); these calls it leaves to the person.
REACH = {}

NOT_FOR_AI = {
	"task.stop_repeat": "Stopping a repeat ends tasks nobody has seen yet, so the person does it from the task's menu.",
	"timer.start": "A timer measures the person's own time as they work, so only they start it.",
	"timer.pause": "A timer measures the person's own time as they work, so only they pause it.",
	"timer.stop": "A timer measures the person's own time as they work, so only they stop it.",
}

MOST_STEPS = 12


_FIRST = {
	"label": _lt("What should I do first?"),
	"ask": _lt(
		"Look at my tasks and say which I should do first and why: what is late, what is due soonest, "
		"and what is most pressing."
	),
	"expects": "my_tasks",
}
_ADD = {
	"label": _lt("Add a task…"),
	"ask": _lt("Add a task to "),
	"fill": True,
	"expects": "plan_task",
}

_STEPS = {
	"label": _lt("Break this into steps"),
	"ask": _lt("Break this task into the steps it takes to finish it, as its checklist. Keep the steps it has."),
	"can": "write",
	"doctype": "Task",
	"expects": "plan_steps",
}
_LEFT = {
	"label": _lt("What is left on this task?"),
	"ask": _lt(
		"What is left to do on this task: the steps and sub-tasks still open, what it waits on, how its "
		"hours compare with the plan, and whether it is late."
	),
	"can": "read",
	"doctype": "Task",
	"expects": "task_facts",
}
_WHO = {
	"label": _lt("Who worked on this?"),
	"ask": _lt("Who has logged time on this task, how much each, and how that compares with the hours planned."),
	"can": "read",
	"doctype": "Task",
	"expects": "task_facts",
}

_CHANGE = {
	"label": _lt("Change this task…"),
	"ask": _lt("Change this task: "),
	"fill": True,
	"can": "write",
	"doctype": "Task",
	"expects": "edit_record",
}

_GIVE = {
	"label": _lt("Give this task to…"),
	"ask": _lt("Give this task to "),
	"fill": True,
	"can": "write",
	"doctype": "Task",
	"expects": "assign_task",
}

SUGGESTIONS = {
	"Task": [
		{**_FIRST, "view": "List"},
		{**_ADD, "view": "List"},
		*({**one, "view": "Form"} for one in (_LEFT, _STEPS, _CHANGE, _GIVE, _WHO)),
	],
}


def page(said: dict) -> str | None:
	"""The sentence the model is told on OneTask's pages."""
	if said.get("page") == "timers":
		return (
			"The reader is on Timers, the phone's page for their task timers: the one running with its time "
			"today, and the paused ones; pausing or stopping adds the time to their timesheet for the week. "
			"my_tasks reads their tasks and task_facts one task with the time logged on it. How timers work is "
			"in OneTask's documentation (how_to)."
		)
	return None


def my_tasks(
	view: Annotated[
		str, "mine for everything assigned to the reader, inbox for what is assigned to them in no project."
	] = "mine",
) -> dict:
	"""The reader's tasks still to do, in the groups My Tasks shows (Overdue,
	Today, Tomorrow, Next 7 Days, Later, No Due Date), each with its priority,
	when it is due, its project, what it is about, and how many open tasks it
	waits on. Read before saying what to do first, what is on the reader's
	list or plate today or this week, or anything else about their work:
	never say they have nothing to do without reading it."""
	from onedesk.one_task import mine

	groups = mine.tasks(view if view in mine.VIEWS else "mine")
	return {
		"view": view,
		"groups": [
			{
				"group": group["label"],
				"tasks": [
					{
						"name": one.name,
						"subject": one.subject,
						"status": one.status,
						"priority": one.priority,
						"due": str(one.due) if one.due else None,
						"project": one.project_title,
						"about": one.get("about_title"),
						"milestone": bool(one.is_milestone),
						"waiting_on": one.waiting,
					}
					for one in group["tasks"]
				],
			}
			for group in groups
		],
	}


def task_facts(task: Annotated[str, "The task's id, such as TASK-2026-00052."]) -> dict:
	"""A task as its page shows it to the reader: its status, priority, dates
	and how late it is, its project, what it waits on and what waits on it,
	its checklist and sub-tasks, its description, and the hours logged on it
	by whom against the hours planned. Read before saying what is left on a
	task or who worked on it."""
	from onedesk.one_task import view

	if not frappe.db.exists("Task", task) or not frappe.has_permission("Task", "read", doc=task):
		return {"error": f"No task the reader may see is {task}."}
	said = view.read(task)
	people = said["people"]
	who = {}
	for one in said["time"]["entries"]:
		key = one["who"] or one["user"] or "?"
		who[key] = round(who.get(key, 0) + one["hours"], 2)
	return {
		"name": said["name"],
		"subject": said["subject"],
		"status": said["status"],
		"priority": said["priority"],
		"project": said["project_title"],
		"starts": str(said["exp_start_date"] or "")[:10] or None,
		"due": said["due"],
		"late_by_days": said["late_by"],
		"assigned": [people.get(one, {}).get("name", one) for one in said["assigned"]],
		"waits_on": [{"subject": one["subject"], "done": one["done"]} for one in said["waits"]],
		"waiting_on_this": [one["subject"] for one in said["blocking"]],
		"checklist": [{"step": one["step"], "done": bool(one["done"])} for one in said["steps"]],
		"sub_tasks": [{"subject": one.subject, "status": one.status} for one in said["sub_tasks"]],
		"description": frappe.utils.strip_html_tags(said["description"] or "")[:2000],
		"planned_hours": said["expected_time"],
		"logged_hours": said["time"]["logged"],
		"draft_hours": said["time"]["drafts"],
		"hours_by_person": who,
	}


def plan_task(
	subject: Annotated[str, "What the task is, as its title: a verb first, as in Send the quote."],
	due: Annotated[str, "When it is due, as YYYY-MM-DD."] | None = None,
	project: Annotated[str, "The project it belongs to, by name or title, if any."] | None = None,
	priority: Annotated[str, "Low, Medium, High or Urgent."] | None = None,
	description: Annotated[str, "What it is for, in a line or two."] | None = None,
	steps: Annotated[list[str], "The steps to finish it, as its checklist."] | None = None,
	give_to: Annotated[list[str], "Colleagues to give it to, by name or email address."] | None = None,
	why: Annotated[str, "In a sentence, why this task."] | None = None,
) -> dict:
	"""Suggest a task, as a card the reader approves. Nothing is made, and
	nobody is told, until they approve it; then it is added, and given to the
	colleagues named, or to the reader when it names nobody and no project."""
	from onedesk.one_ai import proposals
	from onedesk.one_calendar.ai import _person

	users, unknown = [], []
	for one in give_to or []:
		user = _person(one)
		(users.append(user) if user else unknown.append(one))
	if unknown:
		return {"error": f"No colleague found for {', '.join(unknown)}. Ask who they meant."}
	found = None
	if project:
		found = _project(project)
		if not found:
			return {"error": f"No project the reader may see is called {project}. Ask which one they meant."}
	changes = {
		"subject": subject,
		"exp_end_date": str(getdate(due)) if due else None,
		"project": found,
		"priority": priority if priority in ("Low", "Medium", "High", "Urgent") else None,
		"description": description,
		"one_steps": [{"step": one} for one in (steps or [])[:MOST_STEPS] if (one or "").strip()],
		"one_for": ", ".join(dict.fromkeys(users)) or None,
	}
	return {
		"proposal": proposals.propose(
			"Create", "Task", changes={k: v for k, v in changes.items() if v not in (None, [], "")}, why=why
		),
		"state": "Proposed",
		"next": "Tell them approving the card adds the task, and gives it to whoever it names.",
	}


def plan_steps(
	task: Annotated[str, "The task's id, as the page names it."],
	steps: Annotated[list[str], "The steps to add to its checklist, in order."],
	why: Annotated[str, "In a sentence, why these steps."] | None = None,
) -> dict:
	"""Suggest the steps of a task's checklist, as a card the reader approves.
	The steps it has are kept, done or not; the new ones follow them."""
	from onedesk.one_ai import proposals

	if not frappe.db.exists("Task", task) or not frappe.has_permission("Task", "write", doc=task):
		return {"error": "There is no such task the reader may change."}
	held = frappe.get_doc("Task", task)
	kept = [
		{"step": one.step, "done": one.done, "done_when": one.done_when}
		for one in held.get("one_steps") or []
	]
	said = {one["step"].strip().lower() for one in kept}
	new = [{"step": one.strip()} for one in steps or [] if one and one.strip().lower() not in said]
	if not new:
		return {"error": "Those steps are already on its checklist. Say so."}
	return {
		"proposal": proposals.propose(
			"Edit", "Task", changes={"one_steps": kept + new[:MOST_STEPS]}, record=task, why=why
		),
		"state": "Proposed",
	}


def assign_task(
	task: Annotated[str, "The task's id, as the page or the list names it."],
	to: Annotated[list[str], "The colleagues to give it to, by name or email address."],
	why: Annotated[str, "In a sentence, why them."] | None = None,
) -> dict:
	"""Give a task that already exists to one or more colleagues, as a card
	the reader approves. Approving does what the task page's Assign does:
	they are given the task and told. Nobody is given it until then. To make
	a new task for somebody, use plan_task."""
	from onedesk.one_ai import proposals
	from onedesk.one_calendar.ai import _person

	if not frappe.db.exists("Task", task) or not frappe.has_permission("Task", "write", doc=task):
		return {"error": "There is no such task the reader may change."}
	users, unknown = [], []
	for one in to or []:
		user = _person(one)
		if user and user not in ("Administrator", "Guest"):
			users.append(user)
		else:
			unknown.append(one)
	if unknown:
		return {"error": f"No colleague found for {', '.join(unknown)}. Ask who they meant, by email."}
	users = list(dict.fromkeys(users))
	if not users:
		return {"error": "Nobody was named. Ask who should have it."}
	held = set(frappe.parse_json(frappe.db.get_value("Task", task, "_assign") or "[]") or [])
	new = [one for one in users if one not in held]
	if not new:
		return {"error": "The task is already given to them. Say so."}
	subject = frappe.db.get_value("Task", task, "subject") or task
	names = ", ".join(get_fullname(one) for one in new)
	changes = {
		"what": "assign",
		"title": _("Give {0} to {1}").format(subject, names),
		"task": task,
		"users": new,
		"summary": [
			{"label": _("Task"), "value": f"{subject} ({task})"},
			{"label": _("Given to"), "value": ", ".join(f"{get_fullname(one)} ({one})" for one in new)},
		],
		"route": ["Form", "Task", task],
	}
	return {
		"proposal": proposals.propose("Setup", "Task", changes=changes, record=task, why=why),
		"state": "Proposed",
		"next": "Say in one sentence that approving gives them the task and tells them. Nothing changes until they approve it.",
	}


def assigned(changes: dict) -> str:
	"""An assign card approved (one_studio/ai_setup.py): the task given as the page's
	Assign gives it, by whoever pressed Approve, checked again now."""
	from frappe.desk.form.assign_to import add

	task = changes["task"]
	if not frappe.db.exists("Task", task) or not frappe.has_permission("Task", "write", doc=task):
		frappe.throw(_("You may not change {0}.").format(task), frappe.PermissionError)
	for one in changes["users"]:
		if one in ("Administrator", "Guest") or not frappe.db.exists(
			"User", {"name": one, "enabled": 1, "user_type": "System User"}
		):
			frappe.throw(_("{0} is not an enabled user of this workspace.").format(one))
	add({"doctype": "Task", "name": task, "assign_to": changes["users"]})
	return task


def _project(said: str) -> str | None:
	"""A project the reader may see, by its name or its title, if exactly one."""
	said = (said or "").strip()
	if frappe.db.exists("Project", said) and frappe.has_permission("Project", "read", doc=said):
		return said
	found = frappe.get_list("Project", filters={"project_name": ["like", f"%{said}%"]}, pluck="name", limit=2)
	return found[0] if len(found) == 1 else None


READS = (
	"my_tasks",
	"task_facts",
)
"""The tools OneAI reads here (registry/hooks.py lists them in one_ai_reads)."""


SUGGESTS = (
	"plan_task",
	"plan_steps",
	"assign_task",
)
"""The tools OneAI suggests, each as a card a person applies here (registry/hooks.py lists them in one_ai_suggests)."""
