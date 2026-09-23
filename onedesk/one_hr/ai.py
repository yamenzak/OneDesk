"""What OneAI can do in OneHR.

The tools and suggestions this module adds to the panel, named in `hooks.py`
under `one_ai_suggests` and `one_ai_suggestions`. The rules are OneAI's: a tool
runs as the person asking, and anything that would write is a card somebody
approves. What this module adds is what HR knows — whose employee record a
receipt belongs to, what a claim needs, which expense types this workspace has.

**A receipt becomes a claim, never a payment.** `claim_expense` reads nothing
the person could not, and writes nothing: it suggests an Expense Claim in their
own name with one row, and the receipt goes on the claim when it is approved.
The claim then goes through this workspace's approval like any other, which is
where a wrong amount is caught — by the person who approves expenses, not by the
model that read the paper.
"""

from typing import Annotated

import frappe
from frappe.utils import add_days, getdate, today

from onedesk.one_ai import proposals
from onedesk.one_hr import own

#: What the panel offers, by doctype, when it opens on one. `file` means the
#: chip asks for a file first and then says `ask` with it. `can` is the verb the
#: reader must hold on the doctype for the chip to be offered at all.
SUGGESTIONS = {
	"Expense Claim": [
		{
			"label": "Claim a receipt",
			"ask": "Make an expense claim from this receipt.",
			"file": True,
			"can": "create",
		},
	],
	"Leave Application": [
		{"label": "Book time off", "ask": "Help me book time off.", "can": "create"},
		{
			"label": "How much leave do I have?",
			"ask": "How much leave do I have left, and who on my team is off in the next two weeks?",
			"can": "read",
		},
	],
	# OneHR's home is where an employee starts their day, so the three things
	# they come to it for are offered there too.
	"workspace:OneHR": [
		{"label": "Book time off", "ask": "Help me book time off.", "doctype": "Leave Application", "can": "create"},
		{
			"label": "Claim a receipt",
			"ask": "Make an expense claim from this receipt.",
			"doctype": "Expense Claim",
			"file": True,
			"can": "create",
		},
		{
			"label": "How much leave do I have?",
			"ask": "How much leave do I have left, and who on my team is off in the next two weeks?",
			"doctype": "Leave Application",
			"can": "read",
		},
	],
}

#: How far ahead "who is off" looks when no dates are given.
AHEAD = 14


def claim_expense(
	expense_date: Annotated[str, "The date on the receipt, as YYYY-MM-DD."],
	amount: Annotated[float, "The total paid, as printed on the receipt."],
	expense_type: Annotated[str, "What kind of expense it is, in a word or two, such as taxi, meal or hotel."],
	description: Annotated[str, "The vendor and what was bought, in a few words."],
	currency: Annotated[str, "The currency code on the receipt, such as AED."] | None = None,
) -> dict:
	"""Suggest an expense claim, in the asker's own name, from one receipt.

	Nothing is claimed until the person approves it, and then it goes through
	the workspace's own approval like any claim.
	"""
	employee = own.employee_of()
	if not employee:
		return {"error": "The person asking has no employee record here, so there is nobody to claim for."}

	types = frappe.get_all("Expense Claim Type", pluck="name")
	chosen = kind(expense_type, description, types)
	if not chosen:
		return {"error": "This workspace has no expense types yet, so there is nothing to claim under."}

	company = frappe.db.get_value("Employee", employee, "company")
	ours = frappe.db.get_value("Company", company, "default_currency") if company else None
	said = (currency or "").strip().upper()
	if said and ours and said != ours:
		# Claimed in the company's currency or not at all. A converted amount
		# would be a rate the model made up; the approver sees the receipt.
		return {
			"error": f"The receipt is in {said} and claims here are in {ours}. "
			"Say so to the person rather than converting it."
		}

	name = proposals.propose(
		"Create",
		"Expense Claim",
		changes={
			"employee": employee,
			"posting_date": frappe.utils.today(),
			"expenses": [
				{
					"expense_date": expense_date,
					"expense_type": chosen,
					"description": (description or "").strip()[:140],
					"amount": float(amount or 0),
				}
			],
		},
		why=frappe._("From a receipt: {0}, {1}.").format((description or "").strip()[:80], amount),
		files=frappe.flags.get("one_ai_files") or [],
	)
	return {
		"proposal": name,
		"state": "Proposed",
		"said": frappe._("Suggested. It happens when somebody approves it."),
	}


