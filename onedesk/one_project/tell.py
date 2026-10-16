"""Telling people about a project (notifications/one_project/)."""

import frappe
from erpnext import get_company_currency
from frappe import _, _lt
from frappe.utils import add_months, flt, fmt_money, formatdate, get_first_day, get_fullname, getdate, nowdate

from onedesk.one import notify
from onedesk.one_project import kinds, retainer

#: The health worth telling people about.
WORSE = ("At Risk", "Off Track")

#: A status a project's people are told of, as it reads after "is".
STOPPED = {"On hold": _lt("on hold"), "Cancelled": _lt("cancelled")}


def changed(doc, method=None) -> None:
	"""Project on_update: who was added, who now runs it, and how it is going."""
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_import or frappe.flags.in_patch:
		return
	before = doc.get_doc_before_save()
	added(doc, before)
	health(doc, before)
	completed(doc, before)
	stopped(doc, before)
	moved(doc, before)


def added(doc, before) -> None:
	was = {row.user for row in (before.get("users") or [])} if before else set()
	new = sorted({row.user for row in doc.get("users") or []} - was - {"Administrator", "Guest"})
	facts = _facts(doc)
	if new:
		notify.notify("Added to Project", new, record=("Project", doc.name), **facts)
	manager = doc.get("one_manager")
	if (
		manager
		and manager != (before.get("one_manager") if before else None)
		and manager not in ("Administrator", "Guest")
	):
		notify.notify("Made Project Manager", manager, record=("Project", doc.name), **facts)


def health(doc, before) -> None:
	"""Only an open project's health is shown, so only its health is told."""
	said = doc.get("one_health")
	if doc.status != "Open" or said not in WORSE or not before or before.get("one_health") == said:
		return
	people = _people(doc)
	if people:
		notify.notify("Project Health", people, record=("Project", doc.name), health=said, **_facts(doc))


def stopped(doc, before) -> None:
	"""The project's people are told when it is put on hold or cancelled."""
	state = STOPPED.get(doc.status)
	if not state or not before or before.get("status") == doc.status:
		return
	people = _people(doc)
	if people:
		notify.notify("Project Stopped", people, record=("Project", doc.name), state=state, **_facts(doc))


def moved(doc, before) -> None:
	"""The project's people are told when an open project's end moves."""
	was, now = (before.get("expected_end_date") if before else None), doc.get("expected_end_date")
	if doc.status != "Open" or not was or not now or getdate(was) == getdate(now):
		return
	people = _people(doc)
	if people:
		notify.notify(
			"Project End Moved",
			people,
			record=("Project", doc.name),
			ends=formatdate(now),
			was=formatdate(was),
			**_facts(doc),
		)


def _people(doc) -> list[str]:
	"""The project's manager and members."""
	people = {row.user for row in doc.get("users") or []} | {doc.get("one_manager")}
	return sorted(one for one in people if one and one not in ("Administrator", "Guest"))


def completed(doc, before) -> None:
	"""The manager is told when the project is completed, by whoever or by its
	last task, with what's still owed on it (status.due)."""
	if doc.status != "Completed" or not before or before.get("status") == "Completed":
		return
	manager = doc.get("one_manager")
	if not manager or manager in ("Administrator", "Guest") or manager == frappe.session.user:
		return
	from onedesk.one_project.status import due

	owed = sum(one["money"] for one in due(doc.name))
	notify.notify(
		"Project Completed",
		manager,
		record=("Project", doc.name),
		owed=" · " + _("{0} still owed").format(fmt_money(owed, currency=get_company_currency(doc.company)))
		if owed
		else "",
		**_facts(doc),
	)


def _facts(doc) -> dict:
	"""Who did it, the project, and its customer and end date, each led by a
	dot so either may be left out: " · Mansour & Sons · 3 Nov 2026"."""
	return {
		"who": get_fullname(frappe.session.user),
		"project": doc.project_name,
		"customer": f" · {doc.customer}" if doc.get("customer") else "",
		"due": f" · {formatdate(doc.expected_end_date)}" if doc.get("expected_end_date") else "",
	}


def retainer_months() -> None:
	"""Monthly: each open retainer whose last month isn't invoiced, told to
	whoever runs it."""
	last = add_months(get_first_day(getdate(nowdate())), -1)
	for one in frappe.get_all(
		"Project",
		filters={"one_kind": kinds.RETAINER, "status": "Open", "one_monthly_fee": [">", 0]},
		fields=[
			"name",
			"project_name",
			"customer",
			"one_monthly_hours",
			"one_manager",
			"owner",
			"creation",
			"expected_start_date",
		],
	):
		if get_first_day(getdate(one.expected_start_date or one.creation)) > last:
			continue
		if retainer.invoiced(one.name, last):
			continue
		said = _retainer(one, retainer.logged(one.name, last))
		if said:
			notify.notify("Retainer Month to Invoice", **said)


