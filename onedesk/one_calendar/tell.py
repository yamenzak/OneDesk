"""What OneCalendar tells people, and when (the types are notifications.py).

**On save** (`saved`, Event on_update): whoever was just added is told they are
invited; if the time or the place changed, everybody already on it is told;
an event set to Cancelled is a cancellation. **On delete** (`removed`) it is a
cancellation too. Whoever made the change is never told of it.

People inside the workspace are told through the hub, in their language and
by the channels they chose. A guest, somebody outside, is mailed with the
event attached as an iCalendar invitation (`invitation`), so it lands in their
own calendar: a request when invited or changed, a cancellation when
cancelled, each with a newer SEQUENCE so their calendar replaces the last.

**Starting soon** (`soon`, every five minutes): each event's own reminders
(frappe's reminders table on the event), or ten minutes before when it has
none, told once per time it happens. **Each morning** (`today_events`) every
person with something on their calendar that day is told what, from the same
read the calendar makes for them. frappe's own morning mail is stopped
(`install`): it went around the hub, in frappe's template, and left out
events a person is only invited to.
"""

import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.utils import format_datetime, formatdate, get_datetime, getdate, now_datetime, today
from markupsafe import Markup

from onedesk.one import notify
from onedesk.one_calendar.feed import escape, fold, utc

#: How far ahead a reminder may be set and still be looked for.
AHEAD = timedelta(days=2)

#: A reminder when an event names none.
DEFAULT_BEFORE = 10

#: Minutes in each of frappe's reminder intervals.
INTERVAL = {"minutes": 1, "hours": 60, "days": 1440, "weeks": 10080}

#: frappe's own morning mail, stopped because Today's Events replaces it.
FRAPPE_DIGEST = "frappe.desk.doctype.event.event.send_event_digest"


def install(*_args) -> None:
	"""after_migrate: frappe's morning mail stopped, so nobody gets two."""
	frappe.db.set_value("Scheduled Job Type", {"method": FRAPPE_DIGEST}, "stopped", 1)


# ------------------------------------------------------------------ on save


def saved(doc, method=None) -> None:
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_import or frappe.flags.in_patch:
		return
	before = doc.get_doc_before_save()
	if doc.status == "Cancelled":
		if before and before.status != "Cancelled":
			cancelled(doc)
		return
	now, was = people(doc), people(before) if before else {}
	added = {email: user for email, user in now.items() if email not in was}
	if added:
		_invited(doc, added)
	if before and moved(before, doc):
		stayed = {email: user for email, user in now.items() if email not in added}
		_changed(doc, stayed)


def removed(doc, method=None) -> None:
	"""on_trash: a deleted event is a cancelled one to everybody on it."""
	if doc.status != "Cancelled":
		cancelled(doc)


def people(doc) -> dict[str, str | None]:
	"""Everybody on an event by address: its maker and each participant, with
	the user each is, or None for somebody outside."""
	if not doc:
		return {}
	out = {}
	owner = frappe.db.get_value("User", doc.owner, "email") if doc.owner else None
	if owner:
		out[owner.lower()] = doc.owner
	for row in doc.get("event_participants") or []:
		email = (row.email or "").lower()
		if not email:
			continue
		user = (
			row.reference_docname
			if row.reference_doctype == "User"
			else frappe.db.get_value("User", {"email": email, "enabled": 1}, "name")
		)
		out[email] = user or None
	return out


def moved(before, after) -> bool:
	"""Whether what somebody would plan around changed: when, or where. Pure."""
	for field in ("starts_on", "ends_on", "all_day", "location"):
		if str(before.get(field) or "") != str(after.get(field) or ""):
			return True
	return False


def _invited(doc, added: dict) -> None:
	facts = _facts(doc)
	users = [user for user in added.values() if user and user != frappe.session.user]
	if users:
		notify.notify("Invited to an Event", users, record=("Event", doc.name), link=_link(doc), **facts)
	_mail(doc, [email for email, user in added.items() if not user], "REQUEST", facts)


def _changed(doc, stayed: dict) -> None:
	facts = _facts(doc)
	users = [user for user in stayed.values() if user and user != frappe.session.user]
	if users:
		notify.notify("Event Changed", users, record=("Event", doc.name), link=_link(doc), **facts)
	_mail(doc, [email for email, user in stayed.items() if not user], "REQUEST", facts)


