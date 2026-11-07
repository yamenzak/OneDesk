"""OneHR's part of the integration suite (one_demo/check.py runs it):
clocking in, attendance, leave, pay, expenses, hiring and Home as their
people read them, and the one ability."""

import json

import frappe
from frappe.utils import (
	add_days,
	add_months,
	add_to_date,
	date_diff,
	flt,
	get_first_day,
	getdate,
	now_datetime,
	today,
)

from onedesk.one_demo.base import COMPANY, as_user
from onedesk.one_demo.check import (
	CENTS,
	DESKTOP,
	PHONE,
	_asked,
	_card,
	_cookies,
	_employee,
	_Phone,
	_Told,
	_unasked,
	check,
)
from onedesk.one_demo.people import OWNER


@check
def onehr_requests_are_answered_by_who_answers_them():
	"""Layla says yes to Omar's leave and Samir's lunch, Tariq says no to
	Yousef's sick day, Mariam gives Ravi the day shift and turns Imran down,
	Samir counts Nadia's day at the showroom and turns down Rania's. Each
	answer is the record's own state afterwards, and somebody who may not
	answer is refused."""
	from onedesk.one_demo import hr as demo
	from onedesk.one_hr import expense, leave, request, shift

	def waiting(first, **more):
		return frappe.db.get_value("Leave Application", {"employee": _employee(first), "docstatus": 0, **more})

	omar, yousef = waiting("Omar"), waiting("Yousef")
	with as_user("rania@one.test"):
		try:
			leave.approve(omar)
			raise AssertionError("Rania approved Omar's leave")
		except frappe.PermissionError:
			pass
	with as_user(OWNER):
		assert leave.about(omar)
		leave.approve(omar, "Enjoy it.")
		assert frappe.db.get_value("Leave Application", omar, ["status", "docstatus"]) == ("Approved", 1)
	with as_user("tariq@one.test"):
		leave.reject(yousef, "Bring a note from the doctor next time.")
		assert frappe.db.get_value("Leave Application", yousef, ["status", "docstatus"]) == ("Rejected", 1)

	lunch = frappe.db.get_value("Expense Claim", {"employee": _employee("Samir"), "docstatus": 0})
	with as_user(OWNER):
		assert expense.about(lunch)
		expense.approve(lunch)
		assert frappe.db.get_value("Expense Claim", lunch, ["approval_status", "docstatus"]) == ("Approved", 1)
	with as_user("rania@one.test"):
		claim = frappe.new_doc("Expense Claim")
		claim.update({"employee": _employee("Rania"), "expense_approver": "samir@one.test", "payable_account": demo._claims_payable()})
		claim.append("expenses", {"expense_date": today(), "expense_type": "Travel", "description": "Taxi to the tower", "amount": 120, "sanctioned_amount": 120})
		claim.insert()
	with as_user("samir@one.test"):
		expense.reject(claim.name, "The site van went there that day.")
		assert frappe.db.get_value("Expense Claim", claim.name, ["approval_status", "docstatus"]) == ("Rejected", 1)

	name, _starts, _ends = demo.SHIFT
	joseph = frappe.db.get_value("Shift Request", {"employee": _employee("Joseph"), "docstatus": 0})
	with as_user(demo.HR):
		assert demo.HR in shift.approvers(_employee("Joseph"))
		assert shift.hours(name)
		shift.approve(joseph)
		assert frappe.db.exists("Shift Assignment", {"employee": _employee("Joseph"), "shift_type": name, "docstatus": 1})
		frappe.db.set_value("Employee", _employee("Imran"), "shift_request_approver", demo.HR)
		imran = frappe.get_doc({"doctype": "Shift Request", "shift_type": name, "employee": _employee("Imran"), "company": COMPANY, "from_date": add_days(today(), 20), "to_date": add_days(today(), 30), "approver": demo.HR, "status": "Draft"}).insert()
		shift.reject(imran.name, "Days are full that month.")
		assert frappe.db.get_value("Shift Request", imran.name, ["status", "docstatus"]) == ("Rejected", 1)

	nadia = frappe.db.get_value("Attendance Request", {"employee": _employee("Nadia"), "docstatus": 0})
	with as_user(demo.HR):
		request.approve(nadia, "Counted.")
		assert frappe.db.get_value("Attendance Request", nadia, "docstatus") == 1
		from erpnext.setup.doctype.employee.employee import is_holiday

		day = add_days(today(), -2)
		while is_holiday(_employee("Rania"), day):
			day = add_days(day, -1)
		rania = frappe.get_doc({"doctype": "Attendance Request", "employee": _employee("Rania"), "company": COMPANY, "from_date": day, "to_date": day, "reason": "On Duty", "one_reason": "Customer Site", "explanation": "At the tower all day."}).insert()
		request.reject(rania.name, "You were in the office that day.")
		assert frappe.db.get_value("Attendance Request", rania.name, ["docstatus", "one_decision"]) == (0, request.REJECTED)


