"""What happens to new mail after it is filed: rules, out-of-office replies
and bounces, each run from `inbound.Arrival.process` on both kinds of mailbox."""

import email.utils
import re
from email.message import EmailMessage

import frappe
from frappe import _
from frappe.utils import add_days, formatdate, getdate, today

AWAY_ONCE_IN = 4 * 24 * 3600
AWAY_TO = ("Everyone", "Workspace", "Contacts")
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
	from onedesk.one_mail import signatures

	name = (
		signatures.sender_name_for(account.name, None)
		or signatures.default_sender_name(account.name)
		or account.email_account_name
		or ""
	)
	reply["From"] = email.utils.formataddr((name, account.email_id))
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


def on_leave(account: str) -> dict | None:
	"""The approved leave the person a mailbox belongs to is on today, if any:
	OneHR's leave is their out-of-office on every mailbox of their own, read
	as mail arrives, so nobody turns it on or off and a cancelled leave stops
	replying at once. A leave that asks for no replies, and the half day of a
	half-day leave, answer nothing. With it: the day they are back, and who
	covers for them."""
	from onedesk.one_mail import signatures

	user = signatures.person_of(account)
	if not user or not frappe.db.table_exists("Leave Application"):
		return None
	employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
	if not employee:
		return None
	leave = frappe.db.get_value(
		"Leave Application",
		{
			"employee": employee,
			"docstatus": 1,
			"status": "Approved",
			"from_date": ["<=", today()],
			"to_date": [">=", today()],
		},
		[
			"name",
			"from_date",
			"to_date",
			"half_day",
			"half_day_date",
			"one_away_message",
			"one_away_replies",
			"one_covering",
		],
		as_dict=True,
		order_by="to_date desc",
	)
	if not leave or leave.one_away_replies == 0 or half_day_today(leave):
		return None
	leave["back"] = back_on(employee, leave.to_date)
	leave["covering"] = covering_of(leave.one_covering)
	return leave


def half_day_today(leave) -> bool:
	"""Whether today is the half day of a half-day leave, which the person
	works too. Pure."""
	if not leave.get("half_day"):
		return False
	day = leave.get("half_day_date") or (leave.get("from_date") if leave.get("from_date") == leave.get("to_date") else None)
	return bool(day) and getdate(day) == getdate(today())


def back_on(employee: str, to_date) -> object:
	"""The first working day after a leave, past the weekends and holidays
	of the person's holiday list."""
	from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

	day = getdate(add_days(to_date, 1))
	holidays = get_holiday_list_for_employee(employee, raise_exception=False)
	if not holidays:
		return day
	off = {
		getdate(one)
		for one in frappe.get_all(
			"Holiday",
			filters={"parent": holidays, "holiday_date": ["between", [day, add_days(day, 60)]]},
			pluck="holiday_date",
		)
	}
	while day in off:
		day = getdate(add_days(day, 1))
	return day


def covering_of(employee: str | None) -> dict | None:
	"""Who covers for a person on leave, as a reply names them."""
	if not employee:
		return None
	said = frappe.db.get_value(
		"Employee", employee, ["employee_name", "user_id", "company_email", "prefered_email"], as_dict=True
	)
	if not said:
		return None
	address = said.prefered_email or said.company_email or said.user_id
	return {"name": said.employee_name, "email": address, "user": said.user_id} if address else None


def switched_on(account) -> bool:
	"""Whether a mailbox's own Out of Office is on today, within its dates. Pure."""
	if not account.get("one_away"):
		return False
	now = getdate(today())
	if account.get("one_away_from") and now < getdate(account.get("one_away_from")):
		return False
	return not (account.get("one_away_until") and now > getdate(account.get("one_away_until")))


def standard_away(back=None, covering: dict | None = None, lang: str | None = None) -> str:
	"""The reply nobody wrote, in one language. Pure."""
	said = (
		_("I'm on leave and back on {0}. I'll reply then.", lang=lang).format(formatdate(back))
		if back
		else _("I'm away and will reply when I'm back.", lang=lang)
	)
	return f"{said} {cover_line(covering, lang)}" if covering else said


def cover_line(covering: dict, lang: str | None = None) -> str:
	"""The sentence naming who covers. Pure."""
	return _("For anything urgent, please write to {0} at {1}.", lang=lang).format(covering["name"], covering["email"])


