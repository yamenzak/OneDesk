"""OneAI on growth: goals for a cycle, and the training that would help.

**Goals.** Writing three good goals is the part of an appraisal cycle people
put off, and the raw material is already here: the person's designation, the
KRAs this workspace appraises on, last cycle's goals and how far they got,
and the feedback they were given. `goal_facts` hands that over; `draft_goal`
turns each goal the model wrote into a Goal card, in the cycle that is open,
for the person or their manager to approve, change or refuse one by one.

The KRA list, the open cycle's dates and the training catalogue are read
whatever the reader's role:
they are the workspace's own names and dates, not anybody's record, and an
employee who may not open the KRA master still has goals to write against it.
Goals and feedback are read as the person asking.

**Training.** "What would help?" is answered from this workspace's own
training programs and events, against where the latest appraisal says the
person is weakest — not from a catalogue of courses the model has heard of.

Whose goals: your own, your direct reports', or anybody's if you are HR.
"""

import difflib
from typing import Annotated

import frappe
from frappe.utils import getdate

from onedesk.one_ai import proposals
from onedesk.one_hr import own

#: The roles that may draft goals for anybody.
HR = ("HR Manager", "HR User")


def goal_facts(
	employee: Annotated[str, "Whose goals: leave out for the person asking; a direct report's or, for HR, anybody's employee id."] | None = None,
) -> dict:
	"""What goals for the coming cycle should rest on: the person's role, the
	KRAs this workspace appraises on, the open cycle's dates, last cycle's
	goals and how far each got, and the feedback they were given. Read it,
	write up to five goals, then give each to draft_goal."""
	who, refused = _whose(employee)
	if refused:
		return {"error": refused}
	person = frappe.db.get_value("Employee", who, ["employee_name", "designation", "department"], as_dict=True)
	cycle = _open_cycle()
	earlier = frappe.get_list(
		"Goal",
		filters={"employee": who, "is_group": 0},
		fields=["goal_name", "kra", "progress", "status", "end_date"],
		order_by="creation desc",
		limit_page_length=10,
	)
	said = frappe.get_list(
		"Employee Performance Feedback",
		filters={"employee": who, "docstatus": 1},
		fields=["feedback"],
		order_by="creation desc",
		limit_page_length=3,
	)
	return {
		"employee": person.employee_name,
		"designation": person.designation,
		"department": (person.department or "").rsplit(" - ", 1)[0] or None,
		"kras": frappe.get_all("KRA", pluck="name", limit=30),
		"cycle": {"name": cycle.name, "from": str(cycle.start_date), "to": str(cycle.end_date)} if cycle else None,
		"earlier_goals": [
			{"goal": one.goal_name, "kra": one.kra, "progress": f"{one.progress or 0:g}%", "status": one.status}
			for one in earlier
		],
		"feedback": [frappe.utils.strip_html(one.feedback or "")[:600] for one in said if one.feedback],
		"next": "Write up to five goals from these facts: each one thing that can be finished in the cycle, "
		"with how it will be measured, and the KRA it serves from the list. Carry forward what was left "
		"unfinished if it still matters. Then call draft_goal once for each.",
	}


def draft_goal(
	goal_name: Annotated[str, "The goal as a short title: one thing that can be finished in the cycle."],
	description: Annotated[str, "What done looks like, and how it will be measured."],
	kra: Annotated[str, "The KRA it serves, from the list goal_facts gave."] | None = None,
	employee: Annotated[str, "Whose goal: leave out for the person asking."] | None = None,
) -> dict:
	"""Suggest one goal as a Goal card in the open cycle. Call it once per
	goal, up to five. Nothing is created until a person approves the card."""
	who, refused = _whose(employee)
	if refused:
		return {"error": refused}
	if not (goal_name or "").strip():
		return {"error": "The goal has no title."}
	cycle = _open_cycle()
	values = {
		"employee": who,
		"goal_name": goal_name.strip()[:140],
		"start_date": str(cycle.start_date if cycle else getdate()),
		"description": "".join(
			f"<p>{frappe.utils.escape_html(line.strip())}</p>"
			for line in str(description or "").split("\n")
			if line.strip()
		),
	}
	meant = kra_meant(kra, frappe.get_all("KRA", pluck="name", limit=100))
	if meant:
		values["kra"] = meant
	if cycle:
		values["appraisal_cycle"] = cycle.name
		values["end_date"] = str(cycle.end_date)
	return {"proposal": proposals.propose("Create", "Goal", changes=values), "state": "Proposed"}


def training_options(
	employee: Annotated[str, "Whose: leave out for the person asking; a direct report's or, for HR, anybody's."] | None = None,
) -> dict:
	"""Where the latest appraisal says the person is weakest, and this
	workspace's own training programs and upcoming training events. Suggest
	only from these; if none fits, say what kind of training to look for."""
	who, refused = _whose(employee)
	if refused:
		return {"error": refused}
	latest = frappe.get_list(
		"Appraisal",
		filters={"employee": who, "docstatus": ["<", 2]},
		fields=["name", "appraisal_cycle"],
		order_by="creation desc",
		limit_page_length=1,
	)
	weakest = []
	if latest:
		rows = frappe.get_all(
			"Appraisal KRA",
			filters={"parent": latest[0].name, "parenttype": "Appraisal"},
			fields=["kra", "goal_completion", "goal_score"],
		)
		weakest = [
			{"kra": one.kra, "goal_completion": f"{one.goal_completion or 0:g}%"}
			for one in sorted(rows, key=lambda one: one.goal_completion or 0)[:3]
		]
	return {
		"appraisal": latest[0].name if latest else None,
		"weakest": weakest,
		# The catalogue, not anybody's record: read whatever the reader's role,
		# like the KRA list, since somebody who may not open the Training
		# Program master still needs to know what is on offer.
		"programs": [
			{"name": one.name, "about": frappe.utils.strip_html(one.description or "")[:300]}
			for one in frappe.get_all(
				"Training Program",
				filters={"status": ["!=", "Cancelled"]},
				fields=["name", "description"],
				limit=30,
			)
		],
		"coming_events": frappe.get_all(
			"Training Event",
			filters={"start_time": [">=", getdate()], "event_status": ["!=", "Cancelled"]},
			fields=["event_name", "training_program", "start_time", "level", "type"],
			order_by="start_time",
			limit=15,
		),
		"next": "Match the weakest areas to the programs and events above, naming each by its name. "
		"Say plainly when nothing here fits.",
	}


def kra_meant(said: str | None, known: list[str]) -> str | None:
	"""The KRA a model meant, from the workspace's own list. Pure."""
	said = (said or "").strip()
	if not said:
		return None
	low = {one.lower(): one for one in known}
	if said.lower() in low:
		return low[said.lower()]
	near = difflib.get_close_matches(said.lower(), list(low), n=1, cutoff=0.6)
	return low[near[0]] if near else None


def _open_cycle():
	cycles = frappe.get_all(
		"Appraisal Cycle",
		filters={"status": ["in", ["Not Started", "In Progress"]]},
		fields=["name", "start_date", "end_date"],
		order_by="start_date desc",
		limit=1,
	)
	return cycles[0] if cycles else None


def _whose(employee: str | None) -> tuple[str, str | None]:
	mine = own.employee_of()
	if not employee or employee == mine:
		return (mine, None) if mine else ("", "The person asking has no employee record here.")
	if set(HR) & set(frappe.get_roles()):
		return employee, None
	if mine and frappe.db.get_value("Employee", employee, "reports_to") == mine:
		return employee, None
	return "", "Only HR, or the person's own manager, can work on somebody else's goals."
