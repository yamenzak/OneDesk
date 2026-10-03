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
		"about": _lt("When a job to build, suspend, restore, archive or delete a workspace fails."),
		"to": _lt("The operators"),
		"subject": _lt("{what}"),
		"message": _lt("Failed at step {number} of {steps}, {step}.<br>{error}"),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("Signup Not Built"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When a paid workspace can't be built."),
		"to": _lt("The operators"),
		"subject": _lt("{workspace} paid and has no workspace"),
		"message": _lt(
			"{email} paid, but their workspace couldn't be built.<br>{error}<br><br>Build Workspace on the "
			"signup tries again. They've been notified of the delay."
		),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("Workspace Delayed"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When a paid workspace can't be built yet."),
		"to": _lt("The person who signed up"),
		"subject": _lt("{workspace} is delayed"),
		"message": _lt(
			"We have your payment for {workspace}, but setup hit a problem on our side. We're working on it."
			"<br><br>We'll email you when it's ready. You don't need to do anything. If you have a "
			"question, reply to this email."
		),
		"outside": True,
	},
	{
		"name": _lt("Finish Signing Up"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When someone filled in the signup page a day ago and hasn't paid. Sent once."),
		"to": _lt("The person who signed up"),
		"subject": _lt("{workspace} is waiting for you"),
		"message": _lt(
			"You started setting up {workspace} on One but didn't finish paying. The name is held for you "
			'for a week.<br><br><a href="{link}">Finish signing up</a><br><br>If you changed your mind, '
			"there's nothing to do. If something went wrong, reply to this email."
		),
		"outside": True,
	},
	{
		"name": _lt("Sign-in Link"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When someone asks to sign in to their One account by email. It can't be turned off."),
		"to": _lt("The account holder"),
		"subject": _lt("Your sign-in link for One"),
		"message": _lt(
			'<a href="{link}">Sign in to your One account</a><br><br>The link works once, for {minutes} '
			"minutes. If you didn't ask for it, you can ignore this email."
		),
		"outside": True,
		"required": True,
	},
	{
		"name": _lt("Workspace Moved to You"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When a workspace's administrator makes someone else its billing contact."),
		"to": _lt("The new account holder"),
		"subject": _lt("{workspace} is now in your One account"),
		"message": _lt(
			"{by} made you the billing contact for {workspace}. Its invoices and payment notices now come "
			'to you.<br><br><a href="{account}">Open your One account</a> and sign in with this '
			"address. If this is a mistake, reply to this email."
		),
		"outside": True,
	},
	{
		"name": _lt("Workspace Moved Away"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When a workspace's administrator moves it to someone else's account."),
		"to": _lt("The previous account holder"),
		"subject": _lt("{workspace} has left your One account"),
		"message": _lt(
			"{by} moved billing for {workspace} to someone else. You won't get any more invoices for "
			"it. If this is a mistake, reply to this email."
		),
		"outside": True,
	},
	{
		"name": _lt("Confirm Your New Email"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When an account holder asks to change their email. It can't be turned off."),
		"to": _lt("The new address"),
		"subject": _lt("Confirm your new address for One"),
		"message": _lt(
			'<a href="{link}">Use this address for my One account</a><br><br>The link works once, for '
			"{minutes} minutes. If you didn't ask for this, you can ignore this email."
		),
		"outside": True,
		"required": True,
	},
	{
		"name": _lt("Account Email Changed"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When an account holder's email has changed. It can't be turned off."),
		"to": _lt("The previous address"),
		"subject": _lt("Your One account has a new address"),
		"message": _lt(
			"Your One account now signs in with {address}, and invoices go there. If you didn't make this "
			"change, reply to this email right away."
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
		"subject": _lt("{workspace} paid while {state}"),
		"message": _lt(
			"A payment arrived for {workspace}, but its site is gone. Rebuild it from its backup, or refund "
			"the payment in Stripe."
		),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("New Signup"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When someone pays for a new workspace."),
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
			"When another operator changes OneAdmin Settings. Keys show only as changed."
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
		"about": _lt("When the nightly sync takes an offered model off sale."),
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
		"message": _lt("{who} asked to close it. It will be archived on {date} and deleted on {deleted}."),
		"email_default": True,
	},
	{
		"name": _lt("Workspace Owing"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When a workspace becomes overdue or is suspended for non-payment."),
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
			"Every morning, the domains waiting over a day for DNS or not working. Skipped when there are none."
		),
		"to": _lt("The operators"),
		"subject": _lt("{count} domains need attention"),
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
			"{workspace} is ready at {address}.<br><br>A second email has a link to choose your password. "
			"It works for 7 days. If it hasn't arrived, reply to this email.<br><br>It's also in "
			'<a href="{account}">your One account</a> with your other workspaces.'
		),
		"outside": True,
	},
	{
		"name": _lt("Workspace Suspended"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When a workspace is suspended for non-payment."),
		"to": _lt("The workspace's owner"),
		"subject": _lt("{workspace} is suspended"),
		"message": _lt(
			"Payment for {workspace} didn't arrive, so it's suspended. No one can sign in, and nothing in it "
			"is changed.<br><br>Pay the invoice we sent you and it's back right away. If it isn't paid, it "
			"will be archived on {date}. If something is wrong, reply to this email."
		),
		"outside": True,
	},
	{
		"name": _lt("Workspace Archived"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When a suspended workspace is archived for non-payment."),
		"to": _lt("The workspace's owner"),
		"subject": _lt("{workspace} is archived"),
		"message": _lt(
			"{workspace} was suspended and not paid for, so it has been taken offline. A backup is kept, and "
			"your files are still there.<br><br>On {date} the workspace and its files will be permanently "
			"deleted. To restore it before then, pay the invoice we sent you and reply to this email."
		),
		"outside": True,
	},
	{
		"name": _lt("Workspace Closed"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When a workspace closes on the date its billing contact chose."),
		"to": _lt("The workspace's owner"),
		"subject": _lt("{workspace} is closed"),
		"message": _lt(
			"{workspace} is closed, as you asked, and its subscription is cancelled. A backup is kept, and "
			"your files are still there.<br><br>On {date} the workspace and its files will be permanently "
			"deleted. To get it back before then, reply to this email."
		),
		"outside": True,
	},
	{
		"name": _lt("Workspace Restored"),
		"app": "OneAdmin",
		"roles": ("One Operator",),
		"about": _lt("When a suspended workspace is paid for and reopens."),
		"to": _lt("The workspace's owner"),
		"subject": _lt("{workspace} is open again"),
		"message": _lt("Payment received. {workspace} is open again at {address}. Thank you."),
		"outside": True,
	},
]
