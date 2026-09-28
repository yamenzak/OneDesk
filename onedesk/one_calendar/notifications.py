"""What OneCalendar tells people, as notification types (one/notify.py).

Sent by `tell.py`: on an event's save and delete, every five minutes for what
starts soon, and each morning for the day. frappe's own morning mail, which
went around the hub and left out events a person is only invited to, is
stopped (`tell.install`)."""

from frappe import _lt

TYPES = [
	{
		"name": _lt("Invited to an Event"),
		"app": "OneCalendar",
		"about": _lt("When somebody adds you to an event."),
		"to": _lt("Each person added"),
		"subject": _lt("{who} invited you to {event}"),
		"message": _lt("<b>{event}</b>, {when}{where}."),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("Event Changed"),
		"app": "OneCalendar",
		"about": _lt("When the time or the place of an event you are on changes."),
		"to": _lt("Everybody on it, but whoever changed it"),
		"subject": _lt("{event} is now {when}"),
		"message": _lt("{who} changed <b>{event}</b>. It is now {when}{where}."),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("Event Cancelled"),
		"app": "OneCalendar",
		"about": _lt("When an event you are on is cancelled or deleted."),
		"to": _lt("Everybody on it, but whoever cancelled it"),
		"subject": _lt("{event} is cancelled"),
		"message": _lt("{who} cancelled <b>{event}</b>, which was {when}."),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("Starting Soon"),
		"app": "OneCalendar",
		"about": _lt("When an event you are on starts soon, as its reminders say, or ten minutes before."),
		"to": _lt("Whoever made it and everybody invited"),
		"subject": _lt("{event} starts at {time}"),
		"message": _lt("<b>{event}</b> starts at {time}{where}."),
		"push_default": True,
	},
	{
		"name": _lt("Today's Events"),
		"app": "OneCalendar",
		"about": _lt(
			"Every morning, what is on your calendar that day. Not sent on a day with nothing on it."
		),
		"to": _lt("Each person, for their own day"),
		"subject": _lt("{count} on your calendar today"),
		"message": _lt("{events}"),
		"email_default": True,
	},
	{
		"name": _lt("Event Invitation"),
		"app": "OneCalendar",
		"about": _lt(
			"When somebody outside the workspace is invited to an event, or it changes or is cancelled."
		),
		"to": _lt("Each guest, by email, with the event attached for their calendar"),
		"subject": _lt("{state}: {event}, {when}"),
		"message": _lt(
			"{who} {said} <b>{event}</b>, {when}{where}.<br><br>The event is attached, to add to your own calendar."
		),
		"outside": True,
	},
]