def default_away(account, back=None, covering: dict | None = None, lang: str | None = None) -> str:
	"""The standard reply in the person's language, and in the mailbox's
	second one under it when it has one. Pure."""
	first = standard_away(back, covering, lang)
	also = account.get("one_away_also")
	return f"{first}\n\n{standard_away(back, covering, also)}" if also and also != lang else first


def away_message(account, leave: dict | None, lang: str | None = None) -> str | None:
	"""What an out-of-office reply says, or None when nobody is away: the
	mailbox's own reply while it is on, else the leave's message, else the
	mailbox's, else the standard one with the day they are back. Whoever
	covers is named unless the message names them already. Pure."""
	if switched_on(account):
		return account.get("one_away_message") or default_away(account, lang=lang)
	if not leave:
		return None
	covering = leave.get("covering")
	written = leave.get("one_away_message") or account.get("one_away_message")
	if not written:
		return default_away(account, leave.get("back"), covering, lang)
	if covering and covering["email"].lower() not in written.lower():
		written += "\n\n" + cover_line(covering, lang)
	return written


def inside(sender: str) -> bool:
	"""Whether an address is one of the workspace's own: a person's, or one
	of its mailboxes."""
	return bool(
		frappe.db.exists("User", {"name": sender, "enabled": 1, "user_type": "System User"})
		or frappe.db.exists("Email Account", {"email_id": sender})
	)


def reaches(account, sender: str) -> bool:
	"""Whether a mailbox's out-of-office answers this sender, as its Away
	Replies To says: everyone, only the workspace's people, or them and the
	workspace's contacts."""
	to = account.get("one_away_to") or "Everyone"
	if to == "Everyone":
		return True
	if inside(sender):
		return True
	return to == "Contacts" and bool(frappe.db.exists("Contact Email", {"email_id": sender}))


def language_of(account: str) -> str | None:
	"""The language a person's replies are written in: their own."""
	from onedesk.one_mail import signatures

	user = signatures.person_of(account)
	return (frappe.db.get_value("User", user, "language") if user else None) or frappe.db.get_default("lang")


def signed(account, text: str) -> str:
	"""A reply as mail: its lines, then the mailbox's signature, its logo
	reachable from outside."""
	from frappe.utils import escape_html, get_url

	from onedesk.one_mail import signatures

	body = "".join(f'<p dir="auto">{escape_html(one).replace(chr(10), "<br>")}</p>' for one in text.split("\n\n"))
	signature = signatures.written(account.get("signature")) if account.get("add_signature") else ""
	if signature:
		signature = re.sub(r'src="/', f'src="{get_url()}/', signature)
		body += f"<br>{signature}"
	return f'<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px">{body}</div>'


def away(made, message) -> bool:
	"""An out-of-office reply, if the person a mailbox belongs to is away: by
	its own switch, or on approved leave. Never from a shared mailbox, whose
	answer is Auto Reply. Each sender is answered once in AWAY_ONCE_IN, and
	once again when a new time away begins."""
	account = frappe.get_doc("Email Account", made.email_account)
	if account.get("one_shared"):
		return False
	leave = None if switched_on(account) else on_leave(account.name)
	said = away_message(account, leave, language_of(account.name))
	if not said:
		return False
	sender = (made.sender or "").lower()
	if automatic(message, sender) or sender == (account.email_id or "").lower():
		return False
	if not reaches(account, sender):
		return False
	period = leave["name"] if leave else str(account.get("one_away_since") or account.get("one_away_from") or "")
	key = f"one_away:{account.name}:{period}:{sender}"
	if frappe.cache.get_value(key):
		return False
	frappe.cache.set_value(key, 1, expires_in_sec=AWAY_ONCE_IN)
	_reply(account, made, said, signed(account, said))
	return True


def away_state(account: str) -> dict | None:
	"""Whether a person's mailbox is answering for them now, and until when:
	{"until", "leave"}, or None. What the mailbox lists show."""
	doc = frappe.db.get_value(
		"Email Account",
		account,
		["one_away", "one_away_from", "one_away_until", "one_shared"],
		as_dict=True,
	)
	if not doc or doc.one_shared:
		return None
	if switched_on(doc):
		return {"until": doc.one_away_until, "leave": 0}
	leave = on_leave(account)
	return {"until": leave.to_date, "leave": 1} if leave else None


