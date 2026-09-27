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
