"""What a project's page says above its fields. See one/head.py.

How far it has got, whether it is on time, cost against budget, billed
against what there is to bill, the margin, what is late and what comes next,
for the whole tree when it has sub-projects, and the hours logged on it week
by week. The figures are overview.py's, worked out once per request.
"""

import json
from urllib.parse import quote

from frappe import _, _lt
from frappe.utils import fmt_money, formatdate, today
from frappe.utils.caching import request_cache

from onedesk.one_project import overview

#: A task that is still to do is none of these.
DONE = ("Completed", "Cancelled", "Template")

#: How somebody's judgement of a project reads.
HEALTH_TONE = {"At Risk": "waiting", "Off Track": "alarm"}


@request_cache
def _said(name: str) -> dict:
	return overview.overview(name)


def _money(said, value) -> str:
	return fmt_money(value or 0, precision=0, currency=said["currency"])


def _of(said, part, whole) -> str:
	return _("{0} of {1}").format(_money(said, part), _money(said, whole)) if whole else _money(said, part)


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
	return {"value": said["projects"] - 1, "route": "/desk/query-report/Project Tree"}


def done(doc):
	said = _said(doc.name)
	value = (
		_("{0}% · {1} of {2} tasks").format(said["share"], said["done"], said["tasks"])
		if said["tasks"]
		else f"{said['share']}%"
	)
	return {"value": value, "meter": {"value": said["share"], "of": 100}}


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
		"value": _of(said, said["cost"], said["estimated"]),
		"tone": "alarm" if over else None,
		"meter": {"value": said["cost"], "of": said["estimated"]} if said["estimated"] else None,
	}


def billed(doc):
	said = _said(doc.name)
	if not (said["to_bill"] or said["billed"]):
		return None
	return {
		"value": _of(said, said["billed"], said["to_bill"]),
		"meter": {"value": said["billed"], "of": said["to_bill"]} if said["to_bill"] else None,
	}


def margin(doc):
	said = _said(doc.name)
	if not (said["billed"] or said["cost"]):
		return None
	return {"value": _money(said, said["margin"]), "tone": "alarm" if said["margin"] < 0 else None}


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
		f"&exp_end_date={_route(['<', today()])}",
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


MEASURES = {
	"project.health": health,
	"project.sub_projects": sub_projects,
	"project.done": done,
	"project.due": due,
	"project.cost": cost,
	"project.billed": billed,
	"project.margin": margin,
	"project.late": late,
	"project.milestone": milestone,
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
			{"label": _lt("Done"), "source": "Measure", "measure": "project.done"},
			{"label": _lt("Due"), "source": "Measure", "measure": "project.due"},
			{"label": _lt("Cost"), "source": "Measure", "measure": "project.cost"},
			{"label": _lt("Billed"), "source": "Measure", "measure": "project.billed"},
			{"label": _lt("Margin"), "source": "Measure", "measure": "project.margin"},
			{"label": _lt("Overdue Tasks"), "source": "Measure", "measure": "project.late"},
			{"label": _lt("Next Milestone"), "source": "Measure", "measure": "project.milestone"},
		],
		"charts": [{"chart": "project.hours"}],
	},
]
