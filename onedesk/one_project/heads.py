"""What a project's page says above its fields. See one/head.py.

How far it has got, whether it is on time, cost against budget, billed
against the contract, the margin so far and the forecast margin, what is late and what comes next,
for the whole tree when it has sub-projects, and the hours logged on it week
by week. The figures are overview.py's, worked out once per request.
"""

import json
from urllib.parse import quote

import frappe
from frappe import _, _lt
from frappe.utils import add_days, cint, flt, fmt_money, formatdate, today
from frappe.utils.caching import request_cache

from onedesk.one import head, stages
from onedesk.one_project import overview

DONE = ("Completed", "Cancelled", "Template")

HEALTH_TONE = {"At Risk": "waiting", "Off Track": "alarm"}


@request_cache
def _said(name: str) -> dict:
	return overview.overview(name)


def _route(value) -> str:
	"""A list filter in the address, as the desk writes one."""
	return quote(json.dumps(value, separators=(",", ":")), safe="!~*'()")


def health(doc):
	"""Somebody's judgement, not a figure, so it leads: an Open project can be
	in trouble before any number says so."""
	if not doc.get("one_health") or doc.status != "Open":
		return None
	return {"value": _(doc.one_health), "tone": HEALTH_TONE.get(doc.one_health)}


def sub_projects(doc):
	said = _said(doc.name)
	if said["projects"] <= 1:
		return None
	return {"value": said["projects"] - 1, "route": "/desk/project/view/tree"}


def done(doc):
	said = _said(doc.name)
	note = _("{0} of {1} tasks").format(said["done"], said["tasks"]) if said["tasks"] else None
	return {"value": f"{said['share']}%", "note": note, "meter": {"value": said["share"], "of": 100}}


def due(doc):
	said = _said(doc.name)
	if not said["end"]:
		return None
	left = said["days_left"]
	if left is None:
		return formatdate(said["end"])
	if left < 0:
		return {"value": _("{0} days late").format(-left), "tone": "alarm"}
	return _("Today") if left == 0 else _("In {0} days").format(left)


def cost(doc):
	said = _said(doc.name)
	over = said["estimated"] and said["cost"] > said["estimated"]
	return {
		"value": head.money(said["cost"], said["currency"], 0),
		"note": _("of {0}").format(head.money(said["estimated"], said["currency"], 0)) if said["estimated"] else None,
		"tone": "alarm" if over else None,
		"meter": {"value": said["cost"], "of": said["estimated"]} if said["estimated"] else None,
	}


def billed(doc):
	said = _said(doc.name)
	if not (said["to_bill"] or said["billed"]):
		return None
	return {
		"value": head.money(said["billed"], said["currency"], 0),
		"note": _("of {0}").format(head.money(said["to_bill"], said["currency"], 0)) if said["to_bill"] else None,
		"meter": {"value": said["billed"], "of": said["to_bill"]} if said["to_bill"] else None,
	}


def margin(doc):
	said = _said(doc.name)
	if not (said["billed"] or said["cost"]):
		return None
	return {"value": head.money(said["margin"], said["currency"], 0), "tone": "alarm" if said["margin"] < 0 else None}


def forecast(doc):
	"""Where the margin is heading: the contract against everything spent,
	still to be billed on orders, and the budget left (money.py)."""
	said = _said(doc.name)
	if not said["forecast"]:
		return None
	value = said["forecast_margin"]
	return {"value": head.money(value, said["currency"], 0), "tone": "alarm" if value < 0 else None}


def late(doc):
	"""The late tasks across the tree: the list, filtered by route options."""
	said = _said(doc.name)
	if not said["late"]:
		return None
	return {
		"value": said["late"],
		"tone": "alarm",
		"route": f"/desk/task?project={_route(['in', said['tree']])}"
		f"&status={_route(['not in', list(DONE)])}"
		f"&exp_end_date={_route(['between', ['2000-01-01', str(add_days(today(), -1))]])}",
	}


def milestone(doc):
	found = _said(doc.name)["milestone"]
	if not found:
		return None
	return {
		"value": f"{found.subject} · {formatdate(str(found.exp_end_date).split(' ')[0])}",
		"route": f"/desk/task/{quote(found.name, safe='')}",
	}


def hours(doc):
	"""The hours logged, a bar a week: whether the work is moving, which none
	of the totals can say. This week's is the one in the hue."""
	weekly = _said(doc.name)["weekly"]
	if not weekly:
		return None
	return {
		"labels": weekly["labels"],
		"values": weekly["values"],
		"said": _("{0} hours in 12 weeks").format(fmt_money(weekly["total"], precision=1)),
		"route": f"/desk/timesheet?parent_project={quote(doc.name, safe='')}",
		"marked": len(weekly["values"]) - 1,
	}


def _named(doc) -> str | None:
	"""The project a record is for: its own field, a contract's reference, or
	for a deal the project its quote went to, else the customer's one open
	project."""
	if doc.doctype == "Contract":
		return doc.document_name if doc.get("document_type") == "Project" else None
	if doc.doctype == "Opportunity":
		quoted = frappe.get_all(
			"Quotation",
			filters={"opportunity": doc.name, "docstatus": ["<", 2], "project": ["is", "set"]},
			pluck="project",
			order_by="creation desc",
			limit=1,
		)
		if quoted:
			return quoted[0]
		if doc.get("opportunity_from") != "Customer" or not doc.get("party_name"):
			return None
		from onedesk.one_project.chain import customer_project

		return customer_project(doc.party_name)
	return doc.get("project")


