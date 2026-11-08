"""Announcements: a message to everybody in the workspace, from its
administrators, frappe's own Note made public. It runs along the top bar
until its Show Until, and is frappe's Note list, filtered by its Status,
Showing or Ended (one/custom/note.json); how is in One's AGENTS.md, under
announcements.py."""

import json

import frappe
from frappe import _

from onedesk.one import roles

NOTE = "Note"

SAID = 300

#: Announcements the top bar runs at once, newest first.
ON_THE_BAR = 5

#: How long one runs when nobody says until when.
FRESH_DAYS = 7

#: The announcements running when a person folded them to the bar's icon, as a user default.
HIDDEN = "one_news_hidden"

#: What the bar runs for a person, Announcements or News (one/news/desk.py), and whether they folded the news.
SHOWS = "one_bar_shows"
NEWS_FOLDED = "one_bar_news_folded"


def _free(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return user == "Administrator" or frappe.has_permission("Custom Field", "write", user=user)


def before_validate(doc, method=None) -> None:
	"""Note before_validate: shown on sign-in means everybody's, which
	frappe otherwise turns off for a note that is not public; and an
	announcement nobody gave an end runs for FRESH_DAYS, so Showing Now and
	Earlier are a filter on Show Until."""
	from frappe.utils import add_days, now_datetime

	if doc.notify_on_login:
		doc.public = 1
	if doc.public and not doc.expire_notification_on:
		doc.expire_notification_on = add_days(now_datetime(), FRESH_DAYS)
	doc.one_status = (
		("Ended" if frappe.utils.get_datetime(doc.expire_notification_on) <= now_datetime() else "Showing")
		if doc.public
		else None
	)


def ended() -> None:
	"""Every quarter hour: an announcement whose Show Until has passed says
	Ended, so the list's Status filter is right without a page of its own."""
	from frappe.utils import now_datetime

	for name in frappe.get_all(
		NOTE,
		filters=[["public", "=", 1], ["one_status", "=", "Showing"], ["expire_notification_on", "is", "set"], ["expire_notification_on", "<=", now_datetime()]],
		pluck="name",
	):
		frappe.db.set_value(NOTE, name, "one_status", "Ended", update_modified=False)


def validate(doc, method=None) -> None:
	"""Note validate: only an administrator makes one everybody's."""
	if (doc.public or doc.notify_on_login) and not (_free() or roles.administers()):
		frappe.throw(_("Only an administrator posts an announcement. Your notes stay your own."))


def on_update(doc, method=None) -> None:
	"""Note on_update: everybody is told, once, when it becomes public, and
	every open top bar runs the announcements again."""
	if doc.public or doc.has_value_changed("public"):
		_rerun()
	if not doc.public or not (doc.has_value_changed("public") or doc.flags.in_insert):
		return
	from onedesk.one import tell

	tell.announced(doc)


def on_trash(doc, method=None) -> None:
	if doc.public:
		_rerun()


def _rerun() -> None:
	frappe.publish_realtime("one_announcements", {}, after_commit=True)


@frappe.whitelist()
def current() -> dict:
	"""What this person's top bar shows: every announcement running and the
	headlines of the news they follow, which of the two they chose, and
	whether they folded it to its icon. Folding announcements holds until
	one is posted that was not there when they folded."""
	from onedesk.one.news import desk

	running = _running()
	folded = set(json.loads(frappe.defaults.get_user_default(HIDDEN) or "[]"))
	return {
		"running": running,
		"folded": bool(running) and all(one["name"] in folded for one in running),
		"news": desk.headlines(),
		"news_folded": bool(frappe.defaults.get_user_default(NEWS_FOLDED)),
		"shows": frappe.defaults.get_user_default(SHOWS) or "Announcements",
	}


@frappe.whitelist(methods=["POST"])
def hide(what: str = "Announcements") -> None:
	"""Fold the announcements, or the news, to the bar's icon; the next
	announcement posted opens them again."""
	if what == "News":
		frappe.defaults.set_user_default(NEWS_FOLDED, "1")
		return
	frappe.defaults.set_user_default(HIDDEN, json.dumps([one["name"] for one in _running()]))


@frappe.whitelist(methods=["POST"])
def show(what: str = "Announcements") -> None:
	"""Open the folded announcements, or news, again."""
	frappe.defaults.clear_user_default(NEWS_FOLDED if what == "News" else HIDDEN)


@frappe.whitelist(methods=["POST"])
def shows(what: str) -> None:
	"""Run announcements or news along this person's top bar."""
	if what not in ("Announcements", "News"):
		frappe.throw(_("Choose announcements or news."))
	frappe.defaults.set_user_default(SHOWS, what)


def _running() -> list[dict]:
	"""Public announcements not yet expired, newest first. One with no Show
	Until runs for a week from when it was posted."""
	from frappe.utils import add_days, get_fullname, now_datetime, strip_html

	now = now_datetime()
	rows = frappe.get_list(
		NOTE,
		filters={"public": 1},
		or_filters={"expire_notification_on": (">", now), "creation": (">", add_days(now, -FRESH_DAYS))},
		fields=["name", "title", "content", "owner", "creation", "expire_notification_on"],
		order_by="creation desc",
		limit_page_length=ON_THE_BAR * 2,
	)
	out = []
	for one in rows:
		if one.expire_notification_on and one.expire_notification_on <= now:
			continue
		text = " ".join(strip_html(one.content or "").split())
		out.append(
			{
				"name": one.name,
				"title": one.title,
				"text": text[:SAID] + ("…" if len(text) > SAID else ""),
				"by": get_fullname(one.owner),
				"on": str(one.creation),
			}
		)
	return [*_update(now), *out][:ON_THE_BAR]


UPDATE = "one-update"


def _update(now) -> list[dict]:
	"""One's next update, from the account, run first on everybody's bar
	once it is three days away or less (one_admin/releases.py)."""
	from frappe.utils import format_datetime, get_datetime, time_diff_in_hours

	at = frappe.db.get_single_value("Workspace Account", "update_at")
	if not at or not 0 < time_diff_in_hours(get_datetime(at), now) <= 72:
		return []
	when = format_datetime(at, "EEEE d MMMM, HH:mm")
	return [{"name": UPDATE, "title": _("One updates on {0}").format(when), "text": _("It takes a few minutes. What's New says what changes."), "by": "One", "on": str(now)}]


@frappe.whitelist(methods=["POST"])
def stop(name: str) -> None:
	"""An announcement stops running now; it moves to Earlier."""
	doc = frappe.get_doc(NOTE, name)
	if not doc.public or not (_free() or roles.administers()):
		frappe.throw(_("Only an administrator stops an announcement."), frappe.PermissionError)
	doc.expire_notification_on = frappe.utils.now_datetime()
	doc.notify_on_login = 0
	doc.save()


def boot(bootinfo) -> None:
	"""extend_bootinfo: this person's unseen announcements, worked out again
	when frappe has none on hand. A list it emptied after showing one that
	shows on every sign-in stays empty until the next."""
	from frappe.desk.doctype.note.note import UNSEEN_NOTES_KEY, _get_unseen_notes, get_unseen_notes

	if frappe.session.user == "Guest":
		return
	bootinfo.one_announcements = current()
	if frappe.cache.get_value(f"{UNSEEN_NOTES_KEY}{frappe.session.user}") is None:
		_get_unseen_notes()
	bootinfo.notes = get_unseen_notes()
