"""What OneAI does in OneProject: reads a project as its page does, and says
which projects need attention.
"""

import re
from typing import Annotated

import frappe
from frappe import _, _lt
from frappe.utils import add_days, date_diff, flt, get_fullname, getdate, nowdate, strip_html_tags

from onedesk.one_project import agreement, kinds, overview, tree

#: Not a project here: an employee's onboarding or exit checklist (README).
HR = "Employee Boarding"

#: How many of each list the model is shown.
MOST = 15

GOING = {
	"label": _lt("How is this project going?"),
	"ask": _lt(
		"How is this project going? Say in a few lines where it stands against its dates and its "
		"budget, what is late and what it holds up, the next milestone, and what the team said last."
	),
	"can": "read",
	"expects": "project_facts",
}
LATE = {
	"label": _lt("What is late?"),
	"ask": _lt("Which of this project's tasks are late, who is on each, and what waits on them?"),
	"can": "read",
	"expects": "project_facts",
}
UPDATE = {
	"label": _lt("Write the customer an update"),
	"ask": _lt(
		"Write a short update on this project for its customer: what was done, what comes next and "
		"when it should be finished. Plain words. Leave out hours, costs and who in the team does what."
	),
	"can": "read",
	"expects": "project_facts",
}
MONEY = {
	"label": _lt("Where is the money going?"),
	"ask": _lt(
		"Where is this project's money going? Say what the customer has been invoiced and paid, what "
		"it has cost and on what, which cost types are close to or over their budget, and where the "
		"forecast margin is heading."
	),
	"can": "read",
	"expects": "project_facts",
}
SUPPLIERS = {
	"label": _lt("What's left to pay the subcontractors?"),
	"ask": _lt(
		"For each subcontractor on this project, what is left to bill, the retention held, any advance "
		"not yet set off, and what has been paid."
	),
	"can": "read",
	"expects": "project_facts",
}
PLAN = {
	"label": _lt("Plan the tasks"),
	"ask": _lt(
		"Read this project, then suggest the tasks it still needs, each with a due date before its "
		"end, as cards I can approve."
	),
	"can": "write",
	"expects": "plan_task",
}
LOAD = {
	"label": _lt("Who has too much on?"),
	"ask": _lt(
		"Who on this project has too much on? Say who has the most open and late tasks and the most "
		"hours this month, and which tasks could go to somebody with less."
	),
	"can": "read",
	"expects": "project_facts",
}
TIME = {
	"label": _lt("Where did the time go?"),
	"ask": _lt(
		"Where did this project's time go this month? Say who logged it, on which tasks, how much is "
		"billable, and what is still a draft."
	),
	"can": "read",
	"expects": "project_facts",
}
UNBILLED = {
	"label": _lt("What's still to invoice?"),
	"ask": _lt(
		"What on this project is still to invoice? Say what time is billable and not invoiced, what of "
		"the contract is not billed yet, and what is invoiced and not paid."
	),
	"can": "read",
	"expects": "project_facts",
}
ALLOWANCE = {
	"label": _lt("How much of this month's hours are used?"),
	"ask": _lt(
		"How much of this month's retainer hours are used, how many are left, and at this pace will "
		"the month go over? Say which months went over and which are not invoiced yet."
	),
	"can": "read",
	"expects": "project_facts",
}

DRAFT = {
	"label": _lt("Draft my update"),
	"ask": _lt(
		"Draft my update on this project from my week: what I finished, the time I logged, and what is "
		"next or late for me. Two to four plain sentences, in the first person, as a card I can approve."
	),
	"can": "read",
	"expects": "draft_update",
}

#: The project page (project-view), by its open view, from `?view=`.
PAGE = "project-view"
#: The kinds with a customer to bill and to write to; an Internal project has none.
BILLED = (kinds.FIXED, kinds.TIME, kinds.RETAINER)
#: The Tasks view's layouts are the same view.
LAYOUTS = {"board": "tasks", "timeline": "tasks"}


def _here(*offered, kinds: tuple | None = None) -> list[dict]:
	"""Suggestions as the project page offers them: checked on the project the
	page is open on, and, with `kinds`, only on a project of those kinds."""
	said = []
	for one in offered:
		one = {**one, "doctype": one.get("doctype") or "Project"}
		if kinds:
			one["when"] = {"one_kind": list(kinds)}
		said.append(one)
	return said


