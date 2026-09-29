"""What OneAdmin tells, as notification types (one/notify.py).

Sent by `tell.py`. Most go to everybody holding One Operator and to nobody
else. The last four are mailed to a workspace's owner (`outside`): when it is
ready, and when it is suspended, archived or restored, since a new site has
no way to reach them yet and a suspended one cannot. All are offered only to
operators (`roles`), who may reword them.
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
		"message": _lt("It stopped on step {number} of {steps}: {step}.<br>{error}"),
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
		"message": _lt(
			"{email} paid, and making their workspace stopped because: {error}<br><br>Build Workspace on the "
			"signup tries again. They have been told it is delayed."
		),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("Workspace Delayed"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When somebody has paid for a workspace and it could not be made yet."),
		"to": _lt("The person who signed up"),
		"subject": _lt("{workspace} is delayed"),
		"message": _lt(
			"We have your payment for {workspace}. Setting it up hit a problem on our side, and we are on it."
			"<br><br>We will write again when it is ready. You do not need to do anything. If you have a "
			"question, reply to this mail."
		),
		"outside": True,
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
	{
		"name": _lt("Workspace Ready"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When a new workspace has been built and is ready to use."),
		"to": _lt("The workspace's owner"),
		"subject": _lt("{workspace} is ready"),
		"message": _lt(
			"{workspace} is ready at {address}.<br><br>We have sent you a second email with a link to choose "
			"your password. It works for 7 days. If it has not arrived, reply to this mail."
		),
		"outside": True,
	},
	{
		"name": _lt("Workspace Suspended"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When a workspace is suspended for not paying."),
		"to": _lt("The workspace's owner"),
		"subject": _lt("{workspace} is suspended"),
		"message": _lt(
			"Payment for {workspace} did not arrive, so it is suspended: nobody can sign in, and nothing in it "
			"is touched.<br><br>Pay the invoice we sent you and it comes straight back. Unless it is paid, it "
			"is archived on {date}. If something is wrong, reply to this mail."
		),
		"outside": True,
	},
	{
		"name": _lt("Workspace Archived"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When a suspended workspace is archived for not paying."),
		"to": _lt("The workspace's owner"),
		"subject": _lt("{workspace} is archived"),
		"message": _lt(
			"{workspace} was suspended and not paid for, so it has been taken down. A backup is kept, and your "
			"files are where they were.<br><br>On {date} the workspace and its files are deleted, and that "
			"cannot be undone. To have it restored before then, pay the invoice we sent you and reply to this "
			"mail."
		),
		"outside": True,
	},
	{
		"name": _lt("Workspace Restored"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When a suspended workspace is paid for and opens again."),
		"to": _lt("The workspace's owner"),
		"subject": _lt("{workspace} is open again"),
		"message": _lt("Payment arrived, and {workspace} is open again at {address}. Thank you."),
		"outside": True,
	},
]
