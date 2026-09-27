"""What Intake tells people, as notification types (one/notify.py).

All of them come from OneAI, and go to the person it reads for.
"""

from frappe import _lt

TYPES = [
	# inbox.tell: what OneAI read and could not settle alone.
	{
		"name": _lt("Intake Waiting"),
		"app": "Intake",
		"about": _lt("When OneAI reads a document for you and something in it needs you."),
		"to": _lt("The person it reads for"),
		"oneai": True,
		"subject": _lt("{count} things OneAI read in {title} need a look."),
		"push_default": True,
	},
	{
		"name": _lt("Intake Waiting, One Thing"),
		"app": "Intake",
		"about": _lt("When OneAI reads a document for you and one thing in it needs you."),
		"to": _lt("The person it reads for"),
		"follows": "Intake Waiting",
		"oneai": True,
		"subject": _lt("One thing OneAI read in {title} needs a look."),
		"push_default": True,
	},
	# digest: the week, on Mondays.
	{
		"name": _lt("Intake Weekly"),
		"app": "Intake",
		"about": _lt("Once a week, what arrived for you, what OneAI dealt with, and what still waits."),
		"to": _lt("The person it reads for"),
		"oneai": True,
		"subject": _lt(
			"Your week with OneAI: {arrived} documents, {handled} handled, {waiting} wait for you"
		),
		"message": "{week}",
		"email_default": True,
	},
	# planning: something arrived for a task somebody had already closed.
	{
		"name": _lt("Arrived After Closing"),
		"app": "Intake",
		"about": _lt("When a document arrives for a task you already closed. The task stays closed."),
		"to": _lt("Whoever closed the task"),
		"oneai": True,
		"subject": _lt("{title} arrived after you closed this task."),
	},
	# planning: a supplier asks to be paid somewhere new.
	{
		"name": _lt("New IBAN"),
		"app": "Intake",
		"about": _lt("When a known supplier's document asks to be paid to an IBAN we do not have for them."),
		"to": _lt("The person it reads for"),
		"oneai": True,
		"subject": _lt(
			"{title} asks to be paid to an IBAN we do not have for {supplier}. Check with them by phone before paying."
		),
		"email_default": True,
		"push_default": True,
	},
	# filing: a document reads as phishing.
	{
		"name": _lt("Phishing"),
		"app": "Intake",
		"about": _lt("When OneAI thinks a document is phishing."),
		"to": _lt("The person it reads for, and whoever put the file there"),
		"oneai": True,
		"subject": _lt("OneAI thinks {title} is phishing. Do not pay, answer or open links in it."),
		"email_default": True,
		"push_default": True,
	},
]
