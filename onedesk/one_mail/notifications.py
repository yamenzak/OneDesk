"""What OneMail tells people, as notification types (one/notify.py)."""

from frappe import _lt

TYPES = [
	# sync: a connected mailbox stopped letting us in.
	{
		"name": _lt("Mailbox Not Reachable"),
		"app": "OneMail",
		"about": _lt("When a mailbox you hold stops connecting. Once, when it breaks."),
		"to": _lt("Everybody who holds it"),
		"subject": _lt("{mailbox} is not connecting: {reason}"),
		"message": _lt(
			"No new mail is read from <b>{mailbox}</b> until it is connected again. Reconnect it from Settings › Mail."
		),
		"email_default": True,
	},
	# room: storage is full, and mail arrived with attachments it could not keep.
	{
		"name": _lt("Attachments Not Saved"),
		"app": "OneMail",
		"about": _lt("When mail arrives with attachments and the workspace's storage is full. Once a day at most."),
		"to": _lt("Every administrator, and everybody who holds the mailbox"),
		"subject": _lt("Storage is full: attachments to {mailbox} are not being saved"),
		"message": _lt(
			"Mail to <b>{mailbox}</b> still arrives, but its attachments wait until there is room. Free some "
			"space or add storage in Plan and Credits, and they are saved within the hour."
		),
		"email_default": True,
	},
]
