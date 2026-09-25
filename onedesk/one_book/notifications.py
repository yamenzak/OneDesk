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
		"about": _lt(
			"Somebody asked for the credit controllers to be told a customer is over their limit. Sent to them."
		),
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
		"about": _lt("ERPNext made next year's fiscal year by itself, to be looked over. Sent to Accounts."),
		"words": "ERPNext",
		"rule": "Notification for new fiscal year",
		"email_default": True,
	},
	# What ERPNext mails itself, listed so everything sent is on one page.
	{
		"name": _lt("Statement of Accounts"),
		"app": "OneBook",
		"about": _lt("Statements mailed to customers on a schedule, in the words set on each statement run."),
		"mailed_by": "ERPNext",
		"outside": True,
	},
]