#: A project template's page (page/project_template_view).
TEMPLATE_PAGE = "project-template-view"

DRAFT_TEMPLATE = {
	"label": _lt("Draft a template"),
	"ask": _lt(
		"Draft a project template for a kind of job we do. Ask me first what the job is, then offer a "
		"template we have or one from the library before drafting a new one."
	),
	"can": "create",
	"doctype": "Project Template",
	"expects": "draft_template",
}

SUGGESTIONS = {
	"Project Template": [{**DRAFT_TEMPLATE, "view": "List"}],
	f"page:{TEMPLATE_PAGE}": [DRAFT_TEMPLATE],
	"Project": [
		{**GOING, "view": "Form"},
		{**LATE, "view": "Form"},
		{**UPDATE, "view": "Form"},
		{**MONEY, "view": "Form"},
		{**SUPPLIERS, "view": "Form"},
		{**PLAN, "view": "Form"},
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
	# A retainer's first question is its hours, wherever it is asked.
	f"page:{PAGE}": _here(ALLOWANCE, kinds=(kinds.RETAINER,))
	+ _here(DRAFT, GOING, LATE)
	+ _here(UPDATE, kinds=BILLED)
	+ _here(PLAN),
	f"page:{PAGE}/tasks": _here(LATE, PLAN, LOAD),
	f"page:{PAGE}/time": _here(ALLOWANCE, kinds=(kinds.RETAINER,)) + _here(TIME, UNBILLED, LOAD),
	f"page:{PAGE}/money": _here(MONEY) + _here(UNBILLED, kinds=BILLED) + _here(SUPPLIERS),
	f"page:{PAGE}/invoices": _here(UNBILLED) + _here(ALLOWANCE, kinds=(kinds.RETAINER,)),
	f"page:{PAGE}/suppliers": _here(SUPPLIERS, MONEY),
	f"page:{PAGE}/team": _here(LOAD, LATE),
	f"page:{PAGE}/files": _here(GOING) + _here(UPDATE, kinds=BILLED),
	f"page:{PAGE}/activity": _here(DRAFT, GOING) + _here(UPDATE, kinds=BILLED),
}
for _layout, _view in LAYOUTS.items():
	SUGGESTIONS[f"page:{PAGE}/{_layout}"] = SUGGESTIONS[f"page:{PAGE}/{_view}"]

#: What each view is, as the model is told it.
VIEWS = {
	"overview": "the Overview: where it stands, what needs the reader, its numbers and milestones",
	"tasks": "the Tasks view: its tasks as a table, a board or a timeline",
	"time": "the Time view: the hours logged on it",
	"money": "the Money view: what the customer is billed and has paid, and what it costs",
	"invoices": "the Invoices view: its sales invoices",
	"suppliers": "the Suppliers view: its subcontracts and purchase orders",
	"team": "the Team view: its people, their open tasks and their hours, and its contacts outside the company",
	"files": "the Files view: its files",
	"activity": "the Activity view: what happened on it",
}


def page(said: dict) -> str | None:
	"""The sentence the model is told on a project's page, or a template's."""
	if said.get("page") == TEMPLATE_PAGE:
		name = (said.get("record") or "").strip()
		return (
			f"The reader is on the page of project template “{name}”, its tasks in a table, each a day after "
			"the project starts and a number of days long. project_templates lists the workspace's templates "
			"and the library's, and draft_template suggests a new one as a card that makes it when the reader "
			"approves. How templates work is in OneProject's documentation (how_to)."
		)
	if said.get("page") != PAGE:
		return None
	name = (said.get("record") or "").strip()
	if (
		not name
		or not frappe.db.exists("Project", name)
		or not frappe.has_permission("Project", "read", doc=name)
	):
		return "The reader is on a project's page."
	title, kind = frappe.db.get_value("Project", name, ["project_name", "one_kind"])
	view = (said.get("section") or "").strip() or "overview"
	view = LAYOUTS.get(view, view)
	return (
		f"The reader is on the page of project {name} (“{title}”"
		+ (f", a project of kind {kind}" if kind else "")
		+ f"), on {VIEWS.get(view, VIEWS['overview'])}. project_facts reads it as its page shows it: its "
		"dates, tasks, money, time, team, contacts and, for a retainer, its months, and the reader's own week on it; "
		"plan_task suggests a task on it as a card that adds it when the reader approves, and draft_update "
		"drafts the reader's update as a card that puts it under Updates to post. Nothing is changed until "
		"the reader approves. How "
		"OneProject works is in its documentation (how_to)."
	)


def _main(project: str) -> dict:
	"""The project's own work, its sub-projects left out (view.py `_sub_projects`
	"main"), and how much of the whole was ordered as extra work."""
	from onedesk.one_project import billing, view

	own = view.branch_money(tree.totals(project)["own"])
	under = sorted(tree.below({project}, tree.parents()))
	extra = frappe.get_all(
		"Sales Order",
		filters={"project": ["in", under], "docstatus": 1, billing.EXTRA: 1},
		fields=[{"SUM": "base_net_total", "as": "total"}],
	)
	return {
		"ordered": own["ordered"],
		"billed": own["billed"],
		"cost": own["spent"],
		"budget": own["budget"],
		"extra_work_ordered": flt(extra[0].total) if extra else 0,
	}


def project_facts(project: Annotated[str, "The project's id, such as PROJ-0005."]) -> dict:
	"""One project as its page shows it, with its sub-projects added up, and
	its own work apart from them as `main`: where it stands, its dates, what it cost against the estimate, what was billed,
	its late tasks (who is on each, what waits on each), its milestones to
	come, its people and its contacts outside the company, the team's last updates, the reader's own week on
	it, the payment terms and terms and conditions agreed with its customer, and its contracts with the customer and suppliers, signed or not. Read before saying how a project is going, what is late, or writing
	about it."""
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
		fields=["subject", "exp_end_date", "one_bill_share"],
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
		# Its own work apart from what is under it, as its Main row says it.
		"main": _main(project) if len(said["tree"]) > 1 else None,
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
			{
				"milestone": one.subject,
				"due": str(one.exp_end_date) if one.exp_end_date else None,
				"bill_on_completion": f"{flt(one.one_bill_share):g}%" if flt(one.one_bill_share) else None,
			}
			for one in milestones
		],
		"updates": _updates(project),
		"you": _yours(said["tree"]),
		"money": _money(project),
		"kind": doc.get("one_kind"),
		"time": _time(project, doc.get("one_kind")),
		"team": _team(project),
		"contacts": _contacts(project),
		"months": _months(project) if doc.get("one_kind") == kinds.RETAINER else None,
		# Agreed with the customer and carried onto its documents (terms.py, agreement.py).
		"payment_terms": doc.get("one_payment_terms"),
		"terms_and_conditions": doc.get("one_terms"),
		"contracts": [{key: value for key, value in one.items() if key != "route"} for one in agreement.contracts(said["tree"])],
	}


