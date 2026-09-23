"""A person's calendar link. Made and replaced from the calendar's Subscribe
dialog; a Workspace Administrator deletes one here to switch it off. See
`one_calendar/feed.py`."""

from frappe.model.document import Document


class CalendarFeed(Document):
	pass
