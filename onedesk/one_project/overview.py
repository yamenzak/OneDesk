"""A project's page answers first: how far it has got, whether it is on time,
what it has cost against what was budgeted, what has been billed against what
there is to bill, what is late and what comes next. Figures, not charts.

All of it is ERPNext's own: `expected_end_date`, `estimated_costing`, the
costing and billing totals it keeps from timesheets, purchases and invoices,
and the project's tasks. A project with sub-projects answers for the whole tree
(tree.py), since the villa's question is about the villa, handrails included.
"""

from typing import Annotated

import frappe
from frappe.utils import date_diff, getdate, nowdate

from onedesk.one_project import members, tree

#: What a task that is still to do cannot be.
DONE = ("Completed", "Cancelled", "Template")


def days_left(end, today, finished: bool) -> int | None:
	"""Days until the expected end, negative once past; None when there is no
	end or the project is finished. Pure."""
	if not end or finished:
		return None
	return date_diff(getdate(end), getdate(today))


def share(done: int, total: int) -> int:
	"""How much of the work is done, out of 100. Pure."""
	return round(100 * done / total) if total else 0


@frappe.whitelist()
@frappe.read_only()
def overview(project: Annotated[str, "The project."]) -> dict:
	frappe.has_permission("Project", "read", doc=project, throw=True)
	user = frappe.session.user
	doc = frappe.db.get_value("Project", project, ["status", "expected_end_date", "percent_complete"], as_dict=True)
	projects = [one for one in tree.below({project}, tree.parents()) if one == project or members.sees(one, user)]
	today = nowdate()

	counts = frappe.get_all(
		"Task",
		filters={"project": ["in", projects], "status": ["not in", ("Cancelled", "Template")]},
		fields=["status", {"COUNT": "*", "as": "n"}],
		group_by="status",
	)
	total = sum(row.n for row in counts)
	done = sum(row.n for row in counts if row.status == "Completed")
	open_ = [["project", "in", projects], ["status", "not in", DONE]]
	late = frappe.db.count("Task", [*open_, ["exp_end_date", "<", today]])
	milestone = frappe.get_all(
		"Task",
		filters=[*open_, ["is_milestone", "=", 1], ["exp_end_date", ">=", today]],
		fields=["name", "subject", "exp_end_date"],
		order_by="exp_end_date asc",
		limit=1,
	)
	money = tree.totals(project)
	figures = money["tree"]
	return {
		"projects": len(projects),
		"tree": sorted(projects),
		"tasks": total,
		"done": done,
		"share": share(done, total) if total else round(doc.percent_complete or 0),
		"end": str(doc.expected_end_date) if doc.expected_end_date else None,
		"days_left": days_left(doc.expected_end_date, today, doc.status in ("Completed", "Cancelled")),
		"estimated": figures["estimated_costing"],
		"cost": figures["total_costing_amount"] + figures["total_purchase_cost"] + figures["total_consumed_material_cost"],
		"billed": figures["total_billed_amount"],
		"to_bill": figures["total_sales_amount"] or figures["total_billable_amount"],
		"margin": figures["gross_margin"],
		"late": late,
		"milestone": milestone[0] if milestone else None,
		"currency": money["currency"],
	}
