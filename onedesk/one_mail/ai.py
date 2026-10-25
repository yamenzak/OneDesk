"""What OneAI does in OneMail: reads the conversation that is open, says
which conversations wait for an answer, and drafts a reply the way the
reader asks for it."""

import re
from html import unescape
from typing import Annotated

import frappe
from frappe import _, _lt
from frappe.utils import strip_html

from onedesk.one_mail import gate

MOST_TEXT = 4000

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
		{
			"label": _lt("Why is a mailbox not working?"),
			"ask": _lt("Are any of my mailboxes not working, why, and what do I do about it?"),
			"expects": "my_mailboxes",
		},
		{
			"label": _lt("Write a mail template"),
			"ask": _lt("Write a mail template for: "),
			"fill": True,
			"expects": "write_mail_template",
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
	if account and not gate.may_read(account):
		return (
			where
			+ f", in the mailbox {account}, which OneAI is turned off for: nothing in it can be read or drafted."
		)
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
	if not gate.may_read(account):
		return {"error": f"OneAI is turned off for {account}: its mail can't be read."}
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
	if not gate.may_read(account):
		return {"error": f"OneAI is turned off for {account}: its mail can't be read."}
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
	if not gate.may_read(account):
		return {"error": f"OneAI is turned off for {account}: its mail can't be read."}
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
		summary.append({"label": _("Read with OneAI"), "value": _("Turned on for this mailbox")})
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
	from onedesk.one_mail import actions, flow, rules

	account = changes["account"]
	actions.require(account)
	folder = changes.get("folder") or frappe.db.get_value(
		"Mail Folder", {"account": account, "label": changes["label"]}, "name"
	)
	if not folder:
		folder = actions.create_folder(account, changes["label"])
	if changes.get("read"):
		switches.set_mailbox(account, 1)
	steps = flow.from_fields(
		{
			"from_contains": changes.get("from_contains"),
			"subject_contains": changes.get("subject_contains"),
			"body_contains": changes.get("body_contains"),
			"about": changes.get("about"),
			"move_to": folder,
		}
	)
	rule = frappe.get_doc(
		{
			"doctype": "Mail Rule",
			"account": account,
			"title": changes.get("title") or changes["label"],
			"steps": frappe.as_json(steps, indent=None),
		}
	).insert()
	if changes.get("now") and not flow.needs_ai(steps):
		found = []
		for one in frappe.get_all(
			"Communication",
			filters={
				"email_account": account,
				"one_folder": actions.folder_of(account, "Inbox"),
				"sent_or_received": "Received",
			},
			pluck="name",
			order_by="communication_date desc",
			limit=MOST_NOW,
		):
			if flow.walk(steps, rules.facts_of(one))[0]:
				found.append(one)
		if found:
			actions.move(found, folder)
	return rule.name


# The mailboxes the reader has, their signatures, and the workspace's mail
# templates, each change a card the reader approves.


def my_mailboxes() -> dict:
	"""The mailboxes the person asking holds: which they send from, what each
	signs with now, which have stopped connecting and why; and what a
	signature of theirs would be made of (name, job, phone, company)."""
	from onedesk.one_hr import own
	from onedesk.one_mail import holders

	user = frappe.get_doc("User", frappe.session.user)
	employee = own.employee_of()
	work = (
		frappe.db.get_value(
			"Employee", employee, ["designation", "department", "company", "cell_number"], as_dict=True
		)
		if employee
		else None
	) or {}
	return {
		"mailboxes": [
			{
				"mailbox": one["name"],
				"address": one["email"],
				"whose": "the workspace's" if one["workspace"] or one["shared"] else "yours",
				"sends": bool(one["sends"]),
				"may_sign": bool(one["may_sign"]),
				"signature": frappe.db.get_value("Email Account", one["name"], "signature")
				if one["may_sign"]
				else None,
				"not_connecting": one["error"],
				"fix": "Reconnect it on this page with its password" if one["may_reconnect"] else None,
			}
			for one in holders.mailboxes()
		],
		"signature_from": {
			"name": user.full_name,
			"designation": work.get("designation"),
			"department": work.get("department"),
			"company": work.get("company") or frappe.defaults.get_global_default("company"),
			"phone": user.mobile_no or work.get("cell_number"),
			"email": user.email,
		},
	}


def sign_mailbox(
	mailbox: Annotated[str, "The mailbox, as my_mailboxes named it."],
	signature: Annotated[
		str, "The signature: a few short lines of simple HTML (<br> between lines, <b> at most)."
	],
	why: Annotated[str, "In a sentence, what it says."] | None = None,
) -> dict:
	"""Suggest a signature for a mailbox the person asking sends from, as a
	card they approve. Read my_mailboxes first. Nothing changes until they
	approve it."""
	from onedesk.one_ai import proposals
	from onedesk.one_mail import holders

	if not frappe.db.exists("Email Account", mailbox) or not holders.may_sign(mailbox):
		return {"error": f"You cannot change how {mailbox} signs. my_mailboxes lists the ones you can."}
	return {
		"proposal": proposals.propose(
			"Signature",
			"Email Account",
			changes={"signature": (signature or "").strip()},
			record=mailbox,
			why=why,
		),
		"state": "Proposed",
	}


TEMPLATE_HELP = (
	"A template is a subject and a message. Name a field of the record in double braces, bare, as "
	"{{ customer_name }} or {{ due_date }}: never {{ doc.customer_name }}, which the mail composer, the leave "
	"mails and the salary slip all fail on. Nothing else in braces: no conditions, loops or filters. The "
	"message is plain sentences, a blank line between paragraphs. It ends with a closing line such as Kind "
	"regards and no name under it: the mailbox it is sent from signs it. Read workspace_mail_templates with "
	"the kind of record first, for the fields it may name."
)


def workspace_mail_templates(
	doctype: Annotated[
		str, "A kind of record, such as Sales Invoice, to also read the fields a template may name."
	]
	| None = None,
) -> dict:
	"""The workspace's mail templates, for its administrators: each one's
	subject and message as written, the kind of record it is for (none: any
	record), which kinds start the composer with it, and which setting sends
	it (the leave mails, the interview reminders). For a kind of record, the
	fields a template for it may name. Read it before suggesting one."""
	from onedesk.one import roles, rules
	from onedesk.one_mail import mail_templates

	if not roles.administers():
		return {"error": "Only a workspace administrator sees the mail templates."}
	named_by = {}
	for single, field, _kind in mail_templates.NAMED_BY:
		if frappe.db.exists("DocType", single):
			template = frappe.db.get_single_value(single, field)
			if template:
				named_by.setdefault(template, []).append(
					f"{_(single)}: {frappe.get_meta(single).get_label(field)}"
				)
	said = {
		"templates": [
			{
				"name": one["name"],
				"for": one["reference_doctype"] or "any record",
				"subject": one["subject"],
				"message": frappe.utils.strip_html_tags(
					frappe.db.get_value("Email Template", one["name"], "response") or ""
				)[:1500],
				"default_for": one["default_for"],
				"sent_by": named_by.get(one["name"], []),
			}
			for one in mail_templates.templates()
		],
		"how_a_template_is_written": TEMPLATE_HELP,
	}
	if doctype:
		try:
			mail_templates._doctype(doctype)
		except frappe.ValidationError as e:
			frappe.clear_last_message()
			return {"error": str(e)}
		said["fields"] = {"doctype": doctype, "may_name": rules.readable(doctype)}
	return said


def write_mail_template(
	subject: Annotated[str, "One line. Fields of the record as {{ fieldname }}."],
	message: Annotated[str, "The mail itself, paragraphs separated by a blank line. " + TEMPLATE_HELP],
	name: Annotated[str, "An existing template to change, as workspace_mail_templates names it."]
	| None = None,
	new_name: Annotated[str, "A new template's name, such as Payment Reminder."] | None = None,
	for_doctype: Annotated[str, "The kind of record it is for, such as Sales Invoice. Empty: any record."]
	| None = None,
	why: Annotated[str, "In a sentence, what the template is for."] | None = None,
) -> dict:
	"""Suggest a mail template, new or changed, as a card a workspace
	administrator approves: the words a mail about a kind of record starts
	with, picked in the composer on the record and in OneMail. Read
	workspace_mail_templates first. Nothing is saved until they approve it.
	Workspace administrators only."""
	from onedesk.one import roles, rules
	from onedesk.one_ai import proposals
	from onedesk.one_mail import mail_templates

	if not roles.administers():
		return {
			"mend": "write_mail_template",
			"error": "Only a workspace administrator writes mail templates.",
		}
	if bool(name) == bool(new_name):
		return {
			"mend": "write_mail_template",
			"error": "Give name to change a template, or new_name for a new one.",
		}
	held = (
		frappe.get_doc("Email Template", name) if name and frappe.db.exists("Email Template", name) else None
	)
	if name and not held:
		return {
			"mend": "write_mail_template",
			"error": f"There is no template {name}; read workspace_mail_templates for them.",
		}
	if new_name and frappe.db.exists("Email Template", new_name.strip()):
		return {
			"mend": "write_mail_template",
			"error": f"{new_name} is already a template; change it by its name instead.",
		}
	kind = (for_doctype or "").strip() or (held.reference_doctype if held else None) or None
	try:
		if kind:
			mail_templates._doctype(kind)
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {"mend": "write_mail_template", "error": str(e)}
	subject, message = (
		re.sub(r"\{\{-?\s*doc\.(\w+)\s*-?\}\}", r"{{ \1 }}", text or "") for text in (subject, message)
	)
	if not kind and mail_templates.FIELD.search(subject + message):
		return {
			"mend": "write_mail_template",
			"error": "A template that names fields is for one kind of record: give for_doctype, such as Sales Invoice.",
		}
	kept = mail_templates._tags(held)
	for text in (subject, message):
		wrong = mail_templates.check(kind, text, kept)
		if wrong:
			fields = (
				f" Read workspace_mail_templates with doctype {kind} for the fields it may name."
				if kind
				else ""
			)
			return {"mend": "write_mail_template", "error": wrong + fields}
	paragraphs = [one.strip() for one in re.split(r"\n\s*\n", message or "") if one.strip()]
	html = "".join(f"<p>{frappe.utils.escape_html(one).replace(chr(10), '<br>')}</p>" for one in paragraphs)
	changes = {"subject": subject.strip(), "reference_doctype": kind}
	changes["response_html" if held and held.use_html else "response"] = html
	proposal = (
		proposals.propose("Edit", "Email Template", changes=changes, record=held.name, why=why)
		if held
		else proposals.propose(
			"Create", "Email Template", changes={"name": new_name.strip(), **changes}, why=why
		)
	)
	return {
		"proposal": proposal,
		"state": "Proposed",
		"next": "Tell them it is offered in the composer on "
		+ (f"a {kind}" if kind else "any record")
		+ " and in OneMail once they approve it, and that the record's Settings › Mail Templates makes it the "
		"one the composer starts with.",
	}
