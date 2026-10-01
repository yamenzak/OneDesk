"""What OneAdmin tells, as notification types (one/notify.py).

Sent by `tell.py`. Most go to everybody holding One Operator and to nobody
else. The outside ones are mailed to a workspace's owner (`outside`): when it is
ready, and when it is suspended, archived or restored, since a new site has
no way to reach them yet and a suspended one cannot; and to somebody who signed
up, when it is delayed or when they never paid. All are offered only to
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
		"name": _lt("Finish Signing Up"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When somebody filled in the signup page a day ago and has not paid. Sent once."),
		"to": _lt("The person who signed up"),
		"subject": _lt("{workspace} is waiting for you"),
		"message": _lt(
			"You started setting up {workspace} on One and did not finish paying. The name is kept for you "
			'for a week.<br><br><a href="{link}">Finish signing up</a><br><br>If you changed your mind, '
			"there is nothing to do. If something went wrong, reply to this mail."
		),
		"outside": True,
	},
	{
		"name": _lt("Sign-in Link"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt(
			"When somebody asks to sign in to their One account by email. It cannot be turned off, or nobody could."
		),
		"to": _lt("The account holder"),
		"subject": _lt("Your sign-in link for One"),
		"message": _lt(
			'<a href="{link}">Sign in to your One account</a><br><br>The link works once, for {minutes} '
			"minutes. If you did not ask for it, you can ignore this mail."
		),
		"outside": True,
		"required": True,
	},
	{
		"name": _lt("Workspace Moved to You"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When a workspace's administrator makes somebody the one who pays for it."),
		"to": _lt("The new account holder"),
		"subject": _lt("{workspace} is now in your One account"),
		"message": _lt(
			"{by} made you the one who pays for {workspace}. Its invoices and notices about paying come to "
			'you from now on.<br><br><a href="{account}">Open your One account</a> and sign in with this '
			"address. If this is a mistake, reply to this mail."
		),
		"outside": True,
	},
	{
		"name": _lt("Workspace Moved Away"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When a workspace's administrator moves it to somebody else's account."),
		"to": _lt("The previous account holder"),
		"subject": _lt("{workspace} has left your One account"),
		"message": _lt(
			"{by} made somebody else the one who pays for {workspace}. You will get no more invoices for "
			"it. If this is a mistake, reply to this mail."
		),
		"outside": True,
	},
	{
		"name": _lt("Confirm Your New Email"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When an account holder asks to change their address. It cannot be turned off."),
		"to": _lt("The new address"),
		"subject": _lt("Confirm your new address for One"),
		"message": _lt(
			'<a href="{link}">Use this address for my One account</a><br><br>The link works once, for '
			"{minutes} minutes. If you did not ask for this, you can ignore this mail."
		),
		"outside": True,
		"required": True,
	},
	{
		"name": _lt("Account Email Changed"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When an account holder's address has changed. It cannot be turned off."),
		"to": _lt("The previous address"),
		"subject": _lt("Your One account has a new address"),
		"message": _lt(
			"Your One account now signs in with {address}, and its invoices go there. If you did not do "
			"this, reply to this mail at once."
		),
		"outside": True,
		"required": True,
	},
	{
		"name": _lt("Paid While Archived"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When a payment arrives for a workspace whose site has already been archived."),
		"to": _lt("The operators"),
		"subject": _lt("{workspace} paid, and it is {state}"),
		"message": _lt(
			"A payment arrived for {workspace}, whose site is gone. Rebuild it from its backup, or refund the "
			"payment in Stripe."
		),
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
		"name": _lt("Settings Changed"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt(
			"When another operator changes OneAdmin Settings. A key is only ever said to have changed."
		),
		"to": _lt("The other operators"),
		"subject": _lt("{who} changed OneAdmin Settings"),
		"message": _lt("{changes}"),
		"email_default": True,
	},
	{
		"name": _lt("Model Withdrawn"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When the nightly sync takes an offered model off sale, and what now runs instead."),
		"to": _lt("The operators"),
		"subject": _lt("{count} OneAI models were taken off sale"),
		"message": _lt("{models}<br><br>Workspaces that picked them now run on the default."),
		"email_default": True,
	},
	{
		"name": _lt("Workspace Asked to Close"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When the person who pays for a workspace asks for it to be closed."),
		"to": _lt("The operators"),
		"subject": _lt("{workspace} closes on {date}"),
		"message": _lt("{who} asked for it to be closed. It is archived on {date}, and deleted for good on {deleted}."),
		"email_default": True,
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
			"your password. It works for 7 days. If it has not arrived, reply to this mail.<br><br>It is also "
			'in <a href="{account}">your One account</a>, with every other workspace you hold.'
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
		"name": _lt("Workspace Closed"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When a workspace closes on the day its payer asked for."),
		"to": _lt("The workspace's owner"),
		"subject": _lt("{workspace} is closed"),
		"message": _lt(
			"{workspace} is closed, as you asked, and its subscription is cancelled. A backup is kept, and "
			"your files are where they were.<br><br>On {date} the workspace and its files are deleted, and "
			"that cannot be undone. To have it back before then, reply to this mail."
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
