"""OneAI reading a new grievance: a summary, a category, and who may see it."""

import html

import frappe
from frappe.utils import cint

from onedesk.one_hr import hiring, own, tell

CATEGORIES = (
	"Pay",
	"Leave",
	"Workload",
	"Manager",
	"Colleague",
	"Facilities",
	"Other",
	"Harassment",
	"Discrimination",
	"Safety",
)
SENSITIVE = ("Harassment", "Discrimination", "Safety")

TRUSTED = "HR Manager"


def raised(doc, method=None) -> None:
	"""A new grievance: read it once the insert is committed, or, with OneAI's
	reading off, told to HR as it is."""
	if cint(frappe.db.get_single_value("HR Settings", "one_ai_grievances")):
		hiring._later("onedesk.one_hr.ai_grievance.triage", f"grievance::{doc.name}", grievance=doc.name)
	else:
		tell.grievance_raised(doc)


def triage(grievance: str) -> None:
	frappe.set_user(hiring.AUTHOR)
	doc = frappe.get_doc("Employee Grievance", grievance)
	asked = TRIAGE.format(
		subject=doc.subject or "",
		kind=doc.grievance_type or "",
		against=f"{doc.grievance_against_party or ''} {doc.grievance_against or ''}".strip() or "(not said)",
		description=hiring._plain(doc.description, 4000),
		cause=hiring._plain(doc.cause_of_grievance, 1500) or "(not said)",
		categories=", ".join(CATEGORIES),
	)
	answer = hiring._read("grievance", hiring._ask("grievance", asked, None, grievance), grievance)
	if not answer:
		tell.grievance_raised(doc)
		return

	category = answer.get("category") if answer.get("category") in CATEGORIES else "Other"
	sensitive = category in SENSITIVE or bool(answer.get("sensitive"))
	urgency = answer.get("urgency") if answer.get("urgency") in ("Low", "Normal", "High") else "Normal"
	values = {
		"one_ai_category": category,
		"one_ai_urgency": urgency,
		"one_ai_summary": hiring._short(answer.get("summary"), 400),
	}
	if sensitive:
		values["one_ai_sensitive"] = 1
	frappe.db.set_value("Employee Grievance", grievance, values)

	head = " · ".join(
		one
		for one in (
			frappe._(category),
			frappe._("Sensitive") if sensitive else "",
			frappe._("Urgent") if urgency == "High" else "",
		)
		if one
	)
	body = f"<p><strong>{html.escape(head)}</strong></p>"
	if answer.get("summary"):
		body += f"<p>{html.escape(hiring._short(answer['summary'], 400))}</p>"
	steps = [str(one).strip() for one in (answer.get("first_steps") or []) if str(one).strip()][:3]
	if steps:
		body += (
			f"<p><strong>{html.escape(frappe._('First steps'))}</strong></p><ul>"
			+ "".join(f"<li>{html.escape(one)}</li>" for one in steps)
			+ "</ul>"
		)
	hiring._comment("Employee Grievance", grievance, body)
	frappe.db.commit()

	if sensitive or urgency == "High":
		tell.grievance_flagged(doc, sensitive)
	else:
		tell.grievance_raised(doc)
	hiring._refresh("Employee Grievance", grievance)


TRIAGE = """Read one employee grievance for HR.

SUBJECT: {subject}
TYPE GIVEN: {kind}
AGAINST: {against}
WHAT HAPPENED:
{description}
CAUSE, AS THEY SEE IT:
{cause}

Answer with one JSON object and nothing else:
{{
  "summary": "two sentences, neutral: what the person raised and what they want, without deciding who is right",
  "category": "one of: {categories}",
  "sensitive": true or false — true for harassment, discrimination, threats, violence, safety, or anything about a person's body, health or private life,
  "urgency": "Low, Normal or High — High when somebody may be hurt or is being harmed now",
  "first_steps": ["up to three things HR should do first"]
}}
Name nobody the grievance does not name. When in doubt about sensitive, answer true."""


def trusted_users() -> list[str]:
	holders = frappe.get_all("Has Role", filters={"role": TRUSTED, "parenttype": "User"}, pluck="parent")
	return frappe.get_all(
		"User",
		filters={"name": ["in", holders or [""]], "enabled": 1, "user_type": "System User"},
		pluck="name",
	)


def _trusted(user: str) -> bool:
	return user == "Administrator" or TRUSTED in frappe.get_roles(user)


def query(user: str | None = None) -> str:
	"""A sensitive grievance is left out of every list but its raiser's and HR Managers'."""
	user = user or frappe.session.user
	if _trusted(user):
		return ""
	mine = own.employee_of(user)
	return (
		"(ifnull(`tabEmployee Grievance`.one_ai_sensitive, 0) = 0"
		f" or `tabEmployee Grievance`.raised_by = {frappe.db.escape(mine or '-')}"
		f" or `tabEmployee Grievance`.owner = {frappe.db.escape(user)})"
	)


def allowed(doc, ptype=None, user=None, debug=False) -> bool:
	"""And out of its own page.

	True for everything else, not None: frappe reads any falsy answer from a
	`has_permission` hook as a refusal, so "no opinion" written as None shut
	every HR Manager out of every grievance — measured, not assumed. A hook
	can only take permission away; True leaves HRMS's own rules to decide.
	"""
	user = user or frappe.session.user
	if not cint(doc.get("one_ai_sensitive")) or _trusted(user):
		return True
	if doc.get("owner") == user or (doc.get("raised_by") and doc.get("raised_by") == own.employee_of(user)):
		return True
	return False


def unmarked(doc, method=None) -> None:
	"""Only an HR Manager takes the mark off."""
	before = doc.get_doc_before_save()
	if before and cint(before.get("one_ai_sensitive")) and not cint(doc.get("one_ai_sensitive")):
		if not _trusted(frappe.session.user):
			frappe.throw(frappe._("Only an HR Manager can mark a grievance as not sensitive."))
