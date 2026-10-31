"""Reading a feed: one https request to a public address, at most three
redirects each checked again, nothing larger than FETCHED, and the answer
read as RSS or Atom by a parser that resolves no entity and fetches
nothing. Pure but for `get`."""

import html
import ipaddress
import re
import socket
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse

FETCHED = 2 * 1024 * 1024
TIMEOUT = 15
REDIRECTS = 3
AGENT = "One/1.0 (news reader)"
MOST = 100

ATOM = "{http://www.w3.org/2005/Atom}"
MEDIA = "{http://search.yahoo.com/mrss/}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"
DC = "{http://purl.org/dc/elements/1.1/}"


class Unreadable(Exception):
	"""A feed that could not be fetched or read, in words for the source."""


def public(url: str) -> str:
	"""The address, if it is https and every address its host names is on the
	public internet: a feed never reaches the workspace's own network."""
	parsed = urlparse(url or "")
	if parsed.scheme != "https" or not parsed.hostname:
		raise Unreadable("A feed is read over https.")
	try:
		found = socket.getaddrinfo(parsed.hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
	except OSError:
		raise Unreadable(f"{parsed.hostname} could not be found.") from None
	for *_rest, address in found:
		if not ipaddress.ip_address(address[0]).is_global:
			raise Unreadable("A feed is read from the public internet.")
	return url


def get(url: str, etag: str | None = None, modified: str | None = None):
	"""The feed's answer: (status, body, etag, last modified). 304 when it has
	not changed since the etag or date it gave last time."""
	import requests

	headers = {
		"User-Agent": AGENT,
		"Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.5",
	}
	if etag:
		headers["If-None-Match"] = etag
	if modified:
		headers["If-Modified-Since"] = modified
	for _hop in range(REDIRECTS + 1):
		try:
			answer = requests.get(
				public(url), timeout=TIMEOUT, headers=headers, stream=True, allow_redirects=False
			)
		except requests.RequestException as raised:
			raise Unreadable(
				f"{urlparse(url).hostname} could not be reached ({type(raised).__name__})."
			) from None
		if answer.status_code in (301, 302, 303, 307, 308) and answer.headers.get("Location"):
			url = urljoin(url, answer.headers["Location"])
			continue
		if answer.status_code == 304:
			return 304, b"", etag, modified
		if answer.status_code != 200:
			raise Unreadable(f"{urlparse(url).hostname} answered {answer.status_code}.")
		body = answer.raw.read(FETCHED + 1, decode_content=True)
		if len(body) > FETCHED:
			raise Unreadable("The feed is larger than two megabytes.")
		return 200, body, answer.headers.get("ETag"), answer.headers.get("Last-Modified")
	raise Unreadable("The feed moved more than three times.")


def text_of(value: str | None) -> str:
	"""Words without their markup or entities, on one line."""
	value = re.sub(r"<[^>]+>", " ", value or "")
	return " ".join(html.unescape(value).split())


def when(value: str | None) -> datetime | None:
	"""An RSS or Atom date, in UTC without its zone; None when unreadable."""
	value = (value or "").strip()
	if not value:
		return None
	try:
		found = parsedate_to_datetime(value)
	except (TypeError, ValueError, IndexError):
		try:
			found = datetime.fromisoformat(value.replace("Z", "+00:00"))
		except ValueError:
			return None
	if found.tzinfo:
		found = found.astimezone(UTC).replace(tzinfo=None)
	return found


def site_of(url: str | None) -> str:
	"""A website's bare host, without www. Pure."""
	host = (urlparse(url or "").hostname or "").lower()
	return host[4:] if host.startswith("www.") else host


def read(body: bytes) -> dict:
	"""A feed's own link and its items, newest first as the feed gives them:
	each with an id, title, summary, link, picture, date and, where the feed
	names one, the publisher it came from."""
	from lxml import etree

	parser = etree.XMLParser(
		recover=True, resolve_entities=False, no_network=True, huge_tree=False, remove_comments=True
	)
	try:
		root = etree.fromstring(body, parser)
	except etree.XMLSyntaxError:
		root = None
	if root is None:
		raise Unreadable("This is not an RSS or Atom feed.")
	items = root.findall(".//item") or root.findall(f".//{ATOM}entry")
	channel = root.find("channel")
	home = ""
	if channel is not None and (channel.findtext("link") or "").strip().startswith("http"):
		home = channel.findtext("link").strip()
	elif root.find(f"{ATOM}link[@rel='alternate']") is not None:
		home = root.find(f"{ATOM}link[@rel='alternate']").get("href") or ""
	elif root.find(f"{ATOM}link") is not None:
		home = root.find(f"{ATOM}link").get("href") or ""
	if not items and root.tag not in ("rss", f"{ATOM}feed") and channel is None:
		raise Unreadable("This is not an RSS or Atom feed.")
	return {
		"home": home if home.startswith("http") else "",
		"items": [one for one in (_item(item) for item in items[:MOST]) if one],
	}


def _first(item, *names) -> str:
	for name in names:
		found = item.find(name)
		if found is not None:
			value = "".join(found.itertext()).strip()
			if value:
				return value
	return ""


def _item(item) -> dict | None:
	title = text_of(_first(item, "title", f"{ATOM}title"))
	if not title:
		return None
	link = _first(item, "link")
	if not link.startswith("http"):
		atom = item.find(f"{ATOM}link[@rel='alternate']")
		atom = atom if atom is not None else item.find(f"{ATOM}link")
		link = atom.get("href") if atom is not None else ""
	described = _first(item, "description", f"{ATOM}summary", f"{CONTENT}encoded", f"{ATOM}content")
	image = _picture(item, described)
	source = item.find("source")
	publisher = text_of(source.text) if source is not None and source.text else ""
	publisher_site = site_of(source.get("url")) if source is not None and source.get("url") else ""
	guid = _first(item, "guid", f"{ATOM}id") or link or title
	return {
		"guid": guid[:480],
		"title": title[:480],
		"summary": text_of(described)[:600],
		"link": link if link.startswith("http") else "",
		"image": image,
		"published": when(_first(item, "pubDate", f"{ATOM}published", f"{ATOM}updated", f"{DC}date")),
		"publisher": publisher[:140],
		"publisher_site": publisher_site,
	}


def _picture(item, described: str) -> str:
	"""The item's picture: its media content or thumbnail, an image enclosure,
	or the first image in what it says. Only an https address is kept."""
	for name in (f"{MEDIA}content", f"{MEDIA}thumbnail", f"{MEDIA}group/{MEDIA}content"):
		for found in item.findall(name):
			url = found.get("url") or ""
			medium = (found.get("medium") or found.get("type") or "image").lower()
			if url.startswith("https://") and ("image" in medium or medium == ""):
				return url
	enclosure = item.find("enclosure")
	if (
		enclosure is not None
		and (enclosure.get("type") or "").startswith("image")
		and (enclosure.get("url") or "").startswith("https://")
	):
		return enclosure.get("url")
	found = re.search(r"<img[^>]+src=[\"'](https://[^\"']+)", described or "")
	return html.unescape(found.group(1)) if found else ""
