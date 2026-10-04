"""What OneAI does in OneProject: reads a project as its page does, and says
which projects need attention.

`project_facts` hands over the page's own answers (`overview.overview`): how
far it has got, its dates, cost against the budget, what is billed, what is
late and the next milestone, for the project and everything under it, and the
Money view: both sides of the money, the subcontracts, the cost types and
the forecast (`_money`). Beside
them, what the page has further down: the late tasks with who is on each and
what waits on them, the milestones to come, its people, and the team's last
updates. `projects_needing_attention` reads the Projects list as the reader
sees it and keeps the open ones in trouble.

Both read as the person asking: a project they may not open is not read, and
neither are its tasks. Tasks are only suggested (one_task/ai.py `plan_task`),
as cards the reader approves.
"""

from typing import Annotated

import frappe
from frappe import _lt
from frappe.utils import date_diff, flt, get_fullname, getdate, nowdate, strip_html_tags

from onedesk.one_project import overview

#: Not a project here: an employee's onboarding or exit checklist (README).
HR = "Employee Boarding"

#: How many of each list the model is shown.
MOST = 15

SUGGESTIONS = {
	"Project": [
		{
			"label": _lt("How is this project going?"),
			"ask": _lt(
				"How is this project going? Say in a few lines where it stands against its dates and its "
				"budget, what is late and what it holds up, the next milestone, and what the team said last."
			),
			"can": "read",
			"view": "Form",
			"expects": "project_facts",
		},
		{
			"label": _lt("What is late?"),
			"ask": _lt("Which of this project's tasks are late, who is on each, and what waits on them?"),
			"can": "read",
			"view": "Form",
			"expects": "project_facts",
		},
		{
			"label": _lt("Write the customer an update"),
			"ask": _lt(
				"Write a short update on this project for its customer: what was done, what comes next and "
				"when it should be finished. Plain words. Leave out hours, costs and who in the team does what."
			),
			"can": "read",
			"view": "Form",
			"expects": "project_facts",
		},
		{
			"label": _lt("Where is the money going?"),
			"ask": _lt(
				"Where is this project's money going? Say what the customer has been invoiced and paid, what "
				"it has cost and on what, which cost types are close to or over their budget, and where the "
				"forecast margin is heading."
			),
			"can": "read",
			"view": "Form",
			"expects": "project_facts",
		},
		{
			"label": _lt("What's left to pay the subcontractors?"),
			"ask": _lt(
				"For each subcontractor on this project, what is left to bill, the retention held, any advance "
				"not yet set off, and what has been paid."
			),
			"can": "read",
			"view": "Form",
			"expects": "project_facts",
		},
		{
			"label": _lt("Plan the tasks"),
			"ask": _lt(
				"Read this project, then suggest the tasks it still needs, each with a due date before its "
				"end, as cards I can approve."
			),
			"can": "write",
			"view": "Form",
			"expects": "plan_task",
		},
		{
			"label": _lt("Which projects need attention?"),
			"ask": _lt(
				"Which open projects need attention: marked at risk or off track, with late tasks, past their "
				"end date, or over their estimated cost?"
			),
			"can": "read",
			"view": "List",
			"expects": "projects_needing_attention",
		},
	],
}


def project_facts(project: Annotated[str, "The project's id, such as PROJ-0005."]) -> dict:
	"""One project as its page shows it, with its sub-projects added up: where
	it stands, its dates, what it cost against the estimate, what was billed,
	its late tasks (who is on each, what waits on each), its milestones to
	come, its people and the team's last updates. Read before saying how a
	project is going, what is late, or writing about it."""
	if not frappe.db.exists("Project", project) or not frappe.has_permission("Project", "read", doc=project):
		return {"error": f"No project the reader may see is {project}."}
	doc = frappe.get_doc("Project", project)
	said = overview.overview(project)
	today = nowdate()
	open_ = [["project", "in", said["tree"]], ["status", "not in", overview.DONE]]
	late = frappe.get_list(
		"Task",
		filters=[*open_, ["exp_end_date", "<", today]],
		fields=["name", "subject", "status", "exp_end_date", "_assign", "project"],
		order_by="exp_end_date asc",
		limit_page_length=MOST,
	)
	waiting = _waiting_on([one.name for one in late])
	milestones = frappe.get_list(
		"Task",
		filters=[*open_, ["is_milestone", "=", 1]],
		fields=["subject", "exp_end_date"],
		order_by="exp_end_date asc",
		limit_page_length=5,
	)
	return {
		"project": doc.name,
		"title": doc.project_name,
		"status": doc.status,
		"health": doc.get("one_health"),
		"customer": doc.customer,
		"manager": get_fullname(doc.one_manager) if doc.get("one_manager") else None,
		"members": [get_fullname(row.user) for row in doc.users],
		"parent": doc.get("one_parent"),
		"sub_projects": len(said["tree"]) - 1,
		"starts": str(doc.expected_start_date) if doc.expected_start_date else None,
		"ends": said["end"],
		"days_left": said["days_left"],
		"tasks": said["tasks"],
		"done": said["done"],
		"done_share": said["share"],
		"currency": said["currency"],
		"estimated_cost": said["estimated"],
		"cost": said["cost"],
		"billed": said["billed"],
		"to_bill": said["to_bill"],
		"margin": said["margin"],
		"late": [
			{
				"task": one.subject,
				"due": str(one.exp_end_date),
				"days_late": date_diff(today, one.exp_end_date),
				"on_it": [get_fullname(user) for user in frappe.parse_json(one._assign or "[]")],
				"waiting_on_it": waiting.get(one.name, []),
			}
			for one in late
		],
		"late_count": said["late"],
		"milestones": [
			{"milestone": one.subject, "due": str(one.exp_end_date) if one.exp_end_date else None}
			for one in milestones
		],
		"updates": _updates(project),
		"money": _money(project),
	}


