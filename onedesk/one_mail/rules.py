"""What happens to new mail after it is filed: rules, out-of-office replies
and bounces, each run from `inbound.Arrival.process` on both kinds of mailbox."""

import email.utils
import re
from email.message import EmailMessage

import frappe
from frappe import _
from frappe.utils import getdate, today

AWAY_ONCE_IN = 4 * 24 * 3600
ACK_ONCE_IN = 24 * 3600
RULE_REPLY_ONCE_IN = 30 * 24 * 3600
MOST_ASKED = 6000

MACHINES = re.compile(
	r"^(no-?reply|do-?not-?reply|mailer-daemon|postmaster|bounces?)([+.@-]|$)", re.IGNORECASE
)


def matches(rule: dict, message: dict, about: set | None = None) -> bool:
	"""Whether a message is one a rule is for. Pure.

	`about` is the rules OneAI read the message to be about. A rule with an
	About is not for the arrival at all (`about` None): it waits for OneAI,
	which reads the message a moment later (`by_meaning`)."""
	if rule.get("about") and about is None:
		return False
	tests = []
	if rule.get("from_contains"):
		tests.append(rule["from_contains"].lower() in (message.get("sender") or "").lower())
	if rule.get("to_contains"):
		people = f"{message.get('recipients') or ''} {message.get('cc') or ''}".lower()
		tests.append(rule["to_contains"].lower() in people)
	if rule.get("subject_contains"):
		tests.append(rule["subject_contains"].lower() in (message.get("subject") or "").lower())
	if rule.get("body_contains"):
		said = f"{message.get('subject') or ''} {message.get('text') or ''}".lower()
		tests.append(rule["body_contains"].lower() in said)
	if rule.get("has_attachment"):
		tests.append(bool(message.get("has_attachment")))
	if rule.get("about"):
		tests.append(rule.get("name") in about)
	if not tests:
		return False
	return any(tests) if (rule.get("match") or "").startswith("Any") else all(tests)


def automatic(headers, sender: str) -> bool:
	"""Whether a message was sent by a machine, and so gets no away reply.
	`headers` is anything with .get(). Pure."""
	if (headers.get("Auto-Submitted") or "no").strip().lower() != "no":
		return True
	if (headers.get("Precedence") or "").strip().lower() in ("bulk", "list", "junk"):
		return True
	if (
		headers.get("List-Id")
		or headers.get("List-Unsubscribe")
		or headers.get("X-Autoreply")
		or headers.get("X-Autorespond")
	):
		return True
	return bool(MACHINES.match((sender or "").split("@")[0] + "@")) or not sender


def failures(message) -> list[tuple[str, str, str]]:
	"""The addresses a delivery report says failed for good, as (address,
	status, diagnostic). Pure over an email.message."""
	if (
		message.get_content_type() != "multipart/report"
		or message.get_param("report-type") != "delivery-status"
	):
		return []
	out = []
	for part in message.walk():
		if part.get_content_type() != "message/delivery-status":
			continue
		blocks = part.get_payload() if part.is_multipart() else []
		for block in blocks[1:]:
			action = (block.get("Action") or "").strip().lower()
			status = (block.get("Status") or "").strip()
			recipient = (
				(block.get("Final-Recipient") or block.get("Original-Recipient") or "").split(";")[-1].strip()
			)
			if action == "failed" and status.startswith("5") and "@" in recipient:
				out.append(
					(recipient.lower(), status, (block.get("Diagnostic-Code") or "").split(";")[-1].strip())
				)
	return out


def bounced_id(message) -> str | None:
	"""The Message-ID of the message a delivery report is about. Pure."""
	for part in message.walk():
		if part.get_content_type() in ("message/rfc822", "text/rfc822-headers"):
			inner = (
				part.get_payload(0)
				if part.is_multipart()
				else email.message_from_string(part.get_payload(decode=True).decode(errors="replace"))
			)
			found = inner.get("Message-ID")
			if found:
				return found.strip().strip("<>")
	return None


def after(made, arrival) -> None:
	"""Called by Arrival.process for each message filed."""
	if not made or not made.name:
		return
	try:
		bounce(made, arrival.mail)
		if getattr(arrival, "fresh", True) and _in_inbox(made):
			frappe.local.one_rule_replied = None
			run_rules(made, headers=arrival.mail)
			if not away(made, arrival.mail) and not frappe.local.one_rule_replied:
				acknowledge(made, arrival.mail)
	except Exception:
		frappe.log_error(title=f"OneMail could not sort {made.name}")


def _in_inbox(made) -> bool:
	kind = frappe.db.get_value(
		"Mail Folder", {"account": made.email_account, "path": made.one_folder}, "kind"
	)
	return kind == "Inbox" or made.one_folder == "INBOX"


