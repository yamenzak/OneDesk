"""Events, and who may see one.

An Event is frappe's: something at a time, with a subject, a place and the
people it is with. frappe lets a person see a Public event, one they made, one
shared with them, and one they are a participant in. **One adds a fifth: an
event about a record is visible to whoever may read that record** — a meeting
about a deal is on the calendar of everybody who may open the deal, as the deal
itself is. An event is about a record when its Reference, one of its Links or
one of its participants names it.

frappe's permission hooks can only take access away, never grant it, so this is
not a hook: the calendar reads Events itself, here, and shows such an event
without opening it. Clicking it opens the record it is about. The Event's own
form still follows frappe's rule, which is why editing one stays with the
person who made it.

Repeating events are expanded here too (`occurrences`), on the days shown.

**A Public event is on everybody's calendar**, so making one is kept to the
people who speak for the workspace (PUBLISHERS). frappe lets any desk user do
it, and a calendar anybody can write on is a calendar nobody reads.
"""

from datetime import date, datetime, timedelta

import frappe
from frappe import _lt
from frappe.utils import add_months, add_years, get_datetime, getdate

from onedesk.one_calendar import layers

#: The weekday fields a Weekly event ticks, Monday first as `weekday()` counts.
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")

#: Who may put an event on everybody's calendar. The New Event dialog offers
#: it to the same roles (onecalendar.js).
PUBLISHERS = ("Workspace Administrator", "HR Manager")

#: How far a repeat is looked for, so a daily event from years ago still ends.
MOST_REPEATS = 400

LAYERS = [
	{
		"key": "my-events",
		"label": _lt("My Events"),
		"color": "blue",
		"group": "Mine",
		"doctype": "Event",
		"rows": "onedesk.one_calendar.events.mine",
		"move": "onedesk.one_calendar.events.move",
	},
	{
		"key": "company-events",
		"label": _lt("Company Events"),
		"color": "cyan",
		"group": "Workspace",
		"doctype": "Event",
		"rows": "onedesk.one_calendar.events.company",
		"move": "onedesk.one_calendar.events.move",
	},
	{
		"key": "events-about",
		"label": _lt("Events"),
		"color": "blue",
		"group": "Workspace",
		"doctype": "Event",
		"rows": "onedesk.one_calendar.events.about",
		"move": "onedesk.one_calendar.events.move",
		"about": ["*"],
		"only_about": True,
	},
]


def mine(start, end) -> list[dict]:
	return _rows(start, end, "mine")


def company(start, end) -> list[dict]:
	return _rows(start, end, "company")


def about(start, end, record: tuple) -> list[dict]:
	"""The events about one record, on that record's calendar. The reader may
	open the record (layers._about), which is what shows them."""
	return _rows(start, end, "about", tuple(record))


def _rows(start, end, wanted: str, record: tuple | None = None) -> list[dict]:
	user = frappe.session.user
	found = candidates(start, end)
	if not found:
		return []
	names = [one.name for one in found]
	shared = set(
		frappe.get_all(
			"DocShare",
			filters={"share_doctype": "Event", "share_name": ["in", names], "user": user},
			pluck="share_name",
		)
	)
	people, about = _participants(names)
	for one in found:
		about.setdefault(one.name, set())
		if one.reference_doctype and one.reference_docname:
			about[one.name].add((one.reference_doctype, one.reference_docname))
	for link in frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Event", "parent": ["in", names]},
		fields=["parent", "link_doctype", "link_name"],
	):
		about[link.parent].add((link.link_doctype, link.link_name))

	readable = {}
	rows = []
	for one in found:
		records = sorted(about.get(one.name) or [])
		side = whose(one, user, one.name in shared, user in people.get(one.name, ()))
		opens = ("Event", one.name)
		if record:
			# On the record's own calendar: every event about it, opening the
			# event when frappe's rule lets the reader, the record otherwise.
			if record not in records:
				continue
			side, opens = "about", opens if side else record
		elif side is None:
			# Visible only because of a record it is about, if any is readable.
			record = next((pair for pair in records if _can_read(pair, readable)), None)
			if not record:
				continue
			side, opens = "company", record
		if side != wanted:
			continue
		for starts, ends in occurrences(one, start, end):
			rows.append(
				{
					"id": f"{one.name}:{starts.isoformat()}",
					"name": opens[1],
					"doctype": opens[0],
					"title": one.subject,
					"start": starts,
					"end": ends,
					"all_day": one.all_day,
					"editable": one.owner == user and not one.repeat_this_event,
					"description": layers.plain(one.description, 300) or None,
					"about": list(records[0]) if records else None,
				}
			)
	return rows


def whose(event, user: str, shared: bool, participant: bool) -> str | None:
	"""Which layer an event belongs on for this user, by frappe's own rule, or
	None when frappe's rule does not show it to them. Pure."""
	if event.owner == user or shared or participant:
		return "mine"
	if event.event_type == "Public":
		return "company"
	return None