@check
def onehr_the_crews_days_overtime_and_pay_add_up():
	"""Mariam's view of the workshop: who clocked in today and who is in now,
	overtime written on one of Arun's days and collected for his slip, the
	day shift reading check-ins, the payroll's headline, an encashment's
	rate, and an employee's page, read by Mariam and by Rania herself."""
	from onedesk.one_demo import hr as demo
	from onedesk.one_hr import (
		employee,
		encashment,
		learned,
		marking,
		overtime,
		payroll,
		presence,
		shift_setup,
	)

	demo._attendance()
	arun = _employee("Arun")
	worked = frappe.db.get_value("Attendance", {"employee": arun, "status": "Present", "docstatus": 1}, "attendance_date", order_by="attendance_date desc")
	with as_user(demo.HR):
		assert set(marking.clocked_in(today())) >= {_employee("Samir"), _employee("Rania"), arun}
		assert presence.in_now() >= 5
		assert presence.of(_employee("Tariq"))["state"]
		assert overtime.day(arun, str(worked))["ok"] == 1
		overtime.record(arun, str(worked), "Workshop Overtime", 2.5)
		period = overtime.dates(arun, str(worked))
		collected = overtime.collect(arun, period["start_date"], period["end_date"])
		assert any(flt(one.get("overtime_duration") or one.get("hours") or 0) == 2.5 for one in collected["rows"]), collected
		try:
			overtime.record(arun, str(worked), "Workshop Overtime", 6)
			raise AssertionError("more than the type's four hours was written")
		except frappe.ValidationError:
			pass
		shift_setup.start_reading(demo.SHIFT[0])
		assert frappe.db.get_value("Shift Type", demo.SHIFT[0], "enable_auto_attendance") == 1
		entry = frappe.db.get_value("Payroll Entry", {"docstatus": 1, "salary_slip_based_on_timesheet": 0})
		ran = payroll.run(entry)
		assert ran["people"] >= 10 and ran["total"] > 0
		assert encashment.rate(arun, today())["structure"]
		seen = employee.overview(_employee("Rania"))
		assert seen["leave"] and seen["tenure"]
		network = frappe.get_doc({"doctype": "Clock Network", "address": "203.0.113.0/24", "status": "Proposed"}).insert(ignore_permissions=True)
		learned.confirm("Clock Network", network.name)
		assert frappe.db.get_value("Clock Network", network.name, "status") == "Confirmed"
		learned.reject("Clock Network", network.name)
	with as_user("rania@one.test"):
		assert employee.overview(_employee("Rania"))["days"] is not None
		try:
			employee.overview(_employee("Omar"))
			raise AssertionError("Rania read Omar's page")
		except frappe.PermissionError:
			pass


@check
def onehr_a_colleagues_record_opens_for_whoever_may_read_it():
	"""Karim may read Mariam's record but not Leave Policy or Salary
	Structure: it opens without a permission error and offers him nothing to
	assign. Mariam, who assigns them, is offered the salary structures there
	are."""
	from hrms.overrides.employee_master import get_assignable_masters

	company = frappe.db.get_value("Employee", _employee("Mariam"), "company")
	with as_user("karim@one.test"):
		assert not frappe.has_permission("Leave Policy", "read")
		assert not frappe.has_permission("Salary Structure", "read")
		assert not any(get_assignable_masters(company).values())
	with as_user("mariam@one.test"):
		assert get_assignable_masters(company)["Salary Structure"] is True


@check
def onehr_tariq_clocks_in_with_his_phone():
	"""The workspace turns on clocking in. Tariq registers his phone's
	passkey; clocking with it from a network nobody knows is refused, and from
	the office network it goes through. Twice from the office computer it is
	let through and flagged: Mariam lets one stand and turns the other down. He signs in to One with the same
	passkey. A new phone: he asks for a reset, Mariam resets it, and blocks
	it when he leaves."""
	import time
	from unittest import mock

	from onedesk.one_demo import hr as demo
	from onedesk.one_hr import clock, employee, passkey, review, signin

	tariq = _employee("Tariq")
	off = frappe.db.get_value("Employee", tariq, "holiday_list") or frappe.db.get_value("Company", COMPANY, "default_holiday_list")
	frappe.db.delete("Holiday", {"parent": off, "holiday_date": today()})
	frappe.db.set_single_value("HR Settings", "one_self_checkin", 1)
	frappe.db.set_single_value("System Settings", signin.SWITCH, 1)
	phone = _Phone(tariq.encode())
	with as_user("tariq@one.test"):
		_asked(headers={"User-Agent": PHONE})
		made = passkey.finish_registration(json.dumps(phone.make(passkey.start_registration())), {"user_agent": PHONE})
		assert frappe.db.get_value("Clock Device", made["device"], "status") == "Active"
		before = clock.ready()
		assert before["registered"] and before["direction"], before
		_asked(headers={"User-Agent": PHONE})
		refused = clock.punch(json.dumps(phone.sign(passkey.start_assertion())), seen={"user_agent": PHONE})
		assert not refused["ok"] and refused["score"] < 50, refused
	frappe.get_doc({"doctype": "Clock Network", "address": "127.0.0.1/32", "label": "Office", "status": "Confirmed"}).insert(ignore_permissions=True)
	with as_user("tariq@one.test"):
		_asked(headers={"User-Agent": PHONE})
		clean = clock.punch(json.dumps(phone.sign(passkey.start_assertion())), seen={"user_agent": PHONE})
		assert clean["ok"] and not clean["flagged"], clean
		time.sleep(1.1)
		_asked(headers={"User-Agent": DESKTOP})
		punched = clock.punch(json.dumps(phone.sign(passkey.start_assertion())), seen={"user_agent": DESKTOP})
		assert punched["ok"] and punched["flagged"], punched
		time.sleep(1.1)
		_asked(headers={"User-Agent": DESKTOP})
		again = clock.punch(json.dumps(phone.sign(passkey.start_assertion())), seen={"user_agent": DESKTOP})
		assert again["ok"] and again["flagged"], again
	with as_user(demo.HR):
		assert employee.passkey_of(tariq)["label"] == made["label"]
		review.accept(punched["attempt"], "He was at the tower.")
		assert frappe.db.get_value("Clock Attempt", punched["attempt"], "verdict") == "Accepted"
		review.reject(again["attempt"], "Not on site.")
		assert frappe.db.get_value("Employee Checkin", again["checkin"], "skip_auto_attendance") == 1

	frappe.set_user("Guest")
	_asked(headers={"User-Agent": PHONE})
	assert signin.offered()
	options = signin.begin()
	_asked(headers={"User-Agent": PHONE}, cookies=_cookies())
	frappe.local.login_manager = mock.Mock()
	assert signin.finish(json.dumps(phone.sign(options)))["user"] == "tariq@one.test"
	frappe.local.login_manager.login_as.assert_called_once_with("tariq@one.test")

	with as_user("tariq@one.test"):
		_asked(headers={"User-Agent": PHONE})
		assert passkey.ask_for_a_reset("I dropped my phone in the canal.")["told"] >= 1
	with as_user(demo.HR):
		assert passkey.reset(tariq)["reset"] == 1
		assert not passkey.held_by(tariq)
		assert passkey.retire(tariq) >= 1 and passkey.is_blocked(tariq)
	_unasked()


