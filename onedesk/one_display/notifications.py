"""What OneDisplay tells people, one entry per kind of notification, read by
onedesk/notifications/__init__.py beside the other modules' files. Each entry
has the keys of a notification file (notifications/layout.py KEYS), with
`subject` and `message` for its heading and body, and says its `channels`,
each on or why not, and its `sender` (docs/READY.md, mechanism 8). Sent by
tell.py. Pure."""

ALL = {"bell": True, "email": True, "push": True}

TYPES = [
	{
		"name": "Screen Offline",
		"app": "OneDisplay",
		"about": "When a paired screen has not asked for its channel for ten minutes, unless somebody turned it off.",
		"to": "Everybody who runs OneDisplay",
		"channels": ALL,
		"email_default": True,
		"push_default": True,
		"sender": "workspace",
		"subject": "{screen} is offline",
		"message": "It was last seen {when}. Check that it is switched on and has a connection.",
	},
	{
		"name": "Emergency Alert Sent",
		"app": "OneDisplay",
		"about": "When somebody puts an emergency alert on every screen.",
		"to": "Everybody who may send an alert, but whoever sent it",
		"channels": ALL,
		"email_default": True,
		"push_default": True,
		"sender": "workspace",
		"subject": "{who} put an alert on every screen",
		"message": "Every screen shows “{message}” until somebody ends it.",
	},
]
