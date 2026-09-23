"""OneAI answering a policy question from what this workspace actually says.

"How many sick days do I get?" has two honest answers: what somebody wrote
down (an `AI Knowledge` note, the handbook pasted in) and what the system is
set up to do (the Leave Type's maximum, whether it carries forward). A model
asked without either answers from what companies usually do, which is a
confident wrong answer to the one question an employee acts on.

So `hr_policy` hands over both, each with where it came from, and the tool
says the answer names its source — a note by its title, a rule by its record —
and says plainly when neither covers the question. Read as the person asking.
"""

from typing import Annotated

import frappe
from frappe.utils import getdate

from onedesk.one_ai import memory
from onedesk.one_hr import own

#: Words that say which of the workspace's own rules a question is about.
TOPICS = {
	"leave": ("leave", "sick", "annual", "vacation", "holiday", "time off", "maternity", "paternity", "carry", "encash", "absence"),
	"expenses": ("expense", "claim", "receipt", "reimburs", "travel", "allowance", "taxi", "meal"),
	"hours": ("hour", "overtime", "shift", "late", "check", "attendance", "remote", "home"),
	"leaving": ("notice", "resign", "leaving", "quit", "exit", "gratuity", "terminat"),
}

#: How much of one note is handed over: the part around the words asked about.
PASSAGE = 700


def hr_policy(
	question: Annotated[str, "The person's question, in their words."],
) -> dict:
	"""The workspace's own written policies and its configured HR rules that
	bear on a question — leave types and their limits, holidays, expense
	types, working hours, notice. Answer only from what this returns, name the
	note or the record each part of the answer comes from, and say plainly
	when nothing here covers the question rather than answering from what is
	usual elsewhere."""
	words = memory._words(question)
	low = (question or "").lower()
	about = {topic for topic, keys in TOPICS.items() if any(key in low for key in keys)}

	said = {"notes": _notes(words)}
	if "leave" in about:
		said["leave_types"] = _leave_types()
		said["holidays"] = _holidays()
	if "expenses" in about:
		said["expense_types"] = frappe.get_list("Expense Claim Type", pluck="name", limit_page_length=40)
		said["expense_approval"] = (
			"An approver is required on every claim."
			if frappe.db.get_single_value("HR Settings", "expense_approver_mandatory_in_expense_claim")
			else "No approver is required on a claim."
		)
	if "hours" in about:
		hours = frappe.db.get_single_value("HR Settings", "standard_working_hours")
		said["working_hours"] = f"{hours:g} hours a day where the shift does not say" if hours else None
	if "leaving" in about:
		said["notice"] = _notice()

	said["next"] = (
		"Answer from this alone. After each part of the answer, name its source in brackets: a note by its "
		"title, a rule by its record, such as [Leave Type: Sick Leave]. If nothing here answers the question, "
		"say it is not written down here and that HR can answer it — do not answer from what is usual."
	)
	return said


def _notes(words: list[str]) -> list[dict]:
	found = frappe.get_list(
		"AI Knowledge",
		filters={"enabled": 1},
		or_filters=[f for one in words for f in (["title", "like", f"%{one}%"], ["body", "like", f"%{one}%"])],
		fields=["title", "applies_to", "body"],
		limit_page_length=4,
	)
	return [
		{"source": f"Note: {one.title}", "applies_to": one.applies_to, "text": passage(memory._text(one.body), words)}
		for one in found
	]


def passage(text: str, words: list[str], most: int = PASSAGE) -> str:
	"""The part of a note around the first word asked about. Pure."""
	if len(text) <= most:
		return text
	low = text.lower()
	at = min((low.find(one) for one in words if one and low.find(one) >= 0), default=0)
	start = max(0, at - most // 3)
	start = text.rfind(". ", 0, start) + 2 if text.rfind(". ", 0, start) >= 0 else start
	cut = text[start : start + most]
	return ("…" if start else "") + cut + ("…" if start + most < len(text) else "")


def _leave_types() -> list[dict]:
	rows = frappe.get_list(
		"Leave Type",
		fields=[
			"name",
			"max_leaves_allowed",
			"applicable_after",
			"max_continuous_days_allowed",
			"is_carry_forward",
			"maximum_carry_forwarded_leaves",
			"is_lwp",
			"allow_encashment",
			"include_holiday",
			"is_earned_leave",
		],
		limit_page_length=30,
	)
	out = []
	for one in rows:
		rule = {"source": f"Leave Type: {one.name}"}
		if one.max_leaves_allowed:
			rule["most_a_year"] = one.max_leaves_allowed
		if one.max_continuous_days_allowed:
			rule["most_in_a_row"] = one.max_continuous_days_allowed
		if one.applicable_after:
			rule["after_working_days"] = one.applicable_after
		if one.is_carry_forward:
			rule["carries_forward"] = one.maximum_carry_forwarded_leaves or True
		if one.is_lwp:
			rule["unpaid"] = True
		if one.allow_encashment:
			rule["can_be_encashed"] = True
		if one.include_holiday:
			rule["holidays_inside_count"] = True
		if one.is_earned_leave:
			rule["earned_monthly"] = True
		out.append(rule)
	return out


def _holidays() -> dict | None:
	"""The asker's holiday list: which days are off every week, and the next few holidays."""
	employee = own.employee_of()
	named = frappe.db.get_value("Employee", employee, "holiday_list") if employee else None
	if not named and employee:
		company = frappe.db.get_value("Employee", employee, "company")
		named = frappe.db.get_value("Company", company, "default_holiday_list") if company else None
	if not named:
		return None
	days = frappe.get_all(
		"Holiday",
		filters={"parent": named, "parenttype": "Holiday List", "holiday_date": [">=", getdate()]},
		fields=["holiday_date", "description", "weekly_off"],
		order_by="holiday_date",
		limit=40,
	)
	weekly = sorted({str(one.holiday_date.strftime("%A")) for one in days if one.weekly_off})
	coming = [
		f"{one.holiday_date}: {memory._text(one.description)}" for one in days if not one.weekly_off
	][:6]
	return {"source": f"Holiday List: {named}", "weekly_off": weekly, "next_holidays": coming}


def _notice() -> str | None:
	employee = own.employee_of()
	days = frappe.db.get_value("Employee", employee, "notice_number_of_days") if employee else None
	return f"{days} days, on your employee record [Employee: notice period]" if days else None
