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
		"about": _lt("When an administrator changes which apps you may use, or makes you an administrator."),
		"to": _lt("The person whose access it is"),
		"subject": _lt("What you can use in One changed"),
		"message": _lt("{by} changed what you can use: {changes}."),
		"email": False,
	},
	{
		"name": _lt("Administrator Added"),
		"app": "One",
		"about": _lt("When somebody is made an administrator of the workspace."),
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
		"about": _lt("When an administrator invites somebody to the workspace, with the link to join."),
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
		"about": _lt("When the workspace's OneAI credits fall under about three days of what it uses."),
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
		"about": _lt(
			"When OneAI credits arrive, from a pack that was paid for or the plan's monthly credits."
		),
		"to": _lt("Every administrator"),
		"subject": _lt("OneAI credits were added"),
		"message": _lt("OneAI credits were added. The workspace now has {balance}."),
		"email": False,
	},
	{
		"name": _lt("Storage Nearly Full"),
		"app": "One",
		"about": _lt("When the workspace's files take nine tenths of the storage its plan allows."),
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
		"about": _lt("When the workspace's database takes nine tenths of what its plan allows."),
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
		"name": _lt("Plan Changed"),
		"app": "One",
		"about": _lt("When another administrator changes the workspace's plan or its add-ons."),
		"to": _lt("Every other administrator"),
		"subject": _lt("{by} changed the plan to {plan}"),
		"message": _lt("{by} changed the workspace's plan to {plan}. It now costs {monthly} a month."),
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
]
