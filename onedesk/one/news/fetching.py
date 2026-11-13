"""Bringing news in (one/news): when each News Source is fetched, how each
kind is asked, and keeping only its newest items. Reading them out is the
package's own (`news.items`)."""

import re
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import cint, convert_utc_to_system_timezone, get_datetime, now_datetime

from onedesk.one import registry
from onedesk.one.news import ITEM, SOURCE, feeds
from onedesk.one_admin import faults
from onedesk.trust_center import services

EVERY = {
	"15 Minutes": 15,
	"30 Minutes": 30,
	"Hourly": 60,
	"Every 3 Hours": 180,
	"Every 6 Hours": 360,
	"Every 12 Hours": 720,
	"Daily": 1440,
}
SET_TIMES = "At Set Times"
SLOWEST = 1440
# The least time between two runs of OneAI, which costs credits each time.
LEAST = {"OneAI": 360}
MOST_TIMES = 6
AT_ONCE = 20
FIRST_RETRY = 15

GOOGLE_SERVICE = "google_news"
GOOGLE = "onedesk.one_admin.proxy.google_news"
# A Google News source asks OneAdmin, never Google: hourly, or in ten
# minutes while OneAdmin has not fetched its edition yet. Not the
# workspace's to set; OneAdmin fetches Google on its own schedule.
GOOGLE_EVERY = 60
GOOGLE_WAITING = 10

AI = "onedesk.one_admin.proxy.news_brief"


def interval(kind: str, every: str) -> int:
	"""Minutes between two fetches of a source. Pure."""
	if kind == "Google News":
		return GOOGLE_EVERY
	return max(EVERY.get(every, 60), LEAST.get(kind, 0))


def times_in(said: str | None) -> list[tuple[int, int]]:
	"""07:00, 13:30 → [(7, 0), (13, 30)], sorted, each once. Pure; raises
	ValueError for a time it cannot read."""
	out = set()
	for one in re.split(r"[,\s;]+", said or ""):
		if not one:
			continue
		found = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?", one)
		if not found or int(found.group(1)) > 23 or int(found.group(2) or 0) > 59:
			raise ValueError(one)
		out.add((int(found.group(1)), int(found.group(2) or 0)))
	return sorted(out)


def next_at(kind: str, every: str, at: str | None, now: datetime, failures: int = 0) -> datetime:
	"""When a source is fetched next: after its interval, or at its next set
	time. After a failure it waits longer each time, up to a day. Pure."""
	if failures:
		wait = min(FIRST_RETRY * 2 ** (failures - 1), SLOWEST)
		return now + timedelta(minutes=max(wait, 60 if kind == "Google News" else 0))
	if every == SET_TIMES and kind != "Google News":
		times = times_in(at) or [(7, 0)]
		for day in (0, 1):
			for hour, minute in times:
				then = (now + timedelta(days=day)).replace(hour=hour, minute=minute, second=0, microsecond=0)
				if then > now:
					return then
	return now + timedelta(minutes=interval(kind, every))


def due() -> None:
	"""Every five minutes: each source whose time has come is fetched, in
	the background, one job each."""
	names = frappe.get_all(
		SOURCE,
		filters={"enabled": 1, "kind": ["!=", "Written"]},
		or_filters=[["next_fetch", "is", "not set"], ["next_fetch", "<=", now_datetime()]],
		order_by="next_fetch asc",
		pluck="name",
		limit=AT_ONCE,
	)
	for name in names:
		later(name)


def later(name: str) -> None:
	frappe.enqueue(
		"onedesk.one.news.fetching.fetch",
		queue="long" if frappe.db.get_value(SOURCE, name, "kind") == "OneAI" else "short",
		job_id=f"one_news:{name}",
		deduplicate=True,
		enqueue_after_commit=True,
		name=name,
	)


@frappe.whitelist()
def fetch_now(name: str) -> None:
	"""Fetch a source in the background now, from its form."""
	frappe.has_permission(SOURCE, "write", name, throw=True)
	later(name)


def fetch(name: str) -> int:
	"""Fetch one source and keep what is new; returns how many items came."""
	source = frappe.get_doc(SOURCE, name)
	now = now_datetime()
	values = {}
	added = 0
	try:
		said = _read(source, values)
		added = store(source, said["items"])
		values.update(last_fetched=now, last_error="", failures=0)
		if said.get("home") and not source.website:
			values["website"] = said["home"]
		failures = 0
	except (feeds.Unreadable, faults.Refused) as raised:
		failures = cint(source.failures) + 1
		values.update(last_error=str(raised), failures=failures)
	except Exception:
		failures = cint(source.failures) + 1
		values.update(last_error=_("Fetch failed. It will be retried automatically."), failures=failures)
		frappe.log_error(title=f"News from {name}")
	values["next_fetch"] = (
		now + timedelta(minutes=GOOGLE_WAITING)
		if values.get("waiting")
		else next_at(source.kind, source.fetch_every, source.fetch_at, now, failures)
	)
	values.pop("waiting", None)
	frappe.db.set_value(SOURCE, name, values, update_modified=False)
	if values.get("website"):
		from onedesk.one_mail import faces

		faces.dress_later(frappe.get_doc(SOURCE, name))
	if added:
		frappe.publish_realtime("one_news", {"source": name}, after_commit=True)
	return added