def _yours(projects: list[str]) -> dict:
	"""The reader's own last seven days on the project and those under it:
	the tasks of theirs they finished, the hours they logged, and their tasks
	still open, soonest due first."""
	user = frappe.session.user
	today = getdate(nowdate())
	since = add_days(today, -7)
	theirs = [["project", "in", projects], ["_assign", "like", f'%"{user}"%']]
	done = frappe.get_list(
		"Task",
		filters=[*theirs, ["status", "=", "Completed"], ["modified", ">=", str(since)]],
		pluck="subject",
		limit_page_length=MOST,
	)
	open_ = frappe.get_list(
		"Task",
		filters=[*theirs, ["status", "not in", overview.DONE]],
		fields=["subject", "exp_end_date"],
		order_by="exp_end_date asc",
		limit_page_length=MOST,
	)
	hours = frappe.db.sql(
		"""select sum(d.hours) from `tabTimesheet Detail` d join `tabTimesheet` t on t.name = d.parent
		where t.docstatus < 2 and t.user = %s and d.project in %s and date(d.from_time) >= %s""",
		(user, tuple(projects), since),
	)[0][0]
	return {
		"who": get_fullname(user),
		"finished_this_week": done,
		"hours_this_week": flt(hours, 1),
		"open": [
			{
				"task": one.subject,
				"due": str(getdate(one.exp_end_date)) if one.exp_end_date else None,
				"late": bool(one.exp_end_date and getdate(one.exp_end_date) < today),
			}
			for one in open_
		],
	}


