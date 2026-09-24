"""Every email this workspace sends goes through here.

Frappe's Email Queue builds each message and, for each recipient, calls the
`override_email_send` hook instead of its own SMTP when one is set. The hook
replaces the transport for every account, not only ours, so it picks by the
account the queue is sending from:
- an address on the mail domain (`one_hosted`) goes to admin, which checks
  it is this workspace's own and hands it to Cloudflare (one_admin/mailing.py);
- any other account goes over its own SMTP, as Frappe would have sent it.

Email Queue keeps everything else: retries, statuses, the IMAP Sent copy for
a connected account, the Communication.

On the way out, a reply gets a `References` header, which Frappe does not
set. It is its parent's references followed by the parent itself, so the
other side's mail client threads it as ours does (threads.py).
"""

import base64
from email import message_from_bytes
from email.utils import parseaddr

import frappe

from onedesk.one_mail import threads

#: How many ancestors a References header carries. Mail clients keep the
#: first and the last few; twenty is plenty and keeps headers short.
KEPT = 20


def send(queue, sender: str, recipient: str, message) -> None:
	"""The override_email_send hook."""
	raw = message if isinstance(message, bytes) else message.encode()
	raw = with_references(raw)
	account = _account(queue, sender)
	if account and account.get("one_hosted"):
		from onedesk.one import account as admin

		admin.ask(
			"onedesk.one_admin.proxy.mail_send",
			sender=parseaddr(sender)[1],
			recipient=recipient,
			message=base64.b64encode(raw).decode(),
		)
		return
	if not account:
		frappe.throw(frappe._("No mail account can send as {0}.").format(sender))
	server = account.get_smtp_server()
	try:
		server.session.sendmail(from_addr=parseaddr(sender)[1], to_addrs=recipient, msg=raw)
	finally:
		server.quit()


def _account(queue, sender: str):
	from frappe.email.doctype.email_account.email_account import EmailAccount

	if queue.email_account:
		return frappe.get_doc("Email Account", queue.email_account)
	# Frappe answers {what matched: account}, or nothing.
	found = EmailAccount.find_outgoing(match_by_email=parseaddr(sender)[1])
	return next(iter(found.values()), None) if found else None


def chain(parent: str, parents_references: str | None) -> list[str]:
	"""What a reply's References should list: the parent's own references,
	then the parent, the last `KEPT` of them. Pure."""
	ids = [one for one in threads.ids(parents_references) if one != parent] + [parent]
	return ids[-KEPT:]


def with_references(raw: bytes) -> bytes:
	"""The message, with a References header if it replies and has none."""
	parsed = message_from_bytes(raw)
	parents = threads.ids(parsed.get("In-Reply-To"))
	if parsed.get("References") or not parents:
		return raw
	parent = parents[-1]
	held = frappe.db.get_value("Communication", {"message_id": parent}, "one_references")
	parsed["References"] = " ".join(f"<{one}>" for one in chain(parent, held))
	return parsed.as_bytes()


# ------------------------------------------------------------------ filing


def file_sent(doc, method=None) -> None:
	"""Communication before_insert: mail sent from here is in Sent, and in
	the thread of what it answers."""
	if doc.communication_medium != "Email" or doc.sent_or_received != "Sent":
		return
	doc.one_folder = doc.one_folder or "Sent"
	if not doc.one_thread and doc.in_reply_to:
		parent = frappe.db.get_value(
			"Communication", doc.in_reply_to, ["one_thread", "message_id"], as_dict=True
		)
		if parent:
			doc.one_thread = parent.one_thread or parent.message_id


def thread_sent(doc, method=None) -> None:
	"""Communication on_update: a new conversation's thread is its own
	Message-ID, which Frappe gives it only once the queue is made."""
	if doc.communication_medium == "Email" and not doc.one_thread and doc.message_id:
		doc.db_set("one_thread", doc.message_id.strip(" <>"), update_modified=False)
