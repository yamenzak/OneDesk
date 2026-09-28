"""What OneCalendar adds to the agreements: a person may publish their own
calendar to another app through a private link. See one_calendar/feed.py and
one_legal/README.md."""

from onedesk.one_legal.registry import clause

M = "OneCalendar"

clause(
	document="privacy",
	section="modules",
	key="calendar-link",
	module=M,
	body="""
		Where a workspace allows it, a person can make a private link to their own calendar and give it to
		another calendar app, such as Google Calendar, Apple Calendar or Outlook. Whoever holds the link can
		read what that person's calendar shows, from two months back to a year ahead, and never more than that
		person can see in One. That app is the person's choice and keeps what it reads under its own terms. The
		link can be replaced or switched off at any time, it stops working when the person's account is
		disabled, and the workspace's administrators can delete every link at once.
	""",
)

clause(
	document="privacy",
	section="modules",
	key="calendar-guests",
	module=M,
	body="""
		A person can invite somebody outside the workspace to an event by their email address. That address
		is kept as a contact of the workspace, and the guest is mailed the event, and any change to it or its
		cancellation, as an invitation for their own calendar. Where the workspace connects a Google account
		under Google Calendar, the events it syncs are sent to that account and read back from it, both ways,
		and a video call link is made by Google, under Google's terms with that account's holder.
	""",
)

clause(
	document="ai",
	section="modules",
	key="onecalendar-asks",
	module=M,
	body="""
		In OneCalendar, when you ask OneAI about your time, it reads your calendar as you see it. To find a
		time to meet, it reads only when colleagues are busy, never what their events are. An event it
		suggests is made only when you approve it, and the people on it are told then.
	""",
)