def draft_update(
	project: Annotated[str, "The project's id, such as PROJ-0005."],
	update: Annotated[
		str,
		"The reader's update, in their words and in the first person: what they finished, what is next, "
		"and anything in the way. Two to four plain sentences, from project_facts' `you`. Plain text.",
	],
	why: Annotated[str, "In a sentence, what the update says."] | None = None,
) -> dict:
	"""Suggest the reader's update on a project, as a card they approve. Read
	project_facts first. Approving puts it in the line under Updates on the
	project's page, to be read, changed and posted by the reader: nothing is
	posted from here."""
	from onedesk.one_ai import proposals

	if not frappe.db.exists("Project", project) or not frappe.has_permission("Project", "read", doc=project):
		return {"error": f"No project the reader may see is {project}."}
	text = (update or "").strip()
	if not text:
		return {"error": "Write the update itself."}
	return {
		"proposal": proposals.propose("Update", "Project", changes={"text": text}, record=project, why=why),
		"state": "Proposed",
		"next": "Tell them Approve puts the update under Updates on the project's page, to change and post; "
		"it is not posted until they post it.",
	}


def project_templates() -> dict:
	"""The workspace's project templates, and the library's presets with what
	each is for. Read before drafting a template, so one that is already there
	is offered first."""
	from onedesk.one_project import library

	return {
		"templates": frappe.get_list("Project Template", filters={"disabled": 0}, pluck="name", limit=50),
		"library": [
			{
				"key": one["key"],
				"title": one["title"],
				"about": one["about"],
				"tasks": one["tasks"],
				"days": one["days"],
			}
			for one in library.presets()
		],
	}


