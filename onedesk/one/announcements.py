"""Announcements: a message to everybody in the workspace, from its
administrators.

An announcement is frappe's own Note, made public and shown on sign-in, and
running along the top bar until it expires.
"""

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

#: The announcements a person put away from their bar, as a user default.
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
def current() -> list[dict]:
	"""What this person's top bar runs: what is running, less what they hid."""
	hidden = set(json.loads(frappe.defaults.get_user_default(HIDDEN) or "[]"))
	return [one for one in _running() if one["name"] not in hidden]


@frappe.whitelist(methods=["POST"])
def hide() -> None:
	"""Put away what is on the bar now; the next one posted brings it back."""
	frappe.defaults.set_user_default(HIDDEN, json.dumps([one["name"] for one in _running()]))


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
