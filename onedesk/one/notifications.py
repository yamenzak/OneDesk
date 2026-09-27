"""What One itself tells people, as notification types (one/notify.py).

Security notices: each goes to the person whose account it is, on the bell
and always by mail, because a person who did not do it has to find out
wherever they are. See one/signin.py.
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
]
