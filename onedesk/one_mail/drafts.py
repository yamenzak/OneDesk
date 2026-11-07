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