def candidates(start, end) -> list:
	"""Open events on the days shown, and repeating ones that began before."""
	return frappe.db.sql(
		"""
		select name, subject, description, owner, event_type, starts_on, ends_on, all_day,
			repeat_this_event, repeat_on, repeat_till, monday, tuesday, wednesday,
			thursday, friday, saturday, sunday, reference_doctype, reference_docname
		from `tabEvent`
		where status = 'Open'
			and (
				(date(starts_on) <= %(end)s and date(coalesce(ends_on, starts_on)) >= %(start)s)
				or (repeat_this_event = 1 and date(starts_on) <= %(end)s
					and coalesce(repeat_till, '3000-01-01') >= %(start)s)
			)
		order by starts_on
		""",
		{"start": start, "end": end},
		as_dict=True,
	)


def _participants(names: list[str]) -> tuple[dict, dict]:
	people, about = {}, {}
	for row in frappe.get_all(
		"Event Participants",
		filters={"parenttype": "Event", "parent": ["in", names]},
		fields=["parent", "email", "reference_doctype", "reference_docname"],
	):
		if row.email:
			people.setdefault(row.parent, set()).add(row.email)
		if row.reference_doctype and row.reference_docname:
			about.setdefault(row.parent, set()).add((row.reference_doctype, row.reference_docname))
	return people, about


def _can_read(pair: tuple, seen: dict) -> bool:
	if pair not in seen:
		doctype, name = pair
		seen[pair] = bool(
			frappe.db.exists("DocType", doctype)
			and frappe.db.exists(doctype, name)
			and frappe.has_permission(doctype, "read", doc=name)
		)
	return seen[pair]


def occurrences(event, start: date, end: date) -> list[tuple[datetime, datetime | None]]:
	"""When an event happens on the days shown: once, or each time it repeats.
	Pure.

	A repeat keeps the first time's hour and its length. Weekly repeats on the
	days ticked, or on the first time's weekday when none is."""
	first = get_datetime(event.starts_on)
	length = (get_datetime(event.ends_on) - first) if event.ends_on else None

	def at(day: date):
		starts = datetime.combine(day, first.time())
		return starts, (starts + length) if length is not None else None

	if not event.repeat_this_event:
		last = get_datetime(event.ends_on).date() if event.ends_on else first.date()
		return (
			[(first, get_datetime(event.ends_on) if event.ends_on else None)]
			if last >= start and first.date() <= end
			else []
		)

	until = min(end, getdate(event.repeat_till) if event.repeat_till else end)
	days = []
	rule = event.repeat_on
	if rule in ("Daily", "Weekly"):
		ticked = {i for i, name in enumerate(WEEKDAYS) if event.get(name)} or {first.weekday()}
		day = max(first.date(), start)
		while day <= until and len(days) < MOST_REPEATS:
			if rule == "Daily" or day.weekday() in ticked:
				days.append(day)
			day += timedelta(days=1)
	else:
		step = {"Monthly": 1, "Quarterly": 3, "Half Yearly": 6, "Yearly": 12}.get(rule)
		if not step:
			return [at(first.date())] if start <= first.date() <= end else []
		n, day = 0, first.date()
		while day <= until and n < MOST_REPEATS:
			if day >= start:
				days.append(day)
			n += 1
			day = add_years(first.date(), n) if step == 12 else add_months(first.date(), step * n)
			day = getdate(day)
	return [at(day) for day in days]


def move(event: str, start: str, end: str | None = None, all_day: int | None = None) -> None:
	"""An event dragged to another time (layers.move). As its maker, through
	its own save."""
	doc = frappe.get_doc("Event", event)
	doc.check_permission("write")
	if doc.repeat_this_event:
		frappe.throw(frappe._("A repeating event can only be moved from its own page."))
	doc.starts_on = get_datetime(start)
	doc.ends_on = get_datetime(end) if end else None
	if all_day is not None:
		doc.all_day = int(all_day)
	doc.save()


def validate(doc, method=None) -> None:
	"""Guests typed as addresses become participants; and only a publisher
	makes an event Public, or keeps editing one."""
	if doc.get("one_guests"):
		# An address carried in by a suggestion OneAI made (ai.py plan_event) or
		# typed anywhere else: each becomes a participant, a Contact if needed.
		invite(doc, None, doc.one_guests)
		doc.one_guests = None
	if doc.event_type != "Public" or frappe.flags.in_install or frappe.flags.in_migrate:
		return
	before = doc.get_doc_before_save()
	if before and before.event_type == "Public" and doc.owner == frappe.session.user:
		return
	if not set(PUBLISHERS) & set(frappe.get_roles()):
		frappe.throw(
			frappe._(
				"Only a Workspace Administrator or HR Manager can put an event on everyone's calendar."
			),
			frappe.PermissionError,
		)


# ------------------------------------------------------------------ making and showing


