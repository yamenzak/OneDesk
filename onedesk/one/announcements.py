"""Announcements: a message to everybody in the workspace, from its
administrators. docs/DESK-COVERAGE.md, P3.

An announcement is frappe's own Note, made public and shown on sign-in:
frappe pops it up for each person the next time they sign in, once or on
every sign-in, until the day it expires, and writes down who has seen it.
One adds three things:

- **The administrator may announce.** frappe holds a Note's public and
  sign-in fields at a level only its System Manager writes, so anybody
  else's note stays private whatever they send. One gives that level, and
  the one that shows who has seen it, to the workspace administrator.
- **Everybody is told when one is posted,** on the bell and by mail as
  each chose (Announcement), not only at their next sign-in.
- **The administrators see who has read it,** frappe's own Seen By, and
  OneAI answers who has not.

**It pops up.** frappe works out each person's unseen notes in `on_login`,
which runs before the session is made, so it works them out for Guest and
nobody is ever shown one. `boot` works them out again when the desk loads,
whenever frappe has cleared the list (at sign-in, and when a note changes),
so a new announcement also reaches somebody already signed in, once.
"""

import frappe
from frappe import _

from onedesk.one import roles

NOTE = "Note"

GRANTS = {NOTE: ("read", "write", "create", "delete")}

#: How much of an announcement the bell and the mail carry.
SAID = 300


#: The levels of a Note beyond the first: 1 makes it public and shown on
#: sign-in, 2 is who has seen it.
LEVELS = {1: ("read", "write"), 2: ("read",)}


def settle() -> None:
	from frappe.permissions import add_permission, update_permission_property

	roles.grant(GRANTS)
	for level, ptypes in LEVELS.items():
		if frappe.db.exists(
			"Custom DocPerm", {"parent": NOTE, "role": roles.ADMINISTRATOR, "permlevel": level}
		):
			continue
		add_permission(NOTE, roles.ADMINISTRATOR, level)
		for ptype in ptypes:
			update_permission_property(NOTE, roles.ADMINISTRATOR, level, ptype, 1, validate=False)


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
	"""Note on_update: everybody is told, once, when it becomes public."""
	if not doc.public or not (doc.has_value_changed("public") or doc.flags.in_insert):
		return
	from onedesk.one import notify
	from onedesk.one.settings import NOT_PEOPLE

	people = frappe.get_all(
		"User",
		filters={
			"enabled": 1,
			"user_type": "System User",
			"name": ["not in", [*NOT_PEOPLE, frappe.session.user]],
		},
		pluck="name",
	)
	text = frappe.utils.strip_html(doc.content or "").strip()
	notify.notify(
		"Announcement",
		people,
		record=(NOTE, doc.name),
		title=doc.title,
		by=frappe.utils.get_fullname(),
		text=text[:SAID] + ("…" if len(text) > SAID else ""),
	)


def boot(bootinfo) -> None:
	"""extend_bootinfo: this person's unseen announcements, worked out again
	when frappe has none on hand. A list it emptied after showing one that
	shows on every sign-in stays empty until the next."""
	from frappe.desk.doctype.note.note import UNSEEN_NOTES_KEY, _get_unseen_notes, get_unseen_notes

	if frappe.session.user == "Guest":
		return
	if frappe.cache.get_value(f"{UNSEEN_NOTES_KEY}{frappe.session.user}") is None:
		_get_unseen_notes()
	bootinfo.notes = get_unseen_notes()
