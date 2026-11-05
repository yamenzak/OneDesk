"""What OneQuality's records say above their fields: the heads, the measures
they place. See one/head.py.
"""

from urllib.parse import quote

import frappe
from frappe import _, _lt
from frappe.utils import formatdate, get_fullname


def nc_raised_by(doc):
	return {"value": get_fullname(doc.owner)}


def action_done(doc):
	"""How many of its resolutions are done."""
	rows = doc.get("resolutions") or []
	if not rows:
		return None
	done = sum(1 for row in rows if row.status == "Completed")
	return {"value": _("{0} of {1}").format(done, len(rows)), "tone": None if done == len(rows) else "waiting"}


def review_met(doc):
	"""How many of its objectives passed."""
	rows = doc.get("reviews") or []
	if not rows:
		return None
	passed = sum(1 for row in rows if row.status == "Passed")
	return {"value": _("{0} of {1}").format(passed, len(rows)), "tone": "alarm" if any(row.status == "Failed" for row in rows) else None}


def goal_last(doc):
	"""Its latest review: when, and whether it passed."""
	last = frappe.db.get_value("Quality Review", {"goal": doc.name}, ["name", "date", "status"], as_dict=True, order_by="date desc")
	if not last:
		return {"value": _("Not reviewed yet"), "tone": "quiet"}
	return {
		"value": _("{0} on {1}").format(_(last.status), formatdate(last.date)),
		"tone": "alarm" if last.status == "Failed" else None,
		"route": f"/desk/quality-review/{quote(last.name)}",
	}


def procedure_open(doc):
	"""Non conformances still open against it."""
	count = frappe.db.count("Non Conformance", {"procedure": doc.name, "status": "Open"})
	return {"value": str(count), "tone": "waiting" if count else "quiet", "route": f"/desk/non-conformance?procedure={quote(doc.name)}&status=Open"}


HEADS = [
	{
		"doctype": "Non Conformance",
		"band": [
			{"label": _lt("Procedure"), "source": "Field", "field": "procedure"},
			{"label": _lt("Raised By"), "source": "Measure", "measure": "quality.raised_by"},
		],
	},
	{
		"doctype": "Quality Action",
		"band": [
			{"label": _lt("Resolutions Done"), "source": "Measure", "measure": "quality.action_done"},
			{"label": _lt("Goal"), "source": "Field", "field": "goal", "hide_empty": 1},
			{"label": _lt("Procedure"), "source": "Field", "field": "procedure", "hide_empty": 1},
		],
	},
	{
		"doctype": "Quality Review",
		"band": [
			{"label": _lt("Objectives Met"), "source": "Measure", "measure": "quality.review_met"},
			{"label": _lt("Procedure"), "source": "Field", "field": "procedure", "hide_empty": 1},
		],
	},
	{
		"doctype": "Quality Goal",
		"band": [
			{"label": _lt("Last Review"), "source": "Measure", "measure": "quality.goal_last"},
			{"label": _lt("Procedure"), "source": "Field", "field": "procedure", "hide_empty": 1},
		],
	},
	{
		"doctype": "Quality Procedure",
		"band": [
			{"label": _lt("Open Non Conformances"), "source": "Measure", "measure": "quality.procedure_open"},
			{"label": _lt("Process Owner"), "source": "Field", "field": "process_owner_full_name", "hide_empty": 1},
		],
	},
]

MEASURES = {
	"quality.raised_by": nc_raised_by,
	"quality.action_done": action_done,
	"quality.review_met": review_met,
	"quality.goal_last": goal_last,
	"quality.procedure_open": procedure_open,
}
