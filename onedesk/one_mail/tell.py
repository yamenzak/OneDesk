"""Telling people about their mailboxes (notifications/one_mail/)."""

import frappe

from onedesk.one import notify


def attachments_not_saved(doc) -> None:
	"""The administrators and the mailbox's holders, once a day at most."""
	from onedesk.one import roles
	from onedesk.one_mail.room import TOLD

	if frappe.cache.get_value(TOLD):
		return
	frappe.cache.set_value(TOLD, 1, expires_in_sec=24 * 60 * 60)
	holders = frappe.get_all("User Email", filters={"email_account": doc.email_account}, pluck="parent")
	notify.notify(
		"Attachments Not Saved",
		list(dict.fromkeys([*roles.administrators(), *holders])),
		link="/desk/workspace-settings?section=plan",
		sender="Administrator",
		mailbox=frappe.db.get_value("Email Account", doc.email_account, "email_id") or doc.email_account,
	)


def mailbox_not_reachable(doc, said: str, holders: list[str]) -> None:
	"""Whoever holds a mailbox hears that it stopped connecting, and why."""
	notify.notify(
		"Mailbox Not Reachable",
		holders,
		link="/desk/settings?section=mail",
		sender="Administrator",
		mailbox=doc.email_id,
		reason=said,
	)