@check
def onehr_the_clock_says_when_the_shift_starts():
	"""Tariq's shift started an hour ago and he has not checked in: the clock
	gives its start and says he is late, and he is reminded once. He checks in
	and the clock says he is in, late."""

	from onedesk.one_hr import clock, tell

	tariq = _employee("Tariq")
	frappe.db.set_single_value("HR Settings", "one_self_checkin", 1)
	frappe.db.delete("Employee Checkin", {"employee": tariq, "time": [">=", f"{today()} 00:00:00"]})
	frappe.db.delete("Attendance", {"employee": tariq, "attendance_date": today()})
	frappe.db.delete("Leave Application", {"employee": tariq, "from_date": ["<=", today()], "to_date": [">=", today()]})
	off = frappe.db.get_value("Employee", tariq, "holiday_list") or frappe.db.get_value("Company", COMPANY, "default_holiday_list")
	frappe.db.delete("Holiday", {"parent": off, "holiday_date": today()})
	start = max(add_to_date(now_datetime(), hours=-1), frappe.utils.get_datetime(f"{today()} 00:01:00"))
	shift = frappe.get_doc(
		{
			"doctype": "Shift Type",
			"name": "Check Shift",
			"start_time": start.strftime("%H:%M:00"),
			"end_time": "23:59:00",
			"allow_check_out_after_shift_end_time": 0,
			"begin_check_in_before_shift_start_time": 0,
		}
	).insert(ignore_permissions=True)
	frappe.get_doc(
		{"doctype": "Shift Assignment", "employee": tariq, "company": COMPANY, "shift_type": shift.name, "start_date": today(), "status": "Active"}
	).insert(ignore_permissions=True).submit()

	with as_user("tariq@one.test"):
		before = clock.ready()
	assert before["due"].startswith(f"{today()} {start.strftime('%H:%M')}"), before
	assert before["late"] and before["direction"] == "IN", before
	with _Told() as told:
		tell.not_checked_in()
		tell.not_checked_in()
	assert [users for name, users in told.said if name == "Not Checked In"].count(["tariq@one.test"]) == 1, told.said

	checkin = frappe.new_doc("Employee Checkin")
	checkin.flags.one_gated = True
	checkin.update({"employee": tariq, "log_type": "IN", "time": now_datetime()})
	checkin.insert(ignore_permissions=True)
	with as_user("tariq@one.test"):
		after = clock.ready()
	assert after["state"] == "in" and after["late"], after
	frappe.cache.delete_value(f"one-not-checked-in:{tariq}:{start.date()}")


@check
def onehr_uae_papers_are_kept_where_a_company_is_in_the_uae():
	"""Sahara is in the UAE, so an employee's papers may be an Emirates ID, a
	Labour Card, Health Insurance or a Medical Fitness certificate, and
	expire as any other; a workspace with no company there gets none of them."""
	from onedesk.one_hr import papers

	assert papers.wanted({"Germany"}) == [] and "Emirates ID" in papers.wanted({"United Arab Emirates", "Germany"})
	papers.settle()
	for name in ("Emirates ID", "Labour Card", "Health Insurance", "Medical Fitness"):
		assert frappe.db.exists(papers.KIND, name), name


