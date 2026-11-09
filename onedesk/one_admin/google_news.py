"""Google News for every workspace, fetched by OneAdmin alone, one edition
at a time on its own timer, and shared by every workspace that follows the
same topic or search. How gently it asks is in AGENTS.md, under Google
News."""

import hashlib
from datetime import datetime, timezone
from urllib.parse import urlencode

import frappe
from frappe.utils import cint, flt

from onedesk.one_admin import site
from onedesk.one_admin.faults import Refused

GOOGLE = "https://news.google.com/rss"
TOPICS = {
	"World": "WORLD",
	"Business": "BUSINESS",
	"Technology": "TECHNOLOGY",
	"Science": "SCIENCE",
	"Health": "HEALTH",
	"Sports": "SPORTS",
	"Entertainment": "ENTERTAINMENT",
}

REFRESH = 2 * 3600
FORGOTTEN = 3 * 86400
FIRST_PAUSE = 3600
LONGEST_PAUSE = 12 * 3600
KEPT = 40
# A workspace follows at most this many editions, so one cannot make the rest wait.
MOST_A_WORKSPACE = 10

EDITIONS = "one_google_news:editions"
HELD = "one_google_news:edition:{}"
FOLLOWED = "one_google_news:tenant:{}"
PAUSED = "one_google_news:paused"
LOCK = "one_google_news:fetching"


def url(topic: str | None, query: str | None, country: str | None, language: str | None) -> str:
	"""Google News' own RSS for a topic or a search, in a country and
	language. Pure."""
	country = (country or "US").upper()[:2]
	language = (language or "en").split("-")[0].lower()[:3]
	where = {"hl": f"{language}-{country}", "gl": country, "ceid": f"{country}:{language}"}
	query = " ".join((query or "").split())[:200]
	if query:
		return f"{GOOGLE}/search?{urlencode({'q': query, **where})}"
	if topic in TOPICS:
		return f"{GOOGLE}/headlines/section/topic/{TOPICS[topic]}?{urlencode(where)}"
	return f"{GOOGLE}?{urlencode(where)}"


def edition(address: str) -> str:
	"""An edition's short name, from its address. Pure."""
	return hashlib.sha1(address.encode()).hexdigest()[:16]


def untitled(title: str, publisher: str) -> str:
	"""A Google News headline without the " - Publisher" it ends with. Pure."""
	if publisher and title.endswith(f" - {publisher}"):
		return title[: -len(publisher) - 3].strip()
	return title


def next_one(held: list[dict], now: float) -> dict | None:
	"""The one edition to fetch now: one never fetched, the longest asked for
	first; else the stalest past REFRESH. Pure."""
	never = sorted((one for one in held if not one.get("at")), key=lambda one: flt(one.get("since")))
	if never:
		return never[0]
	stale = sorted(
		(one for one in held if now - flt(one.get("at")) >= REFRESH), key=lambda one: flt(one.get("at"))
	)
	return stale[0] if stale else None


def pause_after(pauses: int) -> int:
	"""Seconds every fetch waits after Google's `pauses`th refusal in a row. Pure."""
	return min(FIRST_PAUSE * 2 ** max(pauses - 1, 0), LONGEST_PAUSE)


def _now() -> float:
	return datetime.now(timezone.utc).timestamp()


def _names() -> set[str]:
	return {one.decode() if isinstance(one, bytes) else one for one in frappe.cache.smembers(EDITIONS) or ()}


def headlines(tenant: str, topic: str = "", query: str = "", country: str = "", language: str = "en") -> dict:
	"""What OneAdmin last fetched for an edition. Never fetches: an edition
	asked for the first time is fetched at a coming tick, and `waiting` says
	so."""
	address = url(topic, query, country, language)
	name = edition(address)
	followed = FOLLOWED.format(tenant)
	mine = {one.decode() if isinstance(one, bytes) else one for one in frappe.cache.smembers(followed) or ()}
	if name not in mine and len(mine & _names()) >= MOST_A_WORKSPACE:
		raise Refused(f"A workspace follows at most {MOST_A_WORKSPACE} Google News topics or searches.")
	now = _now()
	held = frappe.cache.get_value(HELD.format(name)) or {"url": address, "since": now}
	held["asked"] = now
	frappe.cache.set_value(HELD.format(name), held)
	frappe.cache.sadd(EDITIONS, name)
	frappe.cache.sadd(followed, name)
	frappe.cache.expire_key(followed, FORGOTTEN)
	return {
		"items": held.get("items") or [],
		"fetched": held.get("at") or 0,
		"waiting": not held.get("at"),
	}


def tick() -> None:
	"""The cron entry, on the admin site only: drop what nobody asks for,
	then fetch at most one edition. Never raises."""
	if not site.is_admin():
		return
	try:
		_tick()
	except Exception:
		frappe.log_error(title="Google News")


def _tick() -> None:
	now = _now()
	paused = frappe.cache.get_value(PAUSED) or {}
	if flt(paused.get("until")) > now:
		return
	held = []
	for name in _names():
		one = frappe.cache.get_value(HELD.format(name))
		if not one or now - flt(one.get("asked")) > FORGOTTEN:
			frappe.cache.srem(EDITIONS, name)
			frappe.cache.delete_value(HELD.format(name))
			continue
		held.append({**one, "name": name})
	chosen = next_one(held, now)
	if not chosen or not frappe.cache.set(frappe.cache.make_key(LOCK), 1, nx=True, ex=240):
		return
	try:
		items = _fetch(chosen["url"])
	except Exception:
		pauses = cint(paused.get("pauses")) + 1
		frappe.cache.set_value(PAUSED, {"until": now + pause_after(pauses), "pauses": pauses})
		frappe.log_error(title="Google News refused a fetch")
		return
	finally:
		frappe.cache.delete(frappe.cache.make_key(LOCK))
	frappe.cache.delete_value(PAUSED)
	name = chosen.pop("name")
	current = frappe.cache.get_value(HELD.format(name)) or chosen
	current.update(items=items, at=now)
	frappe.cache.set_value(HELD.format(name), current)


def _fetch(address: str) -> list[dict]:
	from onedesk.one.news import feeds

	status, body, _etag, _modified = feeds.get(address)
	said = feeds.read(body) if status == 200 else {"items": []}
	out = []
	for one in said["items"][:KEPT]:
		published = one.get("published")
		out.append(
			{
				**one,
				"title": untitled(one["title"], one["publisher"]),
				"summary": "",
				"published": published.isoformat() if published else "",
			}
		)
	return out

