"""What OneHR's pages say above their fields. See one/head.py.

A person's page, first. Where they are right now as the title's pill; a quarter of attendance as a
heat map of named days; and beside it the handful of numbers somebody opens
the record to read: their standing, their last check-in, what leave is left
of each type, what is waiting on an approver, what they hold and what they
are paid under. The figures are employee.py's `overview`, worked out once per
request with the reader's own permissions.

Then the requests and the documents. A request somebody answers (leave, an
attendance correction, a shift, an expense claim) carries Approve and Reject,
each asking for a note and saying what it will do; and every one of these
records opens on a sentence saying what it comes to, which the fields it
opens on do not: how many days of what, what a slip pays, how far a vehicle
went on how much. A sentence that reads a field the form can change redraws
as it changes (`redraw_on`), so it is right before the record is saved.
"""

import re
from urllib.parse import quote

import frappe
from frappe import _, _lt
from frappe.utils import escape_html, flt, fmt_money, formatdate
from frappe.utils.caching import request_cache

from onedesk.one_hr import employee, encashment, expense, payroll, request, review, setup, shift
from onedesk.one_hr import leave as applications

#: What a standing is worth saying about it, by its band. Only low and watch
#: get a colour: a number that is fine is a number nobody has to look at.
STANDING_TONE = {"low": "alarm", "watch": "waiting", "good": None}


@request_cache
def _said(name: str) -> dict:
	return employee.overview(name)


def _number(value) -> str:
	"""A count as a person writes it: 21, not 21.0; 7.5 stays 7.5."""
	value = float(value or 0)
	return str(int(value)) if value.is_integer() else str(value)


def _slug(doctype: str) -> str:
	return doctype.lower().replace(" ", "-")


def state(doc):
	"""Where this person is right now, as a word and a colour."""
	if doc.is_new():
		return None
	return _said(doc.name)["state"]


def standing(doc):
	"""First, beside the quarter it is worked out from: the one number about
	whether the check-ins themselves can be believed."""
	found = _said(doc.name)["standing"]
	if not found:
		return None
	return {
		"value": found["score"],
		"route": f"/desk/clock-attempt?employee={quote(doc.name, safe='')}",
		"tone": STANDING_TONE.get(found["band"]),
	}


def checked(doc):
	"""The last check-in, said the way the clock says it ("5 d")."""
	found = _said(doc.name)["today"]["checkin"]
	if not found:
		return None
	return {
		"label": _("Out") if found.log_type == "OUT" else _("In"),
		"value": "{when}",
		"when": str(found.time),
		"short": 1,
		"route": f"/desk/employee-checkin/{quote(found.name, safe='')}",
	}


def leave(doc):
	"""What is left of each leave type they hold, against the year's
	allocation: one number each."""
	return [
		{
			"label": re.sub(r" Leave$", "", row["type"]),
			"value": _("{0} left").format(_number(row["left"])),
			"route": f"/desk/leave-application?employee={quote(doc.name, safe='')}",
			"tone": None if (row["left"] or 0) > 0 else "quiet",
			"meter": {"value": row["left"], "of": row["allocated"]} if row["allocated"] else None,
		}
		for row in _said(doc.name)["leave"]
	]


def awaiting(doc):
	"""What is waiting on an approver, one number a kind."""
	return [
		{
			"label": _(kind),
			"value": _("{0} awaiting").format(row["count"]),
			"route": f"/desk/{_slug(kind)}?employee={quote(doc.name, safe='')}",
			"tone": "waiting",
		}
		for row in _said(doc.name)["awaiting"]
		if (kind := row["doctype"])
	]


def equipment(doc):
	"""What of the company's they hold, only when they hold something. See
	one_inventory/custody.py."""
	held = _said(doc.name)["equipment"]
	if not held:
		return None
	return {"value": _("{0} held").format(held), "route": f"/desk/asset?custodian={quote(doc.name, safe='')}"}


def pay(doc):
	found = _said(doc.name)["pay"]
	if not found or not found.get("salary_structure"):
		return None
	return {
		"value": found["salary_structure"],
		"route": f"/desk/salary-structure-assignment/{quote(found['name'], safe='')}",
	}


def quarter(doc):
	"""A quarter of attendance, a square a day: frappe-charts' heat map
	geometry, with colours that mean a state rather than an amount."""
	days = _said(doc.name)["days"]
	return {"kind": "heat", "days": days} if days else None


