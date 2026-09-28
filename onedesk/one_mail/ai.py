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
from frappe import _lt
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
