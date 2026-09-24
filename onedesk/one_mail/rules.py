"""What happens to new mail after it is filed: rules, out-of-office replies
and bounces.

Each runs from `inbound.Arrival.process` once a message is in, on both kinds
of mailbox:

- **Rules** (`Mail Rule`) sort mail arriving in the Inbox: move it to a
  folder, mark it read, star it. On a connected mailbox this happens on the
  server through actions.py, so a phone sees the message where the rule put
  it. A rule acts for its mailbox whoever the job runs as
  (`frappe.flags.one_mail_rules`). Rules run on new mail only, never on history read in the background,
  or connecting a mailbox would re-sort years of it.
- **Away** replies once per sender in four days, from the mailbox itself,
  while its holder is away. Nothing that is itself automatic gets one:
  mailing lists, bulk mail, other auto-replies, bounces, and no-reply senders.
- **Bounces**: a delivery report saying an address failed for good puts the
  address on Frappe's own Email Unsubscribe list, which Frappe's queue
  already honours, and marks the message that bounced. A temporary failure
  is left alone.
"""

import email.utils
import re
from email.message import EmailMessage

import frappe
from frappe import _
from frappe.utils import getdate, today

#: How long an away reply is not repeated to the same sender, in seconds.
AWAY_ONCE_IN = 4 * 24 * 3600

#: Senders that are machines.
MACHINES = re.compile(
	r"^(no-?reply|do-?not-?reply|mailer-daemon|postmaster|bounces?)([+.@-]|$)", re.IGNORECASE
)


# ------------------------------------------------------------------ pure


def matches(rule: dict, message: dict) -> bool:
	"""Whether a message is one a rule is for. Pure."""
	tests = []
	if rule.get("from_contains"):
		tests.append(rule["from_contains"].lower() in (message.get("sender") or "").lower())
	if rule.get("to_contains"):
		people = f"{message.get('recipients') or ''} {message.get('cc') or ''}".lower()
		tests.append(rule["to_contains"].lower() in people)
	if rule.get("subject_contains"):
		tests.append(rule["subject_contains"].lower() in (message.get("subject") or "").lower())
	if rule.get("has_attachment"):
		tests.append(bool(message.get("has_attachment")))
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
		# The per-recipient blocks come as the payload's messages after the first.
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


# ------------------------------------------------------------------ after arrival


def after(made, arrival) -> None:
	"""Called by Arrival.process for each message filed."""
	if not made or not made.name:
		return
	try:
		bounce(made, arrival.mail)
		if getattr(arrival, "fresh", True) and _in_inbox(made):
			run_rules(made)
			away(made, arrival.mail)
	except Exception:
		frappe.log_error(title=f"OneMail could not sort {made.name}")


def _in_inbox(made) -> bool:
	kind = frappe.db.get_value(
		"Mail Folder", {"account": made.email_account, "path": made.one_folder}, "kind"
	)
	return kind == "Inbox" or made.one_folder == "INBOX"


def run_rules(made) -> list[str]:
	"""The rules of a message's mailbox, in order, until one says stop."""
	from onedesk.one_mail import actions

	done = []
	message = frappe.db.get_value(
		"Communication",
		made.name,
		["name", "sender", "recipients", "cc", "subject", "has_attachment"],
		as_dict=True,
	)
	for rule in frappe.get_all(
		"Mail Rule",
		filters={"account": made.email_account, "enabled": 1},
		fields=["*"],
		order_by="priority asc, creation asc",
	):
		if not matches(rule, message):
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
		done.append(rule.name)
		if rule.stop:
			break
	return done


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
	reply.set_content(account.get("one_away_message") or _("I am away and will answer when I am back."))
	from onedesk.one_mail import outbound

	outbound.deliver(account, sender, reply.as_bytes())
	return True


# ------------------------------------------------------------------ the page


@frappe.whitelist(methods=["POST"])
def set_away(account: str, away: int = 0, until: str | None = None, message: str | None = None) -> None:
	"""Turn a mailbox's out-of-office reply on or off."""
	from onedesk.one_mail import actions

	actions.require(account)
	frappe.db.set_value(
		"Email Account",
		account,
		{"one_away": int(away), "one_away_until": until or None, "one_away_message": message or None},
		update_modified=False,
	)


@frappe.whitelist()
def away_of(account: str) -> dict:
	from onedesk.one_mail import actions

	actions.require(account)
	return frappe.db.get_value(
		"Email Account", account, ["one_away", "one_away_until", "one_away_message"], as_dict=True
	)


# ------------------------------------------------------------------ who sees rules


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