def draft_template(
	title: Annotated[str, "The template's name, as the kind of job it is for: Kitchen Refit."],
	phases: Annotated[
		list[dict],
		"Its phases in order, each {subject, milestone: true, tasks: [{subject, day, days}]}: `day` is the day "
		"after the project starts that a task begins on, `days` how long it lasts. A task may say what it "
		"comes after by subject (`after`). Tasks are named as work, a noun or a verb first: Order glass.",
	],
	about: Annotated[str, "What kind of job it is for, in a sentence."] | None = None,
	why: Annotated[str, "In a sentence, why this template."] | None = None,
) -> dict:
	"""Suggest a project template, as a card the reader approves. Read
	project_templates first: offer a template the workspace has, or one from
	the library, before drafting a new one. Approving makes it, as the
	library's copy would, and opens it to change."""
	from onedesk.one_ai import proposals
	from onedesk.one_project import library

	if not frappe.has_permission("Project Template", "create"):
		return {"error": "The reader may not make project templates. A Projects Manager may."}
	title = (title or "").strip()
	if not title:
		return {"mend": "draft_template", "error": "Give the template a name."}
	if frappe.db.exists("Project Template", title):
		return {
			"mend": "draft_template",
			"error": f"There is already a template called {title}. Pick another name.",
		}
	preset = {"title": title, "about": (about or "").strip(), "tasks": phases or []}
	try:
		made = library.rows(preset)
	except (KeyError, TypeError, ValueError) as e:
		return {
			"mend": "draft_template",
			"error": f"A task is not written as asked ({e}). Each needs a subject, day and days.",
		}
	if not any(not one["is_group"] for one in made):
		return {"mend": "draft_template", "error": "A template needs tasks."}
	tasks = [one for one in made if not one["is_group"]]
	summary = [
		{"label": _("Tasks"), "value": str(len(tasks))},
		{
			"label": _("Runs"),
			"value": _("{0} days").format(max(one["start"] + one["duration"] for one in made)),
		},
		*(
			{"label": one["subject"], "value": _("Day {0} · {1} days").format(one["start"], one["duration"])}
			for one in made
			if one["is_group"]
		),
	]
	changes = {
		"what": "template",
		"title": title,
		"preset": preset,
		"summary": summary,
		"route": ["project-template-view", title],
	}
	return {
		"proposal": proposals.propose("Setup", "Project Template", changes=changes, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what approving it does. Nothing is made until they approve it.",
	}


def _time(project: str, kind: str | None) -> dict:
	"""The time as the Time view shows it: its totals, and this month's hours
	by person and by task (hours.py). A retainer's hours are billed with its
	month, so it has no time to invoice of its own."""
	from onedesk.one_project import hours

	said = hours.entries(project)
	month = str(getdate(nowdate()).replace(day=1))
	by_person: dict[str, float] = {}
	by_task: dict[str, float] = {}
	for one in said["entries"]:
		if not one["date"] or one["date"] < month:
			continue
		who = one["who"] or one["user"] or "?"
		by_person[who] = by_person.get(who, 0) + one["hours"]
		if one["task_subject"]:
			by_task[one["task_subject"]] = by_task.get(one["task_subject"], 0) + one["hours"]
	totals = dict(said["totals"])
	if kind == kinds.RETAINER:
		totals.pop("to_invoice")
		totals.pop("invoiced")
	return {
		**totals,
		"this_month_by_person": {key: round(value, 2) for key, value in by_person.items()},
		"this_month_by_task": dict(sorted(by_task.items(), key=lambda item: -item[1])[:MOST]),
	}


def _team(project: str) -> list[dict]:
	"""Its people as the Team view shows them: open and late tasks, hours."""
	from onedesk.one_project import team

	return [
		{
			"name": one["name"],
			"manager": one["manager"],
			"member": one["member"],
			"open_tasks": one["open"],
			"late_tasks": one["late"],
			"hours_this_month": one["month"],
			"hours": one["hours"],
		}
		for one in team.team(project)["people"][:MOST]
	]


def _contacts(project: str) -> list[dict]:
	"""Who outside the company is on it, as the Team view lists them."""
	from onedesk.one_project import contacts

	return [
		{
			"role": one["role"],
			"name": one["person"],
			"company": one["company"],
			"email": one["email"],
			"phone": one["phone"],
			"note": one["note"],
		}
		for one in contacts.contacts(project)["contacts"][:MOST]
	]


def _months(project: str) -> dict:
	"""A retainer's months as the page shows them (retainer.py)."""
	from onedesk.one_project import retainer

	said = retainer.months(project)
	return {
		"fee": said["fee"],
		"hours_a_month": said["allowance"],
		"renews": said["renews"],
		"months": [
			{
				"month": one["month"],
				"hours": one["hours"],
				"over": one["over"],
				"drafts": one["drafts"],
				"current": one["current"],
				"invoice": one["invoice"],
			}
			for one in said["months"]
		],
	}


def _money(project: str) -> dict:
	"""The money as the page shows it: both sides, the subcontracts, the
	cost types and the forecast (money.py, budget.py)."""
	from onedesk.one_project import money

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
			for one in said["cost_types"]["lines"]
		],
		"contract": said["contract"],
		"budget": said["budget"],
		"forecast_cost": said["forecast_cost"],
		"forecast_margin": said["forecast_margin"],
		"margin_so_far": said["margin"],
		"earned": said["earned"],
		"kind": said["kind"],
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
	"""The team's last updates, newest first, as the project's activity shows
	them, each with the health it was written in and its lines kept."""
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
		fields=["parent", "user", "project_status", "one_health"],
		order_by="modified desc",
		limit=8,
	)
	return [
		{
			"by": get_fullname(row.user),
			"user": row.user,
			"on": day[row.parent],
			"said": plain(row.project_status)[:LONGEST],
			"health": row.one_health,
		}
		for row in rows
	]


#: The longest update the page and the model are given.
LONGEST = 4000


def plain(html: str | None) -> str:
	"""An update as text, its paragraphs and line breaks kept. Pure."""
	text = re.sub(r"(?i)<br\s*/?>|</?(p|div|li)\b[^>]*>", "\n", html or "")
	lines = (" ".join(strip_html_tags(line).split()) for line in text.split("\n"))
	return "\n".join(line for line in lines if line)