CHARTS = {
	"employee.quarter": {"doctypes": ["Employee"], "label": _lt("Attendance"), "figures": quarter},
}

# ------------------------------------------------------------------ answering a request


def _may_answer(doc) -> bool:
	return (
		not doc.is_new()
		and doc.docstatus == 0
		and bool(frappe.has_permission(doc.doctype, "submit", doc=doc))
	)


def _asks(what: str):
	"""What the verb will do, then the note the person who asked will see."""

	def fields(doc):
		return [
			{
				"fieldtype": "HTML",
				"fieldname": "what",
				"options": f'<p class="text-muted">{escape_html(str(what))}</p>',
			},
			{
				"fieldtype": "Small Text",
				"fieldname": "note",
				"label": _("Note"),
				"description": _("Optional. The person who asked will see it."),
			},
		]

	return fields


def _approves(module):
	"""Approve, as the doctype's own module does it."""
	return lambda doc, note=None, **_values: module.approve(doc.name, note or "")


def _rejects(module):
	return lambda doc, note=None, **_values: module.reject(doc.name, note or "")


def _approve(doc) -> str:
	return _("Approve")


def _reject(doc) -> str:
	return _("Reject")


# ------------------------------------------------------------------ sentences


def _on(date) -> str:
	return formatdate(str(date)) if date else ""


def _money(value, currency=None) -> str:
	return fmt_money(flt(value), currency=currency or frappe.db.get_default("currency"))


def _period(start, end) -> str:
	return f"{_on(start)} – {_on(end)}"


def _name(doc) -> str:
	"""`employee_name` is fetched from the Employee, and is not there yet on a
	form that has only just been given one."""
	if doc.get("employee_name"):
		return doc.employee_name
	return frappe.db.get_value("Employee", doc.employee, "employee_name") or doc.employee


def leave_about(doc):
	"""How many days of what, for whom, and what it leaves them with: the
	table above the form reads Available Leaves beside Pending Approval, and
	the pending number is this one."""
	if doc.is_new() or doc.docstatus != 0 or not flt(doc.total_leave_days):
		return None
	days = flt(doc.total_leave_days)
	after = max(applications._balance(doc) - days, 0)
	when = (
		_on(doc.from_date)
		if str(doc.from_date) == str(doc.to_date)
		else _("{0} to {1}").format(_on(doc.from_date), _on(doc.to_date))
	)
	return {
		"text": _("Approving this books {0} days of {1} for {2}, {3}, leaving them {4}.").format(
			_number(days), doc.leave_type, doc.employee_name or doc.employee, when, _number(after)
		),
		"colour": "blue",
	}


def request_turned_down(doc):
	if doc.get("one_decision") != request.REJECTED:
		return None
	return {"text": _("Turned down by {0}.").format(doc.get("one_decided_by") or ""), "colour": "red"}


def shift_about(doc):
	"""Who may approve it, and what approving puts them on. An employee with
	no approver leaves HRMS's mandatory Approver picker empty, which reads as
	a broken field rather than as missing setup."""
	if doc.docstatus != 0 or not doc.employee:
		return None
	if not shift.approvers(doc.employee):
		return {
			"text": _(
				"Nobody can approve a shift request for {0}. Set a Shift Request Approver on their Employee record first."
			).format(_name(doc)),
			"colour": "red",
		}
	if not doc.shift_type or not doc.from_date:
		return None
	hours = doc.get("one_when") or shift.hours(doc.shift_type)
	named = f"{doc.shift_type} ({hours})" if hours else doc.shift_type
	when = (
		_("from {0} to {1}").format(_on(doc.from_date), _on(doc.to_date))
		if doc.to_date
		else _("from {0}, with no end date").format(_on(doc.from_date))
	)
	return {
		"text": _("Approving this puts {0} on {1} {2}.").format(_name(doc), named, when),
		"colour": "blue",
	}