#: Words on a receipt, and the kind of expense they usually are. Only used when
#: the workspace has a type of that name; a workspace's own types are the list.
KINDS = {
	"Travel": ("taxi", "cab", "uber", "careem", "flight", "airline", "train", "metro", "bus",
			   "hotel", "fuel", "petrol", "parking", "toll", "travel", "transport", "trip"),
	"Food": ("meal", "food", "lunch", "dinner", "breakfast", "restaurant", "cafe", "coffee", "snack"),
	"Calls": ("phone", "mobile", "call", "sim", "internet", "data"),
	"Medical": ("medical", "pharmacy", "clinic", "doctor", "hospital", "medicine"),
}


def kind(said: str | None, description: str | None, types: list[str]) -> str | None:
	"""The workspace's expense type closest to what the model read.

	Decided here rather than by the model, because a model told a type does not
	exist asks the person which one — a question the approver answers better,
	later, on the claim. Its own word first, then what the receipt says, then
	whatever is closest by name, then Others: a claim filed under the wrong type
	is corrected by an approver, and a claim never suggested is not.
	"""
	if not types:
		return None
	by_name = {one.lower(): one for one in types}
	said = (said or "").strip().lower()
	if said in by_name:
		return by_name[said]

	words = f"{said} {(description or '').lower()}"
	for name, clues in KINDS.items():
		if name.lower() in by_name and any(clue in words for clue in clues):
			return by_name[name.lower()]

	import difflib

	near = difflib.get_close_matches(said, list(by_name), n=1, cutoff=0.6)
	if near:
		return by_name[near[0]]
	return by_name.get("others") or by_name.get("other") or types[0]


# ----------------------------------------------------------------- leave


def my_leave(
	from_date: Annotated[str, "The first day asked about, as YYYY-MM-DD, if the person named one."] | None = None,
	to_date: Annotated[str, "The last day asked about, as YYYY-MM-DD."] | None = None,
	leave_type: Annotated[str, "The kind of leave asked about, if one was named."] | None = None,
) -> dict:
	"""The asker's own leave: what is left of each kind, and around the dates asked
	about — the holidays in them, how many days they would cost, and who on their
	team is already off.

	Who is off is exactly what their leave calendar already shows them, by HRMS's
	own rule: their department, when HR Settings shows department leave to
	everybody, and otherwise only what they may read.
	"""
	from hrms.hr.doctype.leave_application.leave_application import (
		add_department_leaves,
		get_leave_details,
		get_number_of_leave_days,
	)
	from hrms.utils.holiday_list import get_holiday_dates_between_range

	employee = own.employee_of()
	if not employee:
		return {"error": "The person asking has no employee record here, so there is no leave to read."}

	details = get_leave_details(employee, today())
	left = {
		kind: {
			"left": one.get("remaining_leaves"),
			"taken": one.get("leaves_taken"),
			"waiting_for_approval": one.get("leaves_pending_approval"),
		}
		for kind, one in (details.get("leave_allocation") or {}).items()
	}
	said = {"balances": left, "approver": details.get("leave_approver")}

	start = getdate(from_date) if from_date else getdate(today())
	end = getdate(to_date) if to_date else (start if from_date else add_days(start, AHEAD))
	said["period"] = {"from": str(start), "to": str(end)}

	holidays = get_holiday_dates_between_range(
		employee, start, end, raise_exception_for_holiday_list=False, as_dict=True
	)
	said["holidays"] = [
		{"date": str(one.holiday_date), "what": one.description, "weekly_off": bool(one.weekly_off)}
		for one in holidays
	]

	kind = _leave_type(leave_type, list(left)) if leave_type or from_date else None
	if kind and from_date:
		said["days_it_would_take"] = {kind: get_number_of_leave_days(employee, kind, start, end)}

	company = frappe.db.get_value("Employee", employee, "company")
	events = []
	add_department_leaves(events, start, end, employee, company)
	mine = set(frappe.get_all("Leave Application", filters={"employee": employee}, pluck="name"))
	said["team_off"] = [
		{"who": one.get("title"), "from": str(one.get("from_date")), "to": str(one.get("to_date"))}
		for one in events
		if one.get("name") not in mine
	]
	said["already_booked"] = frappe.get_list(
		"Leave Application",
		filters={"employee": employee, "from_date": ["<=", end], "to_date": [">=", start], "docstatus": ["<", 2]},
		fields=["from_date", "to_date", "leave_type", "status"],
	)
	return said


