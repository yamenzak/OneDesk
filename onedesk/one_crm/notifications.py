"""What OneCRM sends, as notification types (one/notify.py).

One, and ERPNext mails it: a campaign's mails to its leads, in the Email
Templates its schedule names. Listed so everything sent is on one page.
"""

from frappe import _lt

TYPES = [
	{
		"name": _lt("Email Campaign"),
		"app": "OneCRM",
		"about": _lt("On a campaign's schedule, in the templates it names."),
		"to": _lt("The campaign's leads and contacts"),
		"mailed_by": "ERPNext",
		"outside": True,
	},
]
