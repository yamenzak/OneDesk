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
	{
		"name": "Non Conformance Resolved",
		"app": "OneQuality",
		"roles": ("Quality User", "Quality Manager"),
		"about": "When a non conformance somebody raised is resolved.",
		"to": "Whoever raised it",
		"channels": ALL,
		"email_default": False,
		"sender": "workspace",
		"subject": "{subject} is resolved",
		"message": "{who} resolved it. Read what was done to stop it happening again.",
	},
	{
		"name": "Quality Step Overdue",
		"app": "OneQuality",
		"roles": ("Quality User", "Quality Manager"),
		"about": "The day after a step of a quality action was due and is still open.",
		"to": "Whoever is responsible for the step",
		"channels": ALL,
		"email_default": True,
		"sender": "workspace",
		"subject": "{problem} was due {due}",
		"message": "Your step on {action} is still open. Do it, or say on the action why it waits.",
	},
]
