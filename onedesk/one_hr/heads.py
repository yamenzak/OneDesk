"""What a person's page says above its fields. See one/head.py.

Where they are right now as the title's pill; a quarter of attendance as a
heat map of named days; and beside it the handful of numbers somebody opens
the record to read: their standing, their last check-in, what leave is left
of each type, what is waiting on an approver, what they hold and what they
are paid under. The figures are employee.py's `overview`, worked out once per
request with the reader's own permissions.
"""

import re
from urllib.parse import quote

from frappe import _, _lt
from frappe.utils.caching import request_cache

from onedesk.one_hr import employee

#: What a standing is worth saying about it, by its band. Only low and watch
#: get a colour: a number that is fine is a number nobody has to look at.
STANDING_TONE = {"low": "alarm", "watch": "waiting", "good": None}


@request_cache
def _said(name: str) -> dict:
	return employee.overview(name)


def _number(value) -> str:
	"""A count as a person writes it: 21, not 21.0; 7.5 stays 7.5."""
	value = float(value or 0)
	return str(int(value)) if value.is_integer() else str(value)


def _slug(doctype: str) -> str:
	return doctype.lower().replace(" ", "-")


def state(doc):
	"""Where this person is right now, as a word and a colour."""
	if doc.is_new():
		return None
	return _said(doc.name)["state"]


def standing(doc):
	"""First, beside the quarter it is worked out from: the one number about
	whether the check-ins themselves can be believed."""
	found = _said(doc.name)["standing"]
	if not found:
		return None
	return {
		"value": found["score"],
		"route": f"/desk/clock-attempt?employee={quote(doc.name, safe='')}",
		"tone": STANDING_TONE.get(found["band"]),
	}


def checked(doc):
	"""The last check-in, said the way the clock says it ("5 d")."""
	found = _said(doc.name)["today"]["checkin"]
	if not found:
		return None
	return {
		"label": _("Out") if found.log_type == "OUT" else _("In"),
		"value": "{when}",
		"when": str(found.time),
		"short": 1,
		"route": f"/desk/employee-checkin/{quote(found.name, safe='')}",
	}


def leave(doc):
	"""What is left of each leave type they hold, against the year's
	allocation: one number each."""
	return [
		{
			"label": re.sub(r" Leave$", "", row["type"]),
			"value": _("{0} left").format(_number(row["left"])),
			"route": f"/desk/leave-application?employee={quote(doc.name, safe='')}",
			"tone": None if (row["left"] or 0) > 0 else "quiet",
			"meter": {"value": row["left"], "of": row["allocated"]} if row["allocated"] else None,
		}
		for row in _said(doc.name)["leave"]
	]


def awaiting(doc):
	"""What is waiting on an approver, one number a kind."""
	return [
		{
			"label": _(kind),
			"value": _("{0} awaiting").format(row["count"]),
			"route": f"/desk/{_slug(kind)}?employee={quote(doc.name, safe='')}",
			"tone": "waiting",
		}
		for row in _said(doc.name)["awaiting"]
		if (kind := row["doctype"])
	]


def equipment(doc):
	"""What of the company's they hold, only when they hold something. See
	one_inventory/custody.py."""
	held = _said(doc.name)["equipment"]
	if not held:
		return None
	return {"value": _("{0} held").format(held), "route": f"/desk/asset?custodian={quote(doc.name, safe='')}"}


def pay(doc):
	found = _said(doc.name)["pay"]
	if not found or not found.get("salary_structure"):
		return None
	return {
		"value": found["salary_structure"],
		"route": f"/desk/salary-structure-assignment/{quote(found['name'], safe='')}",
	}


def quarter(doc):
	"""A quarter of attendance, a square a day: frappe-charts' heat map
	geometry, with colours that mean a state rather than an amount."""
	days = _said(doc.name)["days"]
	return {"kind": "heat", "days": days} if days else None


MEASURES = {
	"employee.state": state,
	"employee.standing": standing,
	"employee.checked": checked,
	"employee.leave": leave,
	"employee.awaiting": awaiting,
	"employee.equipment": equipment,
	"employee.pay": pay,
}

CHARTS = {
	"employee.quarter": {"doctypes": ["Employee"], "label": _lt("Attendance"), "figures": quarter},
}

HEADS = [
	{
		"doctype": "Employee",
		"indicators": [{"label": _lt("Where"), "measure": "employee.state"}],
		"band": [
			{"label": _lt("Standing"), "source": "Measure", "measure": "employee.standing"},
			{"label": _lt("In"), "source": "Measure", "measure": "employee.checked"},
			{"label": _lt("Leave"), "source": "Measure", "measure": "employee.leave"},
			{"label": _lt("Awaiting"), "source": "Measure", "measure": "employee.awaiting"},
			{"label": _lt("Equipment"), "source": "Measure", "measure": "employee.equipment"},
			{"label": _lt("Paid under"), "source": "Measure", "measure": "employee.pay"},
		],
		"charts": [{"chart": "employee.quarter"}],
	},
]