@check
def onehr_late_arrivals_can_count_as_an_absent_day():
	"""Off by default. At 4 late arrivals to an absent day, an employee late
	five times in October loses one day on the October payslip, which says
	so, and is paid that much less; with the rule off again nothing is taken.
	The October payroll already ran, so the employee's slip is set aside for
	the check, which is rolled back."""
	from onedesk.one_hr import lates

	assert lates.days_off(5, 4) == 1 and lates.days_off(3, 4) == 0 and lates.days_off(9, 0) == 0
	employee = "HR-EMP-00018"
	start, end = "2026-10-01", "2026-10-31"
	for paid in frappe.get_all("Salary Slip", filters={"employee": employee, "start_date": start, "docstatus": ["<", 2]}, pluck="name"):
		frappe.db.set_value("Salary Slip", paid, "docstatus", 2)
	marked = set(frappe.get_all("Attendance", filters={"employee": employee, "attendance_date": ["between", [start, end]]}, pluck="attendance_date"))
	holidays = set(frappe.get_all("Holiday", filters={"parent": frappe.db.get_value("Company", COMPANY, "default_holiday_list")}, pluck="holiday_date"))
	days = [day for day in (add_days(start, n) for n in range(31)) if getdate(day) not in marked and getdate(day) not in holidays][:5]
	assert len(days) == 5, days
	for day in days:
		frappe.get_doc({"doctype": "Attendance", "employee": employee, "attendance_date": day, "status": "Present", "late_entry": 1, "company": COMPANY}).submit()

	def slip():
		said = frappe.get_doc({"doctype": "Salary Slip", "employee": employee, "posting_date": end, "start_date": start, "end_date": end, "payroll_frequency": "Monthly"})
		said.insert()
		return said

	assert not frappe.db.get_single_value("HR Settings", "one_lates_per_absence"), "off by default"
	plain = slip()
	assert not plain.one_late_days
	paid, gross = plain.payment_days, plain.gross_pay
	plain.delete()
	frappe.db.set_single_value("HR Settings", "one_lates_per_absence", 4)
	late = slip()
	assert late.one_late_days == 1 and late.payment_days == paid - 1, (late.one_late_days, late.payment_days, paid)
	assert late.gross_pay < gross, (late.gross_pay, gross)
	late.save()
	assert late.one_late_days == 1 and late.payment_days == paid - 1, "a second save takes nothing more"
	late.delete()
	frappe.db.set_single_value("HR Settings", "one_lates_per_absence", 0)


@check
def onehr_oneai_answers_and_drafts_for_each_person():
	"""What OneAI reads and suggests in OneHR, as the people who ask: Rania
	about her leave, a day off, a taxi, a salary certificate, her goals and
	training, and the leave policy; Samir about the interview he holds;
	Mariam about the payroll, people leaving, an applicant from a CV, and
	Rania's appraisal. Cards wait for approval; nothing is made yet."""
	from onedesk.one_demo import hr as demo
	from onedesk.one_hr import ai, ai_growth, ai_letters, ai_payroll, ai_policy

	monday = add_days(today(), 7 - getdate(today()).weekday())
	with as_user("rania@one.test"):
		mine = ai.my_leave(str(monday), str(add_days(monday, 1)), "Privilege Leave")
		assert mine.get("balances") or mine.get("left") or mine, mine
		_card(ai.book_leave(str(monday), str(add_days(monday, 1)), "annual", "A family wedding"))
		_card(ai.claim_expense(str(add_days(today(), -1)), 64.5, "taxi", "Careem to the Bayview site", "AED"))
		facts = ai_letters.letter_facts("Salary Certificate")
		assert "error" not in facts, facts
		_card(ai_letters.request_letter("Salary Certificate", "This is to certify that Rania Sabbagh works here.", "Emirates NBD", "opening a bank account"))
		assert "error" not in ai_growth.goal_facts()
		_card(ai_growth.draft_goal("Hand over the villa without snags", "Snag list closed within a week of handover.", "Delivery on Time"))
		assert "error" not in ai_growth.training_options()
		assert "error" not in ai_policy.hr_policy("How many days of annual leave do I get?")
		try:
			assert "error" in ai_letters.letter_facts("Salary Certificate", _employee("Omar"))
		except frappe.PermissionError:
			pass
		try:
			frappe.get_doc({"doctype": "Employee Letter", "employee": _employee("Omar"), "kind": "Salary Certificate", "body": "About Omar."}).insert()
			raise AssertionError("Rania asked for a letter about Omar")
		except (frappe.ValidationError, frappe.PermissionError):
			pass
	interview = frappe.db.get_value("Interview", {"interview_type": "Site Engineer Technical"})
	with as_user("samir@one.test"):
		assert "error" not in ai.interview_facts(interview)
		_card(ai.draft_interview_feedback(interview, "Mira knew the unitised system well.", {"Curtain Wall Design": 4}, "Cleared"))
	appraisal = frappe.db.get_value("Appraisal", {"employee": _employee("Rania")})
	opening = frappe.db.get_value("Job Opening", {})
	entry = frappe.db.get_value("Payroll Entry", {"docstatus": 1, "salary_slip_based_on_timesheet": 0})
	with as_user(demo.HR):
		assert "error" not in ai_payroll.payroll_changes(entry)
		assert "error" not in ai.why_people_leave()
		_card(ai.add_applicant("Dana Aziz", "dana.aziz@example.com", opening, "Eight years on unitised facades; no site supervision yet."))
		assert "error" not in ai.appraisal_facts(appraisal)
		_card(ai.draft_feedback(appraisal, "Rania kept the villa on time and ran the snag walk well."))


