"""What OneHR tells people, as notification types (one/notify.py).

Each is sent through `notify.notify()` by the module named in its comment.
The slots in `{braces}` are what the sender fills in; an administrator who
edits a text uses the same names, as `{{ employee }}`.
"""

from frappe import _lt

TYPES = [
	# doctype/employee_letter: an employee asks HR for a letter.
	{
		"name": _lt("Letter Requested"),
		"app": "OneHR",
		"about": _lt("An employee asks HR for a letter. Sent to HR Managers."),
		"subject": _lt("{employee} asked for a {kind}"),
		"email_default": True,
	},
	# ai_grievance: OneAI read a grievance as sensitive or urgent.
	{
		"name": _lt("Sensitive Grievance"),
		"app": "OneHR",
		"about": _lt("OneAI read a new grievance as sensitive. Sent to the people trusted with grievances."),
		"subject": _lt("A sensitive grievance was raised"),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("Urgent Grievance"),
		"app": "OneHR",
		"about": _lt("OneAI read a new grievance as urgent. Sent to the people trusted with grievances."),
		"subject": _lt("An urgent grievance was raised"),
		"email_default": True,
		"push_default": True,
	},
	# review: a check-in was flagged for a person to judge.
	{
		"name": _lt("Check-in Flagged"),
		"app": "OneHR",
		"about": _lt(
			"A check-in looked wrong, and waits for somebody to accept or reject it. Sent to its reviewers."
		),
		"subject": _lt("{employee}'s check-in needs a look"),
		"message": "{reasons}",
		"push_default": True,
	},
	# setup: a shift has check-ins but writes no attendance from them.
	{
		"name": _lt("Shift Not Reading Check-ins"),
		"app": "OneHR",
		"about": _lt(
			"A shift has check-ins but writes no attendance from them. Sent to HR Managers, at most weekly."
		),
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
		"about": _lt(
			"An employee's leaving date passed, but their status could not be set to Left. Sent to HR."
		),
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
		"about": _lt(
			"Somebody checked in and never checked out, so One checked them out at the shift's end. Sent to them."
		),
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
		"about": _lt(
			"One added a network or location people check in from, because they kept using it. Sent to HR Managers."
		),
		"subject": _lt("A new check-in network or location was proposed"),
	},
]
