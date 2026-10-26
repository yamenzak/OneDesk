"""Announcements: a message to everybody in the workspace, from its
administrators, frappe's own Note made public. It runs along the top bar and
has a page of its own (the island `onedesk.announcements`); how is in One's
AGENTS.md, under announcements.py."""

import json

import frappe
from frappe import _

from onedesk.one import roles

NOTE = "Note"

SAID = 300

#: Announcements the top bar runs at once, newest first.
ON_THE_BAR = 5

#: How long one with no Show Until stays on the bar, as the sign-in pop-up does.
FRESH_DAYS = 7

#: The announcements running when a person folded them to the bar's icon, as a user default.
HIDDEN = "one_news_hidden"


def _free(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return user == "Administrator" or frappe.has_permission("Custom Field", "write", user=user)


def before_validate(doc, method=None) -> None:
	"""Note before_validate: shown on sign-in means everybody's, which
	frappe otherwise turns off for a note that is not public."""
	if doc.notify_on_login:
		doc.public = 1


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
	"""What this person's top bar shows: every announcement running, and
	whether they folded it to its icon. Folding holds until one is posted
	that was not there when they folded."""
	running = _running()
	folded = set(json.loads(frappe.defaults.get_user_default(HIDDEN) or "[]"))
	return {"running": running, "folded": bool(running) and all(one["name"] in folded for one in running)}


@frappe.whitelist(methods=["POST"])
def hide() -> None:
	"""Fold the announcements to the bar's icon; the next one posted opens them again."""
	frappe.defaults.set_user_default(HIDDEN, json.dumps([one["name"] for one in _running()]))


@frappe.whitelist(methods=["POST"])
def show() -> None:
	"""Open the folded announcements again."""
	frappe.defaults.clear_user_default(HIDDEN)


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
	return out[:ON_THE_BAR]


EARLIER = 50


@frappe.whitelist(methods=["GET"])
@frappe.read_only()
def read() -> dict:
	"""The Announcements page (the island `onedesk.announcements`): what is
	running now and what ran before, newest first, each in full. An
	administrator also sees who has seen each, and may post, change and stop
	one."""
	from frappe.utils import get_fullname, now_datetime
	from frappe.utils.html_utils import sanitize_html

	running = {one["name"] for one in _running()}
	posts = _free() or roles.administers()
	rows = frappe.get_list(
		NOTE,
		filters={"public": 1},
		fields=["name", "title", "content", "owner", "creation", "expire_notification_on"],
		order_by="creation desc",
		limit_page_length=EARLIER + ON_THE_BAR * 2,
	)
	seen = {}
	if posts and rows:
		for one in frappe.get_all(
			"Note Seen By", filters={"parent": ["in", [row.name for row in rows]]}, fields=["parent", "user"]
		):
			seen.setdefault(one.parent, []).append(get_fullname(one.user))
	people = frappe.db.count(
		"User", {"enabled": 1, "user_type": "System User", "name": ["not in", ("Administrator", "Guest")]}
	)
	now = now_datetime()
	return {
		"posts": posts,
		"people": people,
		"rows": [
			{
				"name": one.name,
				"title": one.title,
				"html": sanitize_html(one.content or ""),
				"by": get_fullname(one.owner),
				"on": str(one.creation),
				"until": str(one.expire_notification_on) if one.expire_notification_on else None,
				"running": one.name in running,
				"ended": bool(one.expire_notification_on and one.expire_notification_on <= now),
				"seen": sorted(seen.get(one.name, [])) if posts else None,
			}
			for one in rows
		],
	}


@frappe.whitelist(methods=["POST"])
def stop(name: str) -> None:
	"""An announcement stops running now; it stays on the page under Earlier."""
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
