"""The library (library.json): feeds others gathered, which a workspace
adds with one click. plenaryapp/awesome-rss-feeds (CC0) and a few Gulf,
Arabic and German feeds of ours; whoever publishes a feed owns it."""

import json
from functools import lru_cache
from pathlib import Path

import frappe
from frappe import _

from onedesk.one import news
from onedesk.one.news import SOURCE

LIBRARY = Path(__file__).parent / "library.json"
SHOWN = 60


@lru_cache(maxsize=1)
def _library() -> tuple:
	return tuple(json.loads(LIBRARY.read_text(encoding="utf-8")))


def matching(rows, query: str = "", category: str = "", country: str = "") -> list[dict]:
	"""The library's feeds that match words, a category and a country. Pure."""
	words = query.lower().split()
	out = []
	for one in rows:
		if category and one["category"] != category:
			continue
		if country and one["country"] != country:
			continue
		if words and not all(word in f"{one['name']} {one['url']}".lower() for word in words):
			continue
		out.append(one)
	return out


@frappe.whitelist()
@frappe.read_only()
def search(query: str = "", category: str = "", country: str = "") -> dict:
	"""Feeds a workspace can add with one click, gathered by others: each
	with whether it is added already."""
	frappe.has_permission(SOURCE, "create", throw=True)
	rows = _library()
	added = set(frappe.get_all(SOURCE, filters={"kind": "Feed"}, pluck="feed_url"))
	found = matching(rows, query or "", category or "", (country or "").upper())
	return {
		"feeds": [{**one, "added": one["url"] in added} for one in found[:SHOWN]],
		"more": max(0, len(found) - SHOWN),
		"categories": sorted({one["category"] for one in rows}),
		"countries": sorted({one["country"] for one in rows if one["country"]}),
	}


@frappe.whitelist(methods=["POST"])
def add(url: str) -> str:
	"""One feed from the library as a News Source, fetched straight away."""
	frappe.has_permission(SOURCE, "create", throw=True)
	one = next((row for row in _library() if row["url"] == url), None)
	if not one:
		frappe.throw(_("This feed is not in the library."))
	there = frappe.db.get_value(SOURCE, {"feed_url": url}, "name")
	if there:
		return there
	name, n = one["name"], 1
	while frappe.db.exists(SOURCE, name):
		n += 1
		name = f"{one['name']} {n}"
	doc = frappe.get_doc(
		{
			"doctype": SOURCE,
			"source_name": name,
			"kind": "Feed",
			"feed_url": url,
			"category": news.category(_(one["category"])),
		}
	).insert()
	return doc.name


