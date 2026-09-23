"""Sub-projects: a project under a project, to any depth.

ERPNext keeps a project's money per project — its one Sales Order, its
timesheets, its costs, what it has billed and its margin — and has no project
inside a project. So a separately billable piece of a job is a project of its
own, and the one field this adds is **Parent Project** (`one_parent`). The
handrails on a villa are a project under the villa: their own quotation and
order, their own time and invoices, and ERPNext's totals for them as for any
project. Nothing of ERPNext's is copied or changed.

- **A project cannot sit under itself**, however far down (`validate`).
- **A sub-project takes its parent's customer** when it has none.
- **A parent adds up its tree** (`totals`): its own figures and the whole
  tree's, worked out each time rather than stored, so moving a project in the
  tree is right straight away.
- **Group Under New Project** (`group_under`) puts a new project above one —
  the villa above the windows — and moves it and whichever of its sub-projects
  are ticked underneath, so they become siblings.
- **Members of a project see what is under it** (members.under).
- **Where a task is** reads as a path, Villa › Handrails (`path`), on My Tasks
  and on a project's calendar.
"""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils import flt

#: The field.
PARENT = "one_parent"

#: ERPNext's own figures on Project, which the tree adds up.
FIGURES = (
	"estimated_costing",
	"total_costing_amount",
	"total_purchase_cost",
	"total_consumed_material_cost",
	"total_sales_amount",
	"total_billable_amount",
	"total_billed_amount",
	"gross_margin",
)

#: How much of a path My Tasks shows: the project and what it is under.
SHOWN = 3


def parents() -> dict[str, str]:
	"""Every project's parent, for the tree read once per request."""
	kept = getattr(frappe.local, "one_project_parents", None)
	if kept is None:
		kept = frappe.local.one_project_parents = dict(
			frappe.get_all("Project", filters={PARENT: ["is", "set"]}, fields=["name", PARENT], as_list=True)
		)
	return kept


def forget(doc=None, method=None) -> None:
	frappe.local.one_project_parents = None


def children(of: dict[str, str]) -> dict[str, list[str]]:
	"""Parent to children, from child to parent. Pure."""
	found = {}
	for child, parent in of.items():
		found.setdefault(parent, []).append(child)
	return found


def below(projects: set[str], of: dict[str, str]) -> set[str]:
	"""The projects and everything under them. Pure."""
	down, found, waiting = children(of), set(projects), list(projects)
	while waiting:
		for child in down.get(waiting.pop(), []):
			if child not in found:
				found.add(child)
				waiting.append(child)
	return found


def above(project: str, of: dict[str, str]) -> list[str]:
	"""A project and its parents, nearest first. Pure, and stops on a loop."""
	chain, seen = [project], {project}
	while of.get(chain[-1]) and of[chain[-1]] not in seen:
		chain.append(of[chain[-1]])
		seen.add(chain[-1])
	return chain


def loops(project: str, parent: str | None, of: dict[str, str]) -> bool:
	"""Whether putting `project` under `parent` would put it under itself. Pure."""
	if not parent:
		return False
	return project in above(parent, {**of, project: parent})


def validate(doc, method=None) -> None:
	"""Project validate: under a real project, never under itself, and with
	its parent's customer when it has none."""
	parent = doc.get(PARENT)
	if not parent:
		return
	if loops(doc.name, parent, {k: v for k, v in parents().items() if k != doc.name}):
		title = frappe.db.get_value("Project", parent, "project_name") or parent
		frappe.throw(_("{0} is already under {1}, so it cannot be its parent.").format(title, doc.project_name or doc.name))
	if not doc.customer:
		doc.customer = frappe.db.get_value("Project", parent, "customer")


def path(project: str | None) -> str:
	"""Where a project is, top first, as it reads on a task: Villa › Handrails."""
	if not project:
		return ""
	chain = above(project, parents())[:SHOWN]
	titles = dict(frappe.get_all("Project", filters={"name": ["in", chain]}, fields=["name", "project_name"], as_list=True))
	return " › ".join(titles.get(one) or one for one in reversed(chain))


def add_up(rows: list[dict]) -> dict:
	"""The figures of several projects together. Pure."""
	return {field: sum(flt(row.get(field)) for row in rows) for field in FIGURES}


@frappe.whitelist()
@frappe.read_only()
def totals(project: Annotated[str, "The project at the top of the tree to add up."]) -> dict:
	"""A project's own figures and its whole tree's, with the sub-projects
	directly under it, each with its own tree's figures."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	of = parents()
	tree = below({project}, of)
	rows = {one.name: one for one in frappe.get_all(
		"Project", filters={"name": ["in", list(tree)]}, fields=["name", "project_name", "status", "percent_complete", *FIGURES]
	)}
	down = children(of)
	under = []
	for child in sorted(down.get(project, []), key=lambda one: rows[one].project_name or one):
		if child not in rows or not frappe.has_permission("Project", "read", doc=child):
			continue
		branch = below({child}, of)
		under.append({
			"name": child,
			"title": rows[child].project_name,
			"status": rows[child].status,
			"percent_complete": rows[child].percent_complete,
			"below": len(branch) - 1,
			**add_up([rows[one] for one in branch if one in rows]),
		})
	return {
		"own": add_up([rows[project]]),
		"tree": add_up(list(rows.values())),
		"projects": len(rows),
		"under": under,
		"currency": frappe.db.get_default("currency"),
	}


@frappe.whitelist(methods=["POST"])
def group_under(
	project: Annotated[str, "The project to put under a new one."],
	title: Annotated[str, "What the new project above it is called."],
	bring: Annotated[str | list | None, "Sub-projects of it to move up beside it."] = None,
) -> str:
	"""Make a project above `project`, where it was, and move it and the
	sub-projects in `bring` under the new one."""
	doc = frappe.get_doc("Project", project)
	doc.check_permission("write")
	top = frappe.get_doc({
		"doctype": "Project",
		"project_name": title,
		"customer": doc.customer,
		PARENT: doc.get(PARENT),
		"expected_start_date": doc.expected_start_date,
	}).insert()
	doc.set(PARENT, top.name)
	doc.save()
	for name in frappe.parse_json(bring) if bring else []:
		child = frappe.get_doc("Project", name)
		if child.get(PARENT) != project:
			continue
		child.check_permission("write")
		child.set(PARENT, top.name)
		child.save()
	return top.name


def dashboard(data: dict) -> dict:
	"""Sub-projects on a project's page, first among its connections, so + makes
	one with the parent filled in; and the quotations for work under it."""
	data.setdefault("non_standard_fieldnames", {})["Project"] = PARENT
	data.setdefault("transactions", []).insert(0, {"label": _("Sub-projects"), "items": ["Project"]})
	# Quotations for extra work under it (billing.py), beside its orders.
	data["non_standard_fieldnames"]["Quotation"] = "one_project"
	for group in data["transactions"]:
		if "Sales Order" in group.get("items", []):
			group["items"].insert(group["items"].index("Sales Order"), "Quotation")
			break
	else:
		data["transactions"].append({"label": _("Sales"), "items": ["Quotation"]})
	return data
