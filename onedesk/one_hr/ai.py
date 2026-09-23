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

import calendar
from typing import Annotated

import frappe
from frappe import _lt
from frappe.utils import add_days, getdate, today

from onedesk.one_ai import proposals
from onedesk.one_hr import own

#: What the panel offers, by doctype, when it opens on one. `file` means the
#: chip asks for a file first and then says `ask` with it. `can` is the verb the
#: reader must hold on the doctype for the chip to be offered at all. `view`
#: keeps it to the list or the form, and `expects` names the tool the question
#: exists to call — asked for once more if the answer came without it.
SUGGESTIONS = {
	"Expense Claim": [
		{
			"label": _lt("What can I claim?"),
			"ask": _lt("What can I claim as an expense here, and who has to approve it?"),
			"can": "read",
			"view": "List",
		},
		{
			"label": _lt("Claim a receipt"),
			"ask": _lt("Make an expense claim from this receipt."),
			"file": True,
			"can": "create",
			"expects": "claim_expense",
		},
	],
	"Leave Application": [
		{
			"label": _lt("What is our leave policy?"),
			"ask": _lt("What does our leave policy say — how many days of each kind do I get, what carries "
			"forward, and which days are holidays?"),
			"can": "read",
			"view": "List",
		},
		{"label": _lt("Book time off"), "ask": _lt("Help me book time off."), "can": "create"},
		{
			"label": _lt("How much leave do I have?"),
			"ask": _lt("How much leave do I have left, and who on my team is off in the next two weeks?"),
			"can": "read",
		},
	],
	"Job Opening": [
		{
			"label": _lt("Rank the applicants again"),
			"run": "onedesk.one_hr.hiring.rank_again",
			"arg": "opening",
			"can": "write",
			"view": "Form",
			"said": _lt("Placing everybody again from what I wrote about each. The applicant list updates when I am done."),
		},
		{
			"label": _lt("Write this opening"),
			"ask": _lt("Write this opening's description, and what a strong applicant has as one short line "
			"each, from its designation, department and requisition. Suggest both as a change to it."),
			"can": "write",
			"view": "Form",
			"expects": "edit_record",
		},
		{
			"label": _lt("Add applicants from CVs"),
			"ask": _lt("Add an applicant to this opening from each of these CVs."),
			"file": True,
			"doctype": "Job Applicant",
			"can": "create",
			"view": "Form",
			"expects": "add_applicant",
		},
		{
			"label": _lt("Add applicants from CVs"),
			"ask": _lt("Add an applicant from each of these CVs, to the open job each one fits best."),
			"file": True,
			"doctype": "Job Applicant",
			"can": "create",
			"view": "List",
		},
	],
	"Job Applicant": [
		{
			"label": _lt("Screen again"),
			"run": "onedesk.one_hr.hiring.screen_again",
			"arg": "applicant",
			"can": "write",
			"view": "Form",
			"said": _lt("Reading the CV again. The rating, the standing and a comment land on this applicant when I am done."),
		},
		{
			"label": _lt("Write a kind decline"),
			"ask": _lt("Write a short, kind note telling this applicant they were not chosen, that thanks them "
			"for something specific in their application. Do not give reasons."),
			"can": "read",
			"view": "Form",
		},
		{
			"label": _lt("What should I ask first?"),
			"ask": _lt("From this applicant's CV and OneAI's screening of it, what should I confirm on a first "
			"call, and what would a short email asking for the missing pieces say?"),
			"can": "read",
			"view": "Form",
		},
		{
			"label": _lt("Add applicants from CVs"),
			"ask": _lt("Add an applicant from each of these CVs, to the open job each one fits best."),
			"file": True,
			"can": "create",
		},
	],
	"Job Requisition": [
		{
			"label": _lt("Draft the opening"),
			"ask": _lt("Draft a job opening from this requisition — its title, description and what a strong "
			"applicant has, one short line each — and suggest creating it."),
			"doctype": "Job Opening",
			"can": "create",
			"view": "Form",
			"expects": "create_record",
		},
	],
	"Appraisal": [
		{
			"label": _lt("What training would help?"),
			"ask": _lt("From this appraisal, where is this person weakest, and which of our training programs "
			"or coming events would help? If none fits, say what to look for."),
			"can": "read",
			"view": "Form",
		},
		{
			"label": _lt("Draft my feedback"),
			"ask": _lt("Draft my feedback on this appraisal from what happened in the cycle, "
			"and suggest it as my feedback."),
			"doctype": "Employee Performance Feedback",
			"can": "create",
			"view": "Form",
			"expects": "draft_feedback",
		},
	],
	"Interview": [
		{
			"label": _lt("Prepare this interview again"),
			"run": "onedesk.one_hr.hiring.prepare_again",
			"arg": "interview",
			"can": "write",
			"view": "Form",
			"said": _lt("Preparing it again. Before You Start updates on the interview when I am done."),
		},
		{
			"label": _lt("Draft my feedback from the recording"),
			"ask": _lt("Draft my feedback on this interview from its recording and OneAI's remarks, "
			"with a rating for each expected skill, and suggest it as my feedback."),
			"doctype": "Interview Feedback",
			"can": "create",
			"view": "Form",
			"expects": "draft_interview_feedback",
		},
	],
	"Job Offer": [
		{
			"label": _lt("Write the offer terms"),
			"ask": _lt("Write this offer's terms from the opening it is for — the role, the salary range and "
			"the start — and suggest them as a change to it."),
			"can": "write",
			"view": "Form",
			"expects": "edit_record",
		},
	],
	"Employee Onboarding": [
		{
			"label": _lt("Plan the first two weeks"),
			"ask": _lt("From this person's designation and department, what should their first two weeks "
			"hold, day by day, and who should own each part?"),
			"can": "read",
			"view": "Form",
		},
	],
	"Interview Recording": [
		{
			"label": _lt("Transcribe again"),
			"run": "onedesk.one_hr.hiring.transcribe_again",
			"arg": "recording",
			"can": "write",
			"view": "Form",
			"said": _lt("Writing it down again. The transcript and my remarks follow when I am done."),
		},
	],
	"Payroll Entry": [
		{
			"label": _lt("Check this payroll"),
			"ask": _lt("Check this payroll against last month and tell me what looks unusual, most money first."),
			"can": "read",
			"view": "Form",
		},
	],
	"Salary Slip": [
		{
			"label": _lt("What changed since last month?"),
			"ask": _lt("Compare this salary slip with this person's last one and tell me what changed."),
			"can": "read",
			"view": "Form",
		},
	],
	"Employee Letter": [
		{
			"label": _lt("Ask HR for a letter"),
			"ask": _lt("I need a letter from HR — a salary certificate, an experience letter or an employment "
			"letter. Ask me which one and who it is for, then draft it."),
			"view": "List",
			"can": "create",
		},
	],
	"Employee": [
		{
			"label": _lt("Write a letter for this person"),
			"ask": _lt("Write a letter about this employee — ask me which kind and who it is for, then draft it."),
			"doctype": "Employee Letter",
			"can": "submit",
			"view": "Form",
			"expects": "request_letter",
		},
	],
	"Goal": [
		{
			"label": _lt("Draft my goals for this cycle"),
			"ask": _lt("Draft my goals for this appraisal cycle from my role, last cycle's goals and the feedback "
			"I was given, and suggest them."),
			"can": "create",
			"view": "List",
			"expects": "draft_goal",
		},
	],
	"Exit Interview": [
		{
			"label": _lt("Why are people leaving?"),
			"ask": _lt("Why have people left over the last twelve months, and how many said each reason?"),
			"can": "read",
			"view": "List",
		},
	],
	"Employee Separation": [
		{
			"label": _lt("Why are people leaving?"),
			"ask": _lt("Why have people left over the last twelve months, and how many said each reason?"),
			"doctype": "Exit Interview",
			"can": "read",
			"view": "List",
		},
	],
	# OneHR's home is where an employee starts their day, so the three things
	# they come to it for are offered there too.
	"workspace:OneHR": [
		{
			"label": _lt("Ask HR for a letter"),
			"ask": _lt("I need a letter from HR — a salary certificate, an experience letter or an employment "
			"letter. Ask me which one and who it is for, then draft it."),
			"doctype": "Employee Letter",
			"can": "create",
		},
		{"label": _lt("Book time off"), "ask": _lt("Help me book time off."), "doctype": "Leave Application", "can": "create"},
		{
			"label": _lt("Claim a receipt"),
			"ask": _lt("Make an expense claim from this receipt."),
			"doctype": "Expense Claim",
			"file": True,
			"can": "create",
		},
		{
			"label": _lt("How much leave do I have?"),
			"ask": _lt("How much leave do I have left, and who on my team is off in the next two weeks?"),
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


def add_applicant(
	applicant_name: Annotated[str, "The person's full name, as on the CV."],
	email_id: Annotated[str, "Their email address, as on the CV."],
	job_opening: Annotated[str, "The job opening they are applying to: its id, or its title."],
	fit: Annotated[
		str,
		"One line for the hiring manager on how the CV meets what the opening asks for — "
		"what matches and what is missing, under 140 characters. A CV for different work "
		"says so plainly. Never a score or a verdict.",
	],
	phone_number: Annotated[str, "Their phone number, if the CV has one."] | None = None,
	cv_file: Annotated[str, "The file name of the CV this applicant is from."] | None = None,
) -> dict:
	"""Suggest a job applicant from one CV. Call it once per CV. Read the job
	opening first, so the fit line is against what it actually asks for.

	Nothing is added until somebody approves the card; the CV goes on the
	applicant when they do.
	"""
	email = (email_id or "").strip().lower()
	if not frappe.utils.validate_email_address(email):
		return {"error": f"{email_id!r} is not an email address. Read it off the CV again, or ask."}
	opening = _opening(job_opening)
	if not opening:
		there = frappe.get_list("Job Opening", filters={"status": "Open"}, fields=["name", "job_title"])
		return {
			"error": f"There is no job opening called {job_opening!r}. Open ones: "
			+ ", ".join(f"{one.name} ({one.job_title})" for one in there)
		}
	already = frappe.db.get_value("Job Applicant", {"email_id": email}, ["name", "job_title"], as_dict=True)
	if already:
		return {
			"error": f"{applicant_name} ({email}) is already an applicant, for {already.job_title}. "
			"Say so rather than adding them twice."
		}

	cv = _cv(cv_file, applicant_name)
	# Status is Open by default and the designation is fetched from the
	# opening, so neither is the model's to say — and neither crowds the card.
	values = {
		"applicant_name": (applicant_name or "").strip(),
		"email_id": email,
		"job_title": opening,
		# A line for the person deciding, in the field HRMS gives notes. Never
		# the rating: a number a model gave is a number someone will sort by.
		"notes": _short(fit, NOTE),
	}
	if phone_number:
		values["phone_number"] = phone_number.strip()
	if cv:
		values["resume_attachment"] = cv
	name = proposals.propose(
		"Create",
		"Job Applicant",
		changes={key: value for key, value in values.items() if value},
		files=[cv] if cv else [],
	)
	return {"proposal": name, "state": "Proposed"}


# ------------------------------------------------------------- appraisal


def appraisal_facts(
	appraisal: Annotated[str, "The appraisal's id."],
) -> dict:
	"""What happened in one appraisal's cycle, for writing feedback on it: the
	employee's goals and how far they got, the KRAs they are appraised on,
	their own reflection, feedback already given, and their attendance and
	leave in the period. Read it before drafting feedback, then give the
	draft to draft_feedback rather than writing it in the answer."""
	doc = frappe.get_doc("Appraisal", appraisal)
	doc.check_permission("read")
	start, end = doc.start_date, doc.end_date
	employee = doc.employee

	goals = frappe.get_list(
		"Goal",
		filters={"employee": employee, "is_group": 0},
		or_filters=[["appraisal_cycle", "=", doc.appraisal_cycle], ["end_date", ">=", start], ["end_date", "is", "not set"]],
		fields=["goal_name", "kra", "progress", "status"],
		limit_page_length=30,
	)
	given = frappe.get_list(
		"Employee Performance Feedback",
		filters={"appraisal": appraisal, "docstatus": ["<", 2]},
		fields=["reviewer_name", "feedback", "total_score"],
		limit_page_length=10,
	)
	attendance = frappe.get_list(
		"Attendance",
		filters={"employee": employee, "attendance_date": ["between", [start, end]], "docstatus": 1},
		fields=["status", {"COUNT": "*", "as": "days"}],
		group_by="status",
	)
	late = frappe.get_list(
		"Attendance",
		filters={"employee": employee, "attendance_date": ["between", [start, end]], "docstatus": 1, "late_entry": 1},
		fields=[{"COUNT": "*", "as": "days"}],
	)
	leave = frappe.get_list(
		"Leave Application",
		filters={"employee": employee, "status": "Approved", "from_date": ["<=", end], "to_date": [">=", start]},
		fields=["leave_type", {"SUM": "total_leave_days", "as": "days"}],
		group_by="leave_type",
	)
	return {
		"employee": doc.employee_name,
		"designation": doc.designation,
		"cycle": doc.appraisal_cycle,
		"period": {"from": str(start), "to": str(end)},
		"kras": [{"kra": k.kra, "weight": k.per_weightage} for k in doc.appraisal_kra],
		"goals": [
			{"goal": g.goal_name, "kra": g.kra, "progress": f"{g.progress or 0:g}%", "status": g.status}
			for g in goals
		],
		"their_reflection": _plain_text(doc.reflections),
		"feedback_given": [
			{"by": f.reviewer_name, "said": _plain_text(f.feedback)} for f in given if f.feedback
		],
		"attendance": {a.status: a.days for a in attendance},
		"late_arrivals": (late[0].days if late else 0) or 0,
		"leave_taken": {one.leave_type: one.days for one in leave},
		# Said with the facts, because a small model handed them asked the
		# reviewer for the goals and the reflection it had just been given.
		"next": "Write the feedback from these facts alone; leave out whatever is empty here. "
		"Then call draft_feedback with it. Do not ask for anything above.",
	}


def draft_feedback(
	appraisal: Annotated[str, "The appraisal's id."],
	feedback: Annotated[
		str,
		"The feedback, as the reviewer would write it to the employee: what went well and what "
		"to work on, each tied to something that happened. A few short paragraphs. No scores.",
	],
) -> dict:
	"""Suggest the reader's own feedback on an appraisal, from what
	appraisal_facts found. It is a draft for them to edit and rate; nothing is
	saved until they approve the card, and the ratings stay theirs to give."""
	doc = frappe.get_doc("Appraisal", appraisal)
	doc.check_permission("read")
	reviewer = own.employee_of()
	if not reviewer:
		return {"error": "The person asking has no employee record here, so there is no reviewer to write as."}
	if reviewer == doc.employee:
		return {"error": "This is the reader's own appraisal. Their words go in its reflections, not in feedback."}

	text = "".join(f"<p>{frappe.utils.escape_html(one.strip())}</p>" for one in (feedback or "").split("\n") if one.strip())
	mine = frappe.db.get_value(
		"Employee Performance Feedback",
		{"appraisal": appraisal, "reviewer": reviewer, "docstatus": 0},
		"name",
	)
	if mine:
		# Their draft already exists: the words go into it, the ratings they
		# gave stay as they are.
		name = proposals.propose("Edit", "Employee Performance Feedback", record=mine, changes={"feedback": text})
	else:
		name = proposals.propose(
			"Create",
			"Employee Performance Feedback",
			changes={
				"employee": doc.employee,
				"reviewer": reviewer,
				"appraisal": appraisal,
				"appraisal_cycle": doc.appraisal_cycle,
				"feedback": text,
			},
		)
	return {"proposal": name, "state": "Proposed"}


# ------------------------------------------------------------- interview


def interview_facts(
	interview: Annotated[str, "The interview's id."],
) -> dict:
	"""What one interview found, for writing the reader's feedback on it: the
	expected skills, what OneAI prepared, the transcript of its recording and
	OneAI's remarks on it. Read it before drafting feedback, then give the
	draft to draft_interview_feedback rather than writing it in the answer."""
	from onedesk.one_hr import hiring

	doc = frappe.get_doc("Interview", interview)
	doc.check_permission("read")
	skills = frappe.get_all(
		"Expected Skill Set",
		filters={"parent": doc.interview_type, "parenttype": "Interview Type"},
		pluck="skill",
		order_by="idx",
	) if doc.interview_type else []
	recording = frappe.get_list(
		"Interview Recording",
		filters={"interview": interview, "status": "Transcribed"},
		fields=["transcript"],
		order_by="creation desc",
		limit_page_length=1,
	)
	remarks = frappe.get_all(
		"Comment",
		filters={"reference_doctype": "Interview", "reference_name": interview, "owner": hiring.AUTHOR},
		pluck="content",
		order_by="creation desc",
		limit=1,
	)
	return {
		"applicant": doc.get("one_applicant") or doc.job_applicant,
		"round": doc.interview_type,
		"expected_skills": skills,
		"prepared": _plain_text(doc.get("one_ai_prep")),
		"transcript": (recording[0].transcript or "")[: hiring.MOST_TRANSCRIPT] if recording else "",
		"oneai_remarks": _plain_text(remarks[0]) if remarks else "",
		"next": "Write the feedback from these facts alone, rate each expected skill from what was said, "
		"then call draft_interview_feedback. If there is no transcript and no remarks, say so instead.",
	}


def draft_interview_feedback(
	interview: Annotated[str, "The interview's id."],
	feedback: Annotated[
		str,
		"The feedback as the interviewer would write it: what the candidate showed and what they did "
		"not, each tied to something they said. A few short paragraphs.",
	],
	ratings: Annotated[dict, "Each expected skill, to a rating from 1 to 5 for what was said about it."],
	result: Annotated[str, "Cleared or Rejected, if the interviewer said which; otherwise leave it out."] | None = None,
) -> dict:
	"""Suggest the reader's own feedback on an interview, from what
	interview_facts found. It is a draft for them to change and submit;
	nothing is saved until they approve the card."""
	doc = frappe.get_doc("Interview", interview)
	doc.check_permission("read")
	me = frappe.session.user
	on_it = frappe.get_all("Interview Detail", filters={"parent": interview}, pluck="interviewer")
	if me not in on_it:
		return {"error": "The person asking is not one of this interview's interviewers, so there is no feedback of theirs to draft."}
	if frappe.db.exists("Interview Feedback", {"interview": interview, "interviewer": me, "docstatus": ["<", 2]}):
		return {"error": "The person asking has already given feedback on this interview. Say so rather than drafting another."}

	expected = frappe.get_all(
		"Expected Skill Set",
		filters={"parent": doc.interview_type, "parenttype": "Interview Type"},
		pluck="skill",
		order_by="idx",
	) if doc.interview_type else []
	given = {str(key).strip().lower(): value for key, value in (ratings or {}).items()}
	rows = []
	for skill in expected:
		try:
			stars = max(0.0, min(5.0, float(given.get(skill.lower()))))
		except (TypeError, ValueError):
			stars = 0.0
		rows.append({"skill": skill, "rating": round(stars / 5, 2)})

	values = {
		"interview": interview,
		"interviewer": me,
		"interview_type": doc.interview_type,
		"job_applicant": doc.job_applicant,
		"skill_assessment": rows,
		"feedback": _short(feedback, 4000),
	}
	if result in ("Cleared", "Rejected"):
		values["result"] = result
	name = proposals.propose("Create", "Interview Feedback", changes=values)
	return {"proposal": name, "state": "Proposed"}


def _plain_text(html) -> str:
	return " ".join(frappe.utils.strip_html_tags(str(html or "")).split())


# --------------------------------------------------------------- leaving


def why_people_leave(
	from_date: Annotated[str, "The first day of the period, as YYYY-MM-DD. A year ago if not said."] | None = None,
	to_date: Annotated[str, "The last day, as YYYY-MM-DD. Today if not said."] | None = None,
) -> dict:
	"""What people said when they left, over a period: every completed exit
	interview and every leaver's recorded reason, with their department and
	role. Read it to answer why people leave — then group what they said into
	the few reasons behind it, with how many people gave each."""
	end = getdate(to_date) if to_date else getdate(today())
	start = getdate(from_date) if from_date else add_days(end, -365)

	interviews = frappe.get_list(
		"Exit Interview",
		filters={"status": "Completed", "docstatus": ["<", 2], "date": ["between", [start, end]]},
		fields=["employee", "employee_name", "department", "designation", "date", "interview_summary"],
		order_by="date asc",
		limit_page_length=MOST_LEAVERS,
	)
	heard = {one.employee for one in interviews}
	# Somebody who left with a reason written on their record but no interview
	# still said something; somebody interviewed is counted once.
	leavers = frappe.get_list(
		"Employee",
		filters={"relieving_date": ["between", [start, end]], "reason_for_leaving": ["is", "set"]},
		fields=["name", "employee_name", "department", "designation", "relieving_date", "reason_for_leaving"],
		limit_page_length=MOST_LEAVERS,
	)
	said = [
		{
			"who": one.employee_name,
			"department": one.department,
			"role": one.designation,
			"when": str(one.date),
			"said": _plain_text(one.interview_summary),
		}
		for one in interviews
		if _plain_text(one.interview_summary)
	] + [
		{
			"who": one.employee_name,
			"department": one.department,
			"role": one.designation,
			"when": str(one.relieving_date),
			"said": one.reason_for_leaving,
		}
		for one in leavers
		if one.name not in heard
	]
	return {
		"period": {"from": str(start), "to": str(end)},
		"people": len(said),
		"what_they_said": said,
		"next": "Answer as a short list, one line per reason, most common first, each line: the reason, "
		"how many people gave it, and a few of their own words in quotes. Keep separate reasons "
		"separate (pay is not progression). One person can give more than one reason. Say plainly "
		"if there are too few to call anything a pattern.",
	}


#: The most leavers read for one answer.
MOST_LEAVERS = 200


#: What HRMS's notes field holds.
NOTE = 140


def _short(text: str | None, most: int) -> str:
	"""At most `most` characters, cut at a word rather than through one."""
	said = " ".join((text or "").split())
	if len(said) <= most:
		return said
	return said[: most - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def _opening(said: str | None) -> str | None:
	"""The job opening meant: by id, or the one whose title is or holds `said`."""
	said = (said or "").strip()
	if not said:
		return None
	if frappe.db.exists("Job Opening", said):
		return said
	openings = frappe.get_list("Job Opening", fields=["name", "job_title"], limit_page_length=200)
	low = said.lower()
	for test in (lambda t: t == low, lambda t: low in t):
		found = [one.name for one in openings if test((one.job_title or "").lower())]
		if len(found) == 1:
			return found[0]
	return None


def _cv(named: str | None, person: str | None = None) -> str | None:
	"""The uploaded file this applicant came from.

	The model names the file as it pictures it — "Layla Nasser CV.pdf" for
	layla-nasser-cv.pdf — so it is matched as a person would: the name given,
	then the file whose name holds the applicant's, then the closest name,
	and the only file when there is one.
	"""
	import difflib

	files = frappe.flags.get("one_ai_files") or []
	if len(files) == 1:
		return files[0]

	def plain(text: str) -> str:
		return "".join(ch for ch in (text or "").lower() if ch.isalnum())

	stems = {url: plain(url.rsplit("/", 1)[-1].rsplit(".", 1)[0]) for url in files}
	for said in (named, person):
		want = plain((said or "").rsplit(".", 1)[0])
		if not want:
			continue
		held = [url for url, stem in stems.items() if want in stem or stem in want]
		if len(held) == 1:
			return held[0]
	words = [plain(one) for one in (person or "").split() if len(one) > 1]
	held = [url for url, stem in stems.items() if words and all(word in stem for word in words)]
	if len(held) == 1:
		return held[0]
	near = difflib.get_close_matches(plain(named or person or ""), list(stems.values()), n=1, cutoff=0.5)
	return next((url for url, stem in stems.items() if near and stem == near[0]), None)


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


def reader() -> str:
	"""The reader's own employee record, for the `one_ai_reader` hook."""
	employee = own.employee_of()
	if not employee:
		return ""
	return (
		f"Their employee record is {employee}; their own records of any HR type are the ones "
		"whose employee field is that."
	)


def workspace() -> str:
	"""The weekly offs, for the `one_ai_workspace` hook: read off this year's
	default holiday list, because "Friday" costing a day or not is the first
	thing a question about leave turns on."""
	company = frappe.defaults.get_global_default("company")
	listed = company and frappe.db.get_value("Company", company, "default_holiday_list")
	if not listed:
		return ""
	offs = frappe.get_all(
		"Holiday", filters={"parent": listed, "weekly_off": 1}, pluck="holiday_date", limit_page_length=14
	)
	days = sorted({getdate(one).weekday() for one in offs})
	if not days:
		return ""
	names = [calendar.day_name[one] for one in days]
	return f"The weekly days off are {' and '.join(names)}."


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
		if days == 1:
			why = frappe._("1 day of {0}.").format(frappe._(kind))
		else:
			why = frappe._("{0} days of {1}.").format(f"{days:g}", frappe._(kind))
	elif days == 1:
		why = frappe._("1 day of {0}; {1} left after.").format(frappe._(kind), f"{left - days:g}")
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
