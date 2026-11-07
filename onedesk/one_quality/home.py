"""OneQuality's Home (page/onequality, frontend/src/quality/QualityHome.vue):
the problems still open, the actions late, the goals whose last review
failed and the meetings still open, and everything in OneQuality with what
it is for. How it works is in the module's AGENTS.md.
"""

import frappe
from frappe import _lt
from frappe.utils import date_diff, get_fullname, getdate, today

FEW = 5

GROUPS = (
	("problems", _lt("Problems and Actions")),
	("standards", _lt("Procedures and Goals")),
	("people", _lt("Meetings and Feedback")),
	("reports", _lt("Reports")),
	("setup", _lt("Setup")),
)

EVERYTHING = (
	("problems", _lt("Non Conformance"), "DocType", "Non Conformance", _lt("Something done wrong, what caused it and what stops it again.")),
	("problems", _lt("Quality Action"), "DocType", "Quality Action", _lt("What is being done to put a problem right, step by step, by whom.")),
	("standards", _lt("Quality Procedure"), "DocType", "Quality Procedure", _lt("How a piece of work is done, step by step, and who owns it.")),
	("standards", _lt("Quality Goal"), "DocType", "Quality Goal", _lt("What a procedure should achieve, and how often it is checked.")),
	("standards", _lt("Quality Review"), "DocType", "Quality Review", _lt("A goal checked, objective by objective.")),
	("people", _lt("Quality Meeting"), "DocType", "Quality Meeting", _lt("The agenda and the minutes of a quality meeting.")),
	("people", _lt("Quality Feedback"), "DocType", "Quality Feedback", _lt("What a customer or a colleague said of the work.")),
	("reports", _lt("Review"), "Report", "Review", _lt("Every review, passed or failed, goal by goal.")),
	("setup", _lt("Quality Feedback Template"), "DocType", "Quality Feedback Template", _lt("The questions feedback is asked with.")),
)


@frappe.whitelist()
def read() -> dict:
	"""The figures, what needs somebody, and the directory, as the reader may
	see them."""
	if not frappe.get_cached_doc("Page", "onequality").is_permitted():
		raise frappe.PermissionError
	needs = needs_you()
	return {
		"figures": {
			"problems": needs["problems"]["count"],
			"actions": frappe.db.count("Quality Action", {"status": "Open"}) if frappe.has_permission("Quality Action", "read") else None,
			"late": needs["late"]["count"],
			"failing": needs["failing"]["count"],
		},
		"needs": needs,
		"groups": [{"key": key, "label": str(label)} for key, label in GROUPS],
		"everything": directory(),
		"may_make": [doctype for doctype in ("Non Conformance", "Quality Action", "Quality Review") if frappe.has_permission(doctype, "create")],
	}


def _kept(rows: list) -> dict:
	return {"rows": rows[:FEW], "count": len(rows)}


def needs_you() -> dict:
	"""Problems still open, the oldest first; action steps past their day;
	goals whose last review failed; meetings still open."""
	day = getdate(today())
	actions = _actions()
	problems = [
		{**one, "raised_by": get_fullname(one.owner), "days": date_diff(day, getdate(one.creation)), "actions": actions.get(one.name, 0)}
		for one in frappe.get_list("Non Conformance", filters={"status": "Open"}, fields=["name", "subject", "procedure", "owner", "creation"], order_by="creation asc")
	]
	return {
		"problems": _kept(problems),
		"late": _kept(_late(day)),
		"failing": _kept(_failing()),
		"meetings": _kept(_meetings()),
	}


def _meetings() -> list[dict]:
	"""Meetings still open, each by its first point."""
	if not frappe.has_permission("Quality Meeting", "read"):
		return []
	rows = frappe.get_list("Quality Meeting", filters={"status": "Open"}, fields=["name", "creation"], order_by="creation asc")
	for one in rows:
		one["about"] = frappe.db.get_value("Quality Meeting Agenda", {"parent": one.name}, "agenda", order_by="idx asc")
	return rows


def _actions() -> dict:
	if not frappe.has_permission("Quality Action", "read"):
		return {}
	counted: dict = {}
	for one in frappe.get_list("Quality Action", filters={"one_non_conformance": ["is", "set"]}, fields=["one_non_conformance"]):
		counted[one.one_non_conformance] = counted.get(one.one_non_conformance, 0) + 1
	return counted


def _late(day) -> list[dict]:
	"""Each open step of an open action whose day has passed."""
	if not frappe.has_permission("Quality Action", "read"):
		return []
	open_actions = frappe.get_list("Quality Action", filters={"status": "Open"}, pluck="name")
	if not open_actions:
		return []
	rows = frappe.get_all(
		"Quality Action Resolution",
		filters={"parent": ["in", open_actions], "status": "Open", "completion_by": ["<", day]},
		fields=["parent", "problem", "responsible", "completion_by"],
		order_by="completion_by asc",
	)
	return [
		{
			"action": one.parent,
			"problem": one.problem,
			"who": get_fullname(one.responsible) if one.responsible else None,
			"due": str(one.completion_by),
			"late_by": date_diff(day, one.completion_by),
		}
		for one in rows
	]


def _failing() -> list[dict]:
	"""Goals whose latest review failed."""
	if not frappe.has_permission("Quality Review", "read"):
		return []
	out = []
	for goal in frappe.get_list("Quality Goal", fields=["name", "goal", "procedure"]):
		last = frappe.db.get_value("Quality Review", {"goal": goal.name}, ["name", "date", "status"], as_dict=True, order_by="date desc")
		if last and last.status == "Failed":
			out.append({"goal": goal.name, "label": goal.goal or goal.name, "procedure": goal.procedure, "review": last.name, "date": str(last.date)})
	return out


def _may(kind: str, target: str) -> bool:
	if kind == "DocType":
		return bool(frappe.has_permission(target, "read"))
	if not frappe.db.exists(kind, target):
		return False
	return bool(frappe.get_cached_doc(kind, target).is_permitted())


def directory() -> list[dict]:
	"""Everything in OneQuality the reader may open, with what it is for."""
	return [
		{"group": group, "label": str(label), "kind": kind, "target": target, "about": str(about)}
		for group, label, kind, target, about in EVERYTHING
		if _may(kind, target)
	]
