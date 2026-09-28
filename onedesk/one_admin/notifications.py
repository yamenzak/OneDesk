"""What OneAdmin tells the operator, as notification types (one/notify.py).

Sent by `tell.py`, to everybody holding One Operator and to nobody else
(`roles`), so the types are not offered to a workspace's own people either.
"""

from frappe import _lt

TYPES = [
	{
		"name": _lt("Job Failed"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt(
			"When a workspace job stops on a step: building, suspending, restoring, archiving or deleting files."
		),
		"to": _lt("The operators"),
		"subject": _lt("{what}"),
		"message": _lt("At: {step}<br>{error}"),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("Signup Not Built"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When somebody has paid for a workspace and it could not be made."),
		"to": _lt("The operators"),
		"subject": _lt("{workspace} paid and has no workspace"),
		"message": _lt("{email}<br>{error}"),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("New Signup"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When somebody pays for a new workspace."),
		"to": _lt("The operators"),
		"subject": _lt("{workspace} signed up"),
		"message": _lt("{email}{plan}"),
		"push_default": True,
	},
	{
		"name": _lt("Workspace Owing"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When a workspace falls overdue, or is suspended for not paying."),
		"to": _lt("The operators"),
		"subject": _lt("{workspace}: {state}"),
		"message": _lt("{why}"),
		"email_default": True,
	},
	{
		"name": _lt("Domains Waiting"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt(
			"Every morning, the domains that have waited a day for their DNS or stopped working. Not sent when there are none."
		),
		"to": _lt("The operators"),
		"subject": _lt("{count} domains need a look"),
		"message": _lt("{domains}"),
		"email_default": True,
	},
]