@check
def onehr_an_interview_is_recorded_and_its_people_read_again():
	"""Samir records the interview with Mira once she agrees: a part of sound
	is filed and sent to be written down, the recording ends and is sent
	again. Mariam has OneAI read Mira's CV, rank the opening and prepare
	the interview again. The model is not called here: what would run is
	asked for, and that is checked."""
	import base64
	from unittest import mock

	from onedesk.one_demo import hr as demo
	from onedesk.one_hr import hiring

	interview = frappe.db.get_value("Interview", {"interview_type": "Site Engineer Technical"})
	applicant = frappe.db.get_value("Interview", interview, "job_applicant")
	opening = frappe.db.get_value("Job Applicant", applicant, "job_title")
	with mock.patch("onedesk.one_hr.hiring._later") as later:
		with as_user("samir@one.test"):
			try:
				hiring.start_recording(interview, 0)
				raise AssertionError("an interview was recorded without the candidate agreeing")
			except frappe.ValidationError:
				pass
			held = hiring.start_recording(interview, 1)
			hiring.recorded_part(held, "part-1.webm", base64.b64encode(b"\x1aE\xdf\xa3 sound").decode(), 0, 30)
			assert frappe.db.count("Interview Recording Part", {"parent": held}) == 1
			hiring.stop_recording(held, 30)
			assert frappe.db.get_value("Interview Recording", held, "status") in ("Transcribing", "Recorded")
			frappe.db.set_value("Interview Recording", held, "status", "Recorded")
			hiring.transcribe_again(held)
		with as_user(demo.HR):
			hiring.screen_again(applicant)
			hiring.rank_again(opening)
			hiring.prepare_again(interview)
	asked = [one.args[0] for one in later.call_args_list]
	for method in ("transcribe", "screen", "rank", "prepare"):
		assert f"onedesk.one_hr.hiring.{method}" in asked, asked


@check
def onehr_each_payslip_adds_up_and_the_payroll_posts_it():
	"""Each payslip's net pay is its earnings less its deductions, and each
	payroll posts what its slips owe the people on them."""
	wrong = []
	for slip in frappe.get_all("Salary Slip", filters={"docstatus": 1}, fields=["name", "gross_pay", "total_deduction", "net_pay", "payroll_entry"]):
		doc = frappe.get_doc("Salary Slip", slip.name)
		earned = sum(flt(row.amount) for row in doc.earnings if not row.do_not_include_in_total)
		taken = sum(flt(row.amount) for row in doc.deductions if not row.do_not_include_in_total)
		if abs(earned - flt(slip.gross_pay)) > CENTS or abs(taken - flt(slip.total_deduction)) > CENTS or abs(flt(slip.gross_pay) - flt(slip.total_deduction) - flt(slip.net_pay)) > CENTS:
			wrong.append((slip.name, earned, slip.gross_pay, taken, slip.total_deduction, slip.net_pay))
	assert not wrong, wrong[:5]
	payable = frappe.db.get_value("Company", COMPANY, "default_payroll_payable_account")
	for entry in frappe.get_all("Payroll Entry", filters={"docstatus": 1}, pluck="name"):
		owed = frappe.db.sql("select ifnull(sum(net_pay), 0) from `tabSalary Slip` where payroll_entry = %s and docstatus = 1", entry)[0][0]
		posted = frappe.db.sql(
			"""select ifnull(sum(row.credit_in_account_currency - row.debit_in_account_currency), 0)
			from `tabJournal Entry Account` row join `tabJournal Entry` je on je.name = row.parent
			where je.docstatus = 1 and row.reference_type = 'Payroll Entry' and row.reference_name = %s
				and row.account = %s and je.voucher_type != 'Bank Entry'""",
			(entry, payable),
		)[0][0]
		assert abs(flt(owed) - flt(posted)) <= 1, (entry, owed, posted)


@check
def onehr_leave_taken_comes_off_what_is_left():
	"""What each person has left of a kind of leave is what they were given,
	less the days approved, and as adjusted, as the leave form reads it."""
	from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

	year_end = getdate(f"{getdate(today()).year}-12-31")
	checked = 0
	for allocation in frappe.get_all("Leave Allocation", filters={"docstatus": 1}, fields=["name", "employee", "leave_type", "total_leaves_allocated", "from_date", "to_date"]):
		taken = frappe.db.sql(
			"""select ifnull(sum(total_leave_days), 0) from `tabLeave Application`
			where employee = %s and leave_type = %s and status = 'Approved' and docstatus = 1
				and from_date between %s and %s""",
			(allocation.employee, allocation.leave_type, allocation.from_date, allocation.to_date),
		)[0][0]
		adjusted = sum(
			flt(one.leaves_to_adjust) * (-1 if one.adjustment_type == "Reduce" else 1)
			for one in frappe.get_all("Leave Adjustment", filters={"leave_allocation": allocation.name, "docstatus": 1}, fields=["leaves_to_adjust", "adjustment_type"])
		)
		left = get_leave_balance_on(allocation.employee, allocation.leave_type, min(year_end, getdate(allocation.to_date)))
		assert abs(flt(left) - (flt(allocation.total_leaves_allocated) - flt(taken) + adjusted)) <= 0.01, (allocation, taken, adjusted, left)
		checked += bool(taken)
	assert checked >= 2, "nobody has taken leave"


