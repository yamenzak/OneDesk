"""What a task's form says above its fields, and the one verb it offers: when
it is due and how late, the checklist, what it waits on and the hours logged.
See one/head.py.
"""

import frappe
from frappe import _, _lt
from frappe.utils import date_diff, flt, formatdate, today

from onedesk.one_task.capture import DONE


def due(doc):
	if not doc.exp_end_date:
		return None
	late = date_diff(today(), doc.exp_end_date)
	if doc.status in DONE or late < 0:
		return formatdate(doc.exp_end_date)
	if late == 0:
		return {"value": _("Today"), "tone": "waiting"}
	return {"value": _("{0} days late").format(late), "tone": "alarm"}


def steps(doc):
	total = len(doc.get("one_steps") or [])
	if not total:
		return None
	done = sum(1 for row in doc.one_steps if row.done)
	return {"value": _("{0} of {1} done").format(done, total), "meter": {"value": done, "of": total}}


def waits(doc):
	"""The tasks it depends on that are still open, leaving out its own
	sub-tasks, which ERPNext lists there too."""
	under = set(frappe.get_all("Task", filters={"parent_task": doc.name}, pluck="name"))
	names = [row.task for row in doc.get("depends_on") or [] if row.task and row.task not in under]
	if not names:
		return None
	open_ = frappe.get_list(
		"Task", filters={"name": ["in", names], "status": ["not in", DONE]}, pluck="subject", limit=10
	)
	if not open_:
		return None
	said = _("Waiting on {0}").format(open_[0]) if len(open_) == 1 else _("Waiting on {0} other tasks").format(len(open_))
	return {"value": said, "tone": "waiting"}


def _number(value) -> str:
	return f"{flt(value, 1):g}"


def _hours(value) -> str:
	return _("{0} hours").format(_number(value))


def logged(doc):
	actual, expected = flt(doc.actual_time), flt(doc.expected_time)
	if not actual and not expected:
		return None
	if not expected:
		return _hours(actual)
	return {
		"value": _("{0} of {1}").format(_number(actual), _hours(expected)),
		"meter": {"value": min(actual, expected), "of": expected},
		"tone": "alarm" if actual > expected else None,
	}


def _complete(doc):
	doc.status = "Completed"
	doc.save()


MEASURES = {"task.due": due, "task.steps": steps, "task.waits": waits, "task.logged": logged}

VERBS = {
	"task.complete": {
		"doctypes": ["Task"],
		"label": _lt("Complete Task"),
		"when": lambda doc: doc.status not in DONE and bool(doc.has_permission("write")),
		"run": lambda doc: _complete(doc),
	},
}

HEADS = [
	{
		"doctype": "Task",
		"band": [
			{"label": _lt("Expected End Date"), "source": "Measure", "measure": "task.due"},
			{"label": _lt("Checklist"), "source": "Measure", "measure": "task.steps"},
			{"label": _lt("Depends On"), "source": "Measure", "measure": "task.waits"},
			{"label": _lt("Actual Time"), "source": "Measure", "measure": "task.logged"},
		],
		"verbs": [{"verb": "task.complete", "primary": 1}],
	},
]
