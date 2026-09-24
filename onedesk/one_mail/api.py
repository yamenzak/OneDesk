"""What the OneMail page reads: a folder's conversations, and one
conversation's messages.

A conversation is the messages of one thread (`one_thread`) in one mailbox.
The list shows, per folder, one row per conversation that has a message in
that folder, dated by its newest message there. Opening it shows every
message of the conversation in the mailbox, whatever folder each is in, so a
reply in Sent is read beside the message it answers.

Everything is read as the reader, after `actions.require`: only somebody who
holds a mailbox reads it.
"""

import re
from email.utils import parseaddr

import frappe
from frappe.query_builder.functions import Coalesce, Count, Max, Sum
from frappe.utils import cint, strip_html

from onedesk.one_mail import actions, faces, holders

#: Conversations per page of the list.
PAGE = 50

#: Characters of a message's text shown under its subject.
SNIPPET = 140


def snippet(html: str | None) -> str:
	"""A message's first words, as text. Pure apart from Frappe's strip_html."""
	text = strip_html(html or "")
	text = re.sub(r"\s+", " ", text).strip()
	return text[:SNIPPET]


def _address(text: str | None) -> str:
	"""The first address in a From or To, bare and lowercased. Pure."""
	first = (text or "").split(",")[0]
	return (parseaddr(first)[1] or "").lower()


def _paths(account: str, folder: str) -> list[str]:
	"""The `one_folder` values a folder answers to. Mail sent from here is
	filed as "Sent" until its copy on the server is read and matched."""
	row = frappe.db.get_value("Mail Folder", folder, ["account", "path", "kind"], as_dict=True)
	if not row or row.account != account:
		frappe.throw(frappe._("That folder is not in this mailbox."))
	return list({row.path, "Sent"}) if row.kind == "Sent" else [row.path]


@frappe.whitelist()
def mailboxes() -> list[dict]:
	return holders.mailboxes()


@frappe.whitelist()
def conversations(account: str, folder: str | None = None, search: str | None = None, start: int = 0) -> dict:
	"""One page of a folder's conversations, newest first. With `search`, the
	whole mailbox is searched and `folder` is ignored."""
	actions.require(account)
	C = frappe.qb.DocType("Communication")
	query = frappe.qb.from_(C).where(C.email_account == account).where(C.communication_medium == "Email")
	search = (search or "").strip()
	if search:
		like = f"%{search}%"
		query = query.where(
			(C.subject.like(like))
			| (C.sender.like(like))
			| (C.sender_full_name.like(like))
			| (C.recipients.like(like))
			| (C.content.like(like))
		).where(C.one_folder.isnotnull())
	elif folder:
		query = query.where(C.one_folder.isin(_paths(account, folder)))
	else:
		frappe.throw(frappe._("Choose a folder."))
	thread = Coalesce(C.one_thread, C.name)
	rows = (
		query.select(
			thread.as_("thread"),
			Max(C.communication_date).as_("date"),
			Count("*").as_("count"),
			Sum(1 - C.seen).as_("unread"),
			Max(C.one_flagged).as_("flagged"),
			Max(C.has_attachment).as_("attachments"),
		)
		.groupby(thread)
		.orderby("date", order=frappe.qb.desc)
		.limit(PAGE + 1)
		.offset(cint(start))
		.run(as_dict=True)
	)
	more = len(rows) > PAGE
	rows = rows[:PAGE]
	if not rows:
		return {"items": [], "more": 0}
	# The newest message of each conversation, among those listed here.
	newest = {}
	for message in (
		query.select(
			C.name,
			thread.as_("thread"),
			C.subject,
			C.sender,
			C.sender_full_name,
			C.recipients,
			C.content,
			C.communication_date,
			C.sent_or_received,
			C.one_folder,
		)
		.where(thread.isin([row.thread for row in rows]))
		.orderby(C.communication_date, order=frappe.qb.desc)
		.run(as_dict=True)
	):
		newest.setdefault(message.thread, message)
	items = []
	for row in rows:
		message = newest.get(row.thread) or {}
		items.append(
			{
				"thread": row.thread,
				"name": message.get("name"),
				"subject": message.get("subject"),
				"sender": message.get("sender"),
				"sender_name": message.get("sender_full_name"),
				"recipients": message.get("recipients"),
				"sent": int(message.get("sent_or_received") == "Sent"),
				"snippet": snippet(message.get("content")),
				"date": row.date,
				"count": row["count"],
				"unread": cint(row.unread),
				"flagged": cint(row.flagged),
				"attachments": cint(row.attachments),
				"folder": message.get("one_folder"),
			}
		)
	pictures = faces.lookup([_address(one["recipients"] if one["sent"] else one["sender"]) for one in items])
	for one in items:
		one["face"] = pictures.get(_address(one["recipients"] if one["sent"] else one["sender"]))
	return {"items": items, "more": int(more)}


@frappe.whitelist()
def conversation(account: str, thread: str) -> dict:
	"""Every message of one conversation in a mailbox, oldest first, with
	their attachments."""
	actions.require(account)
	messages = frappe.get_all(
		"Communication",
		filters={"email_account": account, "communication_medium": "Email", "one_folder": ["is", "set"]},
		or_filters={"one_thread": thread, "name": thread},
		fields=[
			"name", "subject", "sender", "sender_full_name", "recipients", "cc", "bcc", "content",
			"communication_date", "sent_or_received", "seen", "one_flagged", "one_folder", "has_attachment",
			"reference_doctype", "reference_name", "message_id",
		],
		order_by="communication_date asc",
	)  # fmt: skip
	files = {}
	names = [one.name for one in messages if one.has_attachment]
	if names:
		for row in frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Communication", "attached_to_name": ["in", names]},
			fields=["name", "file_name", "file_url", "file_size", "attached_to_name", "is_private"],
		):
			files.setdefault(row.attached_to_name, []).append(row)
	pictures = faces.lookup([_address(one.sender) for one in messages])
	for one in messages:
		one["face"] = pictures.get(_address(one.sender))
		one["attachments"] = files.get(one.name, [])
		one["snippet"] = snippet(one.content)
	return {"thread": thread, "messages": messages}


@frappe.whitelist()
def names(account: str, threads, folder: str | None = None) -> list[str]:
	"""The messages of these conversations in a mailbox, or only those in one
	folder of it: what reading or starring a conversation changes, and what
	moving it out of a folder moves."""
	actions.require(account)
	threads = frappe.parse_json(threads) if isinstance(threads, str) else threads
	if not threads:
		return []
	filters = {"email_account": account, "communication_medium": "Email", "one_folder": ["is", "set"]}
	if folder:
		filters["one_folder"] = ["in", _paths(account, folder)]
	return frappe.get_all(
		"Communication",
		filters=filters,
		or_filters={"one_thread": ["in", threads], "name": ["in", threads]},
		pluck="name",
	)
