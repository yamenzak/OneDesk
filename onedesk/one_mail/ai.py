"""What OneAI does in OneMail: reads the conversation that is open, says
which conversations wait for an answer, and drafts a reply the way the
reader asks for it.

Everything is read as the reader, and only from a mailbox they hold
(`actions.require`): the same rule that decides who may open a message
decides what OneAI may read of it. A conversation's text goes to the model
only when the reader asks about it; nothing of it is kept but the answer.

A reply is never sent from here. `draft_reply` writes a card; approving it
opens frappe's own email window with the reply written in, the recipients
and the quoted conversation filled as Reply fills them, and the person
reads it, changes it and sends it (onemail.js `reply_to`).
"""

import re
from html import unescape
from typing import Annotated

import frappe
from frappe import _, _lt
from frappe.utils import strip_html

#: Characters of one message's text given to the model.
MOST_TEXT = 4000

#: The newest messages of a conversation given to the model.
MOST_MESSAGES = 15

SUGGESTIONS = {
	"page:onemail": [
		{
			"label": _lt("Summarise this conversation"),
			"ask": _lt(
				"Summarise this conversation in a few lines: who wants what, what was agreed, and what is still open."
			),
			"expects": "open_conversation",
		},
		{
			# The reader says what the reply should say: "turn down their offer",
			# "agree only if they deliver by the 10th". The panel puts these words
			# in its box and waits for theirs.
			"label": _lt("Draft a reply"),
			"ask": _lt("Draft a reply to this conversation that says: "),
			"fill": True,
			"expects": "open_conversation",
		},
		{
			"label": _lt("What needs an answer?"),
			"ask": _lt("Which conversations in this folder are waiting for an answer from us? Oldest first."),
			"expects": "waiting_for_answer",
		},
	],
}


def page(said: dict) -> str | None:
	"""The sentence the model is told on the OneMail page: the mailbox, the
	folder, and the conversation open, when the reader holds it."""
	if said.get("page") != "onemail":
		return None
	from onedesk.one_mail import actions

	account, thread = said.get("box") or "", said.get("record") or ""
	where = "The reader is in OneMail"
	if account and actions.holds(account):
		where += f", in the mailbox {account} (the folder id is {said.get('folder') or 'not open'})"
		subject = _subject(account, thread) if thread else None
		if subject:
			where += f', with the conversation "{subject}" open (its thread is {thread})'
	return (
		where + ". open_conversation reads a conversation's messages; waiting_for_answer lists the folder's "
		"conversations whose last message is not ours. To draft a reply, read the conversation first, then call "
		"draft_reply with the whole reply written as the reader asked, in the language of the conversation: it "
		"becomes a card that opens the email window with the reply in, and is never sent by itself. How OneMail "
		"works is in its documentation (how_to)."
	)


def _subject(account: str, thread: str) -> str | None:
	return frappe.db.get_value(
		"Communication",
		{"email_account": account, "communication_medium": "Email", "one_thread": thread},
		"subject",
	) or frappe.db.get_value("Communication", {"email_account": account, "name": thread}, "subject")


def text(html: str | None) -> str:
	"""A message as plain text, its paragraphs kept. Pure apart from frappe's
	strip_html."""
	said = re.sub(r"(?i)<\s*(br|/p|/div|/li|/tr|/h\d)\b[^>]*>", "\n", html or "")
	said = unescape(strip_html(said))
	return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", said)).strip()


def open_conversation(
	account: Annotated[str, "The mailbox, as the page names it (its address)."],
	thread: Annotated[str, "The conversation's thread, as the page names it."],
) -> dict:
	"""A conversation in a mailbox the reader holds: each message's sender,
	recipients, date, text and attachments, oldest first. Read it before
	summarising a conversation or drafting a reply to it."""
	from onedesk.one_mail import actions, api

	if not actions.holds(account):
		return {"error": f"The reader does not hold {account}."}
	said = api.conversation(account, thread)
	messages = said["messages"][-MOST_MESSAGES:]
	if not messages:
		return {"error": "There is no such conversation in that mailbox."}
	return {
		"subject": messages[-1].subject,
		"messages": [
			{
				"from": one.sender_full_name or one.sender,
				"address": one.sender,
				"to": one.recipients,
				"cc": one.cc,
				"when": str(one.communication_date),
				"ours": one.sent_or_received == "Sent",
				"text": text(one.content)[:MOST_TEXT],
				"attachments": [file.file_name for file in one.attachments],
			}
			for one in messages
		],
		"earlier_left_out": max(0, len(said["messages"]) - MOST_MESSAGES),
	}


