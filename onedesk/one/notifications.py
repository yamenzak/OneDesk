"""What One itself tells people, as notification types (one/notify.py).

Security notices: each goes to the person whose account it is, on the bell
and always by mail, because a person who did not do it has to find out
wherever they are. See one/signin.py. A new administrator is told to every
other administrator the same way, because that is how a taken account widens
itself; what a person may use is told to them (one/settings.py).

The account's news goes to every administrator (one/account.py), and what
costs the workspace if it is missed (credits running out, storage full, a
payment overdue) always by mail as well.
"""

from frappe import _lt

TYPES = [
	{
		"name": _lt("Automation Notice"),
		"app": "One",
		"about": _lt("When an automation sends a notification."),
		"to": _lt("The people the automation names"),
		"subject": _lt("{subject}"),
		"message": _lt("{message}"),
	},
	{
		"name": _lt("Approval Waiting"),
		"app": "One",
		"about": _lt("When a record reaches an approval step for one of your roles."),
		"to": _lt("People with the step's role who can open the record"),
		"subject": _lt("{kind} {record_name} is waiting for you"),
		"message": _lt("The {kind} {record_name} is {state}. Open it to {actions}."),
	},
	{
		"name": _lt("Password Changed"),
		"app": "One",
		"about": _lt("When your password is changed, here or through a reset link."),
		"to": _lt("The person whose password it is"),
		"subject": _lt("Your password was changed"),
		"message": _lt(
			"Your password was changed on {when}, from {device} ({address}). If this was not you, reset it "
			"now from the sign-in page and tell your administrator."
		),
		"email": False,
		"always_mailed": True,
	},
	{
		"name": _lt("Passkey Added"),
		"app": "One",
		"about": _lt("When a passkey is added to your account."),
		"to": _lt("The person whose account it is"),
		"subject": _lt("A passkey was added to your account"),
		"message": _lt(
			"A passkey was added to your account on {when}, from {device} ({address}). If this was not you, "
			"tell your administrator now so they can remove it."
		),
		"email": False,
		"always_mailed": True,
	},
	{
		"name": _lt("Access Changed"),
		"app": "One",
		"about": _lt(
			"When an administrator changes which apps you may use, your level or profile, the records you see, or makes you an administrator."
		),
		"to": _lt("The person whose access it is"),
		"subject": _lt("What you can use in One changed"),
		"message": _lt("{by} changed what you can use: {changes}."),
		"email": False,
	},
	{
		"name": _lt("Administrator Added"),
		"app": "One",
		"about": _lt("When someone is made a workspace administrator."),
		"to": _lt("Every other administrator"),
		"subject": _lt("{person} is now an administrator"),
		"message": _lt(
			"{by} made {person} an administrator of the workspace. If you did not expect this, check "
			"Workspace › People now."
		),
		"email": False,
		"always_mailed": True,
	},
	{
		"name": _lt("Invitation"),
		"app": "One",
		"about": _lt("When an administrator invites someone to the workspace."),
		"to": _lt("The person invited"),
		"subject": _lt("{inviter} invited you to {workspace}"),
		"message": _lt(
			"<b>{inviter}</b> invited you to <b>{workspace}</b> on One.{apps}<br><br>"
			'<a href="{link}">Choose your password</a><br><br>'
			"The link works for {days} days. You sign in with {address}."
		),
		"outside": True,
	},
	{
		"name": _lt("Credits Running Low"),
		"app": "One",
		"about": _lt("When OneAI credits will run out in about three days."),
		"to": _lt("Every administrator"),
		"subject": _lt("OneAI credits are running low"),
		"message": _lt(
			"The workspace has {balance} OneAI credits left, about {days} days at the rate of the last "
			"thirty. Buy more on Workspace › Plan and Credits."
		),
		"email": False,
		"always_mailed": True,
	},
	{
		"name": _lt("Credits Expiring"),
		"app": "One",
		"about": _lt("Before some of the workspace's OneAI credits expire, a week ahead."),
		"to": _lt("Every administrator"),
		"subject": _lt("{credits} OneAI credits expire on {date}"),
		"message": _lt(
			"{credits} of the workspace's OneAI credits expire on {date}. They are used before any others, "
			"so nothing needs doing unless you want them used."
		),
		"email": False,
	},
	{
		"name": _lt("Credits Added"),
		"app": "One",
		"about": _lt("When OneAI credits are added, from a pack, the monthly plan or One."),
		"to": _lt("Every administrator"),
		"subject": _lt("OneAI credits were added"),
		"message": _lt("OneAI credits were added. The workspace now has {balance}.{note}"),
		"email": False,
	},
	{
		"name": _lt("Storage Nearly Full"),
		"app": "One",
		"about": _lt("When files use 90% of the plan's storage."),
		"to": _lt("Every administrator"),
		"subject": _lt("Storage is nearly full"),
		"message": _lt(
			"The workspace's files take {used} of the {limit} its plan allows. Once it is full, nothing new "
			"can be uploaded."
		),
		"email": False,
		"always_mailed": True,
	},
	{
		"name": _lt("Database Nearly Full"),
		"app": "One",
		"about": _lt("When the database uses 90% of the plan's limit."),
		"to": _lt("Every administrator"),
		"subject": _lt("The database is nearly full"),
		"message": _lt(
			"The workspace's database takes {used} of the {limit} its plan allows. Add database or move to a "
			"bigger plan on Workspace › Plan and Credits before it is full."
		),
		"email": False,
		"always_mailed": True,
	},
	{
		"name": _lt("Your Data Is Ready"),
		"app": "One",
		"about": _lt("When the copy of your data you asked for on your profile is ready."),
		"to": _lt("The person who asked"),
		"subject": _lt("Your data is ready"),
		"message": _lt(
			"The copy of your data you asked for is ready to download from your profile. Withheld: {withheld}"
		),
		"email": False,
		"always_mailed": True,
	},
	{
		"name": _lt("Confirm Your Request"),
		"app": "One",
		"about": _lt("When someone who isn't a user makes a request on the Your Data page."),
		"to": _lt("The address given on the page"),
		"subject": _lt("Confirm your request to {workspace}"),
		"message": _lt(
			"You asked {workspace} for {asked}. Open this link within {hours} hours to confirm, and it will "
			"decide within a month: {url}<br><br>If it was not you, do nothing."
		),
		"outside": True,
	},
	{
		"name": _lt("Your Data Is Ready to Download"),
		"app": "One",
		"about": _lt("When a copy asked for on the Your Data page is ready, with the link to download it."),
		"to": _lt("The person who asked"),
		"subject": _lt("Your data is ready"),
		"message": _lt(
			"The copy of your data you asked for is ready: {url}<br><br>The link works for {days} days. "
			"Withheld: {withheld}"
		),
		"outside": True,
	},
	{
		"name": _lt("Your Request Is On Hold"),
		"app": "One",
		"about": _lt("When a deletion asked for on the Your Data page has to wait, and why."),
		"to": _lt("The person who asked"),
		"subject": _lt("Your data is not deleted yet"),
		"message": _lt("Your request to delete your data is on hold, because: {why}"),
		"outside": True,
	},
	{
		"name": _lt("Your Data Is Being Deleted"),
		"app": "One",
		"about": _lt("When a deletion asked for on the Your Data page is approved."),
		"to": _lt("The person who asked"),
		"subject": _lt("Your data is being deleted"),
		"message": _lt(
			"Your request was approved. Your name and address are being taken out of the workspace's records "
			"now. What the law makes it keep, such as invoices, stays."
		),
		"outside": True,
	},
	{
		"name": _lt("Copy Asked"),
		"app": "One",
		"about": _lt("When someone asks for a copy of their data."),
		"to": _lt("Every administrator"),
		"subject": _lt("{person} asked for a copy of their data"),
		"message": _lt(
			"{person} asked for a copy of their data. Review and send it in Workspace › Data Copies within "
			"one month."
		),
		"email": False,
		"always_mailed": True,
	},
	{
		"name": _lt("Confirm Deletion"),
		"app": "One",
		"about": _lt("When you ask for your account to be deleted and sign in without a password."),
		"to": _lt("The person who asked"),
		"subject": _lt("Confirm deleting your account"),
		"message": _lt(
			"You asked for your account to be deleted. Open this link within {hours} hours to confirm, and your "
			"workspace's administrators will decide: {url}. If it was not you, do nothing and your account stays."
		),
		"email": False,
		"always_mailed": True,
	},
	{
		"name": _lt("Privacy Requests Waiting"),
		"app": "One",
		"about": _lt("Every day while a privacy request has waited more than a week for a decision."),
		"to": _lt("Every administrator"),
		"subject": _lt("{count} privacy requests are waiting"),
		"message": _lt(
			"{count} privacy requests have waited more than a week. The law allows one month to respond."
		),
		"email": False,
		"always_mailed": True,
	},
	{
		"name": _lt("Deletion Asked"),
		"app": "One",
		"about": _lt("When someone asks for their account to be deleted."),
		"to": _lt("Every administrator"),
		"subject": _lt("{person} asked for their account to be deleted"),
		"message": _lt(
			"{person} ({email}) asked for their account and what they left in the workspace to be deleted. "
			"Approve it, or hold it and say why, under Workspace › Privacy Requests."
		),
		"email": False,
		"always_mailed": True,
	},
	{
		"name": _lt("Deletion On Hold"),
		"app": "One",
		"about": _lt("When an administrator holds your request to delete your account, and why."),
		"to": _lt("The person who asked"),
		"subject": _lt("Your account is not deleted yet"),
		"message": _lt("An administrator is holding your request to delete your account, because: {why}"),
		"email": False,
		"always_mailed": True,
	},
	{
		"name": _lt("Account Deleted"),
		"app": "One",
		"about": _lt("When an administrator approves deleting your account."),
		"to": _lt("The person whose account it is"),
		"subject": _lt("Your account is being deleted"),
		"message": _lt(
			"Your request was approved. You are signed out, and your account and what only you used are being "
			"deleted now. What the workspace has to keep, such as invoices you raised, stays without your name "
			"and address. Your employee record, if you have one, is HR's."
		),
		"email": False,
		"always_mailed": True,
	},
	{
		"name": _lt("Person Deleted"),
		"app": "One",
		"about": _lt("When another administrator approves an account deletion."),
		"to": _lt("Every other administrator"),
		"subject": _lt("{by} deleted {person}'s account"),
		"message": _lt("{by} approved deleting {person}'s account. It is turned off and being erased now."),
		"email": False,
	},
	{
		"name": _lt("Plan Changed"),
		"app": "One",
		"about": _lt("When another administrator changes the workspace's plan or its add-ons."),
		"to": _lt("Every other administrator"),
		"subject": _lt("{by} changed the plan to {plan}"),
		"message": _lt("{by} changed the workspace's plan to {plan}. It now costs {monthly} a month."),
		"email": False,
	},
	{
		"name": _lt("Announcement"),
		"app": "One",
		"about": _lt("When an administrator posts an announcement."),
		"to": _lt("Everyone in the workspace"),
		"subject": _lt("{title}"),
		"message": _lt("{by} announced: {text}"),
		"email_default": True,
	},
	{
		"name": _lt("Webhooks Failing"),
		"app": "One",
		"about": _lt("Every morning, if webhooks failed to deliver the day before."),
		"to": _lt("Every administrator"),
		"subject": _lt("Webhooks could not deliver yesterday"),
		"message": _lt(
			"These webhooks could not deliver after every try: {webhooks}. Open each call to see what the "
			"other system answered."
		),
		"email_default": True,
	},
	{
		"name": _lt("Full Download Ready"),
		"app": "One",
		"about": _lt("When the full download of the workspace you asked for is ready."),
		"to": _lt("The person who pays for the workspace"),
		"subject": _lt("The full download is ready"),
		"message": _lt(
			"Everything in the workspace, {size}, is ready to download from Plan and Credits: the database, "
			"every record as a spreadsheet, and every file. {missing}"
		),
		"email_default": True,
	},
	{
		"name": _lt("Workspace Closing"),
		"app": "One",
		"about": _lt("When the person who pays for the workspace asks for it to be closed. It cannot be turned off."),
		"to": _lt("Everyone in the workspace"),
		"subject": _lt("The workspace closes on {date}"),
		"message": _lt(
			"{by} asked for the workspace to be closed. It works as usual until {date}. After that no one can "
			"sign in, and on {deleted} everything in it is permanently deleted. Download anything you need "
			"before then."
		),
		"email_default": True,
		"required": True,
	},
	{
		"name": _lt("Workspace Staying Open"),
		"app": "One",
		"about": _lt("When a workspace that was closing is kept open. It cannot be turned off."),
		"to": _lt("Everyone in the workspace"),
		"subject": _lt("The workspace is staying open"),
		"message": _lt("{by} kept the workspace open. Nothing changes."),
		"email_default": True,
		"required": True,
	},
	{
		"name": _lt("Payer Changed"),
		"app": "One",
		"about": _lt("When another administrator changes who pays for the workspace."),
		"to": _lt("Every other administrator"),
		"subject": _lt("{by} changed who pays for the workspace"),
		"message": _lt("{by} made {email} the one who pays. The workspace's invoices go to them from now on."),
		"email": False,
	},
	{
		"name": _lt("Payment Overdue"),
		"app": "One",
		"about": _lt("When payment for the workspace is overdue, with the day it will be suspended."),
		"to": _lt("Every administrator"),
		"subject": _lt("Payment for the workspace is overdue"),
		"message": _lt(
			"Payment for the workspace is overdue. Unless it is paid, the workspace is suspended on {date}."
		),
		"email": False,
		"always_mailed": True,
	},
	{
		"name": _lt("Domain Working"),
		"app": "One",
		"about": _lt("When one of the workspace's own domains starts working."),
		"to": _lt("Every administrator"),
		"subject": _lt("{domain} works now"),
		"message": _lt(
			"The workspace now opens at {domain}. To have sign-in and links in mail use it, make it the main "
			"address on Workspace › Domains."
		),
		"email": False,
		"always_mailed": True,
	},
	{
		"name": _lt("Domain Stopped Working"),
		"app": "One",
		"about": _lt("When one of the workspace's own domains stops working."),
		"to": _lt("Every administrator"),
		"subject": _lt("{domain} stopped working"),
		"message": _lt(
			"The workspace no longer opens at {domain}. Check that its DNS still points at {target}, then "
			"press Check Again on Workspace › Domains."
		),
		"email": False,
		"always_mailed": True,
	},
	{
		"name": _lt("Main Address Changed"),
		"app": "One",
		"about": _lt("When another administrator changes the workspace's main address."),
		"to": _lt("Every other administrator"),
		"subject": _lt("{by} changed the workspace's address to {domain}"),
		"message": _lt(
			"{by} made {domain} the workspace's main address. Sign-in, invitations and every link in mail "
			"now use it."
		),
		"email": False,
		"always_mailed": True,
	},
	{
		"name": _lt("OneAI Changed"),
		"app": "One",
		"about": _lt("When another administrator changes the model or the added instructions of one of OneAI's actions."),
		"to": _lt("Every other administrator"),
		"subject": _lt("{by} changed {action}"),
		"message": _lt(
			"{by} changed {what} for {action}. This applies to everyone and may change its cost. See "
			"OneAI › Actions."
		),
		"email": False,
	},
	# holidays: which days nobody works, for leave, attendance and deadlines.
	{
		"name": _lt("Holidays Changed"),
		"app": "One",
		"about": _lt("When another administrator changes the workspace's holidays."),
		"to": _lt("Every other administrator"),
		"subject": _lt("{by} changed the holidays"),
		"message": _lt("{by} changed the holidays in {holiday_list}: {what}. Leave, attendance and deadlines count around them from now on."),
		"email": False,
	},
	{
		"name": _lt("Holidays Run Out Soon"),
		"app": "One",
		"about": _lt("When the holiday list ends in 60, 30 or 7 days with no list after it."),
		"to": _lt("Every administrator"),
		"subject": _lt("The holiday list ends in {days} days"),
		"message": _lt(
			"{holiday_list} ends on {last_day} and no list follows it. From {first_day} every day counts as a "
			"working day for leave and attendance. Make next year's list in Workspace › Holidays."
		),
		"email_default": True,
	},
]
