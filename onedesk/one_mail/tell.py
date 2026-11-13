"""Telling people about their mailboxes (notifications.py)."""

import frappe
from frappe import _

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
		link="/desk/one?center=account&at=plan",
		sender="Administrator",
		mailbox=frappe.db.get_value("Email Account", doc.email_account, "email_id") or doc.email_account,
	)


def mailbox_not_reachable(doc, said: str, holders: list[str]) -> None:
	"""Whoever holds a mailbox hears that it stopped connecting, and why."""
	notify.notify(
		"Mailbox Not Reachable",
		holders or _admins(),
		link="/desk/onemail?settings=mailboxes",
		sender="Administrator",
		mailbox=doc.email_id,
		reason=said,
	)


def oneai_limit_reached(held) -> None:
	"""A mailbox's credits for the month are spent: whoever OneAI reads
	it for and whoever connected it hear once."""
	owner = frappe.db.get_value("Email Account", held.name, "owner")
	people = [one for one in {held.one_intake_for, owner} if one and one not in ("Administrator", "Guest")]
	notify.notify(
		"Mailbox OneAI Limit Reached",
		people or _admins(),
		link=f"/desk/onemail?settings=mailbox:{held.name}:oneai",
		sender="Administrator",
		mailbox=held.email_id,
		limit=held.one_ai_limit,
	)


def rule_requested(rule) -> None:
	"""A rule asked for on an issued address: everybody who may approve it
	hears what it would do."""
	from onedesk.one import rights

	when, then = said_of(rule)
	notify.notify(
		"Mail Rule Requested",
		rights.people_with("Email Account", "mail_rules", rule.account),
		link=f"/desk/onemail?settings=mailbox:{rule.account}:rules",
		who=frappe.utils.get_fullname(frappe.session.user),
		mailbox=frappe.db.get_value("Email Account", rule.account, "email_id") or rule.account,
		when=frappe.utils.escape_html(when),
		then=frappe.utils.escape_html(then),
	)


def said_of(rule) -> tuple[str, str]:
	"""A rule's steps in words (one_mail/flow.py summary), with its folders'
	and people's names."""
	from onedesk.one_mail import flow, rules

	steps = rules.flow_of(rule)
	folders = dict(frappe.get_all("Mail Folder", filters={"account": rule.account}, fields=["name", "label"], as_list=True))
	people = {one.get("user"): frappe.utils.get_fullname(one.get("user")) for one in flow.actions_in(steps) if one.get("user")}
	return flow.summary(steps, folders, people)


def rule_notice(rule, user: str, name: str) -> None:
	"""A rule's Tell: somebody hears that mail it was waiting for arrived."""
	comm = frappe.db.get_value("Communication", name, ["sender", "sender_full_name", "subject", "email_account"], as_dict=True)
	notify.notify(
		"Mail Rule Notice",
		user,
		link=f"/desk/onemail?box={comm.email_account}",
		sender="Administrator",
		who=comm.sender_full_name or comm.sender,
		mailbox=frappe.db.get_value("Email Account", comm.email_account, "email_id") or comm.email_account,
		subject=comm.subject or "",
		rule=rule.title or rule.name,
	)


def rule_decided(account: str, asker: str, approved: bool) -> None:
	"""The person who asked for a rule hears whether it is on or gone."""
	notify.notify(
		"Mail Rule Approved" if approved else "Mail Rule Declined",
		asker,
		link=f"/desk/onemail?settings=mailbox:{account}:rules",
		who=frappe.utils.get_fullname(frappe.session.user),
		mailbox=frappe.db.get_value("Email Account", account, "email_id") or account,
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


def covering(account: str, person: str, user: str, until) -> None:
	"""Whoever covers for a person on leave hears that their mail is in
	OneMail until they are back."""
	notify.notify(
		"Covering Mail",
		user,
		link=f"/desk/onemail?box={account}",
		sender="Administrator",
		who=frappe.utils.get_fullname(person),
		mailbox=frappe.db.get_value("Email Account", account, "email_id") or account,
		until=frappe.utils.formatdate(until),
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


def no_reply(conversation, link: str) -> None:
	"""A reminder come due with no reply since (team.due), told to whoever
	asked for it."""
	if not conversation.remind_by or not frappe.db.get_value("User", conversation.remind_by, "enabled"):
		return
	notify.notify(
		"No Reply Yet",
		[conversation.remind_by],
		record=("Mail Conversation", conversation.name),
		link=link,
		sender="Administrator",
		subject=conversation.subject or _("A conversation"),
	)