def waiting_for_answer(
	account: Annotated[str, "The mailbox, as the page names it (its address)."],
	folder: Annotated[str, "The folder's id, as the page names it."],
) -> dict:
	"""The conversations in a folder whose newest message came to us rather
	than from us, oldest first: what is waiting for an answer."""
	from onedesk.one_mail import actions, api

	if not actions.holds(account):
		return {"error": f"The reader does not hold {account}."}
	listed = api.conversations(account, folder)["items"]
	waiting = [one for one in listed if not one["sent"]]
	return {
		"waiting": [
			{
				"subject": one["subject"],
				"from": one["sender_name"] or one["sender"],
				"since": str(one["date"]),
				"thread": one["thread"],
				"last_said": one["snippet"],
			}
			for one in reversed(waiting)
		],
		"of_listed": len(listed),
	}


def draft_reply(
	account: Annotated[str, "The mailbox the conversation is in (its address)."],
	thread: Annotated[str, "The conversation's thread."],
	reply: Annotated[
		str,
		"The whole reply, as it should be sent: greeting, body and closing, in the language of the "
		"conversation, saying what the reader asked it to. Plain text; paragraphs apart by a blank line. "
		"No signature: the mailbox adds its own.",
	],
	why: Annotated[str, "In a sentence, what the reply says."] | None = None,
) -> dict:
	"""Suggest a reply to a conversation, as a card the reader approves.
	Read the conversation with open_conversation first. Approving opens the
	email window with the reply written in, to be read, changed and sent by
	the reader: nothing is ever sent from here."""
	from onedesk.one_ai import proposals
	from onedesk.one_mail import actions, api

	if not actions.holds(account):
		return {"error": f"The reader does not hold {account}."}
	messages = api.conversation(account, thread)["messages"]
	if not messages:
		return {"error": "There is no such conversation in that mailbox."}
	body = (reply or "").strip()
	if not body:
		return {"error": "Write the reply itself."}
	last = messages[-1]
	return {
		"proposal": proposals.propose(
			"Reply",
			"Communication",
			changes={"account": account, "thread": thread, "subject": last.subject, "text": body},
			record=last.name,
			why=why,
		),
		"state": "Proposed",
		"next": "Tell them Approve opens the reply in the email window to read, change and send; it is not sent "
		"until they send it.",
	}


#: How many of the Inbox's newest messages a new rule sorts at once, when it
#: is asked to sort what is there now as well.
MOST_NOW = 500


