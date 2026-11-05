"""What OneAI does in OneProject: reads a project as its page does, and says
which projects need attention.
"""

import re
from typing import Annotated

import frappe
from frappe import _, _lt
from frappe.utils import add_days, date_diff, flt, get_fullname, getdate, nowdate, strip_html_tags

from onedesk.one_project import agreement, kinds, money, overview, tree

# What OneAI changes in OneProject: each call its cards make once they are
# approved (approved, below), and the calls it leaves to a person and why.
REACH = {
	"kinds.make": "draft_project",
	"status.change": "set_status",
	"hours.log": "log_time",
	"budget.set_budget": "set_cost_budget",
	"team.add": "add_member",
	"contacts.save": "add_contact",
}

NOT_FOR_AI = {
	"agreement.draw_up": "A contract is the workspace's word to its customer, so a person draws it up from the project.",
	"billing.invoice_time": "An invoice goes to the customer, so a person makes the draft and checks it before it goes.",
	"retainer.invoice_month": "An invoice goes to the customer, so a person makes the month's draft and checks it before it goes.",
	"progress.bill_progress": "A progress bill goes to a customer or comes from a supplier, so a person makes it from the order.",
	"budget.remove_budget": "Taking a budget away loosens what the project may spend, so a person does it.",
	"budget.set_time": "What the team's own hours may cost is the manager's to decide, on the project's budget.",
	"contacts.remove": "Taking a customer's contact off the project is the person's decision, made on its page.",
	"kinds.add_contract": "A contract's value is what the customer agreed to, so a person enters it from the agreement.",
	"library.copy": "OneAI starts a template its own way, as a card from draft_template.",
	"materials.give_back": "Materials going back to a store move stock, so whoever counted them records it.",
	"members.let_in": "It follows a mention in a comment the person writes.",
	"team.remove": "Taking somebody off a project ends what they see of it, so a person does it.",
	"team.show": "What a customer's contact sees on the portal is the workspace's decision, made on the Team view.",
	"template_view.add": "OneAI shapes a template its own way, as a card from draft_template.",
	"template_view.change": "OneAI shapes a template its own way, as a card from draft_template.",
	"template_view.nest": "OneAI shapes a template its own way, as a card from draft_template.",
	"template_view.remove": "OneAI shapes a template its own way, as a card from draft_template.",
	"template_view.wait": "OneAI shapes a template its own way, as a card from draft_template.",
	"templates.add": "OneAI starts a project from a template as a card from draft_project.",
	"templates.save_as": "Making the workspace a template from a project is a person's choice of what to keep.",
	"tree.group_under": "Moving projects under a new one changes who sees them, so a person does it.",
	"updates.post": "OneAI drafts the update with draft_update, and the person posts it in their own name.",
}

