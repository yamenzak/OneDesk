"""What OneAI does in OneCalendar: reads the reader's calendar, says when
colleagues are busy, and suggests an event as a card.

The calendar is read as the reader, through the same merge the page draws
(`layers.entries`): OneAI sees on it exactly what they do. A colleague's
calendar is never read: only when they are busy, from the events they are on,
without what those are. An event is only ever suggested; approving the card
makes it, and the people on it are told then (`tell.py`), not before.
"""

from datetime import timedelta
from typing import Annotated

import frappe
from frappe import _lt
from frappe.utils import get_datetime, getdate, today

#: Entries of the reader's calendar given to the model at once.
MOST = 200

#: The longest stretch asked about at once, in days.
LONGEST = 62

SUGGESTIONS = {
	"page:onecalendar": [
		{
			"label": _lt("What is on this week?"),
			"ask": _lt("What is on my calendar this week? Say what matters most and anything that clashes."),
			"expects": "my_calendar",
		},
		{
			# The reader says who; the model looks for a time everybody is free.
			"label": _lt("Find a time to meet…"),
			"ask": _lt("Find a time this week to meet "),
			"fill": True,
			"expects": "busy_times",
		},
		{
			"label": _lt("Plan my day"),
			"ask": _lt("Look at my calendar today and suggest how to plan the day around what is on it."),
			"expects": "my_calendar",
		},
	],
}


def page(said: dict) -> str | None:
	"""The sentence the model is told on OneCalendar."""
	if said.get("page") != "onecalendar":
		return None
	where = "The reader is on OneCalendar, their calendar"
	# oneai.js names a record's own calendar by its doctype and name.
	doctype, name = said.get("box") or "", said.get("record") or ""
	if (
		doctype
		and name
		and frappe.db.exists("DocType", doctype)
		and frappe.has_permission(doctype, "read", doc=name)
	):
		where = f"The reader is on the calendar of the {doctype} {name}"
	return (
		where + ". my_calendar reads what is on the reader's calendar between two days; busy_times says when "
		"colleagues are busy, never what they are doing; plan_event suggests an event as a card that makes it "
		"when the reader approves, and tells the people on it then. Workspace days off are included in "
		"my_calendar. How OneCalendar works is in its documentation (how_to)."
	)


def _days(start: str | None, end: str | None) -> tuple:
	first = getdate(start or today())
	last = getdate(end or first)
	if last < first:
		first, last = last, first
	return first, min(last, first + timedelta(days=LONGEST))


def my_calendar(
	start: Annotated[str, "The first day, as YYYY-MM-DD."],
	end: Annotated[str, "The last day, as YYYY-MM-DD."] | None = None,
) -> dict:
	"""What is on the reader's own calendar between two days, from every layer
	they may see (their events, tasks, deals' next steps, leave, holidays and
	so on), with the workspace's days off. Read before answering about the
	reader's time or suggesting when something should happen."""
	from onedesk.one_calendar import layers

	first, last = _days(start, end)
	rows = layers.entries(str(first), str(last))[:MOST]
	return {
		"from": str(first),
		"to": str(last),
		"entries": [
			{
				"title": one["title"],
				"start": one["start"],
				"end": one["end"],
				"all_day": one["all_day"],
				"layer": one["layer"],
				"doctype": one["doctype"],
				"name": one["name"],
			}
			for one in rows
		],
		"days_off": layers.days_off(str(first), str(last)),
	}


