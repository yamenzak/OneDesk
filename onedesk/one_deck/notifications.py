"""What OneDeck tells people, one entry per kind of notification, read by
onedesk/notifications/__init__.py beside the other modules' files. Each entry
has the keys of a notification file (notifications/layout.py KEYS), with
`subject` and `message` for its heading and body, and says its `channels`,
each on or why not, and its `sender` (docs/READY.md, mechanism 8). Sent by
tell.py. Pure."""

from onedesk.one import registry

ALL = {"bell": True, "email": True, "push": True}

TYPES = [
	{
		"name": "Video Made for a Presentation",
		"app": registry.name("one_deck"),
		"about": "When a video somebody asked {one_ai} for is ready, on a new slide of their presentation.",
		"to": "Whoever asked for it",
		"channels": ALL,
		"email_default": False,
		"push_default": True,
		"sender": "workspace",
		"subject": "“{what}” is ready in {presentation}",
		"message": "It is on a new slide at the end. Look at it before you show it.",
	},
	{
		"name": "Video Not Made for a Presentation",
		"app": registry.name("one_deck"),
		"about": "When {one_ai} could not make a video somebody asked for in a presentation.",
		"to": "Whoever asked for it",
		"channels": ALL,
		"email_default": False,
		"push_default": True,
		"sender": "workspace",
		"subject": "{one_ai} could not make “{what}”",
		"message": "Nothing was added to {presentation}. Try again, or describe it differently.",
	},
]
