"""A task's steps that tick themselves (docs/INTAKE.md §3.4).

A step OneAI writes can say what completes it, in `done_when`: a record
reaching a state (`{"doctype", "name", "field", "in" | "equals"}`), a reply
going out in the mail thread the ask came in (`{"reply_in": thread}`), or a
day passing (`{"after": date}`). It is checked when that record changes,
when a message is sent and once a day, with no model. A state that changes
back (a payment cancelled) opens the step again: ERPNext's state changed,
not a person's mind. When every step is done, a task OneAI made is done.

The hook on record changes runs for every save, so it first asks a cached
set of the doctypes any open step watches.
"""

import json

import frappe
from frappe.utils import flt, getdate, today

from onedesk.one_hr.hiring import AUTHOR

CACHE = "one_intake_watched_doctypes"


# ------------------------------------------------------------------ pure


def holds(when: dict, value) -> bool:
	"""Whether a record's value satisfies a step's condition. Pure."""
	if "all" in when:
		return all(holds(one, value.get(one["field"]) if isinstance(value, dict) else None) for one in when["all"])
	if "in" in when:
		return value in when["in"]
	if "equals" in when:
		wanted = when["equals"]
		if isinstance(wanted, int | float):
			return abs(flt(value) - flt(wanted)) < 0.005
		return value == wanted
	return False


def passed(when: dict, today_: str) -> bool:
	"""Whether a step that waits for a day is done. Pure."""
	return bool(when.get("after")) and getdate(when["after"]) < getdate(today_)


# ------------------------------------------------------------------ on the site


def _open_steps(like: str | None = None) -> list[dict]:
	filters = {"done": 0, "done_when": ["is", "set"], "parenttype": "Task"}
	if like:
		filters["done_when"] = ["like", f"%{like}%"]
	return frappe.get_all("Task Step", filters=filters, fields=["name", "parent", "done_when"])


def watched() -> set[str]:
	"""The doctypes a step waits on, ticked or not: a ticked step still
	listens, so a cancelled payment opens it again."""
	held = frappe.cache.get_value(CACHE)
	if held is None:
		rows = frappe.get_all("Task Step", filters={"done_when": ["like", '%"doctype"%'], "parenttype": "Task"}, pluck="done_when")
		held = sorted({json.loads(one).get("doctype") for one in rows if one} - {None})
		frappe.cache.set_value(CACHE, held)
	return set(held)


def changed() -> None:
	frappe.cache.delete_value(CACHE)


def record_changed(doc, method=None) -> None:
	"""on_update, on_submit, on_cancel of anything: the steps watching this
	record, ticked or opened again by its state."""
	if frappe.flags.in_migrate or frappe.flags.in_install or frappe.flags.in_patch or doc.doctype not in watched():
		return
	for step in _open_steps(f'"name": "{doc.name}"') + _done_steps(doc):
		when = json.loads(step.done_when)
		if when.get("doctype") != doc.doctype or when.get("name") != doc.name:
			continue
		_set(step, holds(when, doc.as_dict() if "all" in when else doc.get(when.get("field"))))


def paid(doc, method=None) -> None:
	"""Payment Entry and Journal Entry on_submit and on_cancel: the invoices
	they pay change their outstanding amount with db_set, which runs no hook
	of theirs, so the steps watching them are checked from here."""
	rows = doc.get("references") or doc.get("accounts") or []
	for row in rows:
		doctype = row.get("reference_doctype") or row.get("reference_type")
		name = row.get("reference_name")
		if doctype in watched() and name and frappe.db.exists(doctype, name):
			record_changed(frappe.get_doc(doctype, name))


def _done_steps(doc) -> list[dict]:
	return frappe.get_all(
		"Task Step",
		filters={"done": 1, "done_when": ["like", f'%"name": "{doc.name}"%'], "parenttype": "Task"},
		fields=["name", "parent", "done_when"],
	)


def replied(doc, method=None) -> None:
	"""Communication after_insert: a message sent in a thread ticks the reply
	asked for in it."""
	if frappe.flags.in_migrate or doc.sent_or_received != "Sent" or not doc.get("one_thread"):
		return
	for step in _open_steps(f'"reply_in": {json.dumps(doc.one_thread)}'):
		when = json.loads(step.done_when)
		if when.get("attached") and not frappe.db.exists("File", {"attached_to_doctype": "Communication", "attached_to_name": doc.name}):
			continue
		_set(step, True)


def daily() -> None:
	"""A day that has passed ticks the steps waiting for it: an appointment
	that was attended."""
	for step in _open_steps('"after"'):
		if passed(json.loads(step.done_when), today()):
			_set(step, True)


def _set(step: dict, done: bool) -> None:
	now = frappe.db.get_value("Task Step", step["name"], "done")
	if bool(now) == done:
		return
	frappe.db.set_value("Task Step", step["name"], "done", int(done), update_modified=False)
	task = step["parent"]
	left = frappe.db.count("Task Step", {"parent": task, "parenttype": "Task", "done": 0})
	status = frappe.db.get_value("Task", task, "status")
	# A task OneAI made is done when its steps are, and closed as OneAI, so
	# that a state changing back opens it again unless a person has since
	# touched it.
	if not left and status not in ("Completed", "Cancelled") and frappe.db.get_value("Task", task, "owner") == AUTHOR:
		frappe.db.set_value("Task", task, "status", "Completed", modified_by=AUTHOR)
	elif left and status == "Completed" and frappe.db.get_value("Task", task, "modified_by") == AUTHOR:
		frappe.db.set_value("Task", task, "status", "Open", modified_by=AUTHOR)
	changed()
