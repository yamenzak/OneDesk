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

A message from an address on the mail domain that is too large to send has
its largest attachments sent as OneCloud links instead, until it fits
(`shrink`). The links download without an account and stop working after
thirty days.

On the way out, a reply gets a `References` header, which Frappe does not
set. It is its parent's references followed by the parent itself, so the
other side's mail client threads it as ours does (threads.py).
"""

import base64
from email import message_from_bytes
from email.utils import parseaddr

import frappe

from onedesk.one_mail import threads

#: What a message from the mail domain may weigh before its largest
#: attachments go as links. Admin refuses over 5 MiB (one_admin/mailing.py);
#: this leaves room for the headers each recipient's copy adds.
ROOMY = 4 * 1024 * 1024

#: How long a link made for an attachment works, in days.
LINK_DAYS = 30

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

		raw = shrink(raw, _linker(queue), heading=frappe._("Too large to attach, so sent as links:"))

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
	if account.get("one_connected") and account.append_emails_to_sent_folder and _last(queue, recipient):
		file_copy(account, raw)


def _last(queue, recipient: str) -> bool:
	"""Whether this is the queue's last recipient, so a message sent to five
	people is filed in Sent once."""
	return bool(queue.recipients) and queue.recipients[-1].recipient == recipient


def file_copy(account, raw: bytes) -> None:
	"""A connected mailbox's copy of what it sent, in its Sent folder on the
	server, as a mail client would put it. Frappe does this only for accounts
	it reads itself, which connected ones are not. The next sync matches the
	copy to the Communication by its Message-ID."""
	from onedesk.one_mail import actions, imap

	try:
		with imap.Session(account) as session:
			session.append(actions.folder_of(account.name, "Sent") or account.sent_folder_name or "Sent", raw)
	except Exception:
		# The message went; only its copy did not. Not worth failing the queue.
		frappe.log_error(title=f"OneMail could not file a sent copy in {account.name}")


def shrink(
	raw: bytes, link_for, most: int = ROOMY, heading: str = "Too large to attach, so sent as links:"
) -> bytes:
	"""The message, with its largest attachments taken out and named with a
	link in its text, until it weighs `most` or less. `link_for(file name)`
	answers a link, or None for a file it cannot find, which then stays.
	Pure given `link_for`."""
	if len(raw) <= most:
		return raw
	parsed = message_from_bytes(raw)
	if not parsed.is_multipart():
		return raw
	containers = [one for one in parsed.walk() if one.is_multipart()]
	attached = [one for one in parsed.walk() if one.get_content_disposition() == "attachment"]
	attached.sort(key=lambda one: len(one.as_bytes()), reverse=True)
	size, linked = len(raw), []
	for part in attached:
		if size <= most:
			break
		name = part.get_filename()
		url = link_for(name) if name else None
		if not url:
			continue
		for container in containers:
			if part in container.get_payload():
				container.get_payload().remove(part)
				break
		size -= len(part.as_bytes())
		linked.append((name, url))
	if not linked:
		return raw
	_say(parsed, heading, linked)
	return parsed.as_bytes()


def _say(parsed, heading: str, linked: list) -> None:
	"""Add the links to the message's text, plain and HTML alike."""
	from html import escape

	said = {"plain": False, "html": False}
	for part in parsed.walk():
		kind = part.get_content_subtype()
		if (
			part.get_content_maintype() != "text"
			or kind not in said
			or said[kind]
			or part.get_content_disposition() == "attachment"
		):
			continue
		charset = part.get_content_charset() or "utf-8"
		text = (part.get_payload(decode=True) or b"").decode(charset, errors="replace")
		if kind == "plain":
			text += "\n\n" + heading + "\n" + "\n".join(f"{name}: {url}" for name, url in linked) + "\n"
		else:
			rows = "".join(f'<li><a href="{escape(url)}">{escape(name)}</a></li>' for name, url in linked)
			addition = f"<p>{escape(heading)}</p><ul>{rows}</ul>"
			text = text.replace("</body>", addition + "</body>") if "</body>" in text else text + addition
		del part["Content-Transfer-Encoding"]
		part.set_payload(text, charset="utf-8")
		said[kind] = True


def _linker(queue):
	"""`link_for` for one queue: a link for each of its message's files, made
	once however many recipients the message has."""
	made = frappe.local.__dict__.setdefault("one_mail_links", {})

	def link_for(name: str) -> str | None:
		key = (queue.name, name)
		if key not in made:
			made[key] = _link(queue.communication, name)
		return made[key]

	return link_for


def _link(communication: str | None, name: str) -> str | None:
	from frappe.utils import add_days, today

	from onedesk.one_storage import links

	file = communication and frappe.db.get_value(
		"File",
		{"attached_to_doctype": "Communication", "attached_to_name": communication, "file_name": name},
		"name",
	)
	if not file:
		return None
	link = frappe.get_doc(
		{
			"doctype": "Cloud Link",
			"file": file,
			"audience": links.ANYONE,
			"allow_download": 1,
			"expires_on": add_days(today(), LINK_DAYS),
		}
	)
	link.insert(ignore_permissions=True)
	return links.url_of(link.flags.token)


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
			"Communication", doc.in_reply_to, ["one_thread", "message_id", "one_references"], as_dict=True
		)
		if parent:
			doc.one_thread = parent.one_thread or parent.message_id
			if parent.message_id:
				doc.one_references = " ".join(chain(parent.message_id.strip(" <>"), parent.one_references))


def thread_sent(doc, method=None) -> None:
	"""Communication on_update: a new conversation's thread is its own
	Message-ID, which Frappe gives it only once the queue is made."""
	if doc.communication_medium == "Email" and not doc.one_thread and doc.message_id:
		doc.db_set("one_thread", doc.message_id.strip(" <>"), update_modified=False)
