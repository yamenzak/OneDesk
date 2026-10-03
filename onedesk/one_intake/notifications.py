"""What Intake tells people, as notification types (one/notify.py).

All of them come from OneAI, and go to the person it reads for.
"""

from frappe import _lt

TYPES = [
	# inbox.tell: what OneAI read and could not settle alone.
	{
		"name": _lt("Intake Waiting"),
		"app": "OneIntake",
		"about": _lt("When a document read for you needs review."),
		"to": _lt("The person it reads for"),
		"subject": _lt("{count} items in {title} need review."),
		"push_default": True,
	},
	{
		"name": _lt("Intake Waiting, One Thing"),
		"app": "OneIntake",
		"about": _lt("When a document read for you has one item to review."),
		"to": _lt("The person it reads for"),
		"follows": "Intake Waiting",
		"subject": _lt("1 item in {title} needs review."),
		"push_default": True,
	},
	# digest: the week, on Mondays.
	{
		"name": _lt("Intake Weekly"),
		"app": "OneIntake",
		"about": _lt("Once a week, with what arrived, what OneAI handled and what's waiting."),
		"to": _lt("The person it reads for"),
		"subject": _lt("{arrived} documents this week, {handled} handled, {waiting} waiting"),
		"message": "{week}",
		"email_default": True,
	},
	# planning: something arrived for a task somebody had already closed.
	{
		"name": _lt("Arrived After Closing"),
		"app": "OneIntake",
		"about": _lt("When a document arrives for a task you already closed. The task stays closed."),
		"to": _lt("Whoever closed the task"),
		"subject": _lt("{title} arrived after you closed this task."),
	},
	# filing: a document reads as phishing.
	{
		"name": _lt("Phishing"),
		"app": "OneIntake",
		"about": _lt("When a document looks like phishing."),
		"to": _lt("The person it reads for, and whoever put the file there"),
		"subject": _lt("{title} may be phishing. Don't pay, reply or open its links."),
		"email_default": True,
		"push_default": True,
	},
	# settings: an administrator changed what OneAI may do with money.
	{
		"name": _lt("OneIntake Changed"),
		"app": "OneIntake",
		"about": _lt("When another administrator changes e-invoice submission, household, the auditor or the confidence floor."),
		"to": _lt("Every other administrator"),
		"subject": _lt("{by} changed OneIntake: {what}"),
		"message": _lt("{by} changed OneIntake settings ({what}). This applies to all new documents."),
	},
]
