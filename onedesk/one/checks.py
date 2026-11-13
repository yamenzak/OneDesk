"""One's part of the integration suite (one_demo/check.py runs it): its
roles, the Recycle Bin's Everyone's Deletions, and drawn pictures."""

import frappe

from onedesk.one_demo.base import as_user
from onedesk.one_demo.check import check
from onedesk.one_demo.people import OWNER


@check
def one_manager_sees_what_anybody_deleted():
	"""One's roles are made from its abilities.py (rights.settle) and its User
	role is everybody's. Nadia sees only what she deleted herself; made One's
	Manager in AccessCenter, which holds Everyone's Deletions, she sees what
	others deleted too, and still can't empty the bin for good. The demo keeps
	Mariam as One's Manager."""
	from onedesk.one import access_center, recycle

	assert frappe.db.exists("Role", "One User") and frappe.db.exists("Role", "One Manager")
	assert "One User" in frappe.get_roles("nadia@one.test")
	others = frappe.db.get_value(
		"Deleted Document", {"owner": ("not in", ("nadia@one.test", "Administrator", "Guest"))}, "name"
	)
	assert others, "the demo has nothing deleted by anybody but Nadia"
	with as_user("nadia@one.test"):
		assert "nadia@one.test" in (recycle.query() or "") and not recycle._everyone("nadia@one.test")
	assert "One" in access_center.modules() and "AccountCenter" in access_center.modules()
	levels = {one["user"]: one["level"] for one in access_center.people("One")["people"]}
	assert levels.get("mariam@one.test") == "Manager" and levels.get("nadia@one.test") == "User", levels
	access_center.put("One", "nadia@one.test", "Manager")
	try:
		with as_user("nadia@one.test"):
			assert recycle._everyone("nadia@one.test"), "One Manager does not hold Everyone's Deletions"
			doc = frappe.get_doc("Deleted Document", others)
			assert recycle.has_permission(
				doc, "read", "nadia@one.test"
			) or doc.deleted_doctype not in recycle._kinds("nadia@one.test")
			assert not recycle.has_permission(doc, "delete", "nadia@one.test"), (
				"only an administrator empties the bin"
			)
	finally:
		access_center.put("One", "nadia@one.test", "User")
		assert "One User" in frappe.get_roles("nadia@one.test") and "One Manager" not in frappe.get_roles("nadia@one.test")


@check
def the_bin_lists_what_was_deleted_and_puts_it_back():
	"""Nadia deletes a to-do; frappe's Deleted Document list, the Recycle Bin,
	shows it to her and nobody else's, and Restore (recycle.bulk_restore)
	brings it back, marking the row restored."""
	from onedesk.one import recycle

	with as_user("nadia@one.test"):
		note = frappe.get_doc({"doctype": "ToDo", "description": "Bin check: call the glass supplier"}).insert()
		frappe.delete_doc("ToDo", note.name)
		rows = frappe.get_list(
			"Deleted Document",
			filters={"deleted_doctype": "ToDo", "restored": 0},
			fields=["name", "deleted_name", "owner"],
			limit=500,
		)
		row = next((one for one in rows if one.deleted_name == note.name), None)
		assert row, rows
		assert not recycle._everyone("nadia@one.test")
		assert all(one.owner == "nadia@one.test" for one in rows), "Nadia sees somebody else's deletion"
		got = recycle.bulk_restore([row.name])
		assert got["restored"] == [row.name], got
		back = frappe.db.get_value("Deleted Document", row.name, ["restored", "new_name"], as_dict=True)
		assert back.restored and back.new_name, back
		frappe.delete_doc("ToDo", back.new_name)