def _read(source, values: dict) -> dict:
	"""What a source says now: its items and its home page."""
	if source.kind == "Feed":
		status, body, etag, modified = feeds.get(source.feed_url, source.etag, source.last_modified)
		values.update(etag=etag or "", last_modified=modified or "")
		return {"items": [], "home": ""} if status == 304 else feeds.read(body)
	if source.kind == "Google News":
		return _google(source, values)
	if source.kind == "OneAI":
		return _ai(source)
	return {"items": [], "home": ""}


def _codes(source) -> tuple[str | None, str | None]:
	country = frappe.db.get_value("Country", source.country, "code") if source.country else None
	language = source.language or frappe.db.get_default("lang") or "en"
	return country, language


def _google(source, values: dict) -> dict:
	"""Google News, from OneAdmin: what it last fetched for this topic or
	search, shared with every workspace that follows the same. The
	workspace never reaches Google itself."""
	from onedesk.one import account

	if not services.on(GOOGLE_SERVICE):
		raise feeds.Unreadable(_("Google News is turned off. Turn it on in {0}.").format(registry.name("trust_center")))
	country, language = _codes(source)
	said = services.call(
		GOOGLE_SERVICE,
		account.ask,
		GOOGLE,
		topic=source.google_topic or "",
		query=source.google_query or "",
		country=country or "",
		language=language,
	) or {}
	values["waiting"] = bool(said.get("waiting"))
	items = []
	for one in said.get("items") or []:
		title = feeds.text_of(one.get("title"))
		if not title or not one.get("guid"):
			continue
		items.append(
			{
				"guid": str(one["guid"])[:480],
				"title": title[:480],
				"summary": "",
				"link": one.get("link") if str(one.get("link") or "").startswith("https://") else "",
				"image": "",
				"published": get_datetime(one["published"]) if one.get("published") else None,
				"publisher": feeds.text_of(one.get("publisher"))[:140],
				"publisher_site": feeds.site_of(f"https://{one.get('publisher_site') or ''}"),
			}
		)
	return {"items": items, "home": ""}


def _ai(source) -> dict:
	"""OneAI's headlines for the source's brief, searched with Google and
	written by the account, which charges for each run."""
	from onedesk.one import account

	country, language = _codes(source)
	said = account.ask(
		AI,
		brief=source.ai_brief,
		country=country or "",
		language=language,
		most=max(1, min(cint(source.ai_most) or 8, 20)),
	)
	items = []
	for one in (said or {}).get("items") or []:
		title = feeds.text_of(one.get("title"))
		if title:
			items.append(
				{
					"guid": f"{title}|{one.get('publisher_site') or ''}"[:480],
					"title": title[:480],
					"summary": feeds.text_of(one.get("summary"))[:600],
					"link": "",
					"image": "",
					"published": None,
					"publisher": feeds.text_of(one.get("publisher"))[:140],
					"publisher_site": feeds.site_of(f"https://{one.get('publisher_site') or ''}"),
				}
			)
	return {"items": items, "home": ""}


def store(source, entries: list[dict]) -> int:
	"""Keep the items not kept before, then only the source's newest."""
	known = set(frappe.get_all(ITEM, filters={"source": source.name}, pluck="guid"))
	now = now_datetime()
	added = 0
	for one in entries:
		if not one.get("guid") or one["guid"] in known:
			continue
		known.add(one["guid"])
		published = one.get("published")
		if published:
			published = convert_utc_to_system_timezone(published).replace(tzinfo=None)
		doc = frappe.get_doc(
			{
				"doctype": ITEM,
				"source": source.name,
				"category": source.category,
				"guid": one["guid"],
				"title": one["title"],
				"summary": one.get("summary") or "",
				"link": (one.get("link") or "")[:1000],
				"image": (one.get("image") or "")[:1000],
				"published": published if published and published <= now else now,
				"publisher": one.get("publisher") or "",
				"publisher_site": one.get("publisher_site") or "",
			}
		)
		doc.flags.ignore_permissions = True
		doc.flags.from_source = True
		doc.insert()
		added += 1
	prune(source.name, cint(source.keep))
	return added


def prune(source: str, keep: int) -> int:
	"""Delete a source's items past its newest `keep`; 0 keeps them all."""
	if keep <= 0:
		return 0
	old = frappe.get_all(
		ITEM,
		filters={"source": source},
		order_by="published desc, creation desc",
		pluck="name",
		start=keep,
		limit=10_000,
	)
	if old:
		frappe.db.delete(ITEM, {"name": ["in", old]})
	return len(old)


def check_times(said: str | None) -> list[tuple[int, int]]:
	try:
		times = times_in(said)
	except ValueError as raised:
		frappe.throw(_("{0} is not a valid time. Use a format like 07:00, 13:30.").format(str(raised)))
	if len(times) > MOST_TIMES:
		frappe.throw(_("A source can be fetched at most {0} times a day.").format(MOST_TIMES))
	return times


def soon(name: str) -> None:
	"""Fetch a changed source at the next tick."""
	frappe.db.set_value(SOURCE, name, {"next_fetch": now_datetime(), "failures": 0}, update_modified=False)
