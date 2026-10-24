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
		holders or _admins(),
		link="/desk/onemail-settings?section=mail",
		sender="Administrator",
		mailbox=doc.email_id,
		reason=said,
	)


def _admins() -> list[str]:
	from onedesk.one.roles import administrators

	return administrators()


def mailbox_shared(account: str, users: list[str]) -> None:
	"""People given a shared mailbox hear they have it."""
	people = [one for one in users if one != frappe.session.user]
	if people:
		notify.notify(
			"Mailbox Shared With You",
			people,
			link="/desk/onemail",
			who=frappe.utils.get_fullname(frappe.session.user),
			mailbox=frappe.db.get_value("Email Account", account, "email_id") or account,
		)


def not_sent() -> None:
	"""Every five minutes: mail somebody sent that frappe gave up on after
	its retries, told once to whoever sent it."""
	from frappe.utils import add_to_date, now_datetime

	for one in frappe.get_all(
		"Communication",
		filters={
			"sent_or_received": "Sent",
			"communication_medium": "Email",
			"delivery_status": "Error",
			"modified": [">=", add_to_date(now_datetime(), hours=-2)],
		},
		fields=["name", "owner", "subject", "recipients"],
	):
		if one.owner in ("Administrator", "Guest") or not frappe.db.get_value("User", one.owner, "enabled"):
			continue
		notify.notify(
			"Mail Not Sent",
			one.owner,
			record=("Communication", one.name),
			sender="Administrator",
			dedupe_on=["document_type", "document_name"],
			subject=one.subject or "",
			to=one.recipients or "",
		)