@check
def announcements_show_now_and_earlier_and_who_saw_them():
	"""Layla posts an announcement with no end: it is given one a week out, so
	it is under Showing Now (Note's list, Show Until after now) for Samir, who
	cannot stop it; Layla stops it and it is under Earlier."""
	from frappe.utils import now_datetime

	from onedesk.one import announcements

	with as_user(OWNER):
		note = frappe.get_doc(
			{"doctype": "Note", "title": "Check: lift out of service", "content": "<p>Use the stairs.</p>", "public": 1}
		).insert()
		assert note.expire_notification_on and not note.notify_on_login, note.as_dict()
	shown = lambda op: frappe.get_list(  # noqa: E731
		"Note", filters={"public": 1, "expire_notification_on": [op, now_datetime()]}, pluck="name"
	)
	with as_user("samir@one.test"):
		assert note.name in shown(">") and note.name not in shown("<=")
		try:
			announcements.stop(note.name)
			raise AssertionError("Samir stopped an announcement")
		except frappe.PermissionError:
			frappe.clear_last_message()
	with as_user(OWNER):
		announcements.stop(note.name)
		assert note.name in shown("<=") and note.name not in shown(">")
		frappe.delete_doc("Note", note.name)


@check
def the_address_book_is_frappes_contacts_and_addresses():
	"""The rail's Contacts and Addresses are frappe's Contact and Address
	lists, and Acme Holdings' billing address and Jordan Blake both belong to
	Acme under Links."""
	rail = {one.label: one for one in frappe.get_all("Sidebar Item", filters={"parent": "One", "parenttype": "Sidebar"}, fields=["label", "link_type", "link_to"])}
	assert (rail["Contacts"].link_type, rail["Contacts"].link_to) == ("DocType", "Contact"), rail["Contacts"]
	assert (rail["Addresses"].link_type, rail["Addresses"].link_to) == ("DocType", "Address"), rail["Addresses"]
	with as_user(OWNER):
		for doctype in ("Address", "Contact"):
			linked = frappe.get_list(
				doctype,
				filters=[["Dynamic Link", "link_doctype", "=", "Customer"], ["Dynamic Link", "link_name", "=", "Acme Holdings"]],
				pluck="name",
			)
			assert linked, doctype


@check
def ones_rail_leaves_out_what_the_reader_cannot_open():
	"""One's rail links the workspace's centres by address, which frappe
	shows to everyone (reach.unopened): Mariam, who administers nothing, has
	AccountCenter and not ControlCenter or AccessCenter; Layla has them all."""
	from frappe.boot import get_module_sidebars

	from onedesk.one import reach

	def rail(user):
		with as_user(user):
			sidebars = get_module_sidebars()
			reach.unopened(sidebars)
			return [one.get("label") for one in sidebars["One"]["items"]]

	mariam, layla = rail("mariam@one.test"), rail(OWNER)
	assert "AccountCenter" in mariam and not {"ControlCenter", "AccessCenter"} & set(mariam), mariam
	assert {"AccountCenter", "ControlCenter", "AccessCenter", "TrustCenter"} <= set(layla), layla


@check
def a_record_with_no_picture_gets_one_drawn_and_keeps_its_own():
	"""A style picked for contacts in One's settings (avatars.save) draws a
	picture for a new contact with none, locally; one with its own picture
	keeps it; changing the style redraws only the drawn one, and None takes
	it off. The workspace's own choice is put back after."""
	from onedesk.one import avatars
	from onedesk.one_mail import faces

	before = frappe.db.get_default(avatars.KEY)
	keys = {one["key"] for one in avatars.styles()}
	assert {"lorelei", "shapes", "initials"} <= keys, sorted(keys)
	assert set(avatars.gallery("Contact")) == keys
	plain = frappe.get_doc({"doctype": "Contact", "first_name": "Drawn", "last_name": "Check"}).insert(ignore_permissions=True)
	own = frappe.get_doc(
		{"doctype": "Contact", "first_name": "Own", "last_name": "Picture", "image": "/files/own-picture.png"}
	).insert(ignore_permissions=True)
	try:
		frappe.db.set_default(avatars.KEY, '{"Contact": "lorelei"}')
		drawn = faces.dress("Contact", plain.name)
		assert drawn and avatars.style_of(drawn) == "lorelei", drawn
		assert "<metadata" in open(frappe.get_site_path("public", drawn.lstrip("/")), encoding="utf-8").read(), "no credit in the picture"
		assert not faces.dress("Contact", own.name)
		avatars.pick("Contact", "initials")
		avatars.fill("Contact")
		assert avatars.style_of(frappe.db.get_value("Contact", plain.name, "image")) == "initials"
		assert frappe.db.get_value("Contact", own.name, "image") == "/files/own-picture.png"
		frappe.db.set_default(avatars.KEY, "{}")
		avatars.fill("Contact")
		assert not frappe.db.get_value("Contact", plain.name, "image")
		assert frappe.db.get_value("Contact", own.name, "image") == "/files/own-picture.png"
	finally:
		frappe.db.set_default(avatars.KEY, before or "{}")
		for name in (plain.name, own.name):
			frappe.delete_doc("Contact", name, ignore_permissions=True, force=True)
		avatars.fill("Contact")