def expense_about(doc):
	"""What approving pays back, after any advance, and whether less was
	sanctioned than claimed."""
	if doc.is_new() or doc.docstatus != 0:
		return None
	said = expense.about(doc.name)
	money = lambda value: _money(value, said["currency"])  # noqa: E731
	lines = [
		_("Approving this pays {0} back {1}, across {2} expenses.").format(
			said["employee_name"], money(said["payable"]), said["rows"]
		)
		if said["rows"] > 1
		else _("Approving this pays {0} back {1}.").format(said["employee_name"], money(said["payable"]))
	]
	if said["advance"]:
		lines.append(_("{0} of it is already covered by an advance.").format(money(said["advance"])))
	if said["sanctioned"] != said["claimed"]:
		lines.append(
			_("They claimed {0} and {1} was sanctioned.").format(
				money(said["claimed"]), money(said["sanctioned"])
			)
		)
	return {"text": " ".join(lines), "colour": "blue"}


def slip_pays(doc):
	"""What the slip pays, on the tab it opens on, and where the number came
	from when the month was not a whole month."""
	if doc.is_new() or not flt(doc.net_pay):
		return None
	paid = _money(doc.rounded_total or doc.net_pay, doc.currency)
	month = _period(doc.start_date, doc.end_date)
	whole = flt(doc.payment_days) >= flt(doc.total_working_days)
	return {
		"text": _("{0} for {1}, a whole month.").format(paid, month)
		if whole
		else _("{0} for {1}: {2} of {3} days paid.").format(
			paid, month, _number(flt(doc.payment_days, 2)), _number(flt(doc.total_working_days, 2))
		),
		"colour": "green" if doc.docstatus == 1 else "blue",
	}


def payroll_run(doc):
	"""How many people and how much: counted off the slips, which the Overview
	tab has neither of."""
	if doc.is_new():
		return None
	run = payroll.run(doc.name)
	if not run["people"]:
		return {
			"text": _("No salary slips yet for {0} to {1}.").format(_on(doc.start_date), _on(doc.end_date)),
			"colour": "orange",
		}
	money = _money(run["total"], run["currency"] or doc.currency)
	period = _period(doc.start_date, doc.end_date)
	if run["drafts"]:
		return {
			"text": _("{0}: {1} people, {2}, in {3} slips still in draft.").format(
				period, run["people"], money, run["drafts"]
			),
			"colour": "blue",
		}
	return {
		"text": _("{0}: {1} people, {2}, all submitted.").format(period, run["people"], money),
		"colour": "green",
	}


def appraisal_stands(doc):
	"""Where the score stands and which of its three parts is missing: a Final
	Score of 0 reads like a verdict and means nothing has been rated yet."""
	if doc.is_new():
		return None
	missing = [
		said
		for value, said in (
			(doc.goal_score_percentage, _("goals")),
			(doc.avg_feedback_score, _("feedback")),
			(doc.self_score, _("the self appraisal")),
		)
		if not flt(value)
	]
	period = (
		_("{0} to {1}").format(_on(doc.start_date), _on(doc.end_date))
		if doc.start_date and doc.end_date
		else doc.appraisal_cycle
	)
	if len(missing) == 3:
		return {
			"text": _("{0}, {1}. Nothing has been rated yet, so the score is not a verdict.").format(
				doc.employee_name, period
			),
			"colour": "orange",
		}
	score = _("{0} out of 5").format(_number(flt(doc.final_score, 2)))
	if missing:
		return {
			"text": _("{0}, {1} — {2}, still waiting on {3}.").format(
				doc.employee_name, period, score, ", ".join(missing)
			),
			"colour": "orange",
		}
	return {"text": _("{0}, {1} — {2}.").format(doc.employee_name, period, score), "colour": "green"}


def encashment_pays(doc):
	"""What submitting pays, or why it is nought: the rate is a field on the
	salary structure that nothing fills and nothing asks for (encashment.py)."""
	if doc.docstatus != 0 or not doc.employee or not doc.encashment_date:
		return None
	if flt(doc.encashment_amount) > 0:
		return {
			"text": _("Submitting this pays {0} {1} for {2} days of {3}.").format(
				doc.employee_name or doc.employee,
				_money(doc.encashment_amount, doc.currency),
				_number(flt(doc.encashment_days, 2)),
				doc.leave_type,
			),
			"colour": "blue",
		}
	structure = encashment.rate(doc.employee, str(doc.encashment_date))["structure"]
	return {
		"text": _(
			"Nothing to pay yet: {0} has no Leave Encashment Amount Per Day, so a day is worth nought. Set it on the salary structure or on this person's assignment."
		).format(structure)
		if structure
		else _("Nothing to pay yet: this person has no salary structure on {0}.").format(
			_on(doc.encashment_date)
		),
		"colour": "orange",
	}