@check
def onehr_a_leaver_is_paid_their_end_of_service():
	"""Joseph resigned after four years and worked to the end of last month.
	He is no longer on the payroll, and his end of service is the UAE rule on
	resigning between three and five years, 14 days of basic pay a year,
	worked out from his last payslip and paid by the books."""
	from onedesk.one_demo.hr import LEAVER, RESIGNED

	employee = frappe.get_doc("Employee", _employee(LEAVER))
	assert employee.status == "Left" and employee.relieving_date, (employee.status, employee.relieving_date)
	assert not frappe.db.exists("Salary Slip", {"employee": employee.name, "start_date": [">", employee.relieving_date], "docstatus": 1})
	gratuity = frappe.get_doc("Gratuity", {"employee": employee.name, "docstatus": 1})
	assert gratuity.gratuity_rule == RESIGNED
	years = round(date_diff(employee.relieving_date, employee.date_of_joining) / 365)
	slip = frappe.db.get_value("Salary Slip", {"employee": employee.name, "docstatus": 1}, "name", order_by="start_date desc")
	basic = sum(flt(row.default_amount) for row in frappe.get_doc("Salary Slip", slip).earnings if row.salary_component == "Basic Salary")
	assert 3 <= years < 5 and flt(gratuity.current_work_experience) == years, (years, gratuity.current_work_experience)
	assert abs(flt(gratuity.amount) - basic * years * 14 / 30) <= 1, (gratuity.amount, basic, years)
	assert gratuity.status == "Paid" and flt(gratuity.paid_amount) == flt(gratuity.amount), (gratuity.status, gratuity.paid_amount)
	booked = frappe.db.sql(
		"select ifnull(sum(debit - credit), 0) from `tabGL Entry` where voucher_no = %s and account = %s and is_cancelled = 0",
		(gratuity.name, gratuity.expense_account),
	)[0][0]
	assert abs(flt(booked) - flt(gratuity.amount)) <= CENTS, booked


@check
def onehr_an_expense_claim_paid_is_what_the_books_and_project_carry():
	"""A claim paid back is paid what was approved, and a project carries the
	claims approved on it."""
	wrong = []
	for claim in frappe.get_all("Expense Claim", filters={"docstatus": 1, "status": "Paid"}, fields=["name", "grand_total", "total_amount_reimbursed"]):
		if abs(flt(claim.grand_total) - flt(claim.total_amount_reimbursed)) > CENTS:
			wrong.append(claim)
	assert not wrong, wrong
	for project in frappe.get_all("Expense Claim", filters={"docstatus": 1, "approval_status": "Approved", "project": ["is", "set"]}, pluck="project", distinct=True):
		approved = frappe.db.sql(
			"select ifnull(sum(total_sanctioned_amount), 0) from `tabExpense Claim` where project = %s and docstatus = 1 and approval_status = 'Approved'",
			project,
		)[0][0]
		assert abs(flt(frappe.db.get_value("Project", project, "total_expense_claim")) - flt(approved)) <= CENTS, (project, approved)


@check
def onehr_tells_each_moment_somebody_waits_on():
	"""Nadia's attendance request reaches HR, and Mariam's answer reaches her
	with Mariam's note. A letter issued reaches the employee it is about; a
	grievance reaches HR when OneAI is not reading them; a passkey reset is
	asked of HR and its doing told back; an interview's interviewers hear the
	day it is made; a permit a month from expiring reaches the employee and
	HR. Leave answered carries the approver's note."""
	from unittest.mock import patch

	from onedesk.one_hr import request, tell

	told = []

	def heard(name, users, **said):
		told.append((name, [users] if isinstance(users, str) else list(users), said))

	def said(name):
		found = [one for one in told if one[0] == name]
		assert found, (name, [one[0] for one in told])
		return found[-1]

	nadia = frappe.db.get_value("Employee", {"user_id": "nadia@one.test"})
	with patch("onedesk.one.notify.notify", side_effect=heard):
		with as_user("nadia@one.test"):
			asked = frappe.get_doc(
				{"doctype": "Attendance Request", "employee": nadia, "from_date": today(), "to_date": today(), "one_reason": frappe.db.get_value("Attendance Reason", {}), "explanation": "Waiting in for the glazier."}
			).insert()
		_name, users, values = said("Attendance Request Asked")
		assert "mariam@one.test" in users and "nadia@one.test" not in users and values["explanation"] == "Waiting in for the glazier."
		with as_user("mariam@one.test"):
			request.reject(asked.name, "Come in on Thursday instead.")
		_name, users, values = said("Attendance Request Answered")
		assert users == ["nadia@one.test"] and values["note"] == "Mariam Saleh: Come in on Thursday instead.", values

		letter = frappe.get_doc({"doctype": "Employee Letter", "employee": nadia, "kind": frappe.get_meta("Employee Letter").get_field("kind").options.split("\n")[0]})
		letter.flags.ignore_mandatory = True
		with as_user("mariam@one.test"):
			letter.insert()
			letter.submit()
		assert said("Letter Issued")[1] == ["nadia@one.test"]

		frappe.db.set_single_value("HR Settings", "one_ai_grievances", 0)
		with as_user("nadia@one.test"):
			frappe.get_doc({"doctype": "Employee Grievance", "subject": "Parking", "raised_by": nadia, "grievance_against_party": "Department", "grievance_against": frappe.db.get_value("Department", {}), "grievance_type": frappe.db.get_value("Grievance Type", {}), "description": "Nowhere to park."}).insert(ignore_mandatory=True)
		assert "mariam@one.test" in said("Grievance Raised")[1]

		tell.passkey_reset_asked(nadia, registered="iPhone", asking="Pixel", address="10.0.0.1", why="Dropped it")
		assert "mariam@one.test" in said("Passkey Reset Asked")[1]
		with as_user("mariam@one.test"):
			tell.passkey_reset_done(nadia)
		assert said("Passkey Reset Done")[1] == ["nadia@one.test"]

		interview = frappe.copy_doc(frappe.get_doc("Interview", frappe.db.get_value("Interview", {})))
		interview.scheduled_on = add_days(today(), 3)
		interview.insert(ignore_permissions=True)
		_name, users, values = said("Interview Scheduled")
		assert users and values["applicant"], values

		employee = frappe.get_doc("Employee", nadia)
		kind = frappe.get_meta("Employee Document").get_field("document_type").options
		permit = frappe.db.get_value(kind, {}) or frappe.get_doc({"doctype": kind, "identification_document_type": "Work Permit"}).insert(ignore_permissions=True).name
		employee.append("one_documents", {"document_type": permit, "number": "WP-1", "expires_on": add_days(today(), 30)})
		employee.save(ignore_permissions=True)
		tell.documents_expiring()
		_name, users, values = said("Document Expiring")
		assert "nadia@one.test" in users and "mariam@one.test" in users and values["number"] == "WP-1", values

		users = frappe.get_all("Employee", filters={"user_id": ["is", "set"]}, pluck="name")
		leave = frappe.get_doc("Leave Application", frappe.db.get_value("Leave Application", {"docstatus": 1, "employee": ["in", users]}))
		leave.one_note, leave.one_decided_by = "Enjoy it.", "mariam@one.test"
		with as_user("mariam@one.test"):
			leave.answered("Approved")
		assert said("Leave Answered")[2]["note"] == "Mariam Saleh: Enjoy it.", said("Leave Answered")