@check
def one_follows_the_news():
	"""News Sources fetch on their own (one/news): a feed's new items are
	kept and its oldest let go, Google News asks OneAdmin and never Google,
	and nothing while it is off,
	OneAI's headlines come through the account, a Written source takes the
	items written for it, and each person's bar and each screen read them.
	Nothing leaves: the feed and the account are stood in for."""
	from unittest import mock

	from onedesk.one import announcements, news
	from onedesk.one.news import desk, feeds, fetching
	from onedesk.one.news import library as news_library
	from onedesk.trust_center import services

	rss = (
		b'<rss version="2.0"><channel><title>Check</title><link>https://check.example.com/</link>'
		b"<item><title>First headline</title><guid>1</guid><link>https://check.example.com/1</link><pubDate>Sat, 31 Oct 2026 06:00:00 GMT</pubDate></item>"
		b"<item><title>Second headline</title><guid>2</guid><link>https://check.example.com/2</link><pubDate>Sat, 31 Oct 2026 07:00:00 GMT</pubDate></item>"
		b"</channel></rss>"
	)
	names = ("Check Feed", "Check Google", "Check OneAI", "Check Written")
	with as_user(OWNER):
		was = services.on(fetching.GOOGLE_SERVICE)
		try:
			kinds = (("Feed", {"feed_url": "https://check.example.com/rss"}), ("Google News", {"google_topic": "Business"}), ("OneAI", {"ai_brief": "news for a glazing company", "fetch_every": "At Set Times", "fetch_at": "07:00"}), ("Written", {}))
			for name, (kind, extra) in zip(names, kinds, strict=True):
				frappe.get_doc({"doctype": news.SOURCE, "source_name": name, "kind": kind, "category": "Check News", "keep": 1 if kind == "Feed" else 0, **extra}).insert()
			assert frappe.db.exists(news.CATEGORY, "Check News"), "a category is made when it is first named"

			with mock.patch.object(feeds, "get", return_value=(200, rss, '"e1"', "Sat, 31 Oct 2026 07:00:00 GMT")) as got:
				assert fetching.fetch("Check Feed") == 2
			kept = frappe.get_all(news.ITEM, filters={"source": "Check Feed"}, pluck="title")
			assert kept == ["Second headline"], f"Keep 1 holds only the newest: {kept}"
			source = frappe.db.get_value(news.SOURCE, "Check Feed", ["etag", "website", "next_fetch", "last_error"], as_dict=True)
			assert source.etag == '"e1"' and source.website == "https://check.example.com/" and source.next_fetch and not source.last_error
			with mock.patch.object(feeds, "get", return_value=(304, b"", '"e1"', None)) as got:
				assert fetching.fetch("Check Feed") == 0
				assert got.call_args.args[1] == '"e1"', "the feed is asked whether it changed"

			services.switch(fetching.GOOGLE_SERVICE, 0)
			frappe.local.one_services = {}
			with mock.patch("onedesk.one.account.ask") as asked:
				fetching.fetch("Check Google")
				asked.assert_not_called()
			assert "TrustCenter" in frappe.db.get_value(news.SOURCE, "Check Google", "last_error"), "off, Google News is not asked"
			services.switch(fetching.GOOGLE_SERVICE, 1)
			frappe.local.one_services = {}
			google = frappe.get_doc(news.SOURCE, "Check Google")
			google.fetch_every = "15 Minutes"
			google.save()
			assert google.fetch_every == "Hourly", "how often Google News is fetched is not the workspace's to set"
			with mock.patch.object(feeds, "get") as got, mock.patch("onedesk.one.account.ask", return_value={"items": [], "waiting": True}) as asked:
				assert fetching.fetch("Check Google") == 0
				got.assert_not_called()
			assert asked.call_args.args[0] == fetching.GOOGLE and asked.call_args.kwargs["topic"] == "Business", "the workspace asks OneAdmin, never Google"
			soon = frappe.db.get_value(news.SOURCE, "Check Google", "next_fetch")
			assert soon <= frappe.utils.add_to_date(None, minutes=fetching.GOOGLE_WAITING + 1), "a first edition is asked again soon"
			headline = {"guid": "g1", "title": "Gold falls", "link": "https://check.example.com/g1", "published": "2026-10-31T05:00:00", "publisher": "Reuters", "publisher_site": "reuters.com"}
			with mock.patch("onedesk.one.account.ask", return_value={"items": [headline], "waiting": False}):
				assert fetching.fetch("Check Google") == 1
			assert frappe.db.get_value(news.SOURCE, "Check Google", "next_fetch") > frappe.utils.add_to_date(None, minutes=fetching.GOOGLE_EVERY - 1)

			said = {"items": [{"title": "Towers rise", "summary": "Output rose.", "publisher": "thenationalnews.com", "publisher_site": "thenationalnews.com"}]}
			with mock.patch("onedesk.one.account.ask", return_value=said) as asked:
				assert fetching.fetch("Check OneAI") == 1
				assert asked.call_args.args[0] == fetching.AI and asked.call_args.kwargs["brief"] == "news for a glazing company"
			assert frappe.db.get_value(news.ITEM, {"source": "Check OneAI"}, "publisher_site") == "thenationalnews.com"

			frappe.get_doc({"doctype": news.ITEM, "source": "Check Written", "title": "Our own news"}).insert()
			try:
				frappe.get_doc({"doctype": news.ITEM, "source": "Check Feed", "title": "Typed in"}).insert()
			except frappe.ValidationError:
				pass
			else:
				raise AssertionError("a feed's items are only fetched")

			desk.follow(["Check Written"])
			assert {one["title"] for one in desk.headlines()} == {"Our own news"}, "the bar reads the sources this person follows"
			assert desk.headlines()[0]["route"][1] == news.ITEM, "a written headline opens here"
			announcements.shows("News")
			now = announcements.current()
			assert now["shows"] == "News" and now["news"][0]["title"] == "Our own news"

			from onedesk.one.news import adding

			page = b'<html><head><meta property="og:site_name" content="Check Site"><link rel="alternate" type="application/rss+xml" href="/rss"></head></html>'
			with mock.patch.object(feeds, "get", side_effect=[(200, page, None, None), (200, rss, None, None)]):
				found = adding.find("check.example.com")
			assert found["url"] == "https://check.example.com/rss" and found["name"] == "Check Site" and len(found["headlines"]) == 2, found
			assert found["there"] == "Check Feed", "a feed already a source says so"
			with mock.patch.object(feeds, "get", return_value=(200, b"<html></html>", None, None)):
				assert "error" in adding.find("nothing.example.com")
			made = adding.add("Written", "Check Written")
			assert made == "Check Written 2", "a name already taken gets a number"
			frappe.delete_doc(news.SOURCE, made, force=True)
			assert adding.start()["google"]
			latest = adding.latest("Check OneAI")
			assert latest["items"][0]["title"] == "Towers rise" and latest["fetched"]
			assert adding.add_many([]) == []

			found = news_library.search("khaleej", "", "AE")
			assert [one["name"] for one in found["feeds"]] == ["Khaleej Times"] and "World" in found["categories"]
			url = found["feeds"][0]["url"]
			had = frappe.db.get_value(news.SOURCE, {"feed_url": url}, "name")
			added = news_library.add(url)
			assert frappe.db.get_value(news.SOURCE, added, "kind") == "Feed" and news_library.search("khaleej", "", "AE")["feeds"][0]["added"]
			assert not had or added == had, "a feed already added is not added twice"
			added = None if had else added
			following = desk.following()
			assert "Check Written" in {one["name"] for one in following["sources"] if one["followed"]}
			with mock.patch("frappe.enqueue") as queued:
				fetching.fetch_now("Check Feed")
				assert queued.call_args.kwargs["name"] == "Check Feed", "Fetch Now asks in the background"

			rows = news.items(list(names), most=10, order="By Category")
			assert {"category", "colour", "logo", "publisher"} <= set(rows[0]), "a ticker gets each headline's category and logo"
		finally:
			desk.follow([])
			frappe.defaults.clear_user_default(announcements.SHOWS)
			for name in (*names, locals().get("added")):
				if name and frappe.db.exists(news.SOURCE, name):
					frappe.delete_doc(news.SOURCE, name, force=True)
			services.switch(fetching.GOOGLE_SERVICE, int(was))
			frappe.local.one_services = {}