def vehicle_went(doc):
	"""How far, on how much: the record carries both odometer readings and
	not the distance between them, and the litres behind a collapsed section."""
	went = flt(doc.odometer) - flt(doc.last_odometer)
	if doc.is_new() or went <= 0:
		return None
	litres = flt(doc.fuel_qty)
	far = fmt_money(went, precision=0)
	if litres <= 0:
		return {"text": _("{0} on the odometer since the last log.").format(far), "colour": "blue"}
	# Fuel is kept in whatever the vehicle is kept in.
	unit = frappe.db.get_value("Vehicle", doc.license_plate, "uom") or _("units")
	return {
		"text": _("{0} on the odometer since the last log, on {1} {2} costing {3} — {4} per {2}.").format(
			far,
			fmt_money(litres, precision=2),
			unit,
			_money(litres * flt(doc.price)),
			_number(flt(went / litres, 1)),
		),
		"colour": "blue",
	}


#: Where each exemption doctype keeps what was claimed and what is allowed.
EXEMPTION = {
	"Employee Tax Exemption Declaration": ("total_declared_amount", "total_exemption_amount"),
	"Employee Tax Exemption Proof Submission": ("total_actual_amount", "exemption_amount"),
}


def exemption_allowed(doc):
	"""The total, and whether all of it is allowed: a category has a limit, so
	a person can declare thirty and be allowed twenty."""
	claimed_field, allowed_field = EXEMPTION[doc.doctype]
	claimed, allowed = flt(doc.get(claimed_field)), flt(doc.get(allowed_field))
	if doc.is_new() or not claimed:
		return None
	who = doc.employee_name or doc.employee
	if allowed >= claimed:
		return {
			"text": _("{0} claimed {1} for {2}, and all of it is allowed.").format(
				who, _money(claimed, doc.currency), doc.payroll_period
			),
			"colour": "blue",
		}
	return {
		"text": _(
			"{0} claimed {1} for {2}, of which {3} is allowed — the rest is over a category limit."
		).format(who, _money(claimed, doc.currency), doc.payroll_period, _money(allowed, doc.currency)),
		"colour": "orange",
	}


def promotion_changes(doc):
	"""The whole change in one line: it is otherwise three rows down in a
	child table, which cannot be a column or be searched."""
	if doc.is_new() or not doc.promotion_date:
		return None
	changes = [
		_("{0} {1} → {2}").format(row.property.lower(), row.current, row.new)
		if row.current
		else _("{0} becomes {1}").format(row.property.lower(), row.new)
		for row in doc.promotion_details or []
		if row.property and row.get("new")
	]
	when = _on(doc.promotion_date)
	if changes:
		return {
			"text": _("{0}, from {1}: {2}.").format(doc.employee_name, when, ", ".join(changes)),
			"colour": "blue",
		}
	return {
		"text": _("{0}, from {1}. Nothing is listed as changing yet.").format(doc.employee_name, when),
		"colour": "orange",
	}


def overtime_pays(doc):
	"""What the slip pays, or why it pays less than was worked (overtime.py
	writes `one_pay_note` when it does)."""
	if doc.is_new() or not doc.overtime_details:
		return None
	if doc.get("one_pay_note"):
		return {"text": doc.one_pay_note, "colour": "orange"}
	money, hours = _money(doc.get("one_amount")), _number(doc.total_overtime_duration)
	if doc.docstatus == 1:
		return {"text": _("{0} for {1} hours of overtime.").format(money, hours), "colour": "green"}
	return {"text": _("Submitting this pays {0} for {1} hours.").format(money, hours), "colour": "blue"}


def _deaf(doc) -> bool:
	"""A shift that takes check-ins and never turns them into attendance:
	hrms's job returns early, and every list and chart over attendance is
	simply empty."""
	return not (doc.enable_auto_attendance and doc.process_attendance_after and doc.last_sync_of_checkin)


def shift_deaf(doc):
	if doc.is_new() or not _deaf(doc):
		return None
	return {"text": _("Check-ins on this shift are not becoming attendance."), "colour": "orange"}


# ------------------------------------------------------------------ a clock attempt

