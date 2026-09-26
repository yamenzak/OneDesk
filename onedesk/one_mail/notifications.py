"""What OneMail tells people, as notification types (one/notify.py)."""

from frappe import _lt

TYPES = [
	# sync: a connected mailbox stopped letting us in.
	{
		"name": _lt("Mailbox Not Reachable"),
		"app": "OneMail",
		"about": _lt(
			"A mailbox you hold stopped connecting. Sent once, when it breaks, to everybody who holds it."
		),
		"subject": _lt("{mailbox} is not connecting: {reason}"),
		"message": _lt(
			"No new mail is read from <b>{mailbox}</b> until it is connected again. Reconnect it from Settings › Mail."
		),
		"email_default": True,
	},
]