def hours_used(doc, method=None) -> None:
	"""Timesheet on_submit: a retainer whose hours this month the timesheet
	takes past its allowance."""
	month = get_first_day(getdate(nowdate()))
	here: dict[str, float] = {}
	for row in doc.get("time_logs") or []:
		if row.project and row.from_time and get_first_day(getdate(row.from_time)) == month:
			here[row.project] = here.get(row.project, 0.0) + flt(row.hours)
	if not here:
		return
	for one in frappe.get_all(
		"Project",
		filters={"name": ["in", list(here)], "one_kind": kinds.RETAINER, "one_monthly_hours": [">", 0]},
		fields=["name", "project_name", "customer", "one_monthly_hours", "one_manager", "owner"],
	):
		hours = retainer.logged(one.name, month)
		if hours - here[one.name] < flt(one.one_monthly_hours) <= hours:
			said = _retainer(one, hours)
			if said:
				notify.notify("Retainer Hours Used", **said)


def _retainer(one, hours: float) -> dict | None:
	"""Who to tell about a retainer, and what: its manager, or whoever made it."""
	person = one.one_manager or one.owner
	if not person or person in ("Administrator", "Guest"):
		return None
	return {
		"users": person,
		"record": ("Project", one.name),
		"project": one.project_name,
		"hours": f"{flt(hours, 1):g}",
		"allowance": f"{flt(one.one_monthly_hours, 1):g}",
		"customer": f" · {one.customer}" if one.customer else "",
	}


def over_plan(doc, method=None) -> None:
	"""Task on_update: its logged hours (ERPNext's Actual Time, from
	submitted timesheets) just passed its planned hours (Expected Time). Told
	once, as they pass, to whoever has the task and the project's manager."""
	planned = flt(doc.expected_time)
	before = doc.get_doc_before_save()
	if planned <= 0 or not before or not doc.has_value_changed("actual_time"):
		return
	if not (flt(before.actual_time) <= planned < flt(doc.actual_time)):
		return
	people = set(frappe.parse_json(doc.get("_assign") or "[]"))
	head = (
		frappe.db.get_value("Project", doc.project, ["project_name", "one_manager"], as_dict=True)
		if doc.project
		else None
	)
	if head and head.one_manager:
		people.add(head.one_manager)
	people = sorted(one for one in people if one not in ("Administrator", "Guest", frappe.session.user))
	if people:
		notify.notify(
			"Hours Over Plan",
			people,
			record=("Task", doc.name),
			task=doc.subject,
			project=f" · {head.project_name}" if head else "",
			logged=f"{flt(doc.actual_time, 1):g}",
			planned=f"{planned:g}",
		)


def time_over(doc, method=None) -> None:
	"""Timesheet on_submit: a project's logged hours passing its planned
	hours, or its time's cost passing its Time Budget, told to its manager
	once, as they pass. Counted over the project and those under it, as its
	Time view counts them."""
	from onedesk.one_project import hours, tree

	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_import or frappe.flags.in_patch:
		return
	named = {row.project for row in doc.get("time_logs") or [] if row.project}
	if not named:
		return
	of = tree.parents()
	for project in sorted({one for name in named for one in tree.above(name, of)}):
		scope = sorted(tree.below({project}, of))
		rows = [row for row in doc.time_logs if row.project in scope]
		if not rows:
			continue
		head = frappe.db.get_value("Project", project, ["project_name", "one_manager", "company"], as_dict=True)
		if not head or not head.one_manager or head.one_manager in ("Administrator", "Guest", frappe.session.user):
			continue
		whole = frappe.get_all("Project", filters={"name": ["in", scope]}, fields=["one_hours_planned", "one_time_budget"])
		plan = hours.planned(scope) or sum(flt(one.one_hours_planned) for one in whole)
		budget = sum(flt(one.one_time_budget) for one in whole)
		logged, cost = frappe.db.sql(
			"""select sum(log.hours), sum(log.base_costing_amount) from `tabTimesheet Detail` log
			join `tabTimesheet` sheet on sheet.name = log.parent
			where sheet.docstatus = 1 and log.project in %s""",
			(scope,),
		)[0]
		logged, cost = flt(logged), flt(cost)
		here = sum(flt(row.hours) for row in rows)
		if plan and logged - here <= plan < logged:
			notify.notify(
				"Hours Over Plan",
				head.one_manager,
				record=("Project", project),
				task=head.project_name,
				project="",
				logged=f"{flt(logged, 1):g}",
				planned=f"{plan:g}",
			)
		spent = sum(flt(row.base_costing_amount) for row in rows)
		if budget and cost - spent <= budget < cost:
			currency = get_company_currency(head.company)
			notify.notify(
				"Over Budget",
				head.one_manager,
				record=("Project", project),
				project=head.project_name,
				cost_type=_("Time"),
				total=fmt_money(cost, precision=0, currency=currency),
				budget=fmt_money(budget, precision=0, currency=currency),
			)