@check
def oneadmin_fetches_google_news_gently():
	"""OneAdmin alone reaches Google News (one_admin/google_news.py): a first
	ask is answered waiting and fetched at the next tick, two workspaces
	share one fetch, a fresh edition is not fetched again, a refusal pauses
	every fetch, and a workspace follows ten editions at most. Google is
	stood in for."""
	from unittest import mock

	from onedesk.one.news import feeds
	from onedesk.one_admin import google_news, site
	from onedesk.one_admin.faults import Refused

	rss = (
		b'<rss version="2.0"><channel><title>Google News</title>'
		b"<item><title>Gold falls - Reuters</title><guid>g1</guid><link>https://check.example.com/g1</link>"
		b'<pubDate>Sat, 31 Oct 2026 06:00:00 GMT</pubDate><source url="https://www.reuters.com">Reuters</source></item>'
		b"</channel></rss>"
	)
	tenants = ("check-news-a", "check-news-b")
	names = set()
	try:
		first = google_news.headlines(tenants[0], "Business", "", "AE", "en")
		assert first == {"items": [], "fetched": 0, "waiting": True}, first
		google_news.headlines(tenants[1], "Business", "", "AE", "en")
		names = google_news._names()
		with mock.patch.object(site, "is_admin", return_value=True), mock.patch.object(
			feeds, "get", return_value=(200, rss, None, None)
		) as got:
			google_news.tick()
			google_news.tick()
		assert got.call_count == 1, "two workspaces share one fetch, and a fresh edition waits its turn"
		said = google_news.headlines(tenants[1], "Business", "", "AE", "en")
		assert not said["waiting"] and said["items"][0]["title"] == "Gold falls"
		assert said["items"][0]["publisher_site"] == "reuters.com" and said["items"][0]["published"].startswith("2026-10-31")

		google_news.headlines(tenants[0], "", "glass facades", "AE", "en")
		names = google_news._names()
		with mock.patch.object(site, "is_admin", return_value=True), mock.patch.object(
			feeds, "get", side_effect=feeds.Unreadable("Google answered 503.")
		):
			google_news.tick()
		paused = frappe.cache.get_value(google_news.PAUSED)
		assert paused and paused["pauses"] == 1, "a refusal pauses every fetch"
		with mock.patch.object(site, "is_admin", return_value=True), mock.patch.object(feeds, "get") as got:
			google_news.tick()
			got.assert_not_called()
		with mock.patch.object(feeds, "get") as got:
			google_news.tick()
			got.assert_not_called()

		for n in range(google_news.MOST_A_WORKSPACE - 1):
			google_news.headlines(tenants[1], "", f"check words {n}", "AE", "en")
		names = google_news._names()
		try:
			google_news.headlines(tenants[1], "", "one too many", "AE", "en")
		except Refused:
			pass
		else:
			raise AssertionError("a workspace follows ten editions at most")
	finally:
		frappe.cache.delete_value(google_news.PAUSED)
		for name in names:
			frappe.cache.delete_value(google_news.HELD.format(name))
			frappe.cache.srem(google_news.EDITIONS, name)
		for tenant in tenants:
			frappe.cache.delete_value(google_news.FOLLOWED.format(tenant))


