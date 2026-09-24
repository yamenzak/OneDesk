"""Stage 6 of Intake: what a document makes, as a list of actions. Pure.

Each planner takes the Reading as a dict and what `planning.context` found out
about it (who the sender is, which employee, the matter's task) and answers
the actions the door should take. None of them touches the database or asks
a model, so each row of docs/INTAKE.md §3.1 is an ordinary unit test: this
reading, in this context, makes these actions.

Two passes. **Parties** first: the counterpart a document needs and does not
have yet (a supplier for an invoice, a customer for an order, a lead for an
inquiry, an applicant for a CV). The door makes them, the reading's parties
are matched again, and filing runs with the new records in place. Then
**everything else**: the sender's Contact, a person's documents on their
Employee, a sick note's leave, an employee's receipt, one task per matter,
an appointment's event and what our own mail promised.

**A document never creates a party just for being mentioned.** Only the
counterpart, and only when the kind of document says what it must be. A
name alone makes nothing: a supplier needs a VAT id, a tax number, an IBAN,
a register number or its own email domain.
"""

from datetime import timedelta

from frappe.utils import getdate

from onedesk.one_intake.act import Action

#: Readings that are real enough to make anything from.
REAL = ("Action", "Information", "", None)

#: Who a document's counterpart is, by kind: the party whose role this is.
COUNTERPART = {"CV": ("Holder", "Sender"), "Identity Document": ("Holder",), "Sick Note": ("Patient", "Holder", "Sender")}

#: Days before a document runs out that its holder's HR officer is told.
LEAD_DAYS = {"residence permit": 90, "visa": 90, "work permit": 90, "passport": 60, "driving licence": 30, "driving license": 30}
LEAD_DEFAULT = 60

#: A task's priority, one step up for each reminder.
PRIORITY = ("Low", "Medium", "High", "Urgent")

PERSONAL = ("Personal", "Medical", "Pay", "Legal")


# ------------------------------------------------------------------ helpers


def counterpart(reading: dict) -> dict | None:
	"""The party a document is from or about, as far as making a record goes."""
	roles = COUNTERPART.get(reading.get("kind") or "", ("Sender",))
	for role in roles:
		for one in reading.get("parties") or []:
			if one.get("role") == role and not one.get("ours"):
				return one
	return None


def strong(party: dict) -> bool:
	"""Whether a party is identified by more than its name."""
	return any(party.get(key) for key in ("vat_id", "tax_number", "iban", "register")) or bool(party.get("org_domain"))


def _name(party: dict) -> str:
	return (party.get("party_name") or "").strip()


def _split(full: str) -> tuple[str, str]:
	parts = (full or "").strip().split()
	if not parts:
		return "", ""
	return parts[0], " ".join(parts[1:])


def real(reading: dict, ctx: dict) -> bool:
	return reading.get("verdict") in REAL and not ctx.get("history") and reading.get("change") != "Nothing New"


# ------------------------------------------------------------------ pass 1: parties


def parties(reading: dict, ctx: dict) -> list[Action]:
	"""The counterpart the document needs and nobody has made yet."""
	if not real(reading, ctx) or ctx.get("direction") == "Sent":
		return []
	kind = reading.get("kind") or ""
	party = counterpart(reading)
	if not party or party.get("matched_name"):
		return []
	name = _name(party)
	why = ctx.get("why_made") or ""
	if kind in ("Invoice", "Credit Note") and name and strong(party):
		return [
			Action(
				"Create",
				"Supplier",
				values={k: v for k, v in {"supplier_name": name, "supplier_group": ctx.get("supplier_group"), "supplier_type": "Company", "tax_id": party.get("vat_id") or party.get("tax_number"), "country": ctx.get("country_of", {}).get(name)}.items() if v},
				key="party|supplier",
				why=why,
				confidence=(reading.get("confidence") or 100) / 100,
			)
		]
	if kind == "Order" and name:
		if ctx.get("sender_lead"):
			return [Action("Create", "Customer", values={"lead": ctx["sender_lead"]}, key="party|customer", flow="onedesk.one_intake.planning.customer_from_lead", why=why)]
		person = bool(party.get("is_person"))
		return [
			Action(
				"Create",
				"Customer",
				values={k: v for k, v in {"customer_name": name, "customer_group": ctx.get("customer_group"), "territory": ctx.get("territory"), "customer_type": "Individual" if person else "Company"}.items() if v},
				key="party|customer",
				why=why,
			)
		]
	if kind == "Inquiry" and (party.get("email") or ctx.get("sender_email")):
		first, last = _split(party.get("person_name") or (name if party.get("is_person") else ctx.get("sender_name") or ""))
		values = {
			"first_name": first or (party.get("email") or ctx.get("sender_email")).split("@")[0],
			"last_name": last,
			"company_name": None if party.get("is_person") else name,
			"email_id": party.get("email") or ctx.get("sender_email"),
			"phone": party.get("phone"),
			"request_type": "Product Enquiry",
		}
		return [Action("Create", "Lead", values={k: v for k, v in values.items() if v}, key="party|lead", why=why)]
	if kind == "CV" and (party.get("email") or ctx.get("sender_email")) and not ctx.get("sender_is_colleague"):
		values = {
			"applicant_name": name or ctx.get("sender_name"),
			"email_id": party.get("email") or ctx.get("sender_email"),
			"phone_number": party.get("phone"),
			"source": ctx.get("applicant_source"),
		}
		if not values["applicant_name"]:
			return []
		return [Action("Create", "Job Applicant", values={k: v for k, v in values.items() if v}, key="party|applicant", why=why)]
	return []