@frappe.whitelist(methods=["POST"])
def set_away(
	account: str,
	away: int = 0,
	until: str | None = None,
	message: str | None = None,
	from_date: str | None = None,
	to: str | None = None,
	also: str | None = None,
) -> None:
	"""Turn a person's out-of-office reply on or off, with its dates, who it
	answers and a second language: whoever may (holders.may, "away"). A
	shared mailbox answers with Auto Reply instead, and a person's approved
	leave answers on its own (on_leave)."""
	from onedesk.one_mail import holders

	holders.must(account, "away")
	was = frappe.db.get_value(
		"Email Account", account, ["one_shared", "one_away", "one_away_from"], as_dict=True
	)
	if was.one_shared:
		frappe.throw(_("A shared mailbox answers with Auto Reply instead."))
	if to and to not in AWAY_TO:
		frappe.throw(_("That cannot be set."))
	if until and from_date and getdate(until) < getdate(from_date):
		frappe.throw(_("The day it ends can't be before the day it starts."))
	values = {
		"one_away": int(bool(int(away))),
		"one_away_until": until or None,
		"one_away_from": from_date or None,
		"one_away_message": (message or "").strip() or None,
		"one_away_to": to or "Everyone",
		"one_away_also": also or None,
	}
	if values["one_away"] and (not was.one_away or str(was.one_away_from or "") != str(from_date or "")):
		values["one_away_since"] = frappe.utils.now_datetime()
	frappe.db.set_value("Email Account", account, values, update_modified=False)
	frappe.publish_realtime("one_mailbox", after_commit=True)


@frappe.whitelist()
def away_of(account: str) -> dict:
	"""A mailbox's out-of-office as its tab shows it, with the standard reply
	and the leave answering now, if any."""
	from onedesk.one_mail import holders

	holders.sees(account)
	said = frappe.db.get_value(
		"Email Account",
		account,
		[
			"one_away",
			"one_away_from",
			"one_away_until",
			"one_away_message",
			"one_away_to",
			"one_away_also",
			"one_shared",
			"one_hosted",
		],
		as_dict=True,
	)
	leave = on_leave(account) if not said.one_shared else None
	said["leave_until"] = leave.to_date if leave else None
	said["leave_back"] = leave.back if leave else None
	said["covering"] = leave.covering if leave else None
	said["languages"] = languages()
	said["lang"] = language_of(account)
	return said


@frappe.whitelist(methods=["POST"])
def away_preview(account: str, message: str | None = None, also: str | None = None) -> dict:
	"""The reply as a sender gets it, signed, and the standard reply in the
	languages chosen, which an untouched message follows."""
	from onedesk.one_mail import holders

	holders.sees(account)
	doc = frappe.get_doc("Email Account", account)
	doc.one_away_also = also or None
	standard = default_away(doc, lang=language_of(account))
	said = (message or "").strip() or standard
	return {"default": standard, "html": signed(doc, said), "subject": _("Re: {0}").format(_("Your message"))}


def languages() -> list[dict]:
	"""The languages One is written in, for a reply's second language."""
	from pathlib import Path

	codes = ["en", *sorted({path.stem for path in Path(frappe.get_app_path("onedesk", "locale")).glob("*.po")} - {"en"})]
	names = dict(frappe.get_all("Language", filters={"name": ["in", codes]}, fields=["name", "language_name"], as_list=True))
	return [{"value": code, "label": names.get(code) or code} for code in codes]