@check
def one_shows_the_weather_for_its_places():
	"""A place is found by its name and its weather comes through the account,
	once for every workspace near it (one/weather.py, one_admin/weather.py).
	Off, nothing is asked; on, the default place is shown beside the clock in
	the workspace's units. The account is stood in for: no call leaves."""
	from unittest import mock

	from onedesk.one import weather
	from onedesk.trust_center import services

	start = 1_793_433_600
	answer = {
		"place": "25.3,55.3",
		"offset": 4 * 3600,
		"hours": [{"dt": start + i * 3600, "temp": 30 + i, "humidity": 40, "wind_speed": 5, "code": 800} for i in range(20)],
		"days": [{"dt": start + i * 86400, "high": 33, "low": 26, "code": 801} for i in range(10)],
		"credits": 0,
	}
	place = frappe.db.get_value("Weather Place", {"is_default": 1}, "name")
	assert place, "the demo has a default place"
	with as_user(OWNER):
		was = services.on(weather.SERVICE)
		try:
			services.switch(weather.SERVICE, 0)
			frappe.local.one_services = {}
			weather.forget(place)
			with mock.patch("onedesk.one.account.ask") as asked:
				assert weather.here() is None, "off, nothing is shown"
				try:
					weather.search("Dubai")
				except frappe.ValidationError:
					pass
				else:
					raise AssertionError("off, no place can be searched for")
				asked.assert_not_called()
			services.switch(weather.SERVICE, 1)
			frappe.local.one_services = {}
			found = [{"name": "دبي", "region": "Dubai", "country": "AE", "latitude": 25.2647, "longitude": 55.2924}]
			with mock.patch("onedesk.one.account.ask", return_value=found) as asked:
				assert weather.search("Dubai") == found
				assert asked.call_args.args[0] == weather.PLACES and asked.call_args.kwargs["query"] == "Dubai"
				listed = weather.suggest("Dubai")
				assert listed[0]["value"] == "دبي, Dubai, AE" and listed[0]["label"] == "دبي", "towns sharing a name are told apart"
			assert weather.suggest("D") == [], "one letter asks nothing"
			with mock.patch("frappe.get_request_header", side_effect={"X-One-City": "Al%20Barsha", "X-One-Region": "Dubai", "X-One-Country": "AE", "X-One-Latitude": "25.11", "X-One-Longitude": "55.19"}.get):
				assert weather.located() == {"name": "Al Barsha", "region": "Dubai", "country": "AE", "latitude": 25.11, "longitude": 55.19}
			with mock.patch("frappe.get_request_header", return_value=None):
				assert weather.located() == {}, "without the edge's headers, where it is is not guessed"
			with mock.patch("onedesk.one.account.ask", return_value=dict(answer)) as asked, mock.patch.object(weather, "_now", return_value=start + 60):
				shown = weather.here()
				assert shown["place"] == place and shown["temperature"] == "30°C" and len(shown["hours"]) == 13, shown
				assert asked.call_args.args[0] == weather.READING and set(asked.call_args.kwargs) == {"latitude", "longitude"}
				weather.here()
				assert asked.call_count == 1, "the account's answer is kept a quarter of an hour"
		finally:
			weather.forget(place)
			services.switch(weather.SERVICE, int(was))
			frappe.local.one_services = {}


