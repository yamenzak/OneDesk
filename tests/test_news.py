"""News (one/news, one_admin/news.py): a feed read safely, each source on
its own schedule, Google News asked through its own RSS, and OneAI's
headlines kept only where its search found a publisher."""

import ast
import importlib.util
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

NEWS = tree.APP / "one" / "news"
spec = importlib.util.spec_from_file_location("feeds", NEWS / "feeds.py")
feeds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feeds)


def _lifted(source: str, names: tuple, **extra) -> dict:
	space = {"re": re, "datetime": datetime, "timedelta": timedelta, "urlencode": urlencode, **extra}
	for node in ast.parse(source).body:
		named = (
			getattr(node.targets[0], "id", "") if isinstance(node, ast.Assign) else getattr(node, "name", "")
		)
		if named in names:
			exec(ast.unparse(node), space)
	return space


ENGINE = _lifted(
	(NEWS / "fetching.py").read_text(),
	(
		"EVERY",
		"SET_TIMES",
		"SLOWEST",
		"LEAST",
		"FIRST_RETRY",
		"GOOGLE_EVERY",
		"interval",
		"times_in",
		"next_at",
	),
)
GOOGLE = _lifted(
	(tree.APP / "one_admin" / "google_news.py").read_text(),
	(
		"GOOGLE",
		"TOPICS",
		"REFRESH",
		"FIRST_PAUSE",
		"LONGEST_PAUSE",
		"url",
		"untitled",
		"next_one",
		"pause_after",
	),
	flt=float,
)
READER = _lifted((NEWS / "library.py").read_text(), ("matching",))
ADMIN = _lifted(
	(tree.APP / "one_admin" / "news.py").read_text(), ("SPLIT", "QUESTION", "asked", "lines", "domains")
)

RSS = b"""<?xml version="1.0"?>
<!DOCTYPE rss [<!ENTITY boom "BOOM">]>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
<channel><title>Gulf Daily</title><link>https://gulf.example/</link>
<item><title>Towers &amp; glass: a <b>record</b> year</title><link>https://gulf.example/a</link><guid>a-1</guid>
<pubDate>Sat, 31 Oct 2026 08:00:00 +0400</pubDate><description>&lt;p&gt;Output rose.&lt;/p&gt;&amp;boom;</description>
<media:content url="https://gulf.example/a.jpg" medium="image"/></item>
<item><title>Second</title><link>https://gulf.example/b</link><enclosure url="http://gulf.example/b.jpg" type="image/jpeg"/>
<source url="https://www.reuters.com">Reuters</source></item>
<item><title></title><link>https://gulf.example/c</link></item>
</channel></rss>"""

ATOM = b"""<feed xmlns="http://www.w3.org/2005/Atom"><title>A</title><link rel="alternate" href="https://atom.example/"/>
<entry><title>Atom one</title><id>tag:1</id><link href="https://atom.example/1"/><updated>2026-10-30T10:00:00Z</updated><summary>Short</summary></entry></feed>"""


def test_a_feed_is_read_without_its_entities_or_markup():
	pytest.importorskip("lxml")
	said = feeds.read(RSS)
	assert said["home"] == "https://gulf.example/"
	first, second = said["items"]
	assert first["title"] == "Towers & glass: a record year" and "BOOM" not in first["summary"]
	assert first["summary"].startswith("Output rose.") and first["image"] == "https://gulf.example/a.jpg"
	assert first["published"] == datetime(2026, 10, 31, 4, 0), "dates are kept in UTC"
	assert second["image"] == "", "a picture is kept only over https"
	assert (second["publisher"], second["publisher_site"]) == ("Reuters", "reuters.com")
	assert len(said["items"]) == 2, "an item without a title is not news"


def test_atom_is_read_too_and_anything_else_is_refused():
	pytest.importorskip("lxml")
	said = feeds.read(ATOM)
	assert said["home"] == "https://atom.example/" and said["items"][0]["guid"] == "tag:1"
	assert said["items"][0]["link"] == "https://atom.example/1" and said["items"][0]["summary"] == "Short"
	try:
		feeds.read(b"<html><body>not a feed</body></html>")
	except feeds.Unreadable:
		pass
	else:
		raise AssertionError("a web page is not a feed")


def test_a_feed_on_the_workspaces_own_network_is_refused():
	for url in ("http://news.example/rss", "https://127.0.0.1/rss", "https://localhost/rss"):
		try:
			feeds.public(url)
		except feeds.Unreadable:
			continue
		raise AssertionError(f"{url} is not read")


