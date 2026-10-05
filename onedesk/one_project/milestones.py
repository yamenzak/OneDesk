"""A project's milestones: ERPNext's own tasks marked **Is Milestone**, on the
project or any project under it.

- The Overview shows the last two done and the ones to come, soonest first,
  with those without a date last (`pick`). One on a sub-project says which
  (`where`), and each says how far off or how late it is.
- **Bill on Completion** (`one_bill_share`) is a milestone's share of the
  contract, and it's optional. A project bills by milestones only when one
  of its milestones has a share: Work and Billing then counts the shares of
  the milestones done instead of the work done, and Bill Progress starts
  from that share (`billable`). When such a milestone is done, the manager
  of the project with the order is told to bill it (`reached`).
"""

import frappe
from frappe import _
from frappe.utils import date_diff, flt, get_fullname, getdate, nowdate

from onedesk.one import notify
from onedesk.one_project import tree

#: How many milestones the Overview shows, and how many of those may be done.
SHOWN = 8
DONE_SHOWN = 2


def pick(rows: list[dict]) -> list[dict]:
	"""The last milestones done and the ones to come, soonest first, those
	without a date last. Pure."""
	done = sorted((one for one in rows if one["done"]), key=lambda one: one["due"] or "")[-DONE_SHOWN:]
	ahead = sorted(
		(one for one in rows if not one["done"]), key=lambda one: (not one["due"], one["due"] or "")
	)
	return [*done, *ahead][:SHOWN]


def where(project: str, top: str, of: dict[str, str], titles: dict[str, str]) -> str | None:
	"""Where a milestone is under the page's project, top first, as a path:
	Handrails, then Glass for handrails. None when it's the page's own. Pure."""
	chain = []
	for one in tree.above(project, of):
		if one == top:
			break
		chain.append(one)
	return " › ".join(titles.get(one) or one for one in reversed(chain)) or None


def billable(rows: list[dict]) -> dict | None:
	"""The share of the contract the milestones done come to, and which they
	are, when any milestone is billed on completion. Pure."""
	if not any(flt(one.get("share")) for one in rows):
		return None
	done = [one for one in rows if one["done"] and flt(one.get("share"))]
	return {
		"share": min(100.0, sum(flt(one["share"]) for one in done)),
		"names": [one["subject"] for one in done],
	}


def read(project: str, projects: list[str]) -> dict:
	"""The page's milestones, whether it bills by them, and the projects a
	new one may go on."""
	today = getdate(nowdate())
	found = frappe.get_list(
		"Task",
		filters=[
			["project", "in", projects],
			["is_milestone", "=", 1],
			["status", "not in", ("Cancelled", "Template")],
		],
		fields=["name", "subject", "status", "exp_end_date", "project", "one_bill_share"],
		limit=200,
	)
	titles = dict(
		frappe.get_all(
			"Project", filters={"name": ["in", projects]}, fields=["name", "project_name"], as_list=True
		)
	)
	of = tree.parents()
	rows = [
		{
			"name": one.name,
			"subject": one.subject,
			"done": one.status == "Completed",
			"due": str(getdate(one.exp_end_date)) if one.exp_end_date else None,
			"days": date_diff(one.exp_end_date, today) if one.exp_end_date else None,
			"where": where(one.project, project, of, titles),
			"share": flt(one.one_bill_share),
		}
		for one in found
	]
	return {
		"list": pick(rows),
		"billable": billable(rows),
		"projects": [
			{"value": project, "label": titles.get(project) or project},
			*sorted(
				(
					{"value": one, "label": where(one, project, of, titles)}
					for one in set(projects) - {project}
				),
				key=lambda one: one["label"] or "",
			),
		],
	}


def reached(doc, method=None) -> None:
	"""Task on_update: a milestone billed on completion is done, so the
	manager of the project with the order is told to bill it, unless they
	marked it done."""
	if not doc.is_milestone or not flt(doc.get("one_bill_share")) or not doc.project:
		return
	if doc.status != "Completed" or not doc.has_value_changed("status"):
		return
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_import or frappe.flags.in_patch:
		return
	ordered = frappe.get_all(
		"Sales Order Item",
		filters={"project": ["in", tree.above(doc.project, tree.parents())], "docstatus": 1},
		pluck="project",
		distinct=True,
	)
	chain = [one for one in tree.above(doc.project, tree.parents()) if one in ordered]
	if not chain:
		return
	project = frappe.db.get_value("Project", chain[0], ["name", "project_name", "one_manager"], as_dict=True)
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
