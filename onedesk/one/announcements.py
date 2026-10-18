"""Announcements: a message to everybody in the workspace, from its
administrators.

An announcement is frappe's own Note, made public and shown on sign-in.
"""

import frappe
from frappe import _

from onedesk.one import roles

NOTE = "Note"

SAID = 300



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
	from onedesk.one import tell

	tell.announced(doc)


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
