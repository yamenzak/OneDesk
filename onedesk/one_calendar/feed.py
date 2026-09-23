"""The calendar as a link other calendar apps subscribe to.

Google Calendar (*From URL*), Apple Calendar (*New Calendar Subscription*) and
Outlook (*Subscribe from web*) all read the same thing: an iCalendar file at an
address. Each person has one address, with a secret in it, and whoever holds
the address reads that person's calendar — so it is shown once, a new one
switches the old one off, and only its hash is kept.

It carries the layers that are on before anybody chooses, read as that person,
so it holds nothing they could not see on the calendar itself. It is one way:
an event added in Google stays in Google. frappe's own Google Calendar
integration syncs both ways for Events, and needs Google API keys to do it.
"""

import hashlib
import secrets
from datetime import datetime
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, get_system_timezone, get_url, getdate, now_datetime, nowdate

from onedesk.one_calendar import layers

#: The days a subscription carries, before today and after it.
BEHIND, AHEAD = 60, 365

#: What the method is called at, for the address.
METHOD = "onedesk.one_calendar.feed.ics"

#: The longest line the format allows, in bytes.
LINE = 75


@frappe.whitelist(methods=["POST"])
def link() -> dict:
	"""A new address for the reader's calendar. Any older one stops working."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Log in to make a calendar link."), frappe.PermissionError)
	token = secrets.token_urlsafe(24)
	values = {"token_hash": _hash(token), "made_on": now_datetime(), "last_read": None}
	if frappe.db.exists("Calendar Feed", frappe.session.user):
		frappe.db.set_value("Calendar Feed", frappe.session.user, values)
	else:
		frappe.get_doc({"doctype": "Calendar Feed", "user": frappe.session.user, **values}).insert(
			ignore_permissions=True
		)
	address = get_url(f"/api/method/{METHOD}?token={token}")
	return {"https": address, "webcal": "webcal://" + address.split("://", 1)[1]}


@frappe.whitelist()
@frappe.read_only()
def status() -> dict | None:
	"""Whether the reader has a link, when it was made and last read."""
	return frappe.db.get_value("Calendar Feed", frappe.session.user, ["made_on", "last_read"], as_dict=True)


@frappe.whitelist(methods=["POST"])
def stop() -> None:
	"""Switch the reader's link off."""
	frappe.db.delete("Calendar Feed", {"user": frappe.session.user})


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=120, seconds=60 * 60)
def ics(token: str) -> None:
	"""The calendar behind a link, as the person it belongs to."""
	user = frappe.db.get_value("Calendar Feed", {"token_hash": _hash(token or "")}, "user")
	if not user or not frappe.db.get_value("User", user, "enabled"):
		frappe.throw(_("This calendar link does not work any more."), frappe.PermissionError)
	frappe.db.set_value("Calendar Feed", user, "last_read", now_datetime(), update_modified=False)
	frappe.set_user(user)
	keys = [one["key"] for one in layers.offered() if one["on"]]
	today = getdate(nowdate())
	found = layers.entries(str(add_days(today, -BEHIND)), str(add_days(today, AHEAD)), keys) if keys else []
	named = frappe.utils.get_fullname(user)
	frappe.response.update(
		{
			"type": "download",
			"filename": "calendar.ics",
			"content_type": "text/calendar",
			"display_content_as": "inline",
			"filecontent": calendar(
				found,
				f"{frappe.get_hooks('app_title', app_name='onedesk')[0]} · {named}",
				ZoneInfo(get_system_timezone()),
				datetime.now(ZoneInfo("UTC")),
				get_url(),
			).encode("utf-8"),
		}
	)


def _hash(token: str) -> str:
	return hashlib.sha256(token.encode()).hexdigest()


# ----------------------------------------------------------- the format


def calendar(found: list[dict], name: str, zone, now: datetime, site: str) -> str:
	"""An iCalendar file (RFC 5545) of calendar entries. Pure.

	Times are written in UTC, so no calendar app has to know the workspace's
	zone; an all-day entry is a date, and its end is the day after, as it is on
	the calendar."""
	host = site.split("://", 1)[-1]
	lines = [
		"BEGIN:VCALENDAR",
		"VERSION:2.0",
		f"PRODID:-//{host}//Calendar//EN",
		"CALSCALE:GREGORIAN",
		"METHOD:PUBLISH",
		f"X-WR-CALNAME:{escape(name)}",
		"REFRESH-INTERVAL;VALUE=DURATION:PT1H",
		"X-PUBLISHED-TTL:PT1H",
	]
	stamp = now.strftime("%Y%m%dT%H%M%SZ")
	for one in found:
		start, end = datetime.fromisoformat(one["start"]), datetime.fromisoformat(one["end"])
		lines += ["BEGIN:VEVENT", f"UID:{escape(one['id'])}@{host}", f"DTSTAMP:{stamp}"]
		if one["all_day"]:
			lines += [f"DTSTART;VALUE=DATE:{start:%Y%m%d}", f"DTEND;VALUE=DATE:{end:%Y%m%d}"]
		else:
			lines += [f"DTSTART:{utc(start, zone)}", f"DTEND:{utc(end, zone)}"]
		lines.append(f"SUMMARY:{escape(one['title'])}")
		if one.get("description"):
			lines.append(f"DESCRIPTION:{escape(one['description'])}")
		lines += [f"URL:{site}/desk/{slug(one['doctype'])}/{one['name']}", "END:VEVENT"]
	lines.append("END:VCALENDAR")
	return "".join(fold(line) + "\r\n" for line in lines)


def utc(when: datetime, zone) -> str:
	"""A workspace time as the format's UTC stamp. Pure."""
	return when.replace(tzinfo=zone).astimezone(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")


def escape(text) -> str:
	"""Text as a property value: backslash, semicolon, comma and newline
	escaped. Pure."""
	said = str(text or "")
	for plain, written in (("\\", "\\\\"), (";", "\\;"), (",", "\\,"), ("\r\n", "\\n"), ("\n", "\\n")):
		said = said.replace(plain, written)
	return said


def fold(line: str) -> str:
	"""A line cut into LINE-byte pieces, each after the first starting with a
	space, never through a character. Pure."""
	out, piece = [], ""
	for char in line:
		limit = LINE if not out else LINE - 1
		if len((piece + char).encode("utf-8")) > limit:
			out.append(piece)
			piece = char
		else:
			piece += char
	out.append(piece)
	return "\r\n ".join(out)


def slug(doctype: str) -> str:
	return doctype.lower().replace(" ", "-")
