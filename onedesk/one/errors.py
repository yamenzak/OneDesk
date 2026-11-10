"""This workspace's own errors, sent to One's account in summary: the kind of
error, where in the code, how often and when. Never the traceback's text or
the data it was working on (one_admin/errors.py keeps them, README, Errors)."""

import hashlib
import re

import frappe
from frappe.utils import get_datetime, now_datetime

from onedesk.one import account

MOST = 200
TITLE_LONG = 140
CURSOR = "one_errors_sent_until"
FIRST_LOOK_DAYS = 7
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
LONG_NUMBER = re.compile(r"\b\d{4,}\b")
FRAME = re.compile(r'File "(?:[^"]*/)?apps/(?P<app>[^/"]+)/(?P<path>[^"]+)", line \d+, in (?P<fn>\S+)')
OURS = "onedesk"
EXCEPTION = re.compile(r"^([\w.]+(?:Error|Exception|Warning|Timeout|Denied|Fail(?:ed)?|Interrupt))\b")


def kind_of(traceback: str) -> str:
	"""The exception's own name, and nothing it said. Pure."""
	for line in reversed((traceback or "").strip().splitlines()):
		found = EXCEPTION.match(line.strip())
		if found:
			return found.group(1)
	return "Error"


def where_of(traceback: str) -> str:
	"""The last place in One's own code it passed, a file and a function, or
	the last place in any app when it never reached ours. Pure."""
	frames = FRAME.findall(traceback or "")
	if not frames:
		return ""
	ours = [one for one in frames if one[0] == OURS]
	app, path, fn = (ours or frames)[-1]
	return f"{app}/{path}:{fn}"


def scrubbed(title: str) -> str:
	"""A log's title with no address or long number left in it. Pure."""
	first = (title or "").splitlines()[0] if title else ""
	return LONG_NUMBER.sub("#", EMAIL.sub("…", first))[:TITLE_LONG]


def fingerprint_of(kind: str, where: str, title: str) -> str:
	"""The same fault gives the same print, whichever record it was on. Pure."""
	key = f"{kind}|{where}|{re.sub(r'[0-9a-fA-F]{6,}|#', '', title)}"
	return hashlib.sha256(key.encode()).hexdigest()[:32]


def summaries(rows: list[dict]) -> list[dict]:
	"""Error Log rows gathered by kind: one line each, with how many. Pure."""
	seen: dict[str, dict] = {}
	for row in rows:
		kind, where = kind_of(row.get("error")), where_of(row.get("error"))
		title = scrubbed(row.get("method"))
		print_ = fingerprint_of(kind, where, title)
		at = str(row.get("creation"))
		held = seen.setdefault(print_, {"fingerprint": print_, "title": title, "kind": kind, "where": where, "count": 0, "first_seen": at, "last_seen": at})
		held["count"] += 1
		held["first_seen"] = min(held["first_seen"], at)
		held["last_seen"] = max(held["last_seen"], at)
	return list(seen.values())


def pushed() -> None:
	"""Hourly: what this workspace's Error Log gained since the last push."""
	if not frappe.conf.get("one_admin") and not account.configured():
		return
	since = frappe.db.get_default(CURSOR)
	if not since:
		since = frappe.utils.add_days(now_datetime(), -FIRST_LOOK_DAYS)
	rows = frappe.get_all("Error Log", filters={"creation": [">", since]}, fields=["method", "error", "creation"], order_by="creation asc", limit=2000, ignore_permissions=True)
	if not rows:
		return
	newest = max(get_datetime(row.creation) for row in rows)
	summary = summaries(rows)[:MOST]
	if frappe.conf.get("one_admin"):
		from onedesk.one_admin import errors

		house = frappe.db.get_value("Tenant", {"is_house": 1})
		if house:
			errors.heard(house, summary)
	else:
		account.ask("onedesk.one_admin.proxy.errors_seen", rows=summary)
	frappe.db.set_default(CURSOR, str(newest))
