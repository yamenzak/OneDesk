"""What One itself tells people, as notification types (one/notify.py).

Security notices: each goes to the person whose account it is, on the bell
and always by mail, because a person who did not do it has to find out
wherever they are. See one/signin.py. A new administrator is told to every
other administrator the same way, because that is how a taken account widens
itself; what a person may use is told to them (one/settings.py).
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
]