def cancelled(doc) -> None:
	on = people(doc)
	facts = _facts(doc)
	users = [user for user in on.values() if user and user != frappe.session.user]
	if users:
		notify.notify("Event Cancelled", users, link="/desk/onecalendar", **facts)
	_mail(doc, [email for email, user in on.items() if not user], "CANCEL", facts)


def _facts(doc) -> dict:
	return {
		"who": frappe.utils.get_fullname(frappe.session.user),
		"event": doc.subject,
		"when": said_when(doc),
		"where": f", {doc.location}" if doc.location else "",
	}


def said_when(doc) -> str:
	"""An event's time as a sentence says it: the day, and the hours unless it
	is all day."""
	start = get_datetime(doc.starts_on)
	if doc.all_day:
		end = getdate(doc.ends_on) if doc.ends_on else start.date()
		return formatdate(start) if end == start.date() else f"{formatdate(start)} – {formatdate(end)}"
	said = format_datetime(start, "EEE d MMM, HH:mm")
	if doc.ends_on:
		end = get_datetime(doc.ends_on)
		said += " – " + (
			format_datetime(end, "HH:mm")
			if end.date() == start.date()
			else format_datetime(end, "EEE d MMM, HH:mm")
		)
	return said


def _link(doc) -> str:
	return f"/desk/onecalendar?date={getdate(doc.starts_on)}"


# ------------------------------------------------------------------ guests


def _mail(doc, emails: list[str], method: str, facts: dict) -> None:
	"""Each guest mailed the event as an invitation, or its cancellation."""
	if not emails:
		return
	zone = ZoneInfo(frappe.utils.get_system_timezone())
	site = frappe.utils.get_url()
	organizer = frappe.db.get_value("User", doc.owner, "email") or doc.owner
	body = invitation(_as_event(doc), method, organizer, emails, zone, now_datetime(), site, int(time.time()))
	state = {"REQUEST": _("Invitation"), "CANCEL": _("Cancelled")}[method]
	said = _("cancelled") if method == "CANCEL" else _("invites you to")
	for email in emails:
		notify.mail(
			"Event Invitation",
			email,
			state=state,
			said=said,
			attachments=[{"fname": "invite.ics", "fcontent": body}],
			now=False,
			**facts,
		)


def _as_event(doc) -> dict:
	return {
		# A deleted event's name is given out again; its first save is not.
		"name": f"{doc.name}-{get_datetime(doc.creation):%Y%m%d%H%M%S}",
		"subject": doc.subject,
		"starts_on": get_datetime(doc.starts_on),
		"ends_on": get_datetime(doc.ends_on) if doc.ends_on else None,
		"all_day": bool(doc.all_day),
		"location": doc.location,
		"description": frappe.utils.strip_html_tags(doc.description or ""),
		"repeat": _rule(doc) if doc.repeat_this_event else None,
	}


#: frappe's repeat as the format's FREQ.
FREQ = {"Daily": "DAILY", "Weekly": "WEEKLY", "Monthly": "MONTHLY", "Yearly": "YEARLY"}


def _rule(doc) -> str | None:
	freq = FREQ.get(doc.repeat_on)
	if not freq:
		return None
	rule = f"FREQ={freq}"
	if freq == "WEEKLY":
		days = [
			code
			for field, code in zip(
				("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"),
				("MO", "TU", "WE", "TH", "FR", "SA", "SU"),
				strict=True,
			)
			if doc.get(field)
		]
		if days:
			rule += ";BYDAY=" + ",".join(days)
	if doc.repeat_till:
		rule += f";UNTIL={getdate(doc.repeat_till):%Y%m%d}T235959Z"
	return rule


