"""A project's status: ERPNext's own four (Open, On hold, Completed,
Cancelled), and what closing a project means for the work still in it.
"""

from typing import Annotated

import frappe
from frappe import _, _lt
from frappe.utils import comma_or, flt

from onedesk.one_project import tree

#: ERPNext's four, as they read. ERPNext ships no German for "On hold", so
#: ours carries it, for the page's pill as much as for this module.
LABELS = {
	"Open": _lt("Open"),
	"On hold": _lt("On hold"),
	"Completed": _lt("Completed"),
	"Cancelled": _lt("Cancelled"),
}
STATUSES = tuple(LABELS)
CLOSED = ("Completed", "Cancelled")
#: A task still to be done; a Template task belongs to no project's work.
OPEN_TASK = ["not in", ("Completed", "Cancelled", "Template")]


def _open_below(project: str) -> list[str]:
	"""The project's sub-projects, at any depth, that are still open."""
	under = sorted(tree.below({project}, tree.parents()) - {project})
	if not under:
		return []
	return frappe.get_all(
		"Project", filters={"name": ["in", under], "status": ["not in", CLOSED]}, pluck="name"
	)


def _open_tasks(projects: list[str]) -> list[str]:
	return frappe.get_all("Task", filters={"project": ["in", projects], "status": OPEN_TASK}, pluck="name")


@frappe.whitelist()
@frappe.read_only()
def ask(project: Annotated[str, "The project."]) -> dict:
	"""What closing the project would close with it: its open tasks, and its
	open sub-projects with theirs."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	below = _open_below(project)
	return {"tasks": len(_open_tasks([project, *below])), "projects": len(below)}


def held(doc, method=None) -> None:
	"""Project before_validate, ahead of ERPNext's own status from progress:
	the status holds however it is set (the page, a bulk edit, an import).
	"""
	before = None if doc.is_new() else doc.get_doc_before_save()
	was = before.status if before else None
	if doc.status in CLOSED and was not in CLOSED and not doc.is_new():
		below = _open_below(doc.name)
		tasks = _open_tasks([doc.name, *below])
		if not (below or tasks):
			return
		if not doc.flags.get("one_close_work"):
			frappe.throw(_("{0} still has open work.").format(doc.project_name))
		# As ERPNext's own set_project_status: straight to the status, since a
		# task's own checks (its dependencies done first) don't apply to work
		# being closed.
		for name in tasks:
			frappe.db.set_value("Task", name, "status", doc.status)
		for name in below:
			sub = frappe.get_doc("Project", name)
			if sub.status in CLOSED:
				continue
			sub.status = doc.status
			sub.flags.one_close_work = True
			sub.save()
	elif was == "Completed" and doc.status not in CLOSED:
		if doc.percent_complete_method == "Manual" and not frappe.db.count("Task", {"project": doc.name}):
			doc.percent_complete_method = "Task Completion"


@frappe.whitelist(methods=["POST"])
def change(
	project: Annotated[str, "The project."],
	status: Annotated[str, "Open, On hold, Completed or Cancelled."],
	close: Annotated[int, "Close its open tasks and sub-projects too."] = 0,
) -> str:
	"""Sets the project's status so that it holds, and returns it."""
	if status not in STATUSES:
		frappe.throw(_("Pick {0}.").format(comma_or([str(one) for one in LABELS.values()])))
	doc = frappe.get_doc("Project", project)
	doc.check_permission("write")
	if status in CLOSED:
		below = _open_below(project)
		if (below or _open_tasks([project, *below])) and not int(close):
			frappe.throw(_("{0} still has open work.").format(doc.project_name))
		for name in below:
			frappe.has_permission("Project", "write", doc=name, throw=True)
		doc.flags.one_close_work = bool(int(close))
	elif (
		doc.status == "Completed"
		and status == "Open"
		and doc.percent_complete_method != "Manual"
		and frappe.db.count("Task", {"project": project})
		and not frappe.db.count("Task", {"project": project, "status": OPEN_TASK})
	):
		# What ERPNext's own save would do anyway, said before it does.
		frappe.throw(
			_("Every task on {0} is done, so it stays Completed. Add a task to open it again.").format(
				doc.project_name
			)
		)
	doc.status = status
	doc.save()
	return doc.status


def due(project: str) -> list[dict]:
	"""What's still owed on the project and those under it, whoever reads:
	the contract not invoiced, invoices not paid, and retention held."""
	from onedesk.one_project.money import _lines, _retained

	projects = sorted(tree.below({project}, tree.parents()))
	found = []
	left = _lines("Sales Order", projects) - _lines("Sales Invoice", projects)
	if left > 0.5:
		found.append({"key": "not_invoiced", "text": _("Contract not invoiced yet"), "money": left})
	unpaid = flt(
		frappe.db.sql(
			"""select sum(outstanding_amount * conversion_rate) from `tabSales Invoice`
			where docstatus = 1 and project in %s""",
			(projects,),
		)[0][0]
	)
	if unpaid > 0.5:
		found.append({"key": "unpaid", "text": _("Invoices not paid yet"), "money": unpaid})
	held = _retained(projects)
	if held > 0.5:
		found.append({"key": "retention", "text": _("Retention still held"), "money": held})
	return found