#: What the pill says, by verdict first and outcome second.
ATTEMPT_COLOUR = {
	"Accepted": "green",
	"Rejected": "red",
	"Allowed": "green",
	"Flagged": "orange",
	"Refused": "red",
}


def attempt_state(doc):
	said = doc.get("verdict") or doc.get("outcome")
	return {"label": _(said), "colour": ATTEMPT_COLOUR.get(said, "gray")} if said else None


def _unsettled(doc) -> bool:
	"""A flag nobody has settled, to somebody who may write one: an employee
	reading their own attempt sees the reasons and no way to wave them
	through."""
	return (
		doc.outcome == "Flagged" and not doc.verdict and bool(frappe.has_permission("Clock Attempt", "write"))
	)


def _settle_note(required: bool):
	# A note is asked for rather than typed afterwards: why somebody waved a
	# flag through is the part worth having later.
	def fields(doc):
		return [{"fieldtype": "Small Text", "fieldname": "note", "label": _("Note"), "reqd": int(required)}]

	return fields


VERBS = {
	# Who may answer is the `submit` grant (decision.py), and what each
	# verdict does stays in the doctype's own module.
	"leave.approve": {
		"doctypes": ["Leave Application"],
		"label": _approve,
		"when": _may_answer,
		"fields": _asks(_lt("The days are spent and the attendance is marked.")),
		"run": _approves(applications),
	},
	"leave.reject": {
		"doctypes": ["Leave Application"],
		"label": _reject,
		"when": _may_answer,
		"fields": _asks(_lt("Nothing is spent and no attendance is marked.")),
		"run": _rejects(applications),
	},
	"request.approve": {
		"doctypes": ["Attendance Request"],
		"label": _approve,
		"when": _may_answer,
		"fields": _asks(_lt("These days will be marked as worked.")),
		"run": _approves(request),
	},
	"request.reject": {
		"doctypes": ["Attendance Request"],
		"label": _reject,
		"when": _may_answer,
		"fields": _asks(_lt("Nothing will be written to attendance.")),
		"run": _rejects(request),
	},
	"shift.approve": {
		"doctypes": ["Shift Request"],
		"label": _approve,
		"when": _may_answer,
		"fields": _asks(_lt("A Shift Assignment is created and the employee works this shift.")),
		"run": _approves(shift),
	},
	"shift.reject": {
		"doctypes": ["Shift Request"],
		"label": _reject,
		"when": _may_answer,
		"fields": _asks(_lt("The request is closed and nobody is assigned anything.")),
		"run": _rejects(shift),
	},
	"expense.approve": {
		"doctypes": ["Expense Claim"],
		"label": _approve,
		"when": _may_answer,
		"fields": _asks(_lt("The expense is booked and the money is owed to them.")),
		"run": _approves(expense),
	},
	"expense.reject": {
		"doctypes": ["Expense Claim"],
		"label": _reject,
		"when": _may_answer,
		"fields": _asks(_lt("The claim is closed and nothing is booked.")),
		"run": _rejects(expense),
	},
	"shift.read_checkins": {
		"doctypes": ["Shift Type"],
		"label": lambda doc: _("Read Check-ins"),
		"when": lambda doc: not doc.is_new() and _deaf(doc) and bool(doc.has_permission("write")),
		"fields": lambda doc: [
			{
				"fieldtype": "HTML",
				"fieldname": "what",
				"options": '<p class="text-muted">{}</p>'.format(
					escape_html(
						_("Attendance will be written from check-ins on this shift from today onwards.")
					)
				),
			}
		],
		"run": lambda doc, **_values: setup.start_reading(doc.name),
	},
	"attempt.accept": {
		"doctypes": ["Clock Attempt"],
		"label": lambda doc: _("Accept"),
		"title": lambda doc: _("Accept this check-in?"),
		"when": _unsettled,
		"fields": _settle_note(False),
		"run": lambda doc, note=None, **_values: review.accept(doc.name, note) and _("Reviewed"),
	},
	"attempt.reject": {
		"doctypes": ["Clock Attempt"],
		"label": lambda doc: _("Reject"),
		"title": lambda doc: _(
			"Reject it? The check-in stays on the record and stops counting towards the day."
		),
		"when": _unsettled,
		"fields": _settle_note(True),
		"run": lambda doc, note=None, **_values: review.reject(doc.name, note) and _("Reviewed"),
	},
}