def invitation(
	event: dict, method: str, organizer: str, guests: list[str], zone, now: datetime, site: str, sequence: int
) -> str:
	"""One event as an iCalendar invitation (RFC 5545 with iTIP's METHOD):
	REQUEST to add or update it, CANCEL to take it out. Pure.

	The UID is the event's, so each mail replaces the one before it in the
	guest's calendar, and SEQUENCE only ever grows."""
	host = site.split("://", 1)[-1]
	start, end = event["starts_on"], event.get("ends_on")
	lines = [
		"BEGIN:VCALENDAR",
		"VERSION:2.0",
		f"PRODID:-//{host}//OneCalendar//EN",
		"CALSCALE:GREGORIAN",
		f"METHOD:{method}",
		"BEGIN:VEVENT",
		f"UID:{escape(event['name'])}@{host}",
		f"DTSTAMP:{utc(now, zone)}",
		f"SEQUENCE:{sequence}",
	]
	if event["all_day"]:
		last = (end or start).date() + timedelta(days=1)
		lines += [f"DTSTART;VALUE=DATE:{start:%Y%m%d}", f"DTEND;VALUE=DATE:{last:%Y%m%d}"]
	else:
		lines += [f"DTSTART:{utc(start, zone)}", f"DTEND:{utc(end or start + timedelta(hours=1), zone)}"]
	if event.get("repeat"):
		lines.append(f"RRULE:{event['repeat']}")
	lines.append(f"SUMMARY:{escape(event['subject'])}")
	if event.get("location"):
		lines.append(f"LOCATION:{escape(event['location'])}")
	if event.get("description"):
		lines.append(f"DESCRIPTION:{escape(event['description'])}")
	lines.append(f"ORGANIZER:mailto:{organizer}")
	lines += [f"ATTENDEE;ROLE=REQ-PARTICIPANT;RSVP=TRUE:mailto:{one}" for one in guests]
	lines.append("STATUS:CANCELLED" if method == "CANCEL" else "STATUS:CONFIRMED")
	lines += ["END:VEVENT", "END:VCALENDAR"]
	return "".join(fold(line) + "\r\n" for line in lines)


# ------------------------------------------------------------------ starting soon


def soon() -> None:
	"""Every five minutes: each reminder that has come due and not been told."""
	if not frappe.db.get_value("Notification Type", "Starting Soon", "enabled"):
		return
	from onedesk.one_calendar import events

	now = now_datetime()
	day = getdate(now)
	found = events.candidates(day, getdate(now + AHEAD))
	if not found:
		return
	reminders = _reminders([one.name for one in found])
	for one in found:
		for starts, _ends in events.occurrences(one, day, getdate(now + AHEAD)):
			if starts <= now:
				continue
			for before in reminders.get(one.name) or ([] if one.all_day else [DEFAULT_BEFORE]):
				if not (starts - timedelta(minutes=before) <= now):
					continue
				key = f"one_calendar:soon:{one.name}:{starts.isoformat()}:{before}"
				if frappe.cache.get_value(key):
					continue
				frappe.cache.set_value(key, 1, expires_in_sec=3 * 86400)
				_starting(one, starts)


def _reminders(names: list[str]) -> dict[str, list[int]]:
	"""Each event's reminders in minutes before it starts, from frappe's own
	reminders table."""
	out = {}
	for row in frappe.get_all(
		"Event Notifications",
		filters={"parenttype": "Event", "parent": ["in", names]},
		fields=["parent", "before", "interval"],
	):
		minutes = int(row.before or 0) * INTERVAL.get((row.interval or "minutes").lower(), 1)
		out.setdefault(row.parent, []).append(minutes)
	return out


def _starting(event, starts: datetime) -> None:
	doc = frappe.get_doc("Event", event.name)
	users = [user for user in people(doc).values() if user]
	if not users:
		return
	notify.notify(
		"Starting Soon",
		users,
		record=("Event", doc.name),
		link=_link(doc),
		sender="Administrator",
		event=doc.subject,
		time=format_datetime(starts, "HH:mm"),
		where=f", {doc.location}" if doc.location else "",
	)


# ------------------------------------------------------------------ each morning


def today_events() -> None:
	"""Each morning: every person's own day, as their calendar shows it — their
	events and everybody's — when there is something on it."""
	if not frappe.db.get_value("Notification Type", "Today's Events", "enabled"):
		return
	from onedesk.one_calendar import events

	day = getdate(today())
	users = frappe.get_all("User", filters={"enabled": 1, "user_type": "System User"}, pluck="name")
	for user in users:
		if user in ("Administrator", "Guest"):
			continue
		try:
			frappe.set_user(user)
			rows = {one["id"]: one for one in events.mine(day, day) + events.company(day, day)}
		finally:
			frappe.set_user("Administrator")
		if not rows:
			continue
		ordered = sorted(rows.values(), key=lambda one: (not one["all_day"], get_datetime(one["start"])))
		listed = Markup("<br>").join(
			Markup("{} · {}").format(
				_("All day") if one["all_day"] else format_datetime(one["start"], "HH:mm"), one["title"]
			)
			for one in ordered
		)
		notify.notify(
			"Today's Events",
			user,
			link="/desk/onecalendar",
			sender="Administrator",
			count=len(ordered),
			events=listed,
		)