def over_budget(project: str, gone: list[dict]) -> None:
	"""Cost types past their budget, told to the project's manager and whoever set each."""
	head = frappe.db.get_value("Project", project, ["project_name", "one_manager", "company"], as_dict=True)
	currency = get_company_currency(head.company)
	for one in gone:
		people = sorted({head.one_manager, one["set_by"]} - {None, "Administrator", "Guest"})
		if people:
			notify.notify(
				"Over Budget",
				people,
				record=("Budget", one["budget_name"]),
				link=f"/desk/project/{project}",
				dedupe_on=["document_type", "document_name"],
				project=head.project_name,
				cost_type=one["cost_type"],
				total=fmt_money(one["committed"] + one["spent"], precision=0, currency=currency),
				budget=fmt_money(one["budget"], precision=0, currency=currency),
			)


def milestone_done(doc, ordered: str) -> None:
	"""A milestone billed on completion is done, told to the manager of the project with the order."""
	project = frappe.db.get_value("Project", ordered, ["name", "project_name", "one_manager"], as_dict=True)
	if not project.one_manager or project.one_manager in ("Administrator", "Guest", frappe.session.user):
		return
	notify.notify(
		"Milestone Done",
		project.one_manager,
		record=("Project", project.name),
		who=get_fullname(frappe.session.user),
		milestone=doc.subject,
		project=project.project_name,
		share=_("{0}% of the contract").format(f"{flt(doc.one_bill_share):g}"),
	)


def progress_drafted(doc, project: str, order: str | None) -> None:
	"""A bill for a share of the work was drafted, told to the project's manager to check."""
	head = frappe.db.get_value("Project", project, ["project_name", "one_manager"], as_dict=True)
	if not head or not head.one_manager:
		return
	notify.notify(
		"Progress Bill Drafted",
		head.one_manager,
		record=(doc.doctype, doc.name),
		who=get_fullname(frappe.session.user),
		share=f"{flt(doc.one_progress):g}",
		order=order or doc.name,
		project=head.project_name,
		party=doc.get("supplier_name") or doc.get("customer_name") or "",
		amount=fmt_money(doc.grand_total, currency=doc.currency),
	)


def retention_due(doctype: str, name: str, project: str, amount: float, company: str, party: str) -> None:
	"""Retention on an invoice falls due today, told to the project's manager."""
	kept_by = frappe.db.get_value("Project", project, ["project_name", "one_manager"], as_dict=True)
	if not kept_by or not kept_by.one_manager:
		return
	money = fmt_money(amount, currency=frappe.get_cached_value("Company", company, "default_currency"))
	notify.notify(
		"Retention Due",
		kept_by.one_manager,
		record=(doctype, name),
		project=kept_by.project_name,
		held=(_("{0} held by {1}") if doctype == "Sales Invoice" else _("{0} held from {1}")).format(
			money, party
		),
	)


def bill_due(name: str, project: str, amount: float, currency: str, supplier: str) -> None:
	"""A supplier's bill on the project falls due today, told to its manager."""
	head = frappe.db.get_value("Project", project, ["project_name", "one_manager"], as_dict=True)
	if not head or not head.one_manager:
		return
	notify.notify(
		"Bill Due",
		head.one_manager,
		record=("Purchase Invoice", name),
		project=head.project_name,
		owed=_("{0} to {1}").format(fmt_money(amount, currency=currency), supplier),
	)


def update_asked(doc, people: list[str], update) -> None:
	"""The team is asked for a status update, in One, and mailed where mail goes."""
	# The project's own question, where it has one, over the type's text.
	words = (doc.subject, doc.message)
	notify.notify(
		"Project Update Asked",
		people,
		record=("Project", doc.name),
		words=words,
		mailed=False,
		project=doc.project_name,
	)
	if _mail():
		notify.mail(
			"Project Update Asked",
			[frappe.db.get_value("User", user, "email") for user in people],
			words=words,
			reference_doctype="Project Update",
			reference_name=update.name,
			reply_to=frappe.db.get_value(
				"Email Account", {"enable_incoming": 1, "default_incoming": 1}, "email_id"
			),
			project=doc.project_name,
		)


def _mail() -> bool:
	return bool(frappe.db.exists("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}))


def update_summary(update, yesterday: str) -> None:
	"""Yesterday's answers to a status update, told to the project's people."""
	from frappe.utils.html_utils import sanitize_html
	from markupsafe import Markup

	answers = Markup("").join(
		Markup("<p><b>{0}</b>: {1}</p>").format(
			row.full_name or row.user, Markup(sanitize_html(row.project_status or ""))
		)
		for row in update.users
	)
	notify.notify(
		"Project Summary",
		frappe.get_all(
			"Project User", filters={"parenttype": "Project", "parent": update.project}, pluck="user"
		),
		record=("Project", update.project),
		project=frappe.db.get_value("Project", update.project, "project_name") or update.project,
		date=formatdate(yesterday),
		answers=answers,
	)