@check
def onehr_tells_what_the_second_pass_found():
	"""Nadia's leave with no approver reaches HR, and the approver named later
	hears then; her grievance resolved reaches her; a contract a month from
	its end reaches HR; a requisition and a referral reach HR and their
	answers reach whoever asked; a day the shift marked absent reaches her; an
	interview's applicant is mailed when it is."""
	from unittest.mock import patch

	from onedesk.one_hr import tell

	told = []

	def heard(name, users, **said):
		told.append((name, [users] if isinstance(users, str) else list(users), said))

	def said(name):
		found = [one for one in told if one[0] == name]
		assert found, (name, [one[0] for one in told])
		return found[-1]

	nadia = frappe.db.get_value("Employee", {"user_id": "nadia@one.test"})
	with patch("onedesk.one.notify.notify", side_effect=heard):
		leave = frappe.get_doc("Leave Application", frappe.db.get_value("Leave Application", {"employee": nadia}))
		leave = frappe.copy_doc(leave)
		leave.leave_approver, leave.status = None, "Open"
		leave.from_date = leave.to_date = add_days(today(), 40)
		leave.half_day = 0
		leave.flags.ignore_validate = True
		leave.insert(ignore_permissions=True, ignore_mandatory=True)
		assert "mariam@one.test" in said("Leave Asked")[1], said("Leave Asked")
		told.clear()
		leave.leave_approver = "samir@one.test"
		leave.save(ignore_permissions=True)
		assert said("Leave Asked")[1] == ["samir@one.test"]

		frappe.db.set_single_value("HR Settings", "one_ai_grievances", 0)
		with as_user("nadia@one.test"):
			grievance = frappe.get_doc({"doctype": "Employee Grievance", "subject": "Parking", "raised_by": nadia, "grievance_against_party": "Department", "grievance_against": frappe.db.get_value("Department", {}), "grievance_type": frappe.db.get_value("Grievance Type", {}), "description": "Nowhere to park."}).insert(ignore_mandatory=True)
		grievance.status, grievance.resolution_detail = "Resolved", "Two bays are yours now."
		with as_user("mariam@one.test"):
			grievance.save(ignore_permissions=True)
		_name, users, values = said("Grievance Answered")
		assert users == ["nadia@one.test"] and values["note"] == "Two bays are yours now.", values

		frappe.db.set_value("Employee", nadia, "contract_end_date", add_days(today(), 30))
		tell.endings()
		assert "mariam@one.test" in said("Contract Ending")[1]

		with as_user("nadia@one.test"):
			wanted = frappe.get_doc({"doctype": "Job Requisition", "designation": frappe.db.get_value("Designation", {}), "requested_by": nadia, "no_of_positions": 2, "expected_compensation": 1, "posting_date": today(), "description": "Two fitters."}).insert(ignore_permissions=True, ignore_mandatory=True)
		assert "mariam@one.test" in said("Job Requisition Asked")[1]
		with as_user("mariam@one.test"):
			wanted.status = "Open & Approved"
			wanted.save(ignore_permissions=True)
		assert said("Job Requisition Answered")[1] == ["nadia@one.test"]

		with as_user("nadia@one.test"):
			referred = frappe.get_doc({"doctype": "Employee Referral", "first_name": "Rami", "last_name": "Aziz", "email": "rami@example.com", "referrer": nadia, "date": today()}).insert(ignore_permissions=True, ignore_mandatory=True)
		assert "mariam@one.test" in said("Referral Received")[1]
		applicant = frappe.get_doc("Job Applicant", frappe.db.get_value("Job Applicant", {}))
		applicant.employee_referral, applicant.status = referred.name, "Accepted"
		with as_user("mariam@one.test"):
			applicant.save(ignore_permissions=True)
		assert said("Referral Answered")[1] == ["nadia@one.test"]

		absent = frappe._dict(doctype="Attendance", name="ATT-X", status="Absent", employee=nadia, shift="Day", attendance_date=today())
		tell.marked_absent(absent)
		assert said("Marked Absent")[1] == ["nadia@one.test"]

	with patch("frappe.sendmail") as sent:
		interview = frappe.copy_doc(frappe.get_doc("Interview", frappe.db.get_value("Interview", {})))
		interview.scheduled_on = add_days(today(), 3)
		interview.insert(ignore_permissions=True)
	assert any("interview" in call.kwargs["subject"].lower() for call in sent.call_args_list), "the applicant is mailed"


