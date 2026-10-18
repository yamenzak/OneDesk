"""Sub-projects: a project under a project, to any depth."""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils import cint, flt

PARENT = "one_parent"

FIGURES = (
	"estimated_costing",
	"total_costing_amount",
	"total_purchase_cost",
	"total_consumed_material_cost",
	"total_expense_claim",
	"total_sales_amount",
	"total_billable_amount",
	"total_billed_amount",
	"gross_margin",
)

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


def narrow(project: str, only=None) -> None:
	"""The page asked for `project`'s own work, its Main: until the request
	ends, `scope(project)` is the project alone. Only ever set, so a call
	inside the request that doesn't ask keeps what the page asked."""
	if cint(only):
		frappe.local.one_project_only = project


def narrowed(project: str) -> bool:
	"""Whether this request reads `project` on its own (`narrow`)."""
	return getattr(frappe.local, "one_project_only", None) == project


def scope(project: str) -> set[str]:
	"""What a project's page counts: it and everything under it, or itself
	alone when the page is narrowed to its Main."""
	return {project} if narrowed(project) else below({project}, parents())


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
	if doc.is_new() and frappe.db.get_value("Project", parent, "status") == "Cancelled":
		title = frappe.db.get_value("Project", parent, "project_name") or parent
		frappe.throw(_("{0} is cancelled. Open it again to add work to it.").format(title))
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
	"""A project's connections: its sub-projects first, so + makes one with the
	parent filled in; then its work and what it used, what the customer was
	quoted, ordered, sent and invoiced, what was asked of, ordered from and
	billed by suppliers, and the payments, each by the project it names
	(chain.py)."""
	data.setdefault("non_standard_fieldnames", {})["Project"] = PARENT
	data["transactions"] = [
		{"label": _("Sub-projects"), "items": ["Project"]},
		{"label": _("Work"), "items": ["Task", "Timesheet", "Project Update", "Expense Claim", "Stock Entry"]},
		{"label": _("Customer"), "items": ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]},
		{
			"label": _("Suppliers"),
			"items": [
				"Material Request",
				"Request for Quotation",
				"Supplier Quotation",
				"Purchase Order",
				"Purchase Receipt",
				"Purchase Invoice",
			],
		},
		{"label": _("Payments"), "items": ["Payment Entry"]},
	]
	return data


FINISHED = ("Completed", "Cancelled", "Template")


@frappe.whitelist()
@frappe.read_only()
def nodes(
	doctype: str = "Project",
	parent: str | None = None,
	is_root: bool | int | str = False,
	closed: bool | int | str = False,
	**filters,
) -> list[dict]:
	"""The projects directly under one, for the Projects list's Tree view
	(frappe's treeview, public/js/project_tree.js): under the root, those at
	the top. Read as the reader reads projects, so a project whose parent they
	may not see is at the top. Finished ones only when `closed` is ticked."""
	from onedesk.one_hr.lifecycle import BOARDING

	where = [["project_type", "!=", BOARDING]]
	if not _yes(closed):
		where.append(["status", "not in", ["Completed", "Cancelled"]])
	rows = frappe.get_list(
		"Project",
		filters=where,
		fields=["name", "project_name", PARENT, "status", "one_health", "percent_complete"],
		limit_page_length=0,
	)
	return under(rows, None if _yes(is_root) else parent)


def _yes(value) -> bool:
	"""A tick as the tree sends it: true, "true", 1 or "1". Pure."""
	return str(value).strip().lower() in ("1", "true", "yes")


def under(rows: list[dict], parent: str | None) -> list[dict]:
	"""The rows directly under `parent`, or at the top when it is None, each
	saying whether anything is under it. Pure."""
	names = {row["name"] for row in rows}
	up = {row["name"]: row.get(PARENT) if row.get(PARENT) in names else None for row in rows}
	has = set(up.values())
	return [
		{
			"value": row["name"],
			"title": row.get("project_name") or row["name"],
			"expandable": row["name"] in has,
			"status": row.get("status"),
			"health": row.get("one_health"),
			"percent": flt(row.get("percent_complete")),
		}
		for row in sorted(rows, key=lambda one: (one.get("project_name") or one["name"]).lower())
		if up[row["name"]] == parent
	]


@frappe.whitelist()
@frappe.read_only()
def milestones(projects: Annotated[list[str] | str, "The projects on the timeline."]) -> list[dict]:
	"""The milestones still to come on these projects, for the Timeline view
	of Projects, read as the reader reads tasks."""
	projects = frappe.parse_json(projects) if isinstance(projects, str) else projects
	if not projects:
		return []
	return frappe.get_list(
		"Task",
		filters=[
			["project", "in", list(projects)[:500]],
			["is_milestone", "=", 1],
			["status", "not in", FINISHED],
			["exp_end_date", "is", "set"],
		],
		fields=["name", "subject", "project", "exp_end_date"],
		order_by="exp_end_date asc",
		limit_page_length=0,
	)