def run_rules(made, about: set | None = None, headers=None) -> list[str]:
	"""The rules of a message's mailbox, in order, until one says stop. On
	arrival `about` is None and only the rules without an About run; OneAI's
	reading runs those with one (`by_meaning`). `headers` are the message's,
	when it is arriving, so a rule's Reply never answers a machine."""
	from onedesk.one_mail import actions

	done = []
	message = frappe.db.get_value(
		"Communication",
		made.name,
		["name", "sender", "recipients", "cc", "subject", "has_attachment", "content"],
		as_dict=True,
	)
	message["text"] = frappe.utils.strip_html_tags(message.pop("content") or "")
	for rule in rules_of(made.email_account, about is not None):
		if not matches(rule, message, about):
			continue
		frappe.flags.one_mail_rules = True
		try:
			if rule.mark_read:
				actions.mark([made.name], 1)
			if rule.star:
				actions.star([made.name], 1)
			if rule.move_to:
				actions.move([made.name], rule.move_to)
		finally:
			frappe.flags.one_mail_rules = False
		if rule.reply:
			try:
				answer(rule, made.name, headers)
			except Exception:
				frappe.log_error(title=f"OneMail could not reply by the rule {rule.name}")
		done.append(rule.name)
		if rule.stop:
			break
	return done


def answer(rule, name: str, headers=None) -> str | None:
	"""A rule's Reply: its own text, or OneAI's answer from the rule's
	instruction. Once per conversation, never to a machine or to the mailbox
	itself. OneAI's answer waits as a card for whoever made the rule when the
	rule asks for review, and always when it left a blank in brackets for a
	person to fill in. Answers "sent", "card" or None."""
	comm = frappe.db.get_value(
		"Communication",
		name,
		["name", "sender", "sender_full_name", "subject", "content", "one_thread", "message_id", "email_account"],
		as_dict=True,
	)
	account = frappe.get_doc("Email Account", comm.email_account)
	sender = (comm.sender or "").lower()
	if automatic(headers or {}, sender) or sender == (account.email_id or "").lower():
		return None
	key = f"one_rule_reply:{rule.name}:{comm.one_thread or comm.message_id or name}"
	if frappe.cache.get_value(key):
		return None
	if rule.reply_with == "OneAI":
		from onedesk.one_mail import gate

		held = gate.of(account.name)
		if not held or held.one_ai_off or gate.over(held):
			return None
		text = _drafted(rule, comm)
		if not text:
			return None
		frappe.cache.set_value(key, 1, expires_in_sec=RULE_REPLY_ONCE_IN)
		if rule.reply_review or "[" in text:
			_card(rule, comm, account, text)
			return "card"
		_send(account, comm, _paragraphs(text))
		return "sent"
	frappe.cache.set_value(key, 1, expires_in_sec=RULE_REPLY_ONCE_IN)
	html = frappe.render_template(
		rule.reply_text or "",
		{"sender_name": comm.sender_full_name or "", "subject": comm.subject or "", "mailbox": account.email_id},
	)
	_send(account, comm, html)
	return "sent"


def _drafted(rule, comm) -> str:
	"""OneAI's reply (the "reply" action), counted against the mailbox."""
	from onedesk.one_ai import run

	text = frappe.utils.strip_html_tags(comm.content or "")[:MOST_ASKED]
	asked = (
		f"What the reply should say, from the mailbox's owner: {rule.reply_instruction}\n\n"
		f"The message, from {comm.sender_full_name or ''} <{comm.sender}>, subject \"{comm.subject or ''}\":\n\n{text}\n\n"
		"Write the reply in the message's language, as plain text, paragraphs apart by a blank line."
	)
	return (run.once("reply", asked, reference=comm.name) or "").strip()


def _paragraphs(text: str) -> str:
	return "".join(
		f"<p>{frappe.utils.escape_html(one).replace(chr(10), '<br>')}</p>" for one in text.split("\n\n") if one.strip()
	)


def _send(account, comm, html: str) -> None:
	"""The reply, sent from the mailbox in the conversation's thread, signed
	as the mailbox signs."""
	from frappe.core.doctype.communication.email import make

	if account.get("add_signature") and account.get("signature"):
		html += f"<br>{account.signature}"
	subject = comm.subject or ""
	make(
		recipients=comm.sender,
		subject=subject if subject.lower().startswith("re:") else f"Re: {subject}".strip(),
		content=html,
		sender=account.email_id,
		send_email=1,
		in_reply_to=comm.name,
		communication_medium="Email",
	)
	frappe.local.one_rule_replied = comm.name


