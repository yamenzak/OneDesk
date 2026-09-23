"""OneAI writing an HR letter: a salary certificate, an experience letter.

"I need a salary certificate for the bank" is the most common thing an
employee asks HR in the Gulf, and the answer is the same few facts every time,
typed again. Here the employee asks the panel, the facts come off their own
record, the model phrases them for whoever the letter is for, and the draft
becomes an `Employee Letter` that HR issues by submitting it.

**Facts from the record, words from the model.** `letter_facts` hands over
exactly what the letter may say — dates, designation, salary from the last
slip — and the model is told to use nothing else. HR reads the draft before
it is issued, which is where a wrong figure is caught.

**About yourself, or HR about anybody.** An employee's letter is always about
them; the employee is read from who is asking, never taken as an argument.
HR may name somebody.
"""

from typing import Annotated

import frappe
from frappe.utils import flt, fmt_money, getdate

from onedesk.one_ai import proposals
from onedesk.one_hr import own

KINDS = ("Salary Certificate", "Experience Letter", "Employment Letter", "No Objection Certificate", "Other")

#: The roles that may ask for a letter about somebody else.
HR = ("HR Manager", "HR User")


def letter_facts(
	kind: Annotated[str, "Salary Certificate, Experience Letter, Employment Letter, No Objection Certificate or Other."],
	employee: Annotated[str, "Only when HR is asking about somebody else: their employee id."] | None = None,
) -> dict:
	"""What an HR letter about the person may say: their name, designation,
	department, dates, and for a salary certificate their pay from the last
	salary slip. Read it before drafting, write the letter from these facts
	alone, then give it to request_letter."""
	who, refused = _whose(employee)
	if refused:
		return {"error": refused}
	held = frappe.db.get_value(
		"Employee",
		who,
		["employee_name", "designation", "department", "date_of_joining", "status", "relieving_date", "company", "gender"],
		as_dict=True,
	)
	facts = {
		"name": held.employee_name,
		"designation": held.designation,
		"department": (held.department or "").rsplit(" - ", 1)[0] or None,
		"joined": str(held.date_of_joining) if held.date_of_joining else None,
		"still_employed": held.status == "Active",
		"left": str(held.relieving_date) if held.relieving_date else None,
		"company": held.company,
		"today": str(getdate()),
	}
	if _kind(kind) == "Salary Certificate":
		facts["salary"] = _salary(who)
	facts["next"] = (
		"Write the letter body from these facts alone, in the register of a formal HR letter, addressed as "
		"the person asked. Never add a fact that is not here. Then call request_letter with it."
	)
	return facts


def request_letter(
	kind: Annotated[str, "Salary Certificate, Experience Letter, Employment Letter, No Objection Certificate or Other."],
	body: Annotated[str, "The letter's body, written from letter_facts: a few short paragraphs, no letterhead, no date."],
	addressed_to: Annotated[str, "Who it is for, such as a bank or an embassy, or To Whom It May Concern."] | None = None,
	purpose: Annotated[str, "What it is for, in a few words, such as opening a bank account."] | None = None,
	employee: Annotated[str, "Only when HR is asking about somebody else: their employee id."] | None = None,
) -> dict:
	"""Suggest the letter as an Employee Letter draft. Nothing is sent or
	issued: approving the card files the request, and HR issues it."""
	who, refused = _whose(employee)
	if refused:
		return {"error": refused}
	text = "".join(
		f"<p>{frappe.utils.escape_html(one.strip())}</p>" for one in (body or "").split("\n") if one.strip()
	)
	if not text:
		return {"error": "The letter has no body. Write it from letter_facts first."}
	name = proposals.propose(
		"Create",
		"Employee Letter",
		changes={
			"employee": who,
			"kind": _kind(kind),
			"addressed_to": (addressed_to or "").strip()[:140] or frappe._("To Whom It May Concern"),
			"purpose": (purpose or "").strip()[:300],
			"letter_date": str(getdate()),
			"body": text,
		},
	)
	return {"proposal": name, "state": "Proposed"}


def _whose(employee: str | None) -> tuple[str, str | None]:
	"""Whose letter this is, and why not if it cannot be."""
	mine = own.employee_of()
	if not employee or employee == mine:
		if not mine:
			return "", "The person asking has no employee record here, so there is nobody to write a letter about."
		return mine, None
	if not (set(HR) & set(frappe.get_roles())):
		return "", "Only HR can ask for a letter about somebody else. Offer to write one about the person asking."
	if not frappe.db.exists("Employee", employee):
		return "", f"There is no employee {employee!r}."
	return employee, None


def _kind(said: str | None) -> str:
	said = (said or "").strip().lower()
	return next((one for one in KINDS if one.lower() == said or one.lower().startswith(said[:8])), "Other") if said else "Other"


def _salary(employee: str) -> dict | None:
	"""The last submitted slip's monthly pay, read as the person asking."""
	slips = frappe.get_list(
		"Salary Slip",
		filters={"employee": employee, "docstatus": 1},
		fields=["name", "gross_pay", "net_pay", "currency", "start_date"],
		order_by="start_date desc",
		limit_page_length=1,
	)
	if not slips:
		return None
	slip = slips[0]
	earnings = frappe.get_all(
		"Salary Detail",
		filters={"parent": slip.name, "parenttype": "Salary Slip", "parentfield": "earnings"},
		fields=["salary_component", "amount"],
		order_by="idx",
	)
	# The code, not the symbol: a letter to a bank says AED 6,000.00, and the
	# symbol for dirhams is written in Arabic script.
	money = lambda amount: f"{slip.currency} {fmt_money(flt(amount))}".strip()
	return {
		"month": str(slip.start_date)[:7],
		"gross_monthly": money(slip.gross_pay),
		"net_monthly": money(slip.net_pay),
		"made_of": {one.salary_component: money(one.amount) for one in earnings},
	}