HR = "Employee Boarding"

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
CHASE = {
	"label": _lt("Remind a customer of an overdue invoice"),
	"ask": _lt(
		"Which of this project's invoices are past their date? Draft a short, polite reminder for the one "
		"most overdue, as a card I can approve."
	),
	"can": "read",
	"expects": "remind_customer",
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

BILLED = (kinds.FIXED, kinds.TIME, kinds.RETAINER)


def _here(*offered, kinds: tuple | None = None) -> list[dict]:
	"""Suggestions on a project's form: checked on the project it is open on,
	and, with `kinds`, only on a project of those kinds."""
	said = []
	for one in offered:
		one = {**one, "doctype": one.get("doctype") or "Project"}
		if kinds:
			one["when"] = {"one_kind": list(kinds)}
		said.append(one)
	return said


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

WEEK = {
	"label": _lt("Who has too much on this week?"),
	"ask": _lt(
		"Who has too much on this week? Say who is over their hours or close to it, who has late tasks or "
		"tasks with no estimate, and who has room to take some on."
	),
	"can": "read",
	"expects": "run_report",
}

SUGGESTIONS = {
	"report:Workload": [WEEK],
	"Project Template": [{**DRAFT_TEMPLATE, "view": "List"}, {**DRAFT_TEMPLATE, "view": "Form"}],
	"Project": [
		*(
			{**one, "view": "Form"}
			for one in _here(ALLOWANCE, kinds=(kinds.RETAINER,))
			+ _here(DRAFT, GOING, LATE)
			+ _here(UPDATE, kinds=BILLED)
			+ _here(PLAN, MONEY, SUPPLIERS)
			+ _here(UNBILLED, CHASE, kinds=BILLED)
			+ _here(TIME, LOAD)
		),
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
		{
			"label": _lt("Start a project"),
			"ask": _lt(
				"Start a new project. Ask me what it is, who it is for and when it runs, then offer a template "
				"we have or one from the library."
			),
			"can": "create",
			"view": "List",
			"expects": "draft_project",
		},
	],
}


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
		"invoices": _invoices(project),
		"kind": doc.get("one_kind"),
		"time": _time(project, doc.get("one_kind")),
		"team": _team(project),
		"contacts": _contacts(project),
		"months": _months(project) if doc.get("one_kind") == kinds.RETAINER else None,
		"payment_terms": doc.get("one_payment_terms"),
		"terms_and_conditions": doc.get("one_terms"),
		"contracts": [
			{key: value for key, value in one.items() if key != "route"}
			for one in agreement.contracts(said["tree"])
		],
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


def remind_customer(
	invoice: Annotated[str, "The customer's invoice, such as ACC-SINV-2026-00016."],
	mail: Annotated[
		str,
		"The whole mail, as it should be sent: greeting, what is owed and since when, how to pay, and "
		"closing, in the customer's language. Polite and short. Plain text; paragraphs apart by a blank "
		"line. No signature: the mailbox adds its own.",
	],
	why: Annotated[str, "In a sentence, why remind them now."] | None = None,
) -> dict:
	"""Suggest a reminder to the customer about an invoice still owed, as a
	card the reader approves. Read project_facts first: its `invoices` lists
	those past their date. Approving opens the email window on the invoice
	with the mail written in and its print attached, to be read, changed and
	sent by the reader: nothing is sent from here."""
	from onedesk.one_ai import proposals

	if not frappe.db.exists("Sales Invoice", invoice) or not frappe.has_permission(
		"Sales Invoice", "read", doc=invoice
	):
		return {"error": f"No invoice the reader may see is {invoice}."}
	held = frappe.get_doc("Sales Invoice", invoice)
	if held.docstatus != 1 or held.is_return or flt(held.outstanding_amount) <= 0:
		return {"error": f"{invoice} owes nothing, so there is nothing to remind them of."}
	if not frappe.has_permission("Sales Invoice", "email", doc=held):
		return {"error": "The reader may not email invoices."}
	text = (mail or "").strip()
	if not text:
		return {"error": "Write the mail itself."}
	to = held.contact_email or frappe.db.get_value("Customer", held.customer, "email_id") or ""
	return {
		"proposal": proposals.propose(
			"Mail",
			"Sales Invoice",
			changes={"recipients": to, "subject": _("Invoice {0}").format(invoice), "text": text},
			record=invoice,
			why=why,
		),
		"state": "Proposed",
		"next": "Tell them Approve opens the mail on the invoice to read, change and send; it is not sent "
		"until they send it."
		+ ("" if to else " The customer has no email address, so they add who it goes to."),
	}


def add_member(
	project: Annotated[str, "The project's id, such as PROJ-0005."],
	user: Annotated[str, "Who joins it: their email, or their full name."],
	why: Annotated[str, "In a sentence, why they join."] | None = None,
) -> dict:
	"""Suggest somebody in the workspace joins a project's team, as a card
	the reader approves. Approving adds them as the Team view's Add Member
	does: the project is shared with them and they are told."""
	from onedesk.one_ai import proposals

	if not frappe.db.exists("Project", project) or not frappe.has_permission("Project", "read", doc=project):
		return {"error": f"No project the reader may see is {project}."}
	if not frappe.has_permission("Project", "write", doc=project):
		return {"error": "The reader may not change who is on this project."}
	said = (user or "").strip()
	found = (
		[said]
		if frappe.db.exists("User", {"name": said, "enabled": 1, "user_type": "System User"})
		else frappe.get_all(
			"User",
			filters={"full_name": ["like", f"%{said}%"], "enabled": 1, "user_type": "System User"},
			pluck="name",
			limit=3,
		)
	)
	found = [one for one in found if one not in ("Administrator", "Guest")]
	if len(found) != 1:
		return {
			"mend": "add_member",
			"error": f"{len(found) or 'Nobody'} in the workspace matches {said}. Ask who they mean, by email.",
		}
	who = found[0]
	if frappe.db.exists("Project User", {"parenttype": "Project", "parent": project, "user": who}):
		return {"error": f"{get_fullname(who)} is on the project already."}
	title = frappe.db.get_value("Project", project, "project_name") or project
	changes = {
		"what": "member",
		"title": _("Add {0} to {1}").format(get_fullname(who), title),
		"project": project,
		"user": who,
		"summary": [{"label": _("Member"), "value": f"{get_fullname(who)} ({who})"}],
		"route": ["Form", "Project", project],
	}
	return {
		"proposal": proposals.propose("Setup", "Project", changes=changes, record=project, why=why),
		"state": "Proposed",
		"next": "Say in one sentence that approving adds them and tells them. Nothing changes until they approve it.",
	}


def set_status(
	project: Annotated[str, "The project's id, such as PROJ-0005."],
	status: Annotated[str, "Open, On hold, Completed or Cancelled."],
	close_work: Annotated[bool, "Completing or cancelling it closes its open tasks and sub-projects too. Only when the reader agreed."] = False,
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest a project's status, as a card the reader approves. A project
	with open work is completed or cancelled only with that work, so ask
	first and pass close_work. Approving sets it as the page's status does,
	and its people are told.

	Approving runs status.change."""
	from onedesk.one_ai import proposals
	from onedesk.one_project import status as states

	if not frappe.db.exists("Project", project) or not frappe.has_permission("Project", "read", doc=project):
		return {"error": f"No project the reader may see is {project}."}
	if not frappe.has_permission("Project", "write", doc=project):
		return {"error": "The reader may not change this project."}
	if status not in states.STATUSES:
		return {"mend": "set_status", "error": f"The status is one of {', '.join(states.STATUSES)}."}
	doc = frappe.db.get_value("Project", project, ["project_name", "status"], as_dict=True)
	if doc.status == status:
		return {"error": f"{doc.project_name} is {status} already."}
	open_work = states.ask(project) if status in states.CLOSED else {"tasks": 0, "projects": 0}
	if (open_work["tasks"] or open_work["projects"]) and not close_work:
		return {
			"mend": "set_status",
			"error": f"{doc.project_name} has {open_work['tasks']} open tasks and {open_work['projects']} open "
			"sub-projects. Ask whether to close them with it, then pass close_work.",
		}
	summary = [{"label": _("Status"), "value": str(states.LABELS[status])}]
	if open_work["tasks"] or open_work["projects"]:
		summary.append(
			{
				"label": _("Closes"),
				"value": _("{0} open tasks and {1} sub-projects").format(open_work["tasks"], open_work["projects"]),
			}
		)
	changes = {
		"what": "status",
		"title": _("Mark {0} {1}").format(doc.project_name, states.LABELS[status]),
		"project": project,
		"status": status,
		"close": int(bool(close_work)),
		"summary": summary,
	}
	return {
		"proposal": proposals.propose("Setup", "Project", changes=changes, record=project, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what approving it does. Nothing changes until they approve it.",
	}


def add_milestone(
	project: Annotated[str, "The project's id, such as PROJ-0005."],
	subject: Annotated[str, "What the milestone is, as the team will say it: Frames installed."],
	due: Annotated[str, "When it is due, YYYY-MM-DD, inside the project's dates."],
	bill_share: Annotated[float, "On a contract billed on milestones, the share of it billed when this is done, 0 to 100."] | None = None,
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest a milestone on a project, as a card the reader approves.
	Approving adds it as Add Milestone does. Together a project's milestones
	bill at most all of its contract.

	The contract's limit is milestones.kept."""
	from onedesk.one_ai import proposals

	if not frappe.db.exists("Project", project) or not frappe.has_permission("Project", "read", doc=project):
		return {"error": f"No project the reader may see is {project}."}
	if not frappe.has_permission("Task", "create"):
		return {"error": "The reader may not add tasks."}
	subject = (subject or "").strip()
	if not subject:
		return {"mend": "add_milestone", "error": "Give the milestone a name."}
	try:
		day = getdate(due)
	except Exception:
		return {"mend": "add_milestone", "error": "The due date is YYYY-MM-DD."}
	share = flt(bill_share)
	if share < 0 or share > 100:
		return {"mend": "add_milestone", "error": "A milestone bills between 0 and 100% of the contract."}
	billed = sum(
		flt(one)
		for one in frappe.get_all(
			"Task", filters={"project": project, "is_milestone": 1, "status": ["!=", "Cancelled"]}, pluck="one_bill_share"
		)
	)
	if share and billed + share > 100.005:
		return {"mend": "add_milestone", "error": f"The project's milestones bill {billed:g}% already. At most {100 - billed:g}% is left."}
	title = frappe.db.get_value("Project", project, "project_name") or project
	summary = [
		{"label": _("Milestone"), "value": subject},
		{"label": _("Due Date"), "value": frappe.format_value(day, {"fieldtype": "Date"})},
	]
	if share:
		summary.append({"label": _("Bill on Completion"), "value": f"{share:g}%"})
	changes = {
		"what": "milestone",
		"title": _("Add {0} to {1}").format(subject, title),
		"project": project,
		"values": {"subject": subject, "exp_end_date": str(day), "one_bill_share": share},
		"summary": summary,
	}
	return {
		"proposal": proposals.propose("Setup", "Project", changes=changes, record=project, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what approving it adds. Nothing is added until they approve it.",
	}


def log_time(
	project: Annotated[str, "The project's id, such as PROJ-0005."],
	hours: Annotated[float, "How long, in hours."],
	activity: Annotated[str, "The activity, which prices the hours: Installation, Design, Project Management."],
	date: Annotated[str, "The day the work was done, YYYY-MM-DD."] | None = None,
	task: Annotated[str, "The task it was on, by its id, if any."] | None = None,
	description: Annotated[str, "What was done, in a sentence."] | None = None,
) -> dict:
	"""Suggest an entry on the reader's own timesheet for the week, as a card
	the reader approves. Approving logs it as Time's Log Time does, billable
	as the project bills hours.

	Approving runs hours.log."""
	from onedesk.one_ai import proposals

	if not frappe.db.exists("Project", project) or not frappe.has_permission("Project", "read", doc=project):
		return {"error": f"No project the reader may see is {project}."}
	if not frappe.has_permission("Timesheet", "create"):
		return {"error": "The reader may not log time."}
	if flt(hours) <= 0 or flt(hours) > 24:
		return {"mend": "log_time", "error": "Give the hours, more than 0 and at most 24."}
	if not frappe.db.exists("Activity Type", activity):
		names = frappe.get_all("Activity Type", filters={"disabled": 0}, pluck="name")
		return {"mend": "log_time", "error": f"The activity is one of {', '.join(names)}."}
	if task and frappe.db.get_value("Task", task, "project") not in tree.below({project}, tree.parents()):
		return {"mend": "log_time", "error": f"{task} is not a task on this project."}
	day = getdate(date or nowdate())
	title = frappe.db.get_value("Project", project, "project_name") or project
	summary = [
		{"label": _("Hours"), "value": f"{flt(hours):g}"},
		{"label": _("Activity"), "value": activity},
		{"label": _("Date"), "value": frappe.format_value(day, {"fieldtype": "Date"})},
		*([{"label": _("Task"), "value": frappe.db.get_value("Task", task, "subject")}] if task else []),
	]
	changes = {
		"what": "time",
		"title": _("Log {0} h on {1}").format(f"{flt(hours):g}", title),
		"project": project,
		"values": {"date": str(day), "hours": flt(hours), "activity_type": activity, "task": task, "description": description},
		"summary": summary,
	}
	return {
		"proposal": proposals.propose("Setup", "Project", changes=changes, record=project, why=description),
		"state": "Proposed",
		"next": "Say in one sentence what approving it logs. Nothing is logged until they approve it.",
	}


def set_cost_budget(
	project: Annotated[str, "The project's id, such as PROJ-0005."],
	cost_type: Annotated[str, "The cost type, by its name as Money lists it: Site Labour, Subcontract Costs."],
	amount: Annotated[float, "Its budget, in the company's currency."],
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest a cost type's budget on a project, new or changed, as a card
	the reader approves. Approving sets it as Money's Add Cost Type does, and
	it warns when an order or expense goes over.

	Approving runs budget.set_budget."""
	from onedesk.one_ai import proposals

	if not frappe.db.exists("Project", project) or not frappe.has_permission("Project", "read", doc=project):
		return {"error": f"No project the reader may see is {project}."}
	if not frappe.has_permission("Budget", "create"):
		return {"error": "The reader may not set budgets."}
	if flt(amount) <= 0:
		return {"mend": "set_cost_budget", "error": "Give the budget, more than 0."}
	company = frappe.db.get_value("Project", project, "company")
	account = frappe.db.get_value(
		"Account", {"company": company, "account_name": cost_type, "is_group": 0, "root_type": "Expense"}
	) or (cost_type if frappe.db.exists("Account", {"name": cost_type, "company": company, "is_group": 0}) else None)
	if not account:
		return {"mend": "set_cost_budget", "error": f"There is no expense account called {cost_type}."}
	title = frappe.db.get_value("Project", project, "project_name") or project
	currency = money.currency(project)
	changes = {
		"what": "budget",
		"title": _("Budget {0} on {1}").format(cost_type, title),
		"project": project,
		"values": {"account": account, "amount": flt(amount)},
		"summary": [
			{"label": _("Cost Type"), "value": cost_type},
			{"label": _("Budget"), "value": frappe.format_value(flt(amount), {"fieldtype": "Currency"}, currency=currency)},
		],
	}
	return {
		"proposal": proposals.propose("Setup", "Project", changes=changes, record=project, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what approving it sets. Nothing changes until they approve it.",
	}


def add_contact(
	project: Annotated[str, "The project's id, such as PROJ-0005."],
	role: Annotated[
		str,
		"What they are on it: Subcontractor, Supplier, Consultant, Architect, Engineer, Client's "
		"Representative, Authority or Other.",
	],
	contact: Annotated[str, "The person, a Contact's id, when there is one."] | None = None,
	supplier: Annotated[str, "Their company when it is a supplier, the Supplier's id."] | None = None,
	organisation: Annotated[str, "Their company when it is not a supplier."] | None = None,
	note: Annotated[str, "A few words on them."] | None = None,
	why: Annotated[str, "In a sentence, why add them."] | None = None,
) -> dict:
	"""Suggest somebody outside the company is listed on a project's Team ›
	Contacts, as a card the reader approves. Approving adds them as the Team
	view's Add Contact does."""
	from onedesk.one_ai import proposals
	from onedesk.one_project import contacts

	if not frappe.db.exists("Project", project) or not frappe.has_permission("Project", "read", doc=project):
		return {"error": f"No project the reader may see is {project}."}
	if not frappe.has_permission("Project", "write", doc=project):
		return {"error": "The reader may not change this project's contacts."}
	if role not in contacts.ROLES:
		return {"mend": "add_contact", "error": f"Pick the role from {', '.join(contacts.ROLES)}."}
	if not (contact or supplier or organisation):
		return {"mend": "add_contact", "error": "Give the contact, the supplier or the company."}
	for doctype, name in (("Contact", contact), ("Supplier", supplier)):
		if name and not frappe.db.exists(doctype, name):
			return {"mend": "add_contact", "error": f"There is no {doctype} called {name}."}
	person = frappe.db.get_value("Contact", contact, "full_name") if contact else None
	company = (
		frappe.db.get_value("Supplier", supplier, "supplier_name") if supplier else None
	) or organisation
	title = frappe.db.get_value("Project", project, "project_name") or project
	changes = {
		"what": "contact",
		"title": _("Add {0} to {1}").format(person or company, title),
		"project": project,
		"values": {
			"role": role,
			"contact": contact or None,
			"supplier": supplier or None,
			"organisation": None if supplier else organisation or None,
			"note": (note or "").strip() or None,
		},
		"summary": [
			{"label": _("Role"), "value": _(role)},
			*([{"label": _("Contact"), "value": person}] if person else []),
			*([{"label": _("Company"), "value": company}] if company else []),
			*([{"label": _("Note"), "value": note.strip()}] if (note or "").strip() else []),
		],
		"route": ["Form", "Project", project],
	}
	return {
		"proposal": proposals.propose("Setup", "Project", changes=changes, record=project, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what approving it adds. Nothing changes until they approve it.",
	}


def approved(changes: dict) -> str:
	"""A project, status, milestone, time, budget, member or contact card
	approved, made by the page's own code as whoever pressed Approve
	(one_studio/ai_setup.py)."""
	from onedesk.one_project import contacts, team

	if changes["what"] == "project":
		return kinds.make(changes["values"])
	if changes["what"] == "status":
		from onedesk.one_project import status

		status.change(changes["project"], changes["status"], changes.get("close") or 0)
	elif changes["what"] == "milestone":
		frappe.get_doc({"doctype": "Task", "project": changes["project"], "is_milestone": 1, **changes["values"]}).insert()
	elif changes["what"] == "time":
		from onedesk.one_project import hours

		hours.log(changes["project"], **changes["values"])
	elif changes["what"] == "budget":
		from onedesk.one_project import budget

		budget.set_budget(changes["project"], changes["values"]["account"], changes["values"]["amount"])
	elif changes["what"] == "member":
		team.add(changes["project"], changes["user"])
	else:
		contacts.save(changes["project"], **changes["values"])
	return changes["project"]


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
		"route": ["Form", "Project Template", title],
	}
	return {
		"proposal": proposals.propose("Setup", "Project Template", changes=changes, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what approving it does. Nothing is made until they approve it.",
	}


def draft_project(
	title: Annotated[str, "What the job is called, as the team will say it: Head Office Move."],
	kind: Annotated[str, "Fixed Price, Time and Materials, Retainer or Internal."],
	customer: Annotated[str, "Who it is for, by the customer's name. None for an Internal project."]
	| None = None,
	starts: Annotated[str, "When it starts, YYYY-MM-DD."] | None = None,
	ends: Annotated[str, "When it should end, YYYY-MM-DD."] | None = None,
	template: Annotated[str, "A template the workspace has, by name (project_templates)."] | None = None,
	library: Annotated[str, "Or a preset from the library, by its key (project_templates)."] | None = None,
	contract: Annotated[float, "Fixed Price: what the customer pays, in their currency."] | None = None,
	item: Annotated[str, "Fixed Price with a contract: the item to bill it as."] | None = None,
	monthly_fee: Annotated[float, "Retainer: the fee each month."] | None = None,
	monthly_hours: Annotated[float, "Retainer: the hours each month covers."] | None = None,
	why: Annotated[str, "In a sentence, why this project."] | None = None,
) -> dict:
	"""Suggest a new project, as a card the reader approves. Read
	project_templates first and offer a template. Approving makes it as the
	New Project dialog does, with the customer's terms, and opens it.

	Approving runs kinds.make."""
	from onedesk.one_ai import proposals
	from onedesk.one_project import library as presets

	if not frappe.has_permission("Project", "create"):
		return {"error": "The reader may not start projects. A Projects User or Manager may."}
	title = (title or "").strip()
	if not title:
		return {"mend": "draft_project", "error": "Give the project a name."}
	if kind not in kinds.KINDS:
		return {"mend": "draft_project", "error": f"The kind is one of {', '.join(kinds.KINDS)}."}
	client = None
	if kind != kinds.INTERNAL:
		client = frappe.db.get_value("Customer", customer) or frappe.db.get_value(
			"Customer", {"customer_name": customer}
		)
		if not client:
			return {
				"mend": "draft_project",
				"error": f"There is no customer called {customer}. Ask who it is for.",
			}
	if template and not frappe.db.exists("Project Template", template):
		return {"mend": "draft_project", "error": f"There is no template called {template}."}
	if library and library not in {one["key"] for one in presets.presets()}:
		return {"mend": "draft_project", "error": f"The library has no preset {library}."}
	if starts and ends and getdate(ends) < getdate(starts):
		return {"mend": "draft_project", "error": "It ends before it starts."}
	if kind == kinds.FIXED and flt(contract) and not (item and frappe.db.exists("Item", item)):
		return {"mend": "draft_project", "error": "A contract is billed as an item. Ask which, by its code."}
	values = {
		"title": title,
		"kind": kind,
		"client": client,
		"starts": starts or nowdate(),
		"ends": ends,
		"template": template,
		"library": library if not template else None,
		"contract": flt(contract) if kind == kinds.FIXED else 0,
		"item": item if kind == kinds.FIXED else None,
		"monthly_fee": flt(monthly_fee) if kind == kinds.RETAINER else 0,
		"monthly_hours": flt(monthly_hours) if kind == kinds.RETAINER else 0,
	}
	currency = kinds.defaults(client)["currency"] if client else None
	summary = [
		{"label": _("Kind"), "value": _(kind)},
		*([{"label": _("Customer"), "value": client}] if client else []),
		{"label": _("Starts"), "value": frappe.format_value(values["starts"], {"fieldtype": "Date"})},
		*([{"label": _("Ends"), "value": frappe.format_value(ends, {"fieldtype": "Date"})}] if ends else []),
		*([{"label": _("Template"), "value": template or library}] if template or library else []),
		*(
			[
				{
					"label": _("Contract"),
					"value": frappe.format_value(values["contract"], {"fieldtype": "Currency"}, currency=currency),
				}
			]
			if values["contract"]
			else []
		),
		*(
			[
				{
					"label": _("Monthly Fee"),
					"value": frappe.format_value(values["monthly_fee"], {"fieldtype": "Currency"}, currency=currency),
				}
			]
			if values["monthly_fee"]
			else []
		),
	]
	changes = {"what": "project", "title": title, "values": values, "summary": summary}
	return {
		"proposal": proposals.propose("Setup", "Project", changes=changes, why=why),
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


def _invoices(project: str) -> dict:
	"""The customer's invoices as the Invoices view adds them up, and those
	past their date, latest first (billing.py). Nothing when the reader may
	not read invoices."""
	from onedesk.one_project import billing

	said = billing._listed(project, "Sales Invoice")
	return {
		"totals": said["totals"],
		"overdue": [
			{
				"invoice": one["name"],
				"customer": one["party"],
				"due": one["due"],
				"days_late": one["late"],
				"owed": one["owed"],
				"currency": one["currency"],
			}
			for one in sorted(said["rows"], key=lambda one: -(one["late"] or 0))
			if one["late"]
		][:MOST],
	}


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
				for key in (
					"supplier",
					"order",
					"ordered",
					"billed",
					"left",
					"retention",
					"advance",
					"paid",
					"to_pay",
					"overdue",
					"late",
					"due",
				)
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


LONGEST = 4000


def plain(html: str | None) -> str:
	"""An update as text, its paragraphs and line breaks kept. Pure."""
	text = re.sub(r"(?i)<br\s*/?>|</?(p|div|li)\b[^>]*>", "\n", html or "")
	lines = (" ".join(strip_html_tags(line).split()) for line in text.split("\n"))
	return "\n".join(line for line in lines if line)
