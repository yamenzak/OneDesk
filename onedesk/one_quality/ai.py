"""OneAI in OneQuality: what it suggests asking on each of its record types
and on its Home, and quality_now, which reads what the Home shows. It reads
the records through the generic tools (about_record, read_record,
list_records) and changes none of them."""

import frappe
from frappe import _lt

REACH = {}

NOT_FOR_AI = {}

_OPEN = {
	"label": _lt("What is still open?"),
	"ask": _lt("Which non conformances and quality actions are still open, against which procedure, and since when?"),
	"expects": "list_records",
}
_FIXED = {
	"label": _lt("What was done about it?"),
	"ask": _lt("What went wrong here, what was done to put it right, and what stops it happening again?"),
	"can": "read",
	"expects": "read_record",
}
_STEPS = {
	"label": _lt("Summarise this procedure"),
	"ask": _lt("Say in a few lines how this work is done, and which goals and problems point at it."),
	"can": "read",
	"expects": "read_record",
}

HOME = "onequality"

_NOW = {
	"label": _lt("What needs fixing?"),
	"ask": _lt("Which problems are still open, which steps are overdue and with whom, and which goals are failing?"),
	"can": "read",
	"expects": "quality_now",
}

SUGGESTIONS = {
	f"page:{HOME}": [_NOW, _OPEN],
	"Non Conformance": [_FIXED, _OPEN],
	"Quality Action": [_FIXED, _OPEN],
	"Quality Procedure": [_STEPS, _OPEN],
}


def page(said: dict) -> str | None:
	"""The sentence the model is told on OneQuality's Home."""
	if said.get("page") == HOME:
		return (
			"The reader is on OneQuality's Home, which shows the non conformances still open, the action steps past "
			"their day, the goals whose last review failed and the meetings still open, and everything in OneQuality "
			"with what it is for. quality_now reads what it shows. How each part works is in OneQuality's "
			"documentation (how_to)."
		)
	return None


def quality_now() -> dict:
	"""What OneQuality's Home shows: the non conformances still open, the
	oldest first, with who raised them and how many actions each has; the
	steps of open quality actions past their day, with who is responsible;
	the goals whose last review failed; and the meetings still open."""
	from onedesk.one_quality import home

	if not frappe.get_cached_doc("Page", "onequality").is_permitted():
		return {"error": "The reader does not work in quality."}
	needs = home.needs_you()
	return {
		"open": [
			{"name": one["name"], "subject": one["subject"], "procedure": one["procedure"], "raised_by": one["raised_by"], "days_open": one["days"], "actions": one["actions"]}
			for one in needs["problems"]["rows"]
		],
		"open_count": needs["problems"]["count"],
		"overdue_steps": needs["late"]["rows"],
		"overdue_count": needs["late"]["count"],
		"goals_failing": needs["failing"]["rows"],
		"meetings_open": [one["name"] for one in needs["meetings"]["rows"]],
	}