@frappe.whitelist()
def who_is_away(emails: str | list) -> list[dict]:
	"""Of the workspace's people a message is being written to, who is away
	now, until when, and who covers: what the composer warns of."""
	emails = frappe.parse_json(emails) if isinstance(emails, str) and emails.startswith("[") else emails
	if isinstance(emails, str):
		emails = [one.strip() for one in re.split(r"[,;]", emails)]
	said = []
	for address in {(one or "").strip().lower() for one in emails or [] if one}:
		account = frappe.db.get_value("Email Account", {"email_id": address, "one_shared": 0}, "name")
		if not account and frappe.db.exists("User", {"name": address, "enabled": 1}):
			account = next(
				(
					one
					for one in frappe.get_all("User Email", filters={"parent": address, "one_cover_until": ["is", "not set"]}, pluck="email_account")
					if not frappe.db.get_value("Email Account", one, "one_shared")
				),
				None,
			)
		state = away_state(account) if account else None
		if not state:
			continue
		from onedesk.one_mail import signatures

		person = signatures.person_of(account)
		leave = on_leave(account) if state["leave"] else None
		said.append(
			{
				"email": address,
				"name": frappe.utils.get_fullname(person) if person else address,
				"until": state["until"],
				"leave": state["leave"],
				"covering": (leave or {}).get("covering"),
			}
		)
	return said


def cover(*_args) -> None:
	"""Daily: whoever covers for a person on approved leave, where the leave
	says so, reads that person's workspace address until the leave ends, and
	not a day after. They never send from it."""
	for row in frappe.get_all("User Email", filters={"one_cover_until": ["<", today()]}, pluck="name"):
		frappe.db.delete("User Email", {"name": row})
	for leave in frappe.get_all(
		"Leave Application",
		filters={
			"docstatus": 1,
			"status": "Approved",
			"from_date": ["<=", today()],
			"to_date": [">=", today()],
			"one_covering_reads": 1,
		},
		pluck="name",
	):
		covered(frappe.get_doc("Leave Application", leave))


def covered(leave, method=None) -> None:
	"""Leave Application on_submit, on_update_after_submit and on_cancel:
	whoever covers reads the address while the leave is approved and under
	way, and stops when it is cancelled, changed or over."""
	person = frappe.db.get_value("Employee", leave.employee, "user_id")
	cover = covering_of(leave.get("one_covering"))
	address = _issued_to(person)
	if not person or not address:
		return
	for row in frappe.get_all(
		"User Email",
		filters={"email_account": address, "one_cover_until": ["is", "set"]},
		fields=["name", "parent"],
	):
		if not cover or row.parent != cover["user"] or not _covers_now(leave):
			frappe.db.delete("User Email", {"name": row.name})
	if not cover or not cover["user"] or cover["user"] == person or not _covers_now(leave):
		return
	if frappe.db.exists("User Email", {"parent": cover["user"], "email_account": address, "one_cover_until": ["is", "not set"]}):
		return
	fresh = not frappe.db.exists("User Email", {"parent": cover["user"], "email_account": address})
	if fresh:
		from onedesk.one_mail import addresses

		addresses.hold(address, cover["user"])
	frappe.db.set_value(
		"User Email",
		{"parent": cover["user"], "email_account": address},
		{"one_cover_until": leave.to_date, "one_sends": 0},
		update_modified=False,
	)
	if fresh:
		from onedesk.one_mail import tell

		tell.covering(address, person, cover["user"], leave.to_date)
	frappe.publish_realtime("one_mailbox", after_commit=True)


def _covers_now(leave) -> bool:
	return bool(
		leave.docstatus == 1
		and leave.status == "Approved"
		and leave.get("one_covering_reads")
		and getdate(leave.from_date) <= getdate(today()) <= getdate(leave.to_date)
	)


def _issued_to(user: str | None) -> str | None:
	"""A person's workspace address: the one the workspace issued them."""
	if not user:
		return None
	for account in frappe.get_all(
		"User Email", filters={"parent": user, "one_cover_until": ["is", "not set"]}, pluck="email_account"
	):
		if frappe.db.get_value("Email Account", account, ["one_hosted", "one_shared"]) == (1, 0):
			return account
	return None


@frappe.whitelist(methods=["POST"])
def set_auto_reply(account: str, on: int = 0, message: str | None = None) -> None:
	"""Turn a shared mailbox's Auto Reply on or off (acknowledge)."""
	from onedesk.one_mail import holders

	holders.must(account, "auto_reply")
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
	"""A mailbox's rules are seen by its holders and whoever may change them
	(holders.may, "rules"); rules_of_mailbox and save_rule say who changes
	them."""
	from onedesk.one_mail import actions, holders

	user = user or frappe.session.user
	return (
		user == "Administrator"
		or not doc.account
		or actions.holds(doc.account, user)
		or holders.may(doc.account, "rules", user)
	)