@check
def shortcuts_move_for_the_reader_alone():
	"""ShortcutCenter (one/shortcut_center.py): every module's shortcuts.py
	read beside the others, each with its own id. Nadia moves Search to
	Ctrl+Shift+F; it is hers, Karim's is as shipped. Moved back to its own keys
	it is no longer kept; a key the browser keeps is refused; reset puts every
	one back."""
	from onedesk.one import shortcut_center

	ids = [one["id"] for one in shortcut_center.declared()]
	assert len(ids) == len(set(ids)), "two shortcuts share an id"
	assert "one_interface.search" in ids and "one_mail.next" in ids, ids
	shipped = next(one for one in shortcut_center.declared() if one["id"] == "one_interface.search")["keys"]
	with as_user("nadia@one.test"):
		try:
			said = shortcut_center.save("one_interface.search", '["mod+shift+KeyF"]')
			assert said.get("one_interface.search") == ["mod+shift+KeyF"], said
			with as_user("karim@one.test"):
				assert "one_interface.search" not in shortcut_center.yours()
			assert "one_interface.search" not in shortcut_center.save("one_interface.search", list(shipped))
			try:
				shortcut_center.save("one_interface.search", '["mod+KeyW"]')
			except frappe.ValidationError:
				pass
			else:
				raise AssertionError("a key the browser keeps was taken as a shortcut")
		finally:
			assert shortcut_center.reset() == {}