# ------------------------------------------------------------------ pass 2: people


def contact(reading: dict, ctx: dict) -> list[Action]:
	"""The person who wrote, as a Contact: made once, only for real mail
	from outside, and a bare one Frappe made from an address completed
	rather than duplicated."""
	email = ctx.get("sender_email")
	if not real(reading, ctx) or ctx.get("direction") != "Received" or not email or ctx.get("sender_is_colleague"):
		return []
	first, last = _split(ctx.get("sender_name") or "")
	party = ctx.get("sender_party")
	links = [{"link_doctype": party[0], "link_name": party[1]}] if party and party[0] in ("Supplier", "Customer", "Lead", "Prospect") else []
	held = ctx.get("sender_contact")
	if not held:
		values = {"first_name": first or email.split("@")[0], "last_name": last, "email_ids": [{"email_id": email, "is_primary": 1}], "links": links}
		if ctx.get("sender_company"):
			values["company_name"] = ctx["sender_company"]
		return [Action("Create", "Contact", values={k: v for k, v in values.items() if v}, key="contact")]
	out = []
	if ctx.get("sender_contact_bare") and first:
		out.append(Action("Update", "Contact", held, {k: v for k, v in {"first_name": first, "last_name": last}.items() if v}, key="contact|name", over=("first_name",)))
	for link in links:
		if (link["link_doctype"], link["link_name"]) not in {tuple(one) for one in ctx.get("sender_contact_links") or []}:
			out.append(Action("Add", "Contact", held, {"table": "links", "row": link}, key=f"contact|link|{link['link_name']}"))
	return out


def employee_documents(reading: dict, ctx: dict) -> list[Action]:
	"""A person's own documents, on their Employee: an identity document as
	a row with a task before it runs out, a certificate as an education row,
	a sick note as a leave application, a resignation proposed."""
	employee = ctx.get("employee")
	kind = reading.get("kind") or ""
	if not real(reading, ctx) or not employee:
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
		out.append(Action("Add", "Employee", employee, {"table": "one_documents", "row": {k: v for k, v in row.items() if v}}, key=f"document|{number}", sure=True))
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
					flow="onedesk.one_intake.planning.make_task",
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
	elif kind == "Contract" and ctx.get("accepted_offer") and not ctx.get("employee_of_applicant"):
		out.append(Action("Create", "Employee", values={"job_offer": ctx["accepted_offer"]}, key="employee", flow="onedesk.one_intake.planning.employee_from_offer", propose=True))
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


# ------------------------------------------------------------------ tasks, events and promises


def tasks(reading: dict, ctx: dict) -> list[Action]:
	"""One task per matter. A new matter's asks become its steps; a later
	document nudges, moves or closes the task the matter already has."""
	if ctx.get("history") or reading.get("verdict") not in REAL:
		return []
	change = reading.get("change") or "New"
	held = ctx.get("task")
	if held:
		return _follow(reading, ctx, held, change)
	asks = [one for one in reading.get("asks") or [] if not one.get("promise")]
	if ctx.get("direction") == "Sent" or not asks or change in ("Nothing New", "Closing"):
		return []
	sensitive = reading.get("sensitivity") in PERSONAL
	steps = [{"step": _step(one, ctx), "done_when": ctx.get("done_when", {}).get(one.get("what"))} for one in asks]
	by = sorted(str(one["by_date"]) for one in asks if one.get("by_date"))
	about = ctx.get("about")
	subject = ctx["said"]["arrived_for"].format(ctx.get("about_title") or "") if sensitive else (reading.get("title") or ctx["said"]["arrived"])
	values = {
		"subject": subject[:140],
		"exp_end_date": by[0] if by else None,
		"description": None if sensitive else reading.get("summary"),
		"one_about_doctype": about[0] if about else None,
		"one_about": about[1] if about else None,
		"one_steps": [{k: v for k, v in one.items() if v} for one in steps],
		"assign_to": ctx.get("person"),
	}
	return [Action("Create", "Task", values={k: v for k, v in values.items() if v}, key="task", flow="onedesk.one_intake.planning.make_task", sure=True)]


