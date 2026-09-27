"""What OneBook tells people, as notification types (one/notify.py).

All three are ERPNext's: one it mailed and now tells here (tell.py), one of
its rules carried to the bell, and one it mails to customers itself.
"""

from frappe import _lt

TYPES = [
	# tell: ERPNext's "send to credit controller" from the credit limit dialog.
	{
		"name": _lt("Credit Limit Crossed"),
		"app": "OneBook",
		"roles": ("Accounts Manager", "Accounts User"),
		"about": _lt("When somebody flags a customer who is over their credit limit."),
		"to": _lt("Accounts"),
		"subject": _lt("{customer} is over their credit limit"),
		"message": _lt("They owe {outstanding} against a limit of {limit}."),
		"email_default": True,
		"push_default": True,
	},
	# ERPNext's own rule, carried to the bell in its words (one/rules.py).
	{
		"name": _lt("New Fiscal Year"),
		"app": "OneBook",
		"roles": ("Accounts Manager", "Accounts User"),
		"about": _lt("When ERPNext makes next year's fiscal year on its own, so somebody checks it."),
		"to": _lt("Accounts"),
		"words": "ERPNext",
		"rule": "Notification for new fiscal year",
		"email_default": True,
	},
	# What ERPNext mails itself, listed so everything sent is on one page.
	{
		"name": _lt("Statement of Accounts"),
		"app": "OneBook",
		"about": _lt("On each statement run's schedule, in the words set on the run."),
		"to": _lt("Each customer on the run"),
		"mailed_by": "ERPNext",
		"outside": True,
	},
]
