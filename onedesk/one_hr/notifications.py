"""What OneHR tells people, as notification types (one/notify.py).

Each is sent through `notify.notify()` by the module named in its comment.
The slots in `{braces}` are what the sender fills in; an administrator who
edits a text uses the same names, as `{{ employee }}`. `roles` is who can
receive a type, so only they are asked how they want it (Notifications, under You in Settings).
"""

from frappe import _lt

TYPES = [
	# one/settings.py: a person changed where they live or who to call.
	{
		"name": _lt("Employee Details Changed"),
		"app": "OneHR",
		"roles": ("HR Manager",),
		"about": _lt("When an employee changes their address or emergency contact in their profile."),
		"to": _lt("HR managers"),
		"subject": _lt("{employee} changed their {what}"),
	},
	# doctype/employee_letter: an employee asks HR for a letter.
	{
		"name": _lt("Letter Requested"),
		"app": "OneHR",
		"roles": ("HR Manager",),
		"about": _lt("When an employee asks HR for a letter."),
		"to": _lt("HR managers"),
		"subject": _lt("{employee} asked for a {kind}"),
		"email_default": True,
	},
	# ai_grievance: OneAI read a grievance as sensitive or urgent.
	{
		"name": _lt("Sensitive Grievance"),
		"app": "OneHR",
		"roles": ("HR Manager",),
		"about": _lt("When OneAI reads a new grievance as sensitive."),
		"to": _lt("The people trusted with grievances"),
		"oneai": True,
		"subject": _lt("A sensitive grievance was raised"),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("Urgent Grievance"),
		"app": "OneHR",
		"roles": ("HR Manager",),
		"about": _lt("When OneAI reads a new grievance as urgent."),
		"to": _lt("The people trusted with grievances"),
		"oneai": True,
		"subject": _lt("An urgent grievance was raised"),
		"email_default": True,
		"push_default": True,
	},
	# review: a check-in was flagged for a person to judge.
	{
		"name": _lt("Check-in Flagged"),
		"app": "OneHR",
		"roles": ("HR User", "HR Manager"),
		"about": _lt("When a check-in looks wrong and waits for somebody to accept or reject it."),
		"to": _lt("Its reviewers"),
		"subject": _lt("{employee}'s check-in needs a look"),
		"message": "{reasons}",
		"push_default": True,
	},
	# setup: a shift has check-ins but writes no attendance from them.
	{
		"name": _lt("Shift Not Reading Check-ins"),
		"app": "OneHR",
		"roles": ("HR Manager",),
		"about": _lt("When a shift has check-ins but writes no attendance from them. At most once a week."),
		"to": _lt("HR managers"),
		"subject": _lt("Check-ins on {shift} are not becoming attendance"),
		"message": _lt(
			"This shift has check-ins but does not read them, so no Attendance is being written and every "
			"count that reads Attendance is empty. Open the shift and press Read Check-ins."
		),
		"email_default": True,
	},
	# leaving: somebody's leaving date passed and they could not be marked Left.
	{
		"name": _lt("Could Not Mark Left"),
		"app": "OneHR",
		"roles": ("HR User", "HR Manager"),
		"about": _lt("When an employee's leaving date passes and their status could not be set to Left."),
		"to": _lt("HR"),
		"subject": _lt("{employee} could not be marked Left"),
		"message": _lt(
			"Their passkey and shift assignments have been ended, but the status is still Active: {why}"
		),
		"email_default": True,
	},
	# closing: a check-in left open was closed at the shift's end.
	{
		"name": _lt("Check-in Closed for You"),
		"app": "OneHR",
		"roles": ("Employee",),
		"about": _lt(
			"When you checked in, never checked out, and One checked you out at the end of the shift."
		),
		"to": _lt("The employee"),
		"subject": _lt("Your check-in was closed at the end of your shift"),
		"message": _lt(
			"You checked in but never checked out, so a check out was written for you at the shift end. "
			"Tell HR if that is wrong."
		),
		"push_default": True,
	},
	# healing: a new place or network to check in from was added by itself.
	{
		"name": _lt("Check-in Place Proposed"),
		"app": "OneHR",
		"roles": ("HR Manager",),
		"about": _lt("When One adds a network or place people check in from, because they keep using it."),
		"to": _lt("HR managers"),
		"subject": _lt("A new check-in network or location was proposed"),
	},
	# tell: HRMS's approval moments, told here rather than to its phone app.
	{
		"name": _lt("Leave Asked"),
		"app": "OneHR",
		"roles": ("Leave Approver", "HR User", "HR Manager"),
		"about": _lt("When somebody applies for leave."),
		"to": _lt("Their leave approver"),
		"subject": _lt("{employee} asked for {days} days of {leave_type}"),
		"message": _lt("From {from_date} to {to_date}."),
		"email_default": True,
		"push_default": True,
		"replaces": (("HR Settings", "send_leave_notification"),),
	},
	{
		"name": _lt("Leave Answered"),
		"app": "OneHR",
		"roles": ("Employee",),
		"about": _lt("When your leave application is approved, rejected or cancelled."),
		"to": _lt("The employee"),
		"subject": _lt("Your {leave_type} from {from_date} to {to_date} was {status}"),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("Expense Claim Asked"),
		"app": "OneHR",
		"roles": ("Expense Approver", "HR User", "HR Manager"),
		"about": _lt("When somebody claims an expense."),
		"to": _lt("Their expense approver"),
		"subject": _lt("{employee} claimed {amount}"),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("Expense Claim Answered"),
		"app": "OneHR",
		"roles": ("Employee",),
		"about": _lt("When your expense claim is approved or rejected."),
		"to": _lt("The employee"),
		"subject": _lt("Your expense claim for {amount} was {status}"),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("Shift Asked"),
		"app": "OneHR",
		"about": _lt("When somebody asks for a shift."),
		"to": _lt("Their shift approver"),
		"subject": _lt("{employee} asked for {shift} from {from_date} to {to_date}"),
		"push_default": True,
	},
	{
		"name": _lt("Shift Answered"),
		"app": "OneHR",
		"roles": ("Employee",),
		"about": _lt("When your shift request is approved or rejected."),
		"to": _lt("The employee"),
		"subject": _lt("Your request for {shift} from {from_date} was {status}"),
		"push_default": True,
	},
	# tell: HRMS's reminders, which it mailed on its own schedule.
	{
		"name": _lt("Birthday"),
		"app": "OneHR",
		"roles": ("Employee",),
		"about": _lt("On the morning of a colleague's birthday."),
		"to": _lt("Everybody else at their company"),
		"subject": _lt("It is {employee}'s birthday today"),
		"message": _lt("Wish them a happy birthday."),
		"replaces": (("HR Settings", "send_birthday_reminders"),),
		"starts_as": ("HR Settings", "send_birthday_reminders"),
	},
	{
		"name": _lt("Work Anniversary"),
		"app": "OneHR",
		"roles": ("Employee",),
		"about": _lt("On the morning of a colleague's work anniversary."),
		"to": _lt("Everybody else at their company"),
		"subject": _lt("It is {employee}'s work anniversary"),
		"message": _lt("They joined on {joined}, {years} years ago today."),
		"replaces": (("HR Settings", "send_work_anniversary_reminders"),),
		"starts_as": ("HR Settings", "send_work_anniversary_reminders"),
	},
	{
		"name": _lt("Holidays Coming Up"),
		"app": "OneHR",
		"roles": ("Employee",),
		"about": _lt("Every week or month, as HR Settings says, when you have holidays coming up."),
		"to": _lt("Each employee"),
		"subject": _lt("You have holidays coming up"),
		"message": "{holidays}",
		"email_default": True,
		"replaces": (("HR Settings", "send_holiday_reminders"),),
		"starts_as": ("HR Settings", "send_holiday_reminders"),
	},
	{
		"name": _lt("Interview Soon"),
		"app": "OneHR",
		"roles": ("Interviewer", "HR User", "HR Manager"),
		"about": _lt("Shortly before an interview you are on, as long before as HR Settings says."),
		"to": _lt("Its interviewers"),
		"subject": _lt("Interview with {applicant} at {when}"),
		"email_default": True,
		"push_default": True,
		"replaces": (("HR Settings", "send_interview_reminder"),),
		"starts_as": ("HR Settings", "send_interview_reminder"),
	},
	{
		"name": _lt("Interview Soon, to the Applicant"),
		"app": "OneHR",
		"about": _lt("Shortly before an interview, as long before as HR Settings says."),
		"to": _lt("The applicant"),
		"subject": _lt("Your interview is at {when}"),
		"message": _lt("Dear {applicant}, this is a reminder of your interview at {when}."),
		"outside": True,
		"starts_as": ("HR Settings", "send_interview_reminder"),
	},
	{
		"name": _lt("Interview Feedback Due"),
		"app": "OneHR",
		"roles": ("Interviewer", "HR User", "HR Manager"),
		"about": _lt("Every day after an interview, until your feedback on it is in."),
		"to": _lt("Each interviewer who owes it"),
		"subject": _lt("Your feedback on {applicant}'s interview is due"),
		"message": _lt("The interview was on {when}."),
		"email_default": True,
		"replaces": (("HR Settings", "send_interview_feedback_reminder"),),
		"starts_as": ("HR Settings", "send_interview_feedback_reminder"),
	},
	{
		"name": _lt("Interview Moved"),
		"app": "OneHR",
		"roles": ("Interviewer", "HR User", "HR Manager"),
		"about": _lt("When an interview you are on moves to another time."),
		"to": _lt("Its interviewers"),
		"subject": _lt("The interview with {applicant} moved to {when}"),
		"message": _lt("It was at {was}."),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("Interview Moved, to the Applicant"),
		"app": "OneHR",
		"about": _lt("When an interview moves to another time."),
		"to": _lt("The applicant"),
		"subject": _lt("Your interview has moved to {when}"),
		"message": _lt("Dear {applicant}, your interview has moved from {was} to {when}."),
		"outside": True,
	},
	# HRMS's own rules, carried to the bell in their words (one/rules.py).
	{
		"name": _lt("Training Scheduled"),
		"app": "OneHR",
		"roles": ("Employee",),
		"about": _lt("When a training event you attend is scheduled."),
		"to": _lt("Everybody attending"),
		"words": "HRMS",
		"rule": "Training Scheduled",
		"email_default": True,
	},
	{
		"name": _lt("Exit Interview Scheduled"),
		"app": "OneHR",
		"roles": ("Employee",),
		"about": _lt("The day before your exit interview."),
		"to": _lt("The employee leaving"),
		"words": "HRMS",
		"rule": "Exit Interview Scheduled",
		"email_default": True,
	},
	# What HRMS mails itself, listed so everything sent is on one page.
	{
		"name": _lt("Payslip by Email"),
		"app": "OneHR",
		"about": _lt("When a payslip is submitted, with the payslip as a PDF."),
		"to": _lt("Its employee"),
		"mailed_by": "HRMS",
		"switch": ("Payroll Settings", "email_salary_slip_to_employee"),
	},
	{
		"name": _lt("Exit Questionnaire"),
		"app": "OneHR",
		"about": _lt("When somebody is leaving, in the template HR Settings names."),
		"to": _lt("The employee leaving"),
		"mailed_by": "HRMS",
		"outside": True,
	},
	{
		"name": _lt("Earned Leave Not Allocated"),
		"app": "OneHR",
		"about": _lt("When the nightly job cannot allocate earned leave."),
		"to": _lt("HR managers"),
		"mailed_by": "HRMS",
	},
]