def _card(rule, comm, account, text: str) -> None:
	"""OneAI's reply as a card for whoever made the rule, the same card the
	OneAI panel's draft_reply makes: approving opens it in the email window."""
	from onedesk.one_ai import proposals

	was = frappe.session.user
	frappe.set_user(rule.owner)
	try:
		proposals.propose(
			"Reply",
			"Communication",
			changes={"account": account.name, "thread": comm.one_thread or comm.name, "subject": comm.subject, "text": text},
			record=comm.name,
			why=_("Mail rule: {0}").format(rule.name),
		)
	finally:
		frappe.set_user(was)
	frappe.local.one_rule_replied = comm.name


def rules_of(account: str, by_meaning: bool = False) -> list:
	"""A mailbox's rules that are on, in order: those without an About, or
	only those with one."""
	return [
		rule
		for rule in frappe.get_all(
			"Mail Rule",
			filters={"account": account, "enabled": 1},
			fields=["*"],
			order_by="priority asc, creation asc",
		)
		if bool(rule.about) == by_meaning
	]


def by_meaning(message: str, about: set) -> list[str]:
	"""The About rules OneAI read a new message to be about, run once it has
	read it (one_intake/understand.py), on a message still in the Inbox:
	a rule that already moved it on arrival wins."""
	made = frappe.get_doc("Communication", message)
	if not about or not _in_inbox(made):
		return []
	return run_rules(made, about)


def bounce(made, message) -> list[str]:
	"""A delivery report's permanent failures, onto Email Unsubscribe."""
	failed = failures(message)
	for address, status, said in failed:
		why = f"{status} {said}".strip()
		found = frappe.db.get_value("Email Unsubscribe", {"email": address, "global_unsubscribe": 1}, "name")
		if found:
			frappe.db.set_value("Email Unsubscribe", found, "one_bounce", why, update_modified=False)
		else:
			frappe.get_doc(
				{"doctype": "Email Unsubscribe", "email": address, "global_unsubscribe": 1, "one_bounce": why}
			).insert(ignore_permissions=True)
	if failed:
		original = bounced_id(message)
		if original:
			frappe.db.set_value(
				"Communication", {"message_id": original}, "delivery_status", "Bounced", update_modified=False
			)
	return [one[0] for one in failed]


def _reply(account, made, text: str, html: str | None = None) -> None:
	"""An automatic reply to the sender of `made`, threaded under it."""
	from onedesk.one_mail import outbound

	sender = (made.sender or "").lower()
	reply = EmailMessage()
	reply["From"] = email.utils.formataddr((account.email_account_name or "", account.email_id))
	reply["To"] = sender
	reply["Subject"] = f"Re: {made.subject or ''}".strip()
	reply["Date"] = email.utils.formatdate(localtime=True)
	reply["Message-ID"] = email.utils.make_msgid(domain=account.email_id.split("@")[-1])
	reply["Auto-Submitted"] = "auto-replied"
	if made.message_id:
		reply["In-Reply-To"] = f"<{made.message_id.strip('<>')}>"
		reply["References"] = f"<{made.message_id.strip('<>')}>"
	reply.set_content(text)
	if html:
		reply.add_alternative(html, subtype="html")
	outbound.deliver(account, sender, reply.as_bytes())


def starts_conversation(headers) -> bool:
	"""Whether a message opens a conversation rather than answering one.
	`headers` is anything with .get(). Pure."""
	return not (headers.get("In-Reply-To") or headers.get("References"))


def acknowledge(made, message) -> bool:
	"""A shared mailbox's Auto Reply (frappe's own enable_auto_reply and
	auto_reply_message on Email Account): to the first message of each new
	conversation, never to a machine, at most once a day per sender."""
	account = frappe.get_doc("Email Account", made.email_account)
	if not (account.get("one_shared") and account.get("enable_auto_reply")):
		return False
	sender = (made.sender or "").lower()
	if automatic(message, sender) or sender == (account.email_id or "").lower():
		return False
	if not starts_conversation(message):
		return False
	key = f"one_ack:{account.name}:{sender}"
	if frappe.cache.get_value(key):
		return False
	frappe.cache.set_value(key, 1, expires_in_sec=ACK_ONCE_IN)
	said = account.get("auto_reply_message") or ""
	if frappe.utils.strip_html_tags(said).strip():
		html = frappe.render_template(
			said, {"sender_name": made.sender_full_name or "", "subject": made.subject or "", "mailbox": account.email_id}
		)
		_reply(account, made, frappe.utils.to_markdown(html), html)
	else:
		_reply(account, made, _("We received your message and will reply soon."))
	return True