def _step(ask: dict, ctx: dict) -> str:
	what = ctx["said"]["asks"].get(ask.get("what"), ask.get("what") or "")
	detail = (ask.get("detail") or "").strip()
	return f"{what}: {detail}"[:140] if detail else what


def _follow(reading: dict, ctx: dict, held: dict, change: str) -> list[Action]:
	"""What a later document does to the matter's task. A task a person
	closed is not reopened; they are told instead (planning does that)."""
	if held.get("status") in ("Completed", "Cancelled"):
		return []
	out: list[Action] = []
	if change == "Nudge":
		now = held.get("priority") or "Medium"
		higher = PRIORITY[min(PRIORITY.index(now) + 1, len(PRIORITY) - 1)] if now in PRIORITY else "High"
		values = {"priority": higher}
		new_by = sorted(str(one["by_date"]) for one in reading.get("asks") or [] if one.get("by_date"))
		if new_by and (not held.get("exp_end_date") or new_by[0] < str(held["exp_end_date"])[:10]):
			values["exp_end_date"] = new_by[0]
		out.append(Action("Update", "Task", held["name"], values, key=f"task|nudge|{reading.get('name')}", sure=True))
		out.append(Action("Comment", "Task", held["name"], {"comment_type": "Info", "content": ctx["said"]["nudged"].format(reading.get("title") or "")}, key=f"task|nudged|{reading.get('name')}", sure=True))
	elif change == "Update":
		new_by = sorted(str(one["by_date"]) for one in reading.get("asks") or [] if one.get("by_date"))
		if new_by and str(held.get("exp_end_date") or "")[:10] != new_by[0]:
			out.append(Action("Update", "Task", held["name"], {"exp_end_date": new_by[0]}, key=f"task|moved|{reading.get('name')}", sure=True))
	elif change == "Closing":
		out.append(Action("Update", "Task", held["name"], {"status": "Completed"}, key="task|closed", sure=True))
	return out


def event(reading: dict, ctx: dict) -> list[Action]:
	"""An appointment, on the calendar of whoever it is for."""
	if not real(reading, ctx) or reading.get("kind") != "Appointment":
		return []
	when = next((one for one in reading.get("dates") or [] if one.get("what") == "Appointment" and one.get("date")), None)
	if not when:
		return []
	values = {
		"subject": (reading.get("title") or ctx["said"]["appointment"])[:140],
		"starts_on": f"{when['date']} {ctx.get('time_of', {}).get(str(when['date'])) or '09:00:00'}",
		"all_day": 0 if ctx.get("time_of", {}).get(str(when["date"])) else 1,
		"event_type": "Private",
		"description": None if reading.get("sensitivity") in PERSONAL else reading.get("summary"),
		"for": ctx.get("person"),
	}
	return [Action("Create", "Event", values={k: v for k, v in values.items() if v is not None}, key="event", flow="onedesk.one_intake.planning.make_event", sure=True)]


def promises(reading: dict, ctx: dict) -> list[Action]:
	"""What our own mail promised, as a task for whoever wrote it."""
	if ctx.get("direction") != "Sent" or ctx.get("history") or not ctx.get("sender_user"):
		return []
	out = []
	for index, one in enumerate(one for one in reading.get("asks") or [] if one.get("promise")):
		values = {
			"subject": (one.get("detail") or "")[:140],
			"exp_end_date": str(one["by_date"]) if one.get("by_date") else None,
			"one_about_doctype": ctx["about"][0] if ctx.get("about") else None,
			"one_about": ctx["about"][1] if ctx.get("about") else None,
			"assign_to": ctx["sender_user"],
		}
		out.append(Action("Create", "Task", values={k: v for k, v in values.items() if v}, key=f"promise|{index}", flow="onedesk.one_intake.planning.make_task", sure=True))
	return out


def second(reading: dict, ctx: dict) -> list[Action]:
	"""Everything after the parties, in the order the door should take it."""
	return contact(reading, ctx) + employee_documents(reading, ctx) + receipt(reading, ctx) + tasks(reading, ctx) + event(reading, ctx) + promises(reading, ctx)
