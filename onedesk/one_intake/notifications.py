"""What Intake tells people, as notification types (one/notify.py).

All of them come from OneAI, and go to the person it reads for.
"""

from frappe import _lt

TYPES = [
	# inbox.tell: what OneAI read and could not settle alone.
	{
		"name": _lt("Intake Waiting"),
		"app": "Intake",
		"about": _lt("OneAI read a document and something in it needs you. Sent to the person it reads for."),
		"subject": _lt("{count} things OneAI read in <b>{title}</b> need a look."),
		"push_default": True,
	},
	{
		"name": _lt("Intake Waiting, One Thing"),
		"app": "Intake",
		"about": _lt("The same, when only one thing needs you."),
		"subject": _lt("One thing OneAI read in <b>{title}</b> needs a look."),
		"push_default": True,
	},
	# digest: the week, on Mondays.
	{
		"name": _lt("Intake Weekly"),
		"app": "Intake",
		"about": _lt("Once a week, what arrived for you, what OneAI dealt with, and what still waits."),
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
		"about": _lt("A document arrived for a task you had already closed. The task stays closed."),
		"subject": _lt("<b>{title}</b> arrived after you closed this task."),
	},
	# planning: a supplier asks to be paid somewhere new.
	{
		"name": _lt("New IBAN"),
		"app": "Intake",
		"about": _lt("A known supplier's document asks to be paid to an IBAN we do not have for them."),
		"subject": _lt(
			"<b>{title}</b> asks to be paid to an IBAN we do not have for <b>{supplier}</b>. Check with them by phone before paying."
		),
		"email_default": True,
		"push_default": True,
	},
	# filing: a document reads as phishing.
	{
		"name": _lt("Phishing"),
		"app": "Intake",
		"about": _lt(
			"OneAI thinks a document is phishing. Sent to the person it reads for, and whoever put the file there."
		),
		"subject": _lt("OneAI thinks <b>{title}</b> is phishing. Do not pay, answer or open links in it."),
		"email_default": True,
		"push_default": True,
	},
]