def of(doc):
	"""The project a document is for, by name, opening its page. Nothing when
	it names none or the reader may not open it."""
	name = _named(doc)
	if not name or not frappe.has_permission("Project", "read", doc=name):
		return None
	title = frappe.db.get_value("Project", name, "project_name") or name
	return {"value": title, "route": f"/desk/project/{quote(name, safe='')}"}


def _hours(value) -> str:
	value = flt(value)
	return _("{0} h").format(fmt_money(value, precision=1 if value % 1 else 0))


def timesheet_progress(doc):
	"""Logged, then billed when any of it is billable."""
	if doc.docstatus != 1:
		return None
	days = formatdate(doc.start_date) if doc.start_date == doc.end_date else _("{0} to {1}").format(formatdate(doc.start_date), formatdate(doc.end_date))
	billable = flt(doc.total_billable_hours)
	billed = flt(doc.per_billed) >= 100
	return stages.track(
		stages.step(_("Submitted"), "done", days),
		billable and stages.step(_("Billed"), stages.at(billed, True), _("All") if billed else stages.share(doc.per_billed)),
	)


def timesheet_said(doc):
	who = doc.employee_name or (frappe.utils.get_fullname(doc.user) if doc.user else _("somebody"))
	hours = _hours(doc.total_hours)
	if said := stages.draft(doc, _("A draft. Submit it to count {0} of {1}'s time.").format(hours, who)):
		return said
	billable = flt(doc.total_billable_hours)
	if not billable:
		return {"text": _("{0} of {1}'s time; none of it is billed to the customer.").format(hours, who), "colour": "gray"}
	if flt(doc.per_billed) >= 100:
		return {"text": _("Billed: {0} of {1}'s time.").format(_hours(billable), who), "colour": "green"}
	left = billable - flt(doc.total_billed_hours)
	return {"text": _("{0} still to bill to the customer.").format(_hours(left)), "colour": "orange"}


def timesheet_worth(doc):
	"""What the billable hours are worth at the project's rates, which the form
	keeps out of sight."""
	if not flt(doc.total_billable_hours) or not flt(doc.total_billable_amount):
		return None
	return fmt_money(doc.total_billable_amount, currency=doc.currency)


def template_tasks(doc):
	"""Its tasks, leaving out the groups that only hold others."""
	count = cint(doc.get("one_tasks"))
	return str(count) if count else None


def template_days(doc):
	days = cint(doc.get("one_days"))
	if not days:
		return None
	return _("1 day") if days == 1 else _("{0} days").format(days)


def template_used(doc):
	"""How many projects were started from it, opening them."""
	used = frappe.db.count("Project", {"project_template": doc.name})
	if not used:
		return _("Not used yet")
	return {"value": str(used), "route": f"/desk/project?project_template={quote(doc.name, safe='')}"}


MEASURES = {
	"template.tasks": template_tasks,
	"template.days": template_days,
	"template.used": template_used,
	"project.health": health,
	"project.sub_projects": sub_projects,
	"project.done": done,
	"project.due": due,
	"project.cost": cost,
	"project.billed": billed,
	"project.margin": margin,
	"project.forecast": forecast,
	"project.late": late,
	"project.milestone": milestone,
	"project.of": of,
	"timesheet.progress": timesheet_progress,
	"timesheet.said": timesheet_said,
	"timesheet.worth": timesheet_worth,
}

CHARTS = {
	"project.hours": {"doctypes": ["Project"], "label": _lt("Hours Logged, Week by Week"), "figures": hours},
}

HEADS = [
	{
		"doctype": "Project",
		"band": [
			{"label": _lt("Health"), "source": "Measure", "measure": "project.health"},
			{"label": _lt("Sub-projects"), "source": "Measure", "measure": "project.sub_projects"},
			{"label": _lt("% Completed"), "source": "Measure", "measure": "project.done"},
			{"label": _lt("Expected End Date"), "source": "Measure", "measure": "project.due"},
			{"label": _lt("Cost"), "source": "Measure", "measure": "project.cost"},
			{"label": _lt("Billed"), "source": "Measure", "measure": "project.billed"},
			{"label": _lt("Margin So Far"), "source": "Measure", "measure": "project.margin"},
			{"label": _lt("Forecast Margin"), "source": "Measure", "measure": "project.forecast"},
			{"label": _lt("Overdue Tasks"), "source": "Measure", "measure": "project.late"},
			{"label": _lt("Next Milestone"), "source": "Measure", "measure": "project.milestone"},
		],
		"charts": [{"chart": "project.hours"}],
	},
	{
		"doctype": "Project Template",
		"band": [
			{"label": _lt("Tasks"), "source": "Measure", "measure": "template.tasks"},
			{"label": _lt("Duration"), "source": "Measure", "measure": "template.days"},
			{"label": _lt("Projects"), "source": "Measure", "measure": "template.used"},
		],
	},
	{
		"doctype": "Timesheet",
		"sentences": [{"measure": "timesheet.said"}],
		"band": [
			{"label": _lt("Progress"), "source": "Measure", "measure": "timesheet.progress"},
			{"label": _lt("Total Billable Amount"), "source": "Measure", "measure": "timesheet.worth"},
		],
	},
]
