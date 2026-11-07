"""Mail being written, kept on the server as its writer types (Mail Draft):
saved from frappe's composer a moment after each change, listed in its
mailbox's Drafts and on its conversation, opened again where it was left,
and gone once it is sent or discarded. A draft is its writer's alone, even
on a shared mailbox, and is never sent or synced on its own."""

import frappe
from frappe import _

from onedesk.one_mail import actions, live

DRAFT = "Mail Draft"
FIELDS = ("subject", "recipients", "cc", "bcc", "content", "thread", "in_reply_to", "kind", "reference_doctype", "reference_name", "send_after")


def _mine(name: str):
	doc = frappe.get_doc(DRAFT, name)
	if doc.owner != frappe.session.user:
		frappe.throw(_("That draft is somebody else's."), frappe.PermissionError)
	return doc


def has_permission(doc, ptype=None, user=None) -> bool:
	"""A draft opens for its writer only, whatever their roles."""
	return doc.owner == (user or frappe.session.user)


def _account(sender: str | None) -> str | None:
	"""The mailbox the composer sends from, by its address, if the writer
	holds it."""
	from onedesk.one_mail import holders

	found = frappe.db.get_value("Email Account", {"email_id": sender}, "name") if sender else None
	return found if found and found in holders.sending_rows() else None


@frappe.whitelist(methods=["POST"])
def save(sender: str | None = None, name: str | None = None, attachments=None, **values) -> str | None:
	"""The draft as it is now: made the first time, changed after. Nothing is
	kept for an address the writer does not hold."""
	account = _account(sender)
	if not account:
		return None
	actions.require(account)
	if values.get("in_reply_to") and not values.get("thread"):
		values["thread"] = frappe.db.get_value("Communication", values["in_reply_to"], "one_thread") or values["in_reply_to"]
	doc = _mine(name) if name and frappe.db.exists(DRAFT, name) else frappe.new_doc(DRAFT)
	doc.account = account
	for field in FIELDS:
		if field in values:
			doc.set(field, values[field] or None)
	doc.kind = doc.kind or "New"
	if attachments is not None:
		doc.attachments = frappe.as_json(frappe.parse_json(attachments) or [])
	doc.flags.ignore_permissions = True
	doc.save()
	live.changed(account)
	_mirror(doc)
	return doc.name


@frappe.whitelist()
def get(name: str) -> dict:
	"""A draft, to open in the composer again."""
	doc = _mine(name)
	actions.require(doc.account)
	said = {field: doc.get(field) for field in FIELDS}
	said.update(name=doc.name, account=doc.account, sender=frappe.db.get_value("Email Account", doc.account, "email_id"))
	said["attachments"] = frappe.parse_json(doc.attachments or "[]") or []
	return said


@frappe.whitelist()
def replying_to(name: str) -> dict | None:
	"""The message a draft answers, as the composer quotes it."""
	doc = _mine(name)
	if not doc.in_reply_to or not frappe.has_permission("Communication", "read", doc=doc.in_reply_to):
		return None
	return frappe.db.get_value(
		"Communication", doc.in_reply_to, ["name", "sender", "recipients", "cc", "subject", "content", "communication_date"], as_dict=True
	)


@frappe.whitelist(methods=["POST"])
def discard(name: str) -> None:
	"""A draft sent or thrown away."""
	if not frappe.db.exists(DRAFT, name):
		return
	doc = _mine(name)
	account = doc.account
	frappe.delete_doc(DRAFT, name, ignore_permissions=True)
	live.changed(account)
	if doc.message_id and frappe.db.get_value("Email Account", account, "one_connected"):
		frappe.enqueue(
			"onedesk.one_mail.drafts.off_server", account=account, message_id=doc.message_id, queue="short", enqueue_after_commit=True
		)


def listed(account: str) -> list[dict]:
	"""The reader's drafts in a mailbox, newest first, as conversations the
	Drafts folder shows."""
	rows = frappe.get_all(
		DRAFT,
		filters={"account": account, "owner": frappe.session.user},
		fields=["name", "subject", "recipients", "content", "modified", "thread", "kind"],
		order_by="modified desc",
	)
	from onedesk.one_mail.api import snippet

	email = frappe.db.get_value("Email Account", account, "email_id")
	return [
		{
			"thread": f"draft:{one.name}",
			"draft": one.name,
			"name": None,
			"subject": one.subject,
			"sender": email,
			"sender_name": None,
			"recipients": one.recipients,
			"sent": 1,
			"snippet": snippet(one.content),
			"date": one.modified,
			"count": 1,
			"unread": 0,
			"flagged": 0,
			"attachments": 0,
			"folder": None,
		}
		for one in rows
	]


def of_thread(account: str, thread: str) -> str | None:
	"""The reader's draft of a reply in a conversation."""
	return frappe.db.get_value(DRAFT, {"account": account, "thread": thread, "owner": frappe.session.user}, "name", order_by="modified desc")


def scheduled(names: list[str]) -> dict:
	"""When each of these messages, sent from here with a time to wait, goes
	out: frappe's Schedule email, held in its Email Queue until then."""
	if not names:
		return {}
	return {
		one.communication: one.send_after
		for one in frappe.get_all(
			"Email Queue",
			filters={"communication": ["in", names], "status": "Not Sent", "send_after": [">", frappe.utils.now_datetime()]},
			fields=["communication", "send_after"],
		)
	}