def away(made, message) -> bool:
	"""An out-of-office reply, if the mailbox's holder is away."""
	account = frappe.get_doc("Email Account", made.email_account)
	if not account.get("one_away"):
		return False
	if account.get("one_away_until") and getdate(today()) > getdate(account.one_away_until):
		return False
	sender = (made.sender or "").lower()
	if automatic(message, sender) or sender == (account.email_id or "").lower():
		return False
	key = f"one_away:{account.name}:{sender}"
	if frappe.cache.get_value(key):
		return False
	frappe.cache.set_value(key, 1, expires_in_sec=AWAY_ONCE_IN)
	_reply(account, made, account.get("one_away_message") or _("I'm away and will reply when I'm back."))
	return True


@frappe.whitelist(methods=["POST"])
def set_away(account: str, away: int = 0, until: str | None = None, message: str | None = None) -> None:
	"""Turn a mailbox's out-of-office reply on or off. A shared mailbox's is
	its connector's or an administrator's (holders.manages)."""
	from onedesk.one_mail import holders

	holders.manages(account)
	frappe.db.set_value(
		"Email Account",
		account,
		{"one_away": int(away), "one_away_until": until or None, "one_away_message": message or None},
		update_modified=False,
	)


@frappe.whitelist()
def away_of(account: str) -> dict:
	from onedesk.one_mail import holders

	holders.sees(account)
	return frappe.db.get_value(
		"Email Account", account, ["one_away", "one_away_until", "one_away_message"], as_dict=True
	)


@frappe.whitelist(methods=["POST"])
def set_auto_reply(account: str, on: int = 0, message: str | None = None) -> None:
	"""Turn a shared mailbox's Auto Reply on or off (acknowledge)."""
	from onedesk.one_mail import holders

	holders.manages(account)
	if not frappe.db.get_value("Email Account", account, "one_shared"):
		frappe.throw(_("Only a shared mailbox has an Auto Reply."))
	frappe.db.set_value(
		"Email Account",
		account,
		{"enable_auto_reply": int(on), "auto_reply_message": message or None},
		update_modified=False,
	)


@frappe.whitelist()
def auto_reply_of(account: str) -> dict:
	from onedesk.one_mail import holders

	holders.sees(account)
	return frappe.db.get_value("Email Account", account, ["enable_auto_reply", "auto_reply_message"], as_dict=True)


def rule_allowed(doc, ptype=None, user=None, debug=False) -> bool:
	"""A mailbox's rules are its holders'."""
	from onedesk.one_mail import actions

	user = user or frappe.session.user
	return user == "Administrator" or not doc.account or actions.holds(doc.account, user)


def rule_query(user=None) -> str:
	user = user or frappe.session.user
	if user == "Administrator":
		return ""
	return f"""`tabMail Rule`.account in (select email_account from `tabUser Email` where parent = {frappe.db.escape(user)})"""


RULE_FIELDS = (
	"enabled",
	"priority",
	"match",
	"from_contains",
	"to_contains",
	"subject_contains",
	"body_contains",
	"has_attachment",
	"about",
	"move_to",
	"mark_read",
	"star",
	"reply",
	"reply_with",
	"reply_text",
	"reply_instruction",
	"reply_review",
	"stop",
)


@frappe.whitelist()
def rules_of_mailbox(account: str) -> dict:
	"""A mailbox's rules in the order they run, for its Mail Rules tab in
	OneMail's settings. They are its holders' (rule_allowed)."""
	from onedesk.one_mail import actions

	if not actions.holds(account):
		return {"may": False, "rules": []}
	rows = frappe.get_all(
		"Mail Rule",
		filters={"account": account},
		fields=["name", *RULE_FIELDS],
		order_by="priority asc, creation asc",
	)
	labels = dict(
		frappe.get_all(
			"Mail Folder", filters={"name": ["in", [one.move_to for one in rows if one.move_to] or [""]]}, fields=["name", "label"], as_list=True
		)
	)
	for one in rows:
		one["move_to_label"] = labels.get(one.move_to) if one.move_to else None
	return {"may": True, "rules": rows}


@frappe.whitelist(methods=["POST"])
def save_rule(account: str, values: dict | str, name: str | None = None) -> str:
	"""Make or change one of a mailbox's rules, with its holder's permission."""
	values = frappe.parse_json(values) if isinstance(values, str) else values
	doc = frappe.get_doc("Mail Rule", name) if name else frappe.new_doc("Mail Rule")
	if name and doc.account != account:
		frappe.throw(_("That rule is not in this mailbox."))
	doc.update({key: values.get(key) for key in RULE_FIELDS if key in values})
	doc.account = account
	doc.save() if name else doc.insert()
	return doc.name


@frappe.whitelist(methods=["POST"])
def enable_rule(name: str, enabled: int = 1) -> None:
	doc = frappe.get_doc("Mail Rule", name)
	doc.enabled = int(enabled)
	doc.save()


@frappe.whitelist(methods=["POST"])
def delete_rule(name: str) -> None:
	frappe.delete_doc("Mail Rule", name)