def suggest_mail_rule(
	folder: Annotated[
		str, "The folder to move the mail to, by its name, such as CocaCola. Made if the mailbox has none."
	],
	mailbox: Annotated[
		str, "The mailbox's address, one the person holds (my_mailboxes). Left out when they hold one."
	]
	| None = None,
	text_contains: Annotated[str, "A word or words found in the subject or anywhere in the message."]
	| None = None,
	from_contains: Annotated[str, "Part of the sender's address or name."] | None = None,
	subject_contains: Annotated[str, "Found in the subject only."] | None = None,
	about: Annotated[
		str,
		"What the mail is about, in plain words, such as soft drinks, when it is a matter of meaning "
		"rather than of a word. OneAI reads each new mail for it.",
	]
	| None = None,
	sort_inbox_now: Annotated[
		bool, "Also move the mail in the Inbox now that the words match (not for about)."
	] = False,
	why: Annotated[str, "In a sentence, what the rule does."] | None = None,
) -> dict:
	"""Suggest a rule that sorts a mailbox's new mail into a folder, as a card
	the person approves: by words in it, its sender or subject, or by what it
	is about. The folder is made if it is missing, and for a rule about what
	mail says, OneAI starts reading the mailbox. Only for a mailbox the person
	holds."""
	from onedesk.one_ai import proposals
	from onedesk.one_mail import holders

	held = holders.mailboxes()
	box = next(
		(
			one
			for one in held
			if mailbox and mailbox.strip().lower() in (one["name"].lower(), (one["email"] or "").lower())
		),
		held[0] if len(held) == 1 and not mailbox else None,
	)
	if not box:
		return {
			"mend": "suggest_mail_rule",
			"error": "Name one of the mailboxes the person holds: "
			+ ", ".join(one["email"] or one["name"] for one in held),
		}
	label = (folder or "").strip()
	words = {
		key: (value or "").strip()
		for key, value in (
			("body_contains", text_contains),
			("from_contains", from_contains),
			("subject_contains", subject_contains),
		)
	}
	about = (about or "").strip()
	if not label:
		return {"mend": "suggest_mail_rule", "error": "Say which folder the mail goes to."}
	if not any(words.values()) and not about:
		return {
			"mend": "suggest_mail_rule",
			"error": "Say which mail: words in it, its sender, its subject, or what it is about.",
		}
	existing = next(
		(one["name"] for one in box["folders"] if (one["label"] or "").lower() == label.lower()), None
	)
	read = bool(about) and not box["intake"]
	when = [
		_('Subject or text contains "{0}"').format(words["body_contains"]) if words["body_contains"] else "",
		_('From contains "{0}"').format(words["from_contains"]) if words["from_contains"] else "",
		_('Subject contains "{0}"').format(words["subject_contains"]) if words["subject_contains"] else "",
		_("About {0}").format(about) if about else "",
	]
	summary = [
		{"label": _("Mailbox"), "value": box["email"] or box["name"]},
		{"label": _("When"), "value": "; ".join(filter(None, when))},
		{
			"label": _("Move To"),
			"value": label if existing else _("{0} (new folder)").format(label),
		},
	]
	if read:
		summary.append(
			{"label": _("Read with OneAI"), "value": _("Turned on for this mailbox")}
		)
	if sort_inbox_now and any(words.values()):
		summary.append({"label": _("Inbox"), "value": _("Matching mail is moved too")})
	changes = {
		"what": "mail_rule",
		"account": box["name"],
		"folder": existing,
		"label": label,
		**words,
		"about": about,
		"read": int(read),
		"now": int(bool(sort_inbox_now) and any(words.values())),
		"title": _("Sort mail into {0}").format(label),
		"summary": summary,
		"route": ["List", "Mail Rule", {"account": box["name"]}],
	}
	return {
		"proposal": proposals.propose("Setup", "Mail Rule", changes=changes, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what the rule does once approved. Nothing changes until they approve it.",
	}


def make_rule(changes: dict) -> str:
	"""A mail rule's card approved, by a holder of its mailbox: the folder
	made if it is missing, OneAI switched on to read the mailbox if the rule
	is about what mail says, the rule, and what is in the Inbox now sorted
	if that was asked."""
	from onedesk.one_intake import switches
	from onedesk.one_mail import actions, rules

	account = changes["account"]
	actions.require(account)
	folder = changes.get("folder") or frappe.db.get_value(
		"Mail Folder", {"account": account, "label": changes["label"]}, "name"
	)
	if not folder:
		folder = actions.create_folder(account, changes["label"])
	if changes.get("read"):
		switches.set_mailbox(account, 1)
	rule = frappe.get_doc(
		{
			"doctype": "Mail Rule",
			"account": account,
			"from_contains": changes.get("from_contains") or None,
			"subject_contains": changes.get("subject_contains") or None,
			"body_contains": changes.get("body_contains") or None,
			"about": changes.get("about") or None,
			"move_to": folder,
		}
	).insert()
	if changes.get("now"):
		found = []
		for one in frappe.get_all(
			"Communication",
			filters={
				"email_account": account,
				"one_folder": actions.folder_of(account, "Inbox"),
				"sent_or_received": "Received",
			},
			fields=["name", "sender", "recipients", "cc", "subject", "has_attachment", "content"],
			order_by="communication_date desc",
			limit=MOST_NOW,
		):
			one["text"] = strip_html(one.pop("content") or "")
			if rules.matches(rule.as_dict(), one):
				found.append(one.name)
		if found:
			actions.move(found, folder)
	return rule.name