@check
def turn_off_these_emails_works_without_signing_in():
	"""A notification's mail carries a signed link (unsubscribe.link): opened
	as Guest, or posted by a mail client's one-click, it turns that one type's
	email off for Nadia as NotificationCenter's switch does, and Turn On
	Again puts it back. A link with its address changed does nothing."""
	from urllib.parse import parse_qsl

	from werkzeug.test import EnvironBuilder
	from werkzeug.wrappers import Request

	from onedesk.one import notification_center, unsubscribe

	def mailed(kind):
		with as_user("nadia@one.test"):
			return next(one for one in notification_center.yours()["types"] if one["name"] == kind)["email"]

	def opened(url, method="GET"):
		query = url.split("?", 1)[1]
		data = {"List-Unsubscribe": "One-Click"} if method == "POST" else None
		frappe.local.request = Request(EnvironBuilder(method=method, query_string=query, data=data).get_environ())
		said = dict(parse_qsl(query))
		with as_user("Guest"):
			if "unsubscribe.on" in url:
				unsubscribe.on(said["email"], said["doctype"], said["name"])
			else:
				unsubscribe.off(said["email"], said["doctype"], said["name"])
		return frappe.local.message_title

	was_request = getattr(frappe.local, "request", None)
	with as_user("nadia@one.test"):
		kind = next(one["name"] for one in notification_center.yours()["types"] if one["may_email"] and one["email"])
	assert unsubscribe.offered("nadia@one.test", kind) == kind
	email = frappe.db.get_value("User", "nadia@one.test", "email")
	try:
		forged = unsubscribe.link(email, kind).replace("nadia", "omar")
		assert opened(forged) == "This link no longer works" and mailed(kind)
		assert opened(unsubscribe.link(email, kind), "POST") == "Emails Turned Off" and not mailed(kind)
		assert opened(unsubscribe.link(email, kind, unsubscribe.AGAIN)) == "Emails Turned On" and mailed(kind)
		assert opened(unsubscribe.link(email, kind)) == "Emails Turned Off" and not mailed(kind)
	finally:
		frappe.local.request = was_request
		with as_user("nadia@one.test"):
			notification_center.choose(kind, "email", 1)
