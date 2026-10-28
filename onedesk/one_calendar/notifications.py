"""What OneCalendar tells people, one entry per kind of notification, read by
onedesk/notifications/__init__.py beside the other modules' files. Each entry
has the keys of a notification file (notifications/layout.py KEYS), with
`subject` and `message` for its heading and body, and says its `channels`,
each on or why not, and its `sender` (docs/READY.md, mechanism 8). Sent by
tell.py. Pure."""

ALL = {"bell": True, "email": True, "push": True}

OUTSIDE = {
	"bell": "It goes to somebody outside the workspace, who has no bell.",
	"email": True,
	"push": "It goes to somebody outside the workspace, whose devices One never sees.",
}

TYPES = [
	{
		"name": "Event Cancelled",
		"app": "OneCalendar",
		"about": "When an event you are on is cancelled or deleted.",
		"to": "Everybody on it, but whoever cancelled it",
		"channels": ALL,
		"email_default": True,
		"push_default": True,
		"sender": "workspace",
		"subject": "{event} is cancelled",
		"message": "{who} cancelled it. It was {when}.",
	},
	{
		"name": "Event Changed",
		"app": "OneCalendar",
		"about": "When the time or the place of an event you are on changes.",
		"to": "Everybody on it, but whoever changed it",
		"channels": ALL,
		"email_default": True,
		"push_default": True,
		"sender": "workspace",
		"subject": "{who} changed {event}",
		"message": "Now {when}{where}.",
	},
	{
		"name": "Event Invitation",
		"app": "OneCalendar",
		"about": "When somebody outside the workspace is invited to an event, or it changes or is cancelled. Their reply goes to the organizer's own mailbox.",
		"to": "Each guest, by email, with the event attached for their calendar",
		"channels": OUTSIDE,
		"outside": True,
		"sender": "workspace",
		"subject": "{state}: {event}, {when}",
		"message": "{who} {said} <b>{event}</b>, {when}{where}.<br><br>The event is attached, to add to your own calendar.",
	},
	{
		"name": "Invited to an Event",
		"app": "OneCalendar",
		"about": "When somebody adds you to an event.",
		"to": "Each person added",
		"channels": ALL,
		"email_default": True,
		"push_default": True,
		"sender": "workspace",
		"subject": "{who} invited you to {event}",
		"message": "{when}{where}.",
	},
	{
		"name": "Starting Soon",
		"app": "OneCalendar",
		"about": "When an event you are on starts soon, as its reminders say, or ten minutes before.",
		"to": "Whoever made it and everybody invited",
		"channels": ALL,
		"push_default": True,
		"sender": "workspace",
		"subject": "{event} starts at {time}{where}",
	},
	{
		"name": "Taken Off an Event",
		"app": "OneCalendar",
		"about": "When somebody takes you off an event you were on.",
		"to": "Whoever was taken off",
		"channels": ALL,
		"email_default": True,
		"push_default": True,
		"sender": "workspace",
		"subject": "{who} took you off {event}",
		"message": "It was {when}. It is gone from your calendar.",
	},
	{
		"name": "Today's Events",
		"app": "OneCalendar",
		"about": "Every morning, what is on your calendar that day. Not sent on a day with nothing on it.",
		"to": "Each person, for their own day",
		"channels": ALL,
		"button": "Open the Calendar",
		"email_default": True,
		"sender": "workspace",
		"subject": "{count} on your calendar today",
		"message": "{events}",
	},
]