@frappe.whitelist(methods=["POST"])
def make(values: str | dict) -> str:
	"""An event from Add Event, with the people it is for.

	Team members are invited by name, outside guests by address; both become
	frappe's own participants, which is what lets frappe show each of them the
	event. A guest is a Contact, found by their address or made for it, so the
	event is on their timeline. Being told of it is `tell.py`'s, on save."""
	values = frappe.parse_json(values) if isinstance(values, str) else dict(values or {})
	doc = frappe.get_doc(
		{
			"doctype": "Event",
			"subject": (values.get("subject") or "").strip(),
			"all_day": 1 if values.get("all_day") else 0,
			"starts_on": values.get("starts_on"),
			"ends_on": values.get("ends_on") or None,
			"location": values.get("location"),
			"description": values.get("description"),
			"event_type": "Public" if values.get("public") else "Private",
			"reference_doctype": values.get("reference_doctype") or None,
			"reference_docname": values.get("reference_docname") or None,
		}
	)
	invite(doc, values.get("team"), None)
	doc.one_guests = values.get("guests") or None
	doc.insert()
	return doc.name


def invite(doc, team=None, guests=None) -> None:
	"""People added to an event as its participants: team members by user,
	guests by address. Nobody is added twice, and the maker is not added."""
	team = frappe.parse_json(team) if isinstance(team, str) and team.strip().startswith("[") else team
	if isinstance(team, str):
		team = [one.strip() for one in team.split(",")]
	have = {(row.email or "").lower() for row in doc.get("event_participants") or []}
	me = frappe.session.user
	for user in team or []:
		found = frappe.db.get_value("User", {"name": user, "enabled": 1}, ["name", "email"], as_dict=True)
		if not found or found.name == me or (found.email or "").lower() in have:
			continue
		doc.append(
			"event_participants",
			{"reference_doctype": "User", "reference_docname": found.name, "email": found.email},
		)
		have.add((found.email or "").lower())
	for email in addresses(guests):
		if email in have:
			continue
		user = frappe.db.get_value("User", {"email": email, "enabled": 1}, "name")
		if user:
			doc.append(
				"event_participants", {"reference_doctype": "User", "reference_docname": user, "email": email}
			)
		else:
			doc.append(
				"event_participants",
				{"reference_doctype": "Contact", "reference_docname": contact(email), "email": email},
			)
		have.add(email)


def addresses(text) -> list[str]:
	"""Email addresses out of what was typed: commas, semicolons, spaces or
	lines between them; anything that is not one is left out. Pure."""
	import re

	if isinstance(text, list):
		text = ",".join(text)
	found = re.findall(r"[^\s,;<>]+@[^\s,;<>]+\.[^\s,;<>]+", text or "")
	return list(dict.fromkeys(one.lower() for one in found))


def contact(email: str) -> str:
	"""The Contact an address belongs to, made for it when there is none."""
	found = frappe.db.get_value("Contact Email", {"email_id": email, "parenttype": "Contact"}, "parent")
	if found:
		return found
	made = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": email.split("@", 1)[0],
			"email_ids": [{"email_id": email, "is_primary": 1}],
		}
	)
	# Made as a side effect of inviting them, which the person may do whether
	# or not they may add contacts by hand.
	made.insert(ignore_permissions=True)
	return made.name


@frappe.whitelist()
@frappe.read_only()
def card(name: str) -> dict:
	"""What the calendar shows when an event is clicked, for whoever sees it
	on their calendar: by frappe's rule (theirs, shared, invited, Public) or
	because it is about a record they may open. The card says whether they
	may open the event's own page and change it."""
	doc = frappe.get_doc("Event", name)
	user = frappe.session.user
	shared = bool(frappe.db.exists("DocShare", {"share_doctype": "Event", "share_name": name, "user": user}))
	people = {(row.email or "").lower() for row in doc.event_participants}
	opens = frappe.has_permission("Event", "read", doc=doc)
	if not (whose(doc, user, shared, user.lower() in people) or opens or _about_readable(doc)):
		frappe.throw(frappe._("That event is not on your calendar."), frappe.PermissionError)
	return {
		"name": doc.name,
		"subject": doc.subject,
		"starts_on": str(doc.starts_on),
		"ends_on": str(doc.ends_on) if doc.ends_on else None,
		"all_day": bool(doc.all_day),
		"repeats": doc.repeat_on if doc.repeat_this_event else None,
		"location": doc.location,
		"description": frappe.utils.sanitize_html(doc.description or ""),
		"join": doc.google_meet_link or None,
		"owner": frappe.utils.get_fullname(doc.owner),
		"public": doc.event_type == "Public",
		"people": [
			{
				"name": frappe.utils.get_fullname(row.reference_docname)
				if row.reference_doctype == "User"
				else (
					frappe.db.get_value(row.reference_doctype, row.reference_docname, "full_name")
					if row.reference_doctype == "Contact"
					else None
				)
				or row.email,
				"email": row.email,
				"answer": row.attending or None,
			}
			for row in doc.event_participants
		],
		"about": [doc.reference_doctype, doc.reference_docname]
		if doc.reference_doctype and doc.reference_docname
		else None,
		"can_open": bool(opens),
		"can_edit": bool(opens and frappe.has_permission("Event", "write", doc=doc)),
	}


def _about_readable(doc) -> bool:
	pairs = []
	if doc.reference_doctype and doc.reference_docname:
		pairs.append((doc.reference_doctype, doc.reference_docname))
	pairs += [(row.link_doctype, row.link_name) for row in doc.get("links") or []]
	seen = {}
	return any(_can_read(pair, seen) for pair in pairs)
