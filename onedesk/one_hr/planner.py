"""What OneHR's people officer makes of what OneAI read (docs/ARC-AI.md, The
agents): an applicant from a CV, a person's own documents on their
Employee, a sick note as leave, a resignation proposed, and a colleague's
receipt as their expense claim. Pure: each answers actions, which the
agents' door takes."""

from datetime import timedelta

from frappe.utils import getdate

from onedesk.one_ai.reading.act import Action
from onedesk.one_ai.reading.plans import _name, counterpart, known, real


LEAD_DAYS = {"residence permit": 90, "visa": 90, "work permit": 90, "passport": 60, "driving licence": 30, "driving license": 30}


LEAD_DEFAULT = 60


def applicant(reading: dict, ctx: dict) -> list[Action]:
	"""Who sent a CV from outside, as a Job Applicant nobody has made yet."""
	if not real(reading, ctx) or ctx.get("direction") == "Sent" or reading.get("kind") != "CV" or ctx.get("sender_is_colleague"):
		return []
	party = counterpart(reading)
	if not party or known(party) or not (party.get("email") or ctx.get("sender_email")):
		return []
	values = {
		"applicant_name": _name(party) or ctx.get("sender_name"),
		"email_id": party.get("email") or ctx.get("sender_email"),
		"phone_number": party.get("phone"),
		"source": ctx.get("applicant_source"),
	}
	if not values["applicant_name"]:
		return []
	return [Action("Create", "Job Applicant", values={k: v for k, v in values.items() if v}, key="party|applicant", why=ctx.get("why_made") or "")]


def employee_documents(reading: dict, ctx: dict) -> list[Action]:
	"""A person's own documents, on their Employee: an identity document as
	a row (taking the place of the one of its kind it renews) with a task
	before it runs out, a certificate as an education row,
	a sick note as a leave application, a resignation proposed, and the
	contract an applicant signed as their Employee, proposed."""
	employee = ctx.get("employee")
	kind = reading.get("kind") or ""
	if not real(reading, ctx):
		return []
	if kind == "Contract" and ctx.get("accepted_offer") and not ctx.get("employee_of_applicant"):
		return [Action("Create", "Employee", values={"job_offer": ctx["accepted_offer"]}, key="employee", flow="onedesk.one_ai.reading.planning.employee_from_offer", propose=True, as_person=True)]
	if not employee:
		return []
	out: list[Action] = []
	number = reading.get("number") or next((one.get("document_number") for one in reading.get("parties") or [] if one.get("role") == "Holder" and one.get("document_number")), None)
	if kind == "Identity Document" and number:
		if number in (ctx.get("employee_document_numbers") or []):
			return []
		row = {
			"document_type": reading.get("document_type"),
			"number": number,
			"expires_on": reading.get("valid_until"),
			"issued_on": reading.get("issued_on"),
			"country": reading.get("issuing_country"),
			"attachment": ctx.get("file_url"),
		}
		values = {"table": "one_documents", "row": {k: v for k, v in row.items() if v}}
		renews = (ctx.get("employee_documents_by_type") or {}).get(reading.get("document_type"))
		if renews:
			values["replaces"] = renews
		out.append(Action("Add", "Employee", employee, values, key=f"document|{number}", sure=True))
		if reading.get("valid_until"):
			lead = LEAD_DAYS.get((reading.get("document_type") or "").lower(), LEAD_DEFAULT)
			due = getdate(reading["valid_until"]) - timedelta(days=lead)
			out.append(
				Action(
					"Create",
					"Task",
					values={
						"subject": ctx["said"]["renew"].format(reading.get("document_type") or ctx["said"]["document"], ctx.get("employee_name") or employee),
						"exp_end_date": str(max(due, getdate(ctx.get("today")))),
						"one_about_doctype": "Employee",
						"one_about": employee,
						"assign_to": ctx.get("hr_officer") or ctx.get("person"),
					},
					key=f"task|renew|{number}",
					flow="onedesk.one_ai.reading.planning.make_task",
					sure=True,
				)
			)
	elif kind == "Certificate":
		year = getdate(reading["issued_on"]).year if reading.get("issued_on") else None
		issuer = next((_name(one) for one in reading.get("parties") or [] if one.get("role") == "Sender" and not one.get("ours")), "")
		row = {"qualification": (reading.get("title") or "")[:140], "school_univ": issuer, "year_of_passing": year}
		out.append(Action("Add", "Employee", employee, {"table": "education", "row": {k: v for k, v in row.items() if v}}, key="education"))
	elif kind == "Sick Note" and ctx.get("sick_leave_type"):
		start, end = period(reading)
		if start:
			values = {
				"employee": employee,
				"leave_type": ctx["sick_leave_type"],
				"from_date": start,
				"to_date": end or start,
				"posting_date": ctx.get("today"),
				"status": "Open",
				"leave_approver": ctx.get("leave_approver"),
				"description": ctx["said"]["sick_note"],
			}
			out.append(Action("Create", "Leave Application", values={k: v for k, v in values.items() if v}, key="leave", propose_on_error=True, as_person=True))
	elif kind == "Resignation":
		leaving = next((one.get("date") for one in reading.get("dates") or [] if one.get("what") in ("Valid Until", "Deadline", "Period End")), None)
		values = {"resignation_letter_date": reading.get("issued_on") or ctx.get("today"), "relieving_date": leaving}
		out.append(Action("Update", "Employee", employee, {k: v for k, v in values.items() if v}, key="resignation", ends_employment=True))
	return out


def receipt(reading: dict, ctx: dict) -> list[Action]:
	"""A receipt a colleague paid and sent in, as their expense claim."""
	if not real(reading, ctx) or reading.get("kind") != "Receipt" or not ctx.get("sender_employee") or not reading.get("gross"):
		return []
	if ctx.get("company_currency") and reading.get("currency") and reading["currency"] != ctx["company_currency"]:
		return []
	if not ctx.get("expense_type"):
		return []
	values = {
		"employee": ctx["sender_employee"],
		"posting_date": ctx.get("today"),
		"expense_approver": ctx.get("expense_approver"),
		"expenses": [
			{
				"expense_date": reading.get("issued_on") or ctx.get("today"),
				"expense_type": ctx["expense_type"],
				"description": (reading.get("title") or "")[:140],
				"amount": reading["gross"],
				"sanctioned_amount": reading["gross"],
			}
		],
	}
	return [Action("Create", "Expense Claim", values={k: v for k, v in values.items() if v}, key="expense", propose_on_error=True, as_person=True)]


def period(reading: dict) -> tuple[str | None, str | None]:
	"""The first and last day a document covers. Pure."""
	dates = {one.get("what"): one.get("date") for one in reading.get("dates") or [] if one.get("date")}
	start = dates.get("Valid From") or dates.get("Period Start") or reading.get("issued_on")
	end = dates.get("Valid Until") or dates.get("Period End")
	return (str(start) if start else None), (str(end) if end else None)
