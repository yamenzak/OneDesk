"""The team's calendar: the weekly site meeting and Layla's management
meeting, each one event that repeats every week from the week before the
demo was made, so every week shows them; a
handover walk with the customer, a supplier visit and the workshop's safety
briefing, each made as Add Event makes it, with the people it is for."""

import frappe
from frappe.utils import add_days, get_datetime

from onedesk.one_demo.base import ago, as_user

REPEATS = {"Weekly site meeting": "Weekly", "Management meeting": "Weekly"}

EVENTS = (
	("samir@one.test", "Weekly site meeting", -7, "08:00", 1, ("rania@one.test", "tariq@one.test"), None, None, False),
	("wsadmin@one.test", "Management meeting", -6, "10:00", 1, ("omar@one.test", "huda@one.test", "karim@one.test"), None, None, False),
	(
		"samir@one.test",
		"Handover walk at the Mansour villa",
		3,
		"10:00",
		2,
		("rania@one.test", "yousef@one.test"),
		"khalid@mansour.example",
		("Project", "Mansour Villa Windows and Doors"),
		False,
	),
	("karim@one.test", "Al Noor Aluminium visit", 2, "14:00", 1, ("samir@one.test",), None, None, False),
	("mariam@one.test", "Workshop safety briefing", 1, "07:30", 1, (), None, None, True),
	("omar@one.test", "Bayview tower pricing review", -2, "11:00", 1, ("samir@one.test", "huda@one.test"), None, None, False),
)


def run(password=None):
	from onedesk.one_calendar import events

	for user, subject, day, at, hours, team, guests, about, public in EVENTS:
		starts = get_datetime(f"{add_days(ago(0), day)} {at}:00")
		if frappe.db.exists("Event", {"subject": subject, "starts_on": starts}):
			continue
		reference = None
		if about:
			reference = frappe.db.get_value(about[0], {"project_name": about[1]}) if about[0] == "Project" else about[1]
		with as_user(user):
			made = events.make(
				{
					"subject": subject,
					"starts_on": str(starts),
					"ends_on": str(starts.replace(hour=starts.hour + hours)),
					"team": list(team),
					"guests": guests,
					"public": public,
					"reference_doctype": about[0] if reference else None,
					"reference_docname": reference,
				}
			)
			if subject in REPEATS:
				doc = frappe.get_doc("Event", made)
				doc.update({"repeat_this_event": 1, "repeat_on": REPEATS[subject], starts.strftime("%A").lower(): 1})
				doc.save()