def book_leave(
	from_date: Annotated[str, "The first day off, as YYYY-MM-DD."],
	to_date: Annotated[str, "The last day off, as YYYY-MM-DD. The same as from_date for one day."],
	leave_type: Annotated[str, "The kind of leave, such as annual, sick or casual."],
	reason: Annotated[str, "Why, in the person's own words, briefly."] | None = None,
	half_day: Annotated[bool, "True if one of the days is only half a day off."] | None = None,
	half_day_date: Annotated[str, "Which day is the half day, as YYYY-MM-DD."] | None = None,
) -> dict:
	"""Suggest a leave application, in the asker's own name.

	Nothing is applied for until the person approves the card, and then it goes
	to their leave approver like any application.
	"""
	from hrms.hr.doctype.leave_application.leave_application import (
		get_employee_leave_approver,
		get_leave_details,
		get_number_of_leave_days,
	)

	employee = own.employee_of()
	if not employee:
		return {"error": "The person asking has no employee record here, so there is nobody to book leave for."}

	start, end = getdate(from_date), getdate(to_date)
	if end < start:
		start, end = end, start

	allocated = get_leave_details(employee, today()).get("leave_allocation") or {}
	kinds = frappe.get_all("Leave Type", pluck="name")
	kind = _leave_type(leave_type, list(allocated) or kinds, kinds)
	if not kind:
		return {"error": "This workspace has no leave types yet."}

	days = get_number_of_leave_days(employee, kind, start, end, 1 if half_day else 0, half_day_date or None)
	left = (allocated.get(kind) or {}).get("remaining_leaves")
	unpaid = frappe.db.get_value("Leave Type", kind, "is_lwp")
	if not unpaid and left is not None and days > left:
		return {
			"error": f"That is {days} days of {kind} and {left} are left. Say so to the person, "
			"and offer fewer days or another kind of leave."
		}
	if days <= 0:
		return {"error": f"Every day from {start} to {end} is a holiday or a weekly off, so it costs no leave."}

	values = {
		"employee": employee,
		"leave_type": kind,
		"from_date": str(start),
		"to_date": str(end),
		"description": (reason or "").strip()[:280],
		"posting_date": today(),
	}
	if half_day:
		values.update({"half_day": 1, "half_day_date": half_day_date or str(start)})
	approver = get_employee_leave_approver(employee)
	if approver:
		values["leave_approver"] = approver
	elif frappe.db.get_single_value("HR Settings", "leave_approver_mandatory_in_leave_application"):
		# Said now rather than at Approve, where it is a red toast about a field
		# the person never saw and cannot fill.
		return {
			"error": "Nobody approves this person's leave yet, so it cannot be applied for. Say that "
			"HR sets a leave approver on their employee record or their department."
		}

	if left is None or unpaid:
		why = frappe._("{0} days of {1}.").format(f"{days:g}", frappe._(kind))
	else:
		why = frappe._("{0} days of {1}; {2} left after.").format(f"{days:g}", frappe._(kind), f"{left - days:g}")
	name = proposals.propose("Create", "Leave Application", changes=values, why=why)
	from hrms.utils.holiday_list import get_holiday_dates_between_range

	free = get_holiday_dates_between_range(
		employee, start, end, raise_exception_for_holiday_list=False, as_dict=True
	)
	return {
		"proposal": name,
		"state": "Proposed",
		"days_it_takes": days,
		"left_after": None if unpaid or left is None else left - days,
		"days_that_cost_nothing": [
			{"date": str(one.holiday_date), "what": one.description, "weekly_off": bool(one.weekly_off)}
			for one in free
		],
		"said": "Suggested, not applied for. Say how many days it takes and name any day in it that "
		"costs nothing. Once the person approves the card it goes to their leave approver.",
	}


def _leave_type(said: str | None, offered: list[str], every: list[str] | None = None) -> str | None:
	"""The leave type closest to what the person said, from what they have.

	Picked here for the reason `kind` is: a model told a type does not exist
	asks, and the approver is the one who corrects a wrong type.
	"""
	import difflib

	names = offered or every or []
	if not names:
		return None
	by_name = {one.lower(): one for one in (every or names)}
	said = (said or "").strip().lower()
	if said in by_name:
		return by_name[said]
	for one in names:
		if said and said in one.lower():
			return one
	near = difflib.get_close_matches(said, [one.lower() for one in names], n=1, cutoff=0.5)
	if near:
		return by_name.get(near[0]) or names[0]
	# What people say instead of a type's name.
	for words, meant in ((("ill", "unwell", "doctor", "medical"), "sick"),):
		if any(word in said for word in words):
			found = [one for one in names if meant in one.lower()]
			if found:
				return found[0]
	# Nothing like it: "vacation", "time off", "a day off" — the annual kind
	# first, then casual.
	for meant in ("annual", "casual"):
		found = [one for one in names if meant in one.lower()]
		if found:
			return found[0]
	return names[0]