def test_each_kind_is_fetched_no_faster_than_it_may_be():
	interval = ENGINE["interval"]
	assert interval("Feed", "15 Minutes") == 15
	assert interval("Google News", "15 Minutes") == 60, "a Google News source asks OneAdmin hourly"
	assert interval("Google News", "Daily") == 60, "and how often is not the workspace's to set"
	assert interval("OneAI", "Hourly") == 360, "each OneAI run costs credits"


def test_set_times_come_round_and_failures_wait_longer():
	next_at, times_in = ENGINE["next_at"], ENGINE["times_in"]
	assert times_in("13:30, 7, 07:00") == [(7, 0), (13, 30)]
	for wrong in ("25:00", "7am"):
		try:
			times_in(wrong)
		except ValueError:
			continue
		raise AssertionError(wrong)
	now = datetime(2026, 10, 31, 9, 0)
	assert next_at("OneAI", "At Set Times", "07:00, 13:00", now) == datetime(2026, 10, 31, 13, 0)
	assert next_at("OneAI", "At Set Times", "07:00", now) == datetime(2026, 11, 1, 7, 0), (
		"tomorrow's when today's is past"
	)
	assert next_at("Feed", "Hourly", None, now) == now + timedelta(hours=1)
	assert next_at("Feed", "Hourly", None, now, failures=1) == now + timedelta(minutes=15)
	assert next_at("Feed", "Hourly", None, now, failures=4) == now + timedelta(minutes=120)
	assert next_at("Feed", "Hourly", None, now, failures=20) == now + timedelta(days=1), "at most a day"
	assert next_at("Google News", "Hourly", None, now, failures=1) == now + timedelta(hours=1), (
		"never sooner than an hour"
	)


def test_google_news_is_its_own_rss_for_a_topic_or_a_search():
	url = GOOGLE["url"]
	assert (
		url("Business", None, "AE", "en")
		== "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-AE&gl=AE&ceid=AE%3Aen"
	)
	assert url("Business", "glass facades", "AE", "ar").startswith(
		"https://news.google.com/rss/search?q=glass+facades&hl=ar-AE"
	)
	assert url("Top Stories", "", None, None) == "https://news.google.com/rss?hl=en-US&gl=US&ceid=US%3Aen"
	assert GOOGLE["untitled"]("Gold falls - Reuters", "Reuters") == "Gold falls"
	assert GOOGLE["untitled"]("Gold falls", "Reuters") == "Gold falls"


def test_oneadmin_fetches_one_edition_at_a_time_and_backs_off():
	next_one, pause_after, refresh = GOOGLE["next_one"], GOOGLE["pause_after"], GOOGLE["REFRESH"]
	now = 100_000.0
	held = [
		{"name": "fresh", "at": now - 60},
		{"name": "stale", "at": now - refresh - 5},
		{"name": "staler", "at": now - refresh - 50},
	]
	assert next_one(held, now)["name"] == "staler", "the stalest past its refresh"
	assert next_one([*held, {"name": "new", "since": now - 1}, {"name": "older", "since": now - 9}], now)["name"] == "older", (
		"an edition never fetched comes first, the longest waiting first"
	)
	assert next_one([{"name": "fresh", "at": now - 60}], now) is None, "nothing is fetched before it is due"
	assert pause_after(1) == GOOGLE["FIRST_PAUSE"] and pause_after(2) == 2 * GOOGLE["FIRST_PAUSE"]
	assert pause_after(50) == GOOGLE["LONGEST_PAUSE"], "a refusal pauses every fetch, up to a limit"


def test_the_library_is_searched_by_words_category_and_country():
	import json

	rows = json.loads((NEWS / "library.json").read_text(encoding="utf-8"))
	assert len(rows) > 500 and all(one["url"].startswith("http") for one in rows)
	assert len({one["url"] for one in rows}) == len(rows), "each feed once"
	found = READER["matching"](rows, "khaleej", "", "AE")
	assert [one["name"] for one in found] == ["Khaleej Times"]
	assert all(one["category"] == "Business" for one in READER["matching"](rows, "", "Business", ""))


def test_oneai_keeps_a_publisher_only_where_its_search_found_one():
	text = "Towers rise ||| Output rose. ||| www.TheNationalNews.com/business\nMade up ||| It never happened ||| fake.example\nNo split here\n"
	found = ADMIN["domains"](
		{
			"groundingChunks": [
				{"web": {"title": "thenationalnews.com"}},
				{"web": {"title": "A Title With Words"}},
			]
		}
	)
	assert found == {"thenationalnews.com"}
	said = ADMIN["lines"](text, found, 5)
	assert [one["title"] for one in said] == ["Towers rise", "Made up"]
	assert said[0]["publisher_site"] == "thenationalnews.com" and said[1]["publisher_site"] == ""
	assert "brief: news in the UAE?" in ADMIN["asked"]("news in the UAE.", "", "en", 5)
