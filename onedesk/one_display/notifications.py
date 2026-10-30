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
		"name": "Long Wait",
		"app": "OneDisplay",
		"about": "When somebody in a queue has waited longer than the queue allows.",
		"to": "Whoever staffs one of the queue's counters",
		"channels": ALL,
		"email_default": False,
		"push_default": True,
		"sender": "workspace",
		"subject": "{ticket} has waited {minutes} minutes",
		"message": "{service}, in {queue}. Call it from Counter.",
	},
	{
		"name": "Made by OneAI",
		"app": "OneDisplay",
		"about": "When a piece of music somebody asked OneAI for is ready in its playlist.",
		"to": "Whoever asked for it",
		"channels": ALL,
		"email_default": False,
		"push_default": True,
		"sender": "workspace",
		"subject": "“{what}” is ready in {playlist}",
		"message": "It is paused until you play it. Look at it first, then clear Paused.",
	},
	{
		"name": "Not Made by OneAI",
		"app": "OneDisplay",
		"about": "When OneAI could not make a piece of music somebody asked for.",
		"to": "Whoever asked for it",
		"channels": ALL,
		"email_default": False,
		"push_default": True,
		"sender": "workspace",
		"subject": "OneAI could not make “{what}”",
		"message": "Nothing was added to {playlist}. Try again, or describe it differently.",
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