@frappe.whitelist(methods=["POST"])
def unschedule(name: str) -> str:
	"""A scheduled message taken back before it goes: its queue is emptied
	and it is a draft again, to change and send."""
	doc = frappe.get_doc("Communication", name)
	if doc.owner != frappe.session.user or not doc.email_account:
		frappe.throw(_("Only whoever wrote it may take it back."), frappe.PermissionError)
	actions.require(doc.email_account)
	held = frappe.get_all("Email Queue", filters={"communication": name, "status": "Not Sent"}, pluck="name")
	if not held:
		frappe.throw(_("It has already gone."))
	for queue in held:
		frappe.db.delete("Email Queue Recipient", {"parent": queue})
		frappe.db.delete("Email Queue", {"name": queue})
	draft = frappe.get_doc(
		{
			"doctype": DRAFT,
			"account": doc.email_account,
			"subject": doc.subject,
			"recipients": doc.recipients,
			"cc": doc.cc,
			"bcc": doc.bcc,
			"content": doc.content,
			"thread": doc.one_thread,
			"in_reply_to": doc.in_reply_to,
			"kind": "Reply" if doc.in_reply_to else "New",
			"reference_doctype": doc.reference_doctype,
			"reference_name": doc.reference_name,
		}
	)
	draft.flags.ignore_permissions = True
	draft.insert()
	frappe.delete_doc("Communication", name, ignore_permissions=True, force=True)
	live.changed(doc.email_account)
	return draft.name


def _mirror(doc) -> None:
	"""A connected mailbox's draft goes to its Drafts on the server too, so a
	mail app on a phone shows it: once a moment after the last change."""
	if not frappe.db.get_value("Email Account", doc.account, "one_connected"):
		return
	if not doc.message_id:
		from email.utils import make_msgid

		domain = (frappe.db.get_value("Email Account", doc.account, "email_id") or "one").split("@")[-1]
		doc.db_set("message_id", make_msgid(domain=domain).strip("<>"), update_modified=False)
	frappe.enqueue(
		"onedesk.one_mail.drafts.to_server",
		name=doc.name,
		queue="short",
		job_id=f"onemail_draft:{doc.name}",
		deduplicate=True,
		enqueue_after_commit=True,
	)


def message(doc) -> bytes:
	"""A draft as the message a mail client keeps in Drafts. Pure apart from
	reading its mailbox's address."""
	from email.message import EmailMessage
	from email.utils import format_datetime

	sender = frappe.db.get_value("Email Account", doc.account, "email_id")
	said = EmailMessage()
	said["From"] = sender
	for header, value in (("To", doc.recipients), ("Cc", doc.cc), ("Bcc", doc.bcc)):
		if value:
			said[header] = ", ".join(one.strip() for one in value.replace(";", ",").split(",") if one.strip())
	said["Subject"] = doc.subject or ""
	said["Message-ID"] = f"<{doc.message_id}>"
	said["Date"] = format_datetime(frappe.utils.get_datetime(doc.modified).astimezone())
	if doc.in_reply_to:
		parent = frappe.db.get_value("Communication", doc.in_reply_to, "message_id")
		if parent:
			said["In-Reply-To"] = f"<{parent.strip('<>')}>"
			said["References"] = f"<{parent.strip('<>')}>"
	from frappe.core.utils import html2text

	said.set_content(html2text(doc.content or ""))
	said.add_alternative(doc.content or "", subtype="html")
	return said.as_bytes()


def _replace(session, path: str, message_id: str, raw: bytes | None) -> None:
	session.select(path, readonly=False)
	session.expunge(session.uids(f'HEADER Message-ID "{message_id}"'))
	if raw:
		session.append(path, raw, "\\Draft \\Seen")


def to_server(name: str) -> None:
	"""The draft as it is now, in its connected mailbox's Drafts: the copy
	before it taken out, this one put in."""
	from onedesk.one_mail import actions, imap

	if not frappe.db.exists(DRAFT, name):
		return
	doc = frappe.get_doc(DRAFT, name)
	path = actions.folder_of(doc.account, "Drafts")
	if not path or not doc.message_id:
		return
	try:
		with imap.Session(frappe.get_doc("Email Account", doc.account)) as session:
			_replace(session, path, doc.message_id, message(doc))
	except Exception:
		frappe.log_error(title=f"OneMail could not keep a draft in {doc.account}'s Drafts")


def off_server(account: str, message_id: str) -> None:
	"""A draft sent or thrown away leaves the server's Drafts too."""
	from onedesk.one_mail import actions, imap

	path = actions.folder_of(account, "Drafts")
	if not path:
		return
	try:
		with imap.Session(frappe.get_doc("Email Account", account)) as session:
			_replace(session, path, message_id, None)
	except Exception:
		frappe.log_error(title=f"OneMail could not take a draft out of {account}'s Drafts")


def mirrored(account: str) -> list[str]:
	"""The Message-IDs of the reader's drafts kept on the server, whose copies
	the Drafts folder does not list again."""
	return frappe.get_all(DRAFT, filters={"account": account, "owner": frappe.session.user, "message_id": ["is", "set"]}, pluck="message_id")
