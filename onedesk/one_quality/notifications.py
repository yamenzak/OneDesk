"""What OneQuality tells people, one entry per kind of notification, read by
onedesk/notifications/__init__.py beside the other modules' files. Each entry
has the keys of a notification file (notifications/layout.py KEYS), with
`subject` and `message` for its heading and body, and says its `channels`,
each on or why not, and its `sender` (docs/READY.md, mechanism 8). Pure."""

ALL = {"bell": True, "email": True, "push": True}

TYPES = [
	{
		"name": "Non Conformance Raised",
		"app": "OneQuality",
		"roles": ("Quality Manager",),
		"about": "When somebody records work that did not follow its procedure.",
		"to": "The quality managers",
		"channels": ALL,
		"email_default": True,
		"sender": "workspace",
		"subject": "{subject}",
		"message": "{who} raised it against {procedure}. Decide what is done about it.",
	},
]