def rule_query(user=None) -> str:
	from onedesk.one import abilities

	user = user or frappe.session.user
	if user == "Administrator" or abilities.held("Email Account", "mail_rules", user):
		return ""
	return (
		f"""(`tabMail Rule`.account in (select email_account from `tabUser Email` where parent = {frappe.db.escape(user)})"""
		f""" or `tabMail Rule`.account in (select share_name from `tabDocShare` where share_doctype = 'Email Account'"""
		f""" and user = {frappe.db.escape(user)} and mail_rules = 1))"""
	)


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
	"requested_by",
)


@frappe.whitelist()
def rules_of_mailbox(account: str) -> dict:
	"""A mailbox's rules in the order they run, for its Mail Rules tab in
	OneMail's settings. Whoever manages the mailbox changes them; the person
	a workspace address is issued to asks for them (`asks`), and each waits
	for a Mail Manager (save_rule)."""
	from onedesk.one_mail import holders

	manages = holders.may(account, "rules")
	asks = not manages and holders.issued_to_them(account)
	if not (manages or asks):
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
		one["requested_by_name"] = frappe.utils.get_fullname(one.requested_by) if one.requested_by else None
	return {"may": True, "manages": int(manages), "asks": int(asks), "rules": rows}


def _changer(account: str) -> bool:
	"""Whether the reader changes a mailbox's rules outright (True) or asks
	for them (False); anyone else is refused."""
	from onedesk.one_mail import holders

	if holders.may(account, "rules"):
		return True
	if holders.issued_to_them(account):
		return False
	holders.must(account, "rules")
	return False


@frappe.whitelist(methods=["POST"])
def save_rule(account: str, values: dict | str, name: str | None = None) -> str:
	"""Make or change one of a mailbox's rules. On a workspace address the
	person holds but doesn't manage, the rule is saved off and asked for, and
	every Mail Manager hears of it; a change to a running rule is asked for
	again."""
	values = frappe.parse_json(values) if isinstance(values, str) else values
	outright = _changer(account)
	doc = frappe.get_doc("Mail Rule", name) if name else frappe.new_doc("Mail Rule")
	if name and doc.account != account:
		frappe.throw(_("That rule is not in this mailbox."))
	doc.update({key: values.get(key) for key in RULE_FIELDS if key in values and key != "requested_by"})
	doc.account = account
	if not outright:
		doc.enabled = 0
		doc.requested_by = frappe.session.user
	doc.flags.ignore_permissions = True
	doc.save() if name else doc.insert()
	if not outright:
		from onedesk.one_mail import tell

		tell.rule_requested(doc)
	return doc.name


@frappe.whitelist(methods=["POST"])
def enable_rule(name: str, enabled: int = 1) -> None:
	doc = frappe.get_doc("Mail Rule", name)
	if not _changer(doc.account):
		frappe.throw(_("A Mail Manager approves the rules of this mailbox."), frappe.PermissionError)
	doc.enabled = int(enabled)
	doc.flags.ignore_permissions = True
	doc.save()


@frappe.whitelist(methods=["POST"])
def delete_rule(name: str) -> None:
	"""Delete a rule: whoever manages its mailbox, or the person who asked
	for it while it still waits."""
	doc = frappe.get_doc("Mail Rule", name)
	if not _changer(doc.account) and doc.requested_by != frappe.session.user:
		frappe.throw(_("A Mail Manager approves the rules of this mailbox."), frappe.PermissionError)
	frappe.delete_doc("Mail Rule", name, ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def decide_rule(name: str, approve: int = 1) -> None:
	"""A Mail Manager approves a rule somebody asked for, which turns it on,
	or declines it, which deletes it. The person who asked hears either way."""
	from onedesk.one_mail import holders, tell

	doc = frappe.get_doc("Mail Rule", name)
	holders.must(doc.account, "rules")
	asker = doc.requested_by
	if not asker:
		frappe.throw(_("Nobody asked for this rule."))
	if int(approve):
		doc.enabled = 1
		doc.requested_by = None
		doc.flags.ignore_permissions = True
		doc.save()
	else:
		frappe.delete_doc("Mail Rule", name, ignore_permissions=True)
	tell.rule_decided(doc.account, asker, bool(int(approve)))
