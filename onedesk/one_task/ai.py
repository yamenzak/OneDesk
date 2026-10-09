"""What OneAI does in OneTask: reads the reader's tasks, suggests a task as a
card, and breaks a task into the steps of its checklist.
"""

from typing import Annotated

import frappe
from frappe import _lt
from frappe.utils import getdate

#: Steps suggested for one task at once: more is a plan, which is a project.
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
	# The reader says what; the model fills in the rest and suggests the card.
	"label": _lt("Add a task…"),
	"ask": _lt("Add a task to "),
	"fill": True,
	"expects": "plan_task",
}

#: A task's page (page/task_view), by its open view, from `?view=`.
PAGE = "task-view"

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

SUGGESTIONS = {
	f"page:{PAGE}": [_LEFT, _STEPS],
	f"page:{PAGE}/time": [_WHO, _LEFT],
	"page:my-tasks": [_FIRST, _ADD],
	"page:my-tasks/inbox": [_FIRST, _ADD],
	"Task": [
		{
			"label": _lt("Break this into steps"),
			"ask": _lt(
				"Break this task into the steps it takes to finish it, as its checklist. Keep the steps it has."
			),
			"can": "write",
			"view": "Form",
			"expects": "plan_steps",
		},
	],
}


def page(said: dict) -> str | None:
	"""The sentence the model is told on OneTask's pages."""
	if said.get("page") == PAGE:
		name = (said.get("record") or "").strip()
		if not name or not frappe.db.exists("Task", name) or not frappe.has_permission("Task", "read", doc=name):
			return "The reader is on a task's page."
		subject = frappe.db.get_value("Task", name, "subject")
		return (
			f"The reader is on the page of task {name} (“{subject}”). task_facts reads it as its page shows "
			"it: its dates, what it waits on and what waits on it, its checklist, its sub-tasks and the time "
			"logged on it; plan_steps suggests the steps of its checklist as a card. Nothing is changed until "
			"the reader approves. How a task's page works is in OneTask's documentation (how_to)."
		)
	if said.get("page") != "my-tasks":
		return None
	where = (
		"The reader is in OneTask, on the Inbox: their own tasks in no project"
		if said.get("section") == "inbox"
		else "The reader is in OneTask, on My Tasks: everything assigned to them and still to do"
	)
	return (
		where + ". my_tasks reads the list as they see it, grouped by when each is due; plan_task suggests "
		"a task as a card that adds it when the reader approves, and can give it to a colleague; "
		"plan_steps suggests the steps of a task's checklist. Nothing is added or changed until the "
		"reader approves. How OneTask works is in its documentation (how_to)."
	)


def my_tasks(
	view: Annotated[
		str, "mine for everything assigned to the reader, inbox for their own tasks in no project."
	] = "mine",
) -> dict:
	"""The reader's tasks still to do, in the groups My Tasks shows (Overdue,
	Today, Tomorrow, Next 7 Days, Later, No Due Date), each with its priority,
	when it is due, its project and what it is about. Read before saying what
	to do first or answering about the reader's work."""
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


def _project(said: str) -> str | None:
	"""A project the reader may see, by its name or its title, if exactly one."""
	said = (said or "").strip()
	if frappe.db.exists("Project", said) and frappe.has_permission("Project", "read", doc=said):
		return said
	found = frappe.get_list("Project", filters={"project_name": ["like", f"%{said}%"]}, pluck="name", limit=2)
	return found[0] if len(found) == 1 else None