def busy_times(
	people: Annotated[list[str], "The colleagues, by name or email address."],
	start: Annotated[str, "The first day, as YYYY-MM-DD."],
	end: Annotated[str, "The last day, as YYYY-MM-DD."] | None = None,
) -> dict:
	"""When colleagues are busy between two days: the times of the events they
	are on, never what those events are, and the reader's own for comparison.
	Use it to find a time everybody is free, then suggest it with plan_event."""
	from onedesk.one_calendar import events

	first, last = _days(start, end)
	found = {}
	unknown = []
	for one in [frappe.session.user, *(people or [])]:
		user = _person(one)
		if user:
			found.setdefault(user, [])
		elif one:
			unknown.append(one)
	candidates = events.candidates(first, last)
	if candidates:
		names = [one.name for one in candidates]
		shared = {}
		for row in frappe.get_all(
			"DocShare",
			filters={"share_doctype": "Event", "share_name": ["in", names]},
			fields=["user", "share_name"],
		):
			shared.setdefault(row.user, set()).add(row.share_name)
		on, _about = events._participants(names)
		for user in found:
			email = (frappe.db.get_value("User", user, "email") or user).lower()
			for event in candidates:
				participant = email in {one.lower() for one in on.get(event.name, ())}
				side = events.whose(event, user, event.name in shared.get(user, set()), participant)
				if side != "mine":
					continue
				for starts, ends in events.occurrences(event, first, last):
					found[user].append(
						{
							"start": str(starts),
							"end": str(ends or starts + timedelta(hours=1)),
							"all_day": bool(event.all_day),
						}
					)
	return {
		"from": str(first),
		"to": str(last),
		"busy": {
			frappe.utils.get_fullname(user): sorted(slots, key=lambda one: one["start"])
			for user, slots in found.items()
		},
		"not_found": unknown,
	}


def _person(said: str) -> str | None:
	"""A colleague by their user name, email or full name, if exactly one."""
	said = (said or "").strip()
	if not said:
		return None
	filters = {"enabled": 1, "user_type": "System User"}
	for field in ("name", "email"):
		found = frappe.db.get_value("User", {**filters, field: said}, "name")
		if found:
			return found
	matches = frappe.get_all(
		"User", filters={**filters, "full_name": ["like", f"%{said}%"]}, pluck="name", limit=2
	)
	return matches[0] if len(matches) == 1 else None


def plan_event(
	subject: Annotated[str, "What the event is, as its title."],
	starts_on: Annotated[str, "When it starts, as YYYY-MM-DD HH:MM:SS in the workspace's time."],
	ends_on: Annotated[str, "When it ends, as YYYY-MM-DD HH:MM:SS."] | None = None,
	all_day: Annotated[bool, "Whether it takes the whole day."] = False,
	location: Annotated[str, "Where, or a video call link."] | None = None,
	description: Annotated[str, "What it is for, in a line or two."] | None = None,
	team: Annotated[list[str], "Colleagues to invite, by name or email address."] | None = None,
	guests: Annotated[list[str], "Email addresses of people outside the workspace to invite."] | None = None,
	why: Annotated[str, "In a sentence, why this time."] | None = None,
) -> dict:
	"""Suggest an event on the reader's calendar, as a card they approve.
	Nobody is told of it, and nothing is made, until they approve it; then the
	people on it are invited, and guests outside are mailed the event."""
	from onedesk.one_ai import proposals

	users, unknown = [], []
	for one in team or []:
		user = _person(one)
		(users.append(user) if user else unknown.append(one))
	if unknown:
		return {
			"error": f"No colleague found for {', '.join(unknown)}. Ask who they meant, or invite them as guests."
		}
	start = get_datetime(starts_on)
	end = get_datetime(ends_on) if ends_on else (None if all_day else start + timedelta(hours=1))
	changes = {
		"subject": subject,
		"starts_on": str(start),
		"ends_on": str(end) if end else None,
		"all_day": 1 if all_day else 0,
		"location": location,
		"description": description,
		"event_participants": [
			{
				"reference_doctype": "User",
				"reference_docname": user,
				"email": frappe.db.get_value("User", user, "email"),
			}
			for user in dict.fromkeys(users)
			if user != frappe.session.user
		],
		"one_guests": ", ".join(guests or []) or None,
	}
	return {
		"proposal": proposals.propose(
			"Create", "Event", changes={k: v for k, v in changes.items() if v not in (None, [], "")}, why=why
		),
		"state": "Proposed",
		"next": "Tell them approving the card puts it on their calendar and invites the people on it.",
	}