MEASURES = {
	"employee.state": state,
	"employee.standing": standing,
	"employee.checked": checked,
	"employee.leave": leave,
	"employee.awaiting": awaiting,
	"employee.equipment": equipment,
	"employee.pay": pay,
	"leave.about": leave_about,
	"request.turned_down": request_turned_down,
	"shift.about": shift_about,
	"expense.about": expense_about,
	"slip.pays": slip_pays,
	"payroll.run": payroll_run,
	"appraisal.stands": appraisal_stands,
	"encashment.pays": encashment_pays,
	"vehicle.went": vehicle_went,
	"exemption.allowed": exemption_allowed,
	"promotion.changes": promotion_changes,
	"overtime.pays": overtime_pays,
	"shift_type.deaf": shift_deaf,
	"attempt.state": attempt_state,
}

HEADS = [
	{
		"doctype": "Employee",
		"indicators": [{"label": _lt("Where"), "measure": "employee.state"}],
		"band": [
			{"label": _lt("Standing"), "source": "Measure", "measure": "employee.standing"},
			{"label": _lt("In"), "source": "Measure", "measure": "employee.checked"},
			{"label": _lt("Leave"), "source": "Measure", "measure": "employee.leave"},
			{"label": _lt("Awaiting"), "source": "Measure", "measure": "employee.awaiting"},
			{"label": _lt("Equipment"), "source": "Measure", "measure": "employee.equipment"},
			{"label": _lt("Paid under"), "source": "Measure", "measure": "employee.pay"},
		],
		"charts": [{"chart": "employee.quarter"}],
	},
	{
		"doctype": "Leave Application",
		"sentences": [{"measure": "leave.about"}],
		"verbs": [{"verb": "leave.approve"}, {"verb": "leave.reject"}],
	},
	{
		"doctype": "Attendance Request",
		"sentences": [{"measure": "request.turned_down"}],
		"verbs": [{"verb": "request.approve"}, {"verb": "request.reject"}],
	},
	{
		"doctype": "Shift Request",
		"sentences": [{"measure": "shift.about"}],
		"redraw_on": ["employee", "shift_type", "from_date", "to_date"],
		"verbs": [{"verb": "shift.approve"}, {"verb": "shift.reject"}],
	},
	{
		"doctype": "Expense Claim",
		"sentences": [{"measure": "expense.about"}],
		"verbs": [{"verb": "expense.approve"}, {"verb": "expense.reject"}],
	},
	{
		"doctype": "Salary Slip",
		"sentences": [{"measure": "slip.pays"}],
		"redraw_on": ["net_pay"],
	},
	{
		"doctype": "Payroll Entry",
		"sentences": [{"measure": "payroll.run"}],
	},
	{
		"doctype": "Appraisal",
		"sentences": [{"measure": "appraisal.stands"}],
		"redraw_on": ["final_score"],
	},
	{
		"doctype": "Leave Encashment",
		"sentences": [{"measure": "encashment.pays"}],
		"redraw_on": ["employee", "encashment_date", "encashment_days", "encashment_amount"],
	},
	{
		"doctype": "Vehicle Log",
		"sentences": [{"measure": "vehicle.went"}],
		"redraw_on": ["odometer", "fuel_qty", "price"],
	},
	{
		"doctype": "Employee Tax Exemption Declaration",
		"sentences": [{"measure": "exemption.allowed"}],
		"redraw_on": ["total_declared_amount", "total_exemption_amount"],
	},
	{
		"doctype": "Employee Tax Exemption Proof Submission",
		"sentences": [{"measure": "exemption.allowed"}],
		"redraw_on": ["total_actual_amount", "exemption_amount"],
	},
	{
		"doctype": "Employee Promotion",
		"sentences": [{"measure": "promotion.changes"}],
		"redraw_on": ["promotion_date", "promotion_details"],
	},
	{
		"doctype": "Overtime Slip",
		"sentences": [{"measure": "overtime.pays"}],
	},
	{
		"doctype": "Shift Type",
		"sentences": [{"measure": "shift_type.deaf"}],
		"verbs": [{"verb": "shift.read_checkins"}],
	},
	{
		"doctype": "Clock Attempt",
		"indicators": [{"label": _lt("State"), "measure": "attempt.state"}],
		"verbs": [{"verb": "attempt.reject"}, {"verb": "attempt.accept", "primary": 1}],
	},
]