def _money(project: str) -> dict:
	"""The money as the page shows it: both sides, the subcontracts, the
	cost types and the forecast (money.py, budget.py)."""
	from onedesk.one_project import budget, money

	said = money.money(project)
	return {
		"customer": {one["label"]: one["value"] for one in said["customer"]},
		"cost": {one["label"]: one["value"] for one in said["cost"] + said["own"]},
		"subcontracts": [
			{
				key: one[key]
				for key in ("supplier", "order", "ordered", "billed", "left", "retention", "advance", "paid")
			}
			for one in said["suppliers"][:MOST]
		],
		"cost_types": [
			{key: one[key] for key in ("cost_type", "budget", "committed", "spent", "left")}
			for one in budget._lines(project)
		],
		"contract": said["contract"],
		"budget": said["budget"],
		"forecast_cost": said["forecast_cost"],
		"forecast_margin": said["forecast_margin"],
		"margin_so_far": said["margin"],
	}


def projects_needing_attention() -> dict:
	"""The open projects the reader may see that need attention, worst first:
	marked At Risk or Off Track, with late tasks, past their expected end, or
	costing more than their estimate. Read before saying which projects need
	attention."""
	today = nowdate()
	projects = frappe.get_list(
		"Project",
		filters=[["status", "=", "Open"], ["project_type", "!=", HR]],
		fields=[
			"name",
			"project_name",
			"one_health",
			"expected_end_date",
			"estimated_costing",
			"total_costing_amount",
			"total_purchase_cost",
			"total_consumed_material_cost",
			"customer",
		],
		limit_page_length=0,
	)
	if not projects:
		return {"projects": []}
	late = {
		row.project: row.n
		for row in frappe.get_list(
			"Task",
			filters=[
				["project", "in", [one.name for one in projects]],
				["status", "not in", overview.DONE],
				["exp_end_date", "<", today],
			],
			fields=["project", {"COUNT": "*", "as": "n"}],
			group_by="project",
		)
	}
	out = []
	for one in projects:
		cost = (
			flt(one.total_costing_amount)
			+ flt(one.total_purchase_cost)
			+ flt(one.total_consumed_material_cost)
		)
		why = []
		if one.one_health in ("At Risk", "Off Track"):
			why.append(f"marked {one.one_health}")
		if late.get(one.name):
			why.append(f"{late[one.name]} late task" + ("s" if late[one.name] != 1 else ""))
		if one.expected_end_date and getdate(one.expected_end_date) < getdate(today):
			days = date_diff(today, one.expected_end_date)
			why.append(f"{days} day{'s' if days != 1 else ''} past its end")
		if flt(one.estimated_costing) and cost > flt(one.estimated_costing):
			why.append("over its estimated cost")
		if why:
			out.append({"project": one.name, "title": one.project_name, "customer": one.customer, "why": why})
	out.sort(key=lambda row: -len(row["why"]))
	return {"projects": out[:MOST], "open": len(projects)}


def _waiting_on(tasks: list[str]) -> dict[str, list[str]]:
	"""For each task, the open tasks that depend on it, by subject."""
	if not tasks:
		return {}
	rows = frappe.get_all(
		"Task Depends On", filters={"task": ["in", tasks], "parenttype": "Task"}, fields=["task", "parent"]
	)
	names = {row.parent for row in rows}
	open_ = (
		{
			one.name: one.subject
			for one in frappe.get_list(
				"Task",
				filters=[["name", "in", list(names)], ["status", "not in", overview.DONE]],
				fields=["name", "subject"],
			)
		}
		if names
		else {}
	)
	out: dict[str, list[str]] = {}
	for row in rows:
		if row.parent in open_:
			out.setdefault(row.task, []).append(open_[row.parent])
	return out


def _updates(project: str) -> list[dict]:
	"""The team's last updates, newest first, as the project's activity shows them."""
	asks = frappe.get_all(
		"Project Update",
		filters={"project": project},
		fields=["name", "date"],
		order_by="date desc",
		limit=10,
	)
	if not asks:
		return []
	day = {one.name: str(one.date) for one in asks}
	rows = frappe.get_all(
		"Project User",
		filters={
			"parenttype": "Project Update",
			"parent": ["in", list(day)],
			"project_status": ["is", "set"],
		},
		fields=["parent", "user", "project_status"],
		order_by="modified desc",
		limit=8,
	)
	return [
		{
			"by": get_fullname(row.user),
			"on": day[row.parent],
			"said": " ".join(strip_html_tags(row.project_status).split())[:600],
		}
		for row in rows
	]
