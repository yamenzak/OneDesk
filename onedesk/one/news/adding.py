"""Adding a News Source from the desk's Add News Source dialog
(news_source_list.js). A feed is found from whatever address a person
has, the site's or the feed's, and shown with its newest headlines before
it is added; the other kinds are made from the few things they need."""

from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, pretty_date

from onedesk.one import news
from onedesk.one.news import SOURCE, feeds, fetching, library

# Where a site keeps its feed when its page does not say.
USUAL = ("/feed", "/rss", "/rss.xml", "/feed.xml", "/atom.xml")
SHOWN = 3
KINDS = ("Feed", "Google News", "OneAI", "Written")


def address(said: str) -> str:
	"""What a person typed as an https address: a bare site gets https. Pure."""
	said = (said or "").strip()
	if said and "://" not in said:
		said = f"https://{said}"
	if said.startswith("http://"):
		said = "https://" + said[len("http://") :]
	return said


def _read(url: str) -> dict | None:
	"""The feed at an address, or the page found there when it is not one."""
	_status, body, _etag, _modified = feeds.get(url)
	try:
		return {"url": url, **feeds.read(body)}
	except feeds.Unreadable:
		return {"url": url, "page": body}


def _found(url: str) -> dict:
	"""The feed at an address, or the first one its page names, or the
	library's for its site, or one at a usual place on its site."""
	first = _read(url)
	if "items" in first:
		return first
	named = feeds.site_name(first["page"])
	tried = {url}
	shelf = [row["url"] for row in library._library() if library.site(row["url"]) == library.site(url)]
	for one in [*feeds.linked(first["page"], url)[:3], *shelf[:1]]:
		tried.add(one)
		try:
			said = _read(one)
		except feeds.Unreadable:
			continue
		if "items" in said:
			return {**said, "named": named}
	root = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
	for path in USUAL:
		if root + path in tried:
			continue
		try:
			said = _read(root + path)
		except feeds.Unreadable:
			continue
		if "items" in said:
			return {**said, "named": named}
	raise feeds.Unreadable(_("No feed was found at this address. Try the feed's own address."))


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=20, seconds=60)
def find(url: str) -> dict:
	"""A feed from a site's or a feed's address, with its name, its site and
	its newest headlines, and the source it already is, if any."""
	frappe.has_permission(SOURCE, "create", throw=True)
	try:
		said = _found(address(url))
	except feeds.Unreadable as raised:
		return {"error": str(raised)}
	home = said.get("home") or ""
	site = feeds.site_of(home or said["url"])
	return {
		"url": said["url"],
		"name": said.get("named") or feeds.named(said.get("title")) or site,
		"site": site,
		"logo": news.logos({site}).get(site, ""),
		"there": frappe.db.get_value(SOURCE, {"feed_url": said["url"]}, "name") or "",
		"headlines": [
			{"title": one["title"], "ago": pretty_date(one["published"]) if one.get("published") else ""}
			for one in said["items"][:SHOWN]
		],
	}


def _unique(name: str) -> str:
	base, n = (name or "").strip()[:120] or _("News"), 1
	name = base
	while frappe.db.exists(SOURCE, name):
		n += 1
		name = f"{base} {n}"
	return name


@frappe.whitelist(methods=["POST"])
def add(kind: str, name: str = "", category: str = "", **values) -> str:
	"""A News Source of one kind from what the dialog asked for; fetched at
	the next tick."""
	frappe.has_permission(SOURCE, "create", throw=True)
	if kind not in KINDS:
		frappe.throw(_("Choose a type of source."))
	doc = {"doctype": SOURCE, "kind": kind, "category": news.category(category)}
	if kind == "Feed":
		doc["feed_url"] = address(values.get("feed_url"))
		there = frappe.db.get_value(SOURCE, {"feed_url": doc["feed_url"]}, "name")
		if there:
			return there
		name = name or feeds.site_of(doc["feed_url"])
	elif kind == "Google News":
		doc.update(
			google_topic=values.get("google_topic") or "Top Stories",
			google_query=(values.get("google_query") or "").strip(),
			country=values.get("country") or None,
			language=values.get("language") or None,
		)
		topic = doc["google_topic"]
		name = name or f"Google News · {doc['google_query'] or _(topic)}"
	elif kind == "OneAI":
		doc.update(
			ai_brief=(values.get("ai_brief") or "").strip(),
			fetch_every=fetching.SET_TIMES,
			fetch_at=values.get("fetch_at") or "07:00",
			country=values.get("country") or None,
			language=values.get("language") or None,
		)
		name = name or f"OneAI · {doc['ai_brief'][:40]}"
	doc["source_name"] = _unique(name)
	return frappe.get_doc(doc).insert().name


@frappe.whitelist(methods=["POST"])
def add_many(urls: str | list) -> list[str]:
	"""Several library feeds at once, each under its library name."""
	from onedesk.one.news import library

	frappe.has_permission(SOURCE, "create", throw=True)
	urls = frappe.parse_json(urls) if isinstance(urls, str) else urls
	return [library.add(url) for url in (urls or [])[: cint(library.SHOWN)]]


@frappe.whitelist()
@frappe.read_only()
def start() -> dict:
	"""What the dialog needs before it asks anything: whether Google News is
	on, and the workspace's country and language to start from."""
	from onedesk.one_legal import services

	frappe.has_permission(SOURCE, "create", throw=True)
	return {
		"google": bool(services.on(fetching.GOOGLE_SERVICE)),
		"country": frappe.db.get_default("country") or "",
		"language": frappe.db.get_default("lang") or "en",
	}


@frappe.whitelist()
@frappe.read_only()
def latest(name: str) -> dict:
	"""A source's newest headlines and when it was fetched, for its form."""
	frappe.has_permission(SOURCE, "read", name, throw=True)
	source = frappe.db.get_value(SOURCE, name, ["kind", "last_fetched", "next_fetch"], as_dict=True)
	return {
		"fetched": pretty_date(source.last_fetched) if source.last_fetched else "",
		"next": frappe.utils.format_datetime(source.next_fetch, "HH:mm") if source.next_fetch else "",
		"items": [
			{"name": one["name"], "title": one["title"], "ago": one["ago"], "link": one["link"]}
			for one in news.items([name], most=6)
		],
	}
