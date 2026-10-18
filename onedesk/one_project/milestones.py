"""A project's milestones: ERPNext's own tasks marked **Is Milestone**, on the
project or any project under it.
"""

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, nowdate

from onedesk.one_project import tree

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


def lane(project: str, top: str, of: dict[str, str]) -> str:
	"""Which part of the page's job a project's milestone belongs to: the page's
	own project, or the sub-project directly under it that it sits in. Pure."""
	chain = tree.above(project, of)
	return chain[chain.index(top) - 1] if top in chain and chain.index(top) else top


def lanes(rows: list[dict], top: str, titles: dict[str, str]) -> list[dict]:
	"""The milestones a row per part of the job, Main first and then the
	parts by their next milestone, each soonest first and those without a
	date last. None when there is only one part. Pure."""
	found = {}
	for one in rows:
		found.setdefault(one["lane"], []).append(one)
	if len(found) < 2:
		return []
	order = lambda one: (not one["due"], one["due"] or "")  # noqa: E731

	def ahead(key):
		return min((order(one) for one in found[key] if not one["done"]), default=(True, "~"))

	keys = [top] if top in found else []
	keys += sorted((key for key in found if key != top), key=lambda key: (ahead(key), titles.get(key) or key))
	return [
		{
			"key": key,
			"title": None if key == top else titles.get(key) or key,
			"milestones": sorted(found[key], key=order),
			"done": sum(1 for one in found[key] if one["done"]),
		}
		for key in keys
	]


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
			"lane": lane(one.project, project, of),
			"in_lane": where(one.project, lane(one.project, project, of), of, titles),
		}
		for one in found
	]
	return {
		"list": pick(rows),
		"lanes": lanes(rows, project, titles) if not tree.narrowed(project) else [],
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


def kept(doc, method=None) -> None:
	"""Task validate: a milestone bills a share between 0 and 100% of its
	project's contract, and its project's milestones together bill at most
	all of it. Work isn't added to a cancelled project. However the task is
	made or changed: the page, a bulk edit or Data Import."""
	share = flt(doc.get("one_bill_share"))
	if share < 0 or share > 100:
		frappe.throw(_("A milestone bills between 0 and 100% of the contract."))
	if not doc.project or doc.get("is_template"):
		return
	if doc.is_new() and frappe.db.get_value("Project", doc.project, "status") == "Cancelled":
		frappe.throw(
			_("{0} is cancelled. Open it again to add work to it.").format(
				frappe.db.get_value("Project", doc.project, "project_name") or doc.project
			)
		)
	if not doc.is_milestone or not share:
		return
	others = sum(
		flt(one)
		for one in frappe.get_all(
			"Task",
			filters={"project": doc.project, "is_milestone": 1, "name": ["!=", doc.name or ""], "status": ["!=", "Cancelled"]},
			pluck="one_bill_share",
		)
	)
	if others + share > 100.005:
		frappe.throw(
			_("The milestones on this project would bill {0}% of the contract. Together they bill at most 100%.").format(
				f"{others + share:g}"
			)
		)


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
	from onedesk.one_project import tell

	tell.milestone_done(doc, chain[0])
