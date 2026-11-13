"""OneCalendar's part of the integration suite (one_demo/check.py runs it): the
week as the team sees it, an event made and moved, a calendar link made,
renewed, read and stopped, OneAI's reads, and who may put an event on
everyone's calendar."""

import frappe
from frappe.utils import add_days, today

from onedesk.one_demo.base import as_user
from onedesk.one_demo.checking import check


@check
def onecalendar_shows_each_person_their_week():
	"""The week's events, days off and layers as the team sees them, an event's
	card, one moved, a feed link made, renewed, read and stopped, and OneAI's
	reads and a suggested event."""
	from onedesk.one_calendar import agent, events, feed, layers

	start, end = str(add_days(today(), -7)), str(add_days(today(), 7))
	with as_user("rania@one.test"):
		seen = layers.entries(start, end)
		meetings = [one for one in seen if "Weekly site meeting" in (one.get("title") or "")]
		assert len(meetings) >= 2, seen
		assert layers.layers() and isinstance(layers.days_off(start, end), list)
		assert events.card(meetings[0]["name"])
		assert agent.my_calendar(start, end)
		assert agent.busy_times(["Tariq"], start, end)
		assert agent.plan_event("Snag walk", f"{add_days(today(), 4)} 09:00:00").get("state") == "Proposed"
	with as_user("samir@one.test"):
		made = events.make({"subject": "Supplier call", "starts_on": f"{add_days(today(), 2)} 15:00:00", "team": ["karim@one.test"]})
		assert frappe.db.exists("Event Participants", {"parent": made, "reference_docname": "karim@one.test"})
		mine = next(one for one in layers.entries(start, end) if one["name"] == made and one["editable"])
		layers.move(mine["layer"], mine["name"], f"{add_days(today(), 1)} 09:00:00")
		assert feed.allowed(), "Calendar Links stay on when System Settings is saved"
		link = feed.mine()
		renewed = feed.renew()
		assert renewed["https"] != link["https"]
		feed.ics(renewed["https"].split("token=", 1)[1])
		assert b"BEGIN:VCALENDAR" in frappe.response["filecontent"] and b"Weekly site meeting" in frappe.response["filecontent"]
		feed.stop()


@check
def only_a_calendar_manager_puts_an_event_on_everyones_calendar():
	"""Mariam, a OneCalendar Manager, makes a closure everybody sees, and
	Samir, who is not one, is refused. Samir's own private event is his to
	make, and the screen is told which of the two each of them may do."""
	from onedesk.one_calendar import events

	day = f"{add_days(today(), 5)} 00:00:00"
	with as_user("mariam@one.test"):
		assert events.may_publish()
		closure = events.make({"subject": "Workshop closed", "starts_on": day, "all_day": 1, "public": 1})
	with as_user("samir@one.test"):
		assert not events.may_publish()
		assert frappe.has_permission("Event", "read", closure)
		try:
			events.make({"subject": "Team lunch", "starts_on": day, "all_day": 1, "public": 1})
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody who is not a OneCalendar Manager put an event on everyone's calendar")
		assert events.make({"subject": "Dentist", "starts_on": day, "all_day": 1})