@check
def onehr_home_tells_everybody_their_day():
	"""Mariam's Home: the headcount as Employee counts it, last month's
	payroll as its slips add up, Ravi's shift and Nadia's attendance request
	waiting on her, Yousef's flagged check-in, and every row of the directory
	opening something that exists. Nadia's Home: her own request waiting and
	the leave she has left, and no story, which is HR's to read."""
	from onedesk.one_hr import home, story

	with as_user("mariam@one.test"):
		told = story.read()
		said = home.read()
	cards = told["cards"]
	assert set(cards) >= {"headcount", "joined", "present", "away", "payroll", "openings"}, set(cards)
	company = frappe.defaults.get_global_default("company")
	here = frappe.db.count("Employee", {"company": company, "status": "Active"})
	assert cards["headcount"]["value"] == here, (cards["headcount"], here)
	last = get_first_day(add_months(today(), -1))
	paid = sum(flt(one) for one in frappe.get_all("Salary Slip", filters={"company": company, "docstatus": 1, "start_date": last}, pluck="base_net_pay"))
	assert abs(cards["payroll"]["value"] - paid) < 1, (cards["payroll"], paid)
	waiting = {(one["doctype"], one["who"]) for one in said["needs"]["approve"]["rows"]}
	assert ("Attendance Request", "Nadia Khoury") in waiting, waiting
	assert said["needs"]["flagged"]["count"] >= 1
	assert [one["step"] for one in told["hiring"]["funnel"]] == list(story.FUNNEL)
	for row in said["everything"]:
		kind = "DocType" if row["kind"] == "List" else row["kind"]
		assert frappe.db.exists(kind, row["target"]), row
	with as_user("nadia@one.test"):
		assert story.read() is None
		said = home.read()
	assert not said["hr"] and said["needs"]["mine"]["count"] >= 1
	assert {one["leave_type"] for one in said["needs"]["leave"]}, said["needs"]["leave"]


@check
def onehr_deleting_an_interviews_sound_is_an_ability():
	"""Delete an Interview's Sound starts with the HR Manager: anybody else
	deleting a recording's sound is refused."""
	from onedesk.one import rights
	from onedesk.one_hr import hiring

	assert rights.held("HR Settings", "hr_sound", "mariam@one.test")
	assert not rights.held("HR Settings", "hr_sound", "samir@one.test")
	sound = frappe._dict(attached_to_doctype="Interview Recording")
	with as_user("samir@one.test"):
		try:
			hiring.keep_sound(sound)
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("somebody without the ability deleted an interview's sound")
	with as_user("mariam@one.test"):
		hiring.keep_sound(sound)


@check
def onehr_riyadh_keeps_its_own_people():
	"""Sahara Glass Saudi's supervisor is its own: his weekend is Friday and
	Saturday, his leave says what is left, Home read in Riyadh counts him in
	riyals, and Rania, limited to the Dubai company, does not see him."""
	from onedesk.one_hr import heads, story

	ahmed = frappe.db.get_value("Employee", {"company": "Sahara Glass Saudi"}, "name")
	assert ahmed, "the Riyadh company has an employee"
	weekend = {getdate(day).weekday() for day in frappe.get_all("Holiday", filters={"parent": frappe.db.get_value("Company", "Sahara Glass Saudi", "default_holiday_list"), "weekly_off": 1}, pluck="holiday_date")}
	assert weekend == {4, 5}, weekend
	leave = frappe.get_doc("Leave Application", frappe.db.get_value("Leave Application", {"employee": ahmed, "docstatus": 1}))
	assert heads.leave_left(leave)["value"], "a leave says what is left"
	with as_user("mariam@one.test"):
		frappe.defaults.set_user_default("company", "Sahara Glass Saudi")
		try:
			said = story.read()
		finally:
			frappe.defaults.set_user_default("company", COMPANY)
	assert said["currency"] == "SAR" and said["cards"]["headcount"]["value"] == 1, said["cards"].get("headcount")
	with as_user("rania@one.test"):
		assert not frappe.has_permission("Employee", "read", ahmed)
