"""What OneCalendar tells people, and when (the types are in notifications/one_calendar/)."""

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
	gone = {email: user for email, user in was.items() if email not in now}
	if gone:
		_taken_off(doc, gone)
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
	# Shared with somebody (OneIntake's events are made by OneAI and shared
	# with whoever they are for): they are on it too.
	for user in (
		frappe.get_all("DocShare", filters={"share_doctype": "Event", "share_name": doc.name}, pluck="user")
		if doc.get("name") and not doc.is_new()
		else []
	):
		email = frappe.db.get_value("User", {"name": user, "enabled": 1}, "email")
		if email:
			out[email.lower()] = user
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
	_mail(doc, [email for email, user in stayed.items() if not user], "REQUEST", facts, changed=True)


def _taken_off(doc, gone: dict) -> None:
	"""People taken off an event: told in One, and a guest outside sent its
	cancellation, so it leaves their calendar."""
	facts = _facts(doc)
	users = [user for user in gone.values() if user and user != frappe.session.user]
	if users:
		notify.notify("Taken Off an Event", users, link="/desk/onecalendar", **facts)
	_mail(doc, [email for email, user in gone.items() if not user], "CANCEL", facts)


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


def _mail(doc, emails: list[str], method: str, facts: dict, changed: bool = False) -> None:
	"""Each guest mailed the event as an invitation, a change to it, or its
	cancellation."""
	if not emails:
		return
	zone = ZoneInfo(frappe.utils.get_system_timezone())
	site = frappe.utils.get_url()
	organizer = frappe.db.get_value("User", doc.owner, "email") or doc.owner
	body = invitation(_as_event(doc), method, organizer, emails, zone, now_datetime(), site, int(time.time()))
	state = {"REQUEST": _("Changed") if changed else _("Invitation"), "CANCEL": _("Cancelled")}[method]
	said = _("cancelled") if method == "CANCEL" else _("changed") if changed else _("invites you to")
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
	# Nobody who said they are not coming.
	declined = {
		(row.email or "").lower() for row in doc.get("event_participants") or [] if row.attending == "No"
	}
	users = [user for email, user in people(doc).items() if user and email not in declined]
	if not users:
		return
	notify.notify(
		"Starting Soon",
		users,
		record=("Event", doc.name),
		link=_link(doc),
		sender="Administrator",
		event=doc.subject,
		# The day too when it is not today, or tomorrow's reads as today's.
		time=format_datetime(starts, "HH:mm")
		if getdate(starts) == getdate(now_datetime())
		else format_datetime(starts, "EEE d MMM, HH:mm"),
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
