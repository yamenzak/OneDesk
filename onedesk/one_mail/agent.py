"""What OneAI does in OneMail: reads the conversation that is open, says
which conversations wait for an answer, drafts a reply the way the reader
asks for it, and suggests as a card anything the page changes (REACH)."""

import re
from html import unescape
from typing import Annotated

import frappe
from frappe import _, _lt
from frappe.utils import strip_html

from onedesk.one import registry
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
		"becomes a card that opens the email window with the reply in, and is never sent by itself. "
		"work_conversation gives the open conversation to a colleague, marks it done, snoozes it or sets a "
		"reminder, as a card. How OneMail "
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
		summary.append({"label": _("Read with {0}").format(registry.name("one_ai")), "value": _("Turned on for this mailbox")})
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
		"route": ["List", "Automation", {"scope": box["name"]}],
	}
	return {
		"proposal": proposals.propose("Setup", "Automation", changes=changes, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what the rule does once approved. Nothing changes until they approve it.",
	}


def make_rule(changes: dict) -> str:
	"""A mail rule's card approved, by a holder of its mailbox: the folder
	made if it is missing, OneAI switched on to read the mailbox if the rule
	is about what mail says, the rule, and what is in the Inbox now sorted
	if that was asked."""
	from onedesk.one.automation import engine, flow
	from onedesk.one_ai.reading import switches
	from onedesk.one_mail import actions, blocks, rules

	account = changes["account"]
	actions.require(account)
	folder = changes.get("folder") or frappe.db.get_value(
		"Mail Folder", {"account": account, "label": changes["label"]}, "name"
	)
	if not folder:
		folder = actions.create_folder(account, changes["label"])
	if changes.get("read"):
		switches.set_mailbox(account, 1)
	steps = blocks.from_fields(
		{
			"from_contains": changes.get("from_contains"),
			"subject_contains": changes.get("subject_contains"),
			"body_contains": changes.get("body_contains"),
			"about": changes.get("about"),
			"move_to": folder,
		}
	)
	rule = rules.save_rule(account, {"title": changes.get("title") or changes["label"], "steps": steps})
	if changes.get("now") and not flow.needs_ai(steps) and frappe.db.get_value("Automation", rule, "enabled"):
		known = engine.kinds_of(blocks.ARRIVES)
		found = []
		for one in frappe.get_all(
			"Communication",
			filters={
				"email_account": account,
				"one_folder": actions.folder_of(account, "Inbox"),
				"sent_or_received": "Received",
				"one_held": 0,
			},
			pluck="name",
			order_by="communication_date desc",
			limit=MOST_NOW,
		):
			if flow.walk(steps, rules.facts_of(one), known)[0]:
				found.append(one)
		if found:
			actions.move(found, folder)
	return rule


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
				"folders": [folder["label"] for folder in one["folders"]],
				"away": bool(frappe.db.get_value("Email Account", one["name"], "one_away")),
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


# OneAI's reach (docs/READY.md, mechanism 11): every call of OneMail's that
# changes something is a card OneAI suggests, approved through that call
# itself, or is named in NOT_FOR_AI with the reason.

REACH = {
	"actions.mark": "sort_conversations",
	"actions.star": "sort_conversations",
	"actions.move": "sort_conversations",
	"actions.delete": "sort_conversations",
	"actions.create_folder": "change_folder",
	"actions.rename_folder": "change_folder",
	"actions.delete_folder": "change_folder",
	"linking.file": "file_conversation",
	"linking.unfile": "file_conversation",
	"rules.set_away": "suggest_away",
	"rules.save_rule": "suggest_mail_rule",
	"rules.enable_rule": "change_mail_rule",
	"rules.delete_rule": "change_mail_rule",
	"rules.decide_rule": "change_mail_rule",
	"holders.set_signature": "sign_mailbox",
	"holders.grant": "share_mailbox",
	"holders.revoke": "share_mailbox",
	"holders.give": "share_mailbox",
	"holders.set_personal_sends": "suggest_mail_policy",
	"holders.set_sends": "suggest_mail_policy",
	"holders.set_external": "suggest_mail_policy",
	"holders.set_allowed_domains": "suggest_mail_policy",
	"holders.set_defaults": "suggest_mail_policy",
	"connect.add_domain": "company_domain",
	"connect.remove_domain": "company_domain",
	"mail_templates.set_default": "default_mail_template",
	"team.assign": "work_conversation",
	"team.done": "work_conversation",
	"team.snooze": "work_conversation",
	"team.remind": "work_conversation",
}

NOT_FOR_AI = {
	"actions.put_back": "It undoes a move with what the move answered, which only the toast that offers Undo holds.",
	"addresses.give": "A person's address is theirs for good once given, so an administrator chooses it with them.",
	"connect.connect": "It takes the mailbox's password, which is never typed to OneAI.",
	"connect.connect_for": "It takes the mailbox's password, which is never typed to OneAI.",
	"connect.reconnect": "It takes the mailbox's password, which is never typed to OneAI.",
	"connect.disconnect": "Mail stops arriving and only the password brings it back, so its holder does it on its Connection tab.",
	"gate.set_settings": "How far OneAI reads a mailbox and what it may spend is decided by the mailbox's manager, never by OneAI.",
	"holders.set_access": "It replaces everyone who holds a mailbox at once, with the whole list in view; share_mailbox changes one person.",
	"inbound.notice": "It is the mail Worker's signed call that new mail is waiting, not anything a person does.",
	"signatures.set_preset": "A preset is picked by looking at it drawn; sign_mailbox writes a signature itself.",
	"team.note": "A note is the team's own words to each other about a conversation.",
	"team.replying": "It says the reader has the reply window open, which only the window knows.",
	"drafts.save": "A draft is kept as its writer types; draft_reply writes one for the reader to finish.",
	"drafts.discard": "Throwing a draft away is its writer's own choice, made where they wrote it.",
	"drafts.unschedule": "Taking back a message about to go is its writer's own choice, made on the message.",
	"held.release": "A message held as risky is kept from OneAI and every agent, so only a person who read why lets it in.",
	"held.discard": "A message held as risky is kept from OneAI and every agent, so only a person decides what happens to it.",
	"held.set_levels": "When mail is warned and held is a Mail Manager's decision about the workspace's safety, never OneAI's.",
}

ACCOUNTANT = "one_book"

TOOLS = ("incoming", "hand_on")
WAKES = {"mail": "incoming"}
"""What its agent calls in the workspace (one_ai/agents/api.py)."""

LEVELS = {
	"actions.mark": "Draft",
	"actions.star": "Draft",
	"actions.move": "Draft",
	"actions.delete": "Ask First",
	"actions.create_folder": "Draft",
	"actions.rename_folder": "Draft",
	"actions.delete_folder": "Ask First",
	"linking.file": "Do it",
	"linking.unfile": "Draft",
	"rules.set_away": "Ask First",
	"rules.save_rule": "Ask First",
	"rules.enable_rule": "Ask First",
	"rules.delete_rule": "Ask First",
	"rules.decide_rule": "Ask First",
	"holders.set_signature": "Ask First",
	"holders.grant": "Ask First",
	"holders.revoke": "Ask First",
	"holders.give": "Ask First",
	"holders.set_personal_sends": "Ask First",
	"holders.set_sends": "Ask First",
	"holders.set_external": "Ask First",
	"holders.set_allowed_domains": "Ask First",
	"holders.set_defaults": "Ask First",
	"connect.add_domain": "Ask First",
	"connect.remove_domain": "Ask First",
	"mail_templates.set_default": "Ask First",
	"team.assign": "Draft",
	"team.done": "Draft",
	"team.snooze": "Draft",
	"team.remind": "Draft",
	"incoming": "Do it",
	"hand_on": "Do it",
}
"""How far its agent goes with each action (one_ai/agents/levels.py)."""

LABELS = {
	"actions.mark": _lt("Mark Conversations"),
	"actions.star": _lt("Star Conversations"),
	"actions.move": _lt("Move Conversations"),
	"actions.delete": _lt("Delete Conversations"),
	"actions.create_folder": _lt("Create Folder"),
	"actions.rename_folder": _lt("Rename Folder"),
	"actions.delete_folder": _lt("Delete Folder"),
	"linking.file": _lt("Link to Record"),
	"linking.unfile": _lt("Unlink from Record"),
	"rules.set_away": _lt("Set Away Reply"),
	"rules.save_rule": _lt("Save Mail Rule"),
	"rules.enable_rule": _lt("Enable Mail Rule"),
	"rules.delete_rule": _lt("Delete Mail Rule"),
	"rules.decide_rule": _lt("Approve Mail Rule"),
	"holders.set_signature": _lt("Set Signature"),
	"holders.grant": _lt("Share Mailbox"),
	"holders.revoke": _lt("Stop Sharing Mailbox"),
	"holders.give": _lt("Set Mailbox Permissions"),
	"holders.set_personal_sends": _lt("Allow New Addresses to Send"),
	"holders.set_sends": _lt("Allow Address to Send"),
	"holders.set_external": _lt("Allow Connecting Own Mailboxes"),
	"holders.set_allowed_domains": _lt("Set Allowed Domains"),
	"holders.set_defaults": _lt("Set Default Mailboxes"),
	"connect.add_domain": _lt("Add Company Domain"),
	"connect.remove_domain": _lt("Remove Company Domain"),
	"mail_templates.set_default": _lt("Set Default Template"),
	"team.assign": _lt("Assign Conversation"),
	"team.done": _lt("Mark Conversation Done"),
	"team.snooze": _lt("Snooze Conversation"),
	"team.remind": _lt("Set Reply Reminder"),
	"incoming": _lt("Read Incoming Mail"),
	"hand_on": _lt("Pass On Invoices"),
}
"""Each action as people read it, in AICenter (one_ai/agents/levels.py)."""

APPROVED = (
	"mail_rule",
	"conversations",
	"folder",
	"filing",
	"away",
	"rule_change",
	"sharing",
	"mail_policy",
	"domain",
	"template_default",
	"team",
)

ACTS = {
	"move": _lt("Move to {0}"),
	"archive": _lt("Archive"),
	"trash": _lt("Move to Trash"),
	"read": _lt("Mark as Read"),
	"unread": _lt("Mark as Unread"),
	"star": _lt("Star"),
	"unstar": _lt("Remove Star"),
}


def _held(mailbox: str | None) -> dict | None:
	"""One of the reader's mailboxes, by its name or its address; the only one
	when they hold one and name none."""
	from onedesk.one_mail import holders

	held = holders.mailboxes()
	said = (mailbox or "").strip().lower()
	if not said:
		return held[0] if len(held) == 1 else None
	return next((one for one in held if said in (one["name"].lower(), (one["email"] or "").lower())), None)


def _account(mailbox: str | None) -> str | None:
	"""Any of the workspace's mailboxes, by its name or its address, for the
	cards an administrator approves."""
	said = (mailbox or "").strip()
	if not said:
		return None
	return frappe.db.get_value("Email Account", said, "name") or frappe.db.get_value(
		"Email Account", {"email_id": said}, "name"
	)


def _card(what: str, title: str, summary: list, why: str | None, then: str, **values) -> dict:
	"""A card the reader approves, done by OneMail's own call (approved)."""
	from onedesk.one_ai import proposals

	changes = {"what": what, "title": title, "summary": [one for one in summary if one["value"]], **values}
	return {"proposal": proposals.propose("Setup", "Email Account", changes=changes, why=why), "state": "Proposed", "next": then}


def _not(tool: str, error: str) -> dict:
	return {"mend": tool, "error": error}


def _folder_named(box: dict, label: str | None) -> dict | None:
	said = (label or "").strip().lower()
	return next(
		(one for one in box["folders"] if said in ((one["label"] or "").lower(), (one["name"] or "").lower())), None
	)


def _labels(box: dict) -> str:
	return ", ".join(one["label"] for one in box["folders"])


def sort_conversations(
	act: Annotated[str, "move, archive, trash, read, unread, star or unstar."],
	threads: Annotated[list[str], "The conversations' threads, as waiting_for_answer or the page names them."],
	mailbox: Annotated[str, "The mailbox they are in (my_mailboxes). Left out when the reader holds one."]
	| None = None,
	folder: Annotated[str, "For move: the folder, by its name, such as Suppliers (my_mailboxes)."] | None = None,
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest moving, archiving, trashing, marking or starring conversations
	in a mailbox the reader holds, as a card they approve. Trash undoes from
	the Trash folder; a conversation already in Trash is left alone."""
	box = _held(mailbox)
	if not box:
		return _not("sort_conversations", "Name one of the reader's mailboxes (my_mailboxes).")
	if act not in ACTS:
		return _not("sort_conversations", f"act is one of {', '.join(ACTS)}.")
	if not threads:
		return _not("sort_conversations", "Name the conversations by their threads.")
	target = None
	if act == "move":
		target = _folder_named(box, folder)
		if not target:
			return _not("sort_conversations", f"Name a folder of {box['email']}: {_labels(box)}. change_folder makes one.")
	label = str(ACTS[act]).format(target["label"]) if target else str(ACTS[act])
	return _card(
		"conversations",
		label,
		[
			{"label": _("Mailbox"), "value": box["email"]},
			{"label": _("Conversations"), "value": str(len(threads))},
		],
		why,
		"Say in one sentence what happens once approved. Nothing changes until they approve it.",
		account=box["name"],
		threads=list(threads),
		act=act,
		folder=target["name"] if target else None,
	)


def change_folder(
	act: Annotated[str, "make, rename or delete."],
	label: Annotated[str, "make: the new folder's name. rename: its new name."] | None = None,
	folder: Annotated[str, "rename or delete: the folder, by its name (my_mailboxes)."] | None = None,
	inside: Annotated[str, "make: the folder it goes inside, if any."] | None = None,
	mailbox: Annotated[str, "The mailbox (my_mailboxes). Left out when the reader holds one."] | None = None,
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest making, renaming or deleting a folder of a mailbox the reader
	holds, as a card they approve. A deleted folder's mail goes to Trash
	first."""
	box = _held(mailbox)
	if not box:
		return _not("change_folder", "Name one of the reader's mailboxes (my_mailboxes).")
	if act not in ("make", "rename", "delete"):
		return _not("change_folder", "act is make, rename or delete.")
	held = _folder_named(box, folder) if act != "make" else None
	parent = _folder_named(box, inside) if act == "make" and inside else None
	if act != "make" and (not held or held["kind"] != "Other"):
		return _not("change_folder", f"Name one of the folders made in {box['email']}, not Inbox, Sent or the like: {_labels(box)}.")
	if act != "delete" and not (label or "").strip():
		return _not("change_folder", "Say the folder's name.")
	if inside and not parent:
		return _not("change_folder", f"There is no folder {inside} in {box['email']}: {_labels(box)}.")
	title = {
		"make": _("New Folder {0}").format(label.strip()) if act == "make" else "",
		"rename": _("Rename {0} to {1}").format(held["label"], (label or "").strip()) if held and act == "rename" else "",
		"delete": _("Delete {0}").format(held["label"]) if held else "",
	}[act]
	return _card(
		"folder",
		title,
		[
			{"label": _("Mailbox"), "value": box["email"]},
			{"label": _("Inside"), "value": parent["label"] if parent else None},
			{"label": _("Its Mail"), "value": _("Moved to Trash") if act == "delete" else None},
		],
		why,
		"Say in one sentence what happens once approved. Nothing changes until they approve it.",
		account=box["name"],
		act=act,
		label=(label or "").strip(),
		folder=held["name"] if held else None,
		parent=parent["name"] if parent else None,
	)


def file_conversation(
	thread: Annotated[str, "The conversation's thread."],
	doctype: Annotated[str, "The kind of record, such as Customer or Project."],
	name: Annotated[str, "The record's name (its ID)."],
	take_off: Annotated[bool, "Take the conversation off the record instead."] = False,
	mailbox: Annotated[str, "The mailbox it is in (my_mailboxes). Left out when the reader holds one."]
	| None = None,
	why: Annotated[str, "In a sentence, why it belongs there."] | None = None,
) -> dict:
	"""Suggest filing a conversation on a record, where it shows in the
	record's mail, or taking it off one, as a card the reader approves."""
	box = _held(mailbox)
	if not box:
		return _not("file_conversation", "Name one of the reader's mailboxes (my_mailboxes).")
	if not frappe.db.exists(doctype, name):
		return _not("file_conversation", f"There is no {doctype} {name}.")
	if not frappe.has_permission(doctype, "read", doc=name):
		return _not("file_conversation", f"The reader can't open {doctype} {name}.")
	title = (_("Take Off {0}") if take_off else _("File on {0}")).format(f"{_(doctype)} {name}")
	return _card(
		"filing",
		title,
		[{"label": _("Mailbox"), "value": box["email"]}],
		why,
		"Say in one sentence what happens once approved. Nothing changes until they approve it.",
		account=box["name"],
		thread=thread,
		doctype=doctype,
		name=name,
		off=int(bool(take_off)),
	)


def suggest_away(
	on: Annotated[bool, "Turn the out-of-office reply on, or off."],
	mailbox: Annotated[str, "The person's mailbox (my_mailboxes). Left out when they hold one."] | None = None,
	starts: Annotated[str, "The first day away, YYYY-MM-DD. Empty: from now."] | None = None,
	until: Annotated[str, "The last day away, YYYY-MM-DD."] | None = None,
	message: Annotated[
		str, "The reply, in plain sentences. Empty: the standard reply, which says the dates."
	]
	| None = None,
	answers: Annotated[str, "Everyone, Workspace (people at the company) or Contacts."] = "Everyone",
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest turning a person's out-of-office reply on or off, with its
	dates and who it answers, as a card they approve. Not for a shared
	mailbox, which answers by a mail rule."""
	from onedesk.one_mail import holders, rules

	box = _held(mailbox)
	if not box or box["shared"] or box["workspace"]:
		return _not("suggest_away", "Name one of the person's own mailboxes (my_mailboxes); a shared one answers by a rule.")
	if not holders.may(box["name"], "away"):
		return _not("suggest_away", f"The reader can't change the out-of-office of {box['email']}.")
	if answers not in rules.AWAY_TO:
		return _not("suggest_away", f"answers is one of {', '.join(rules.AWAY_TO)}.")
	if on and starts and until and frappe.utils.getdate(until) < frappe.utils.getdate(starts):
		return _not("suggest_away", "The last day can't be before the first.")
	return _card(
		"away",
		_("Out of Office On") if on else _("Out of Office Off"),
		[
			{"label": _("Mailbox"), "value": box["email"]},
			{"label": _("From"), "value": starts if on else None},
			{"label": _("Until"), "value": until if on else None},
			{"label": _("Answers"), "value": _(answers) if on else None},
			{"label": _("Reply"), "value": (message or "").strip() or (_("The standard reply") if on else None)},
		],
		why,
		"Say in one sentence what the reply does once approved. Nothing changes until they approve it.",
		account=box["name"],
		away=int(bool(on)),
		from_date=starts or None,
		until=until or None,
		message=(message or "").strip() or None,
		to=answers,
	)


def mail_rules(
	mailbox: Annotated[str, "The mailbox (my_mailboxes). Left out when the reader holds one."] | None = None,
) -> dict:
	"""A mailbox's rules in the order they run: each one's name, what it
	watches for and does, whether it is on, and who asked for one that waits
	for a Mail Manager. Read it before change_mail_rule."""
	from onedesk.one_mail import rules

	box = _held(mailbox)
	if not box:
		return _not("mail_rules", "Name one of the reader's mailboxes (my_mailboxes).")
	said = rules.rules_of_mailbox(box["name"])
	if not said["may"]:
		return {"error": f"The reader doesn't manage the rules of {box['email']}."}
	return {
		"mailbox": box["email"],
		"manages": bool(said["manages"]),
		"rules": [
			{
				"rule": one["name"],
				"title": one["title"],
				"when": one["when"],
				"then": one["then"],
				"on": bool(one["enabled"]),
				"asked_by": one["requested_by_name"],
			}
			for one in said["rules"]
		],
	}


def change_mail_rule(
	rule: Annotated[str, "The rule, as mail_rules names it."],
	act: Annotated[str, "on, off, delete, approve (one somebody asked for) or decline."],
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest turning a mail rule on or off, deleting it, or approving or
	declining one somebody asked for, as a card the reader approves. Read
	mail_rules first."""
	from onedesk.one_mail import holders

	from onedesk.one_mail.blocks import ARRIVES

	held = frappe.db.get_value("Automation", {"name": rule, "trigger": ARRIVES}, ["name", "scope as account", "title", "requested_by"], as_dict=True)
	if not held or not _held(held.account):
		return _not("change_mail_rule", "Name a rule as mail_rules lists it.")
	if act not in ("on", "off", "delete", "approve", "decline"):
		return _not("change_mail_rule", "act is on, off, delete, approve or decline.")
	if act in ("approve", "decline") and not held.requested_by:
		return _not("change_mail_rule", "Nobody asked for this rule: approve and decline are for one that waits.")
	if act != "delete" and not holders.may(held.account, "rules"):
		return _not("change_mail_rule", "A Mail Manager does this to the rules of this mailbox.")
	title = {
		"on": _("Turn On {0}"),
		"off": _("Turn Off {0}"),
		"delete": _("Delete {0}"),
		"approve": _("Approve {0}"),
		"decline": _("Decline {0}"),
	}[act].format(held.title)
	return _card(
		"rule_change",
		title,
		[{"label": _("Mailbox"), "value": frappe.db.get_value("Email Account", held.account, "email_id")}],
		why,
		"Say in one sentence what happens once approved. Nothing changes until they approve it.",
		rule=held.name,
		act=act,
	)


def workspace_mail() -> dict:
	"""For whoever sets OneMail up: the workspace's shared mailboxes and who
	reads and sends from each, the company's domains, whether people may
	connect their own mailboxes and at which domains, and whether a new
	person's address sends. Read it before share_mailbox,
	suggest_mail_policy or company_domain."""
	from onedesk.one_mail import connect, holders

	try:
		said = holders.shared()
	except frappe.PermissionError:
		frappe.clear_last_message()
		return {"error": "The reader's role doesn't reach the workspace's mailboxes."}
	return {
		"mailboxes": [
			{
				"mailbox": one["email_id"],
				"workspace": bool(one["workspace"]),
				"sends_by_default": bool(one["sends_default"]),
				"people": [
					{"person": row["user"], "name": row["name"], "sends": bool(row["sends"]), "may": row["may"]}
					for row in one["people"]
				],
			}
			for one in said["mailboxes"]
		],
		"may_give": [one["key"] for one in said["abilities"]],
		"own_mailboxes_allowed": bool(said["external"]),
		"own_mailboxes_at": said["allowed_domains"] or "any domain",
		"new_addresses_send": bool(said["personal_sends"]),
		"company_domains": [one.domain_name for one in connect.domains()] if holders.may_do("policy") else None,
	}


def share_mailbox(
	mailbox: Annotated[str, "One of the workspace's shared mailboxes (workspace_mail)."],
	person: Annotated[str, "The person, by their user (an email address)."],
	reads: Annotated[bool, "Whether they read it at all: false takes it away from them."] = True,
	sends: Annotated[bool, "Whether they send from it too."] = False,
	may: Annotated[list[str], "What they may change in it beyond their role, from workspace_mail's may_give."]
	| None = None,
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest who reads and sends from one of the workspace's shared
	mailboxes, one person at a time, as a card the reader approves. Read
	workspace_mail first."""
	from onedesk.one_mail import holders
	from onedesk.one_mail.access import SHARED

	account = _account(mailbox)
	if not account or not frappe.db.get_value("Email Account", account, "one_shared"):
		return _not("share_mailbox", "Name one of the workspace's shared mailboxes (workspace_mail).")
	if not holders.may(account, "holders"):
		return _not("share_mailbox", "The reader's role doesn't change who holds this mailbox.")
	if not frappe.db.get_value("User", {"name": person, "enabled": 1, "user_type": "System User"}):
		return _not("share_mailbox", f"{person} isn't in this workspace.")
	wrong = [one for one in may or [] if one not in SHARED]
	if wrong:
		return _not("share_mailbox", f"may is from {', '.join(SHARED)}.")
	name = frappe.utils.get_fullname(person)
	return _card(
		"sharing",
		(_("Share {0} with {1}") if reads else _("Stop Sharing {0} with {1}")).format(
			frappe.db.get_value("Email Account", account, "email_id"), name
		),
		[
			{"label": _("Sends"), "value": (_("Yes") if sends else _("No")) if reads else None},
			{"label": _("May Change"), "value": ", ".join(may) if reads and may else None},
		],
		why,
		"Say in one sentence what changes once approved. Nothing changes until they approve it.",
		account=account,
		user=person,
		reads=int(bool(reads)),
		sends=int(bool(sends)),
		may=list(may) if may is not None else None,
	)


def suggest_mail_policy(
	own_mailboxes: Annotated[bool, "Whether people may connect a mailbox of their own, such as Gmail."]
	| None = None,
	own_mailboxes_at: Annotated[list[str], "The only domains they may connect one at; empty: any."]
	| None = None,
	new_addresses_send: Annotated[bool, "Whether the address a new person is given sends as well as receives."]
	| None = None,
	address: Annotated[str, "One person's workspace address, to change whether it sends."] | None = None,
	address_sends: Annotated[bool, "Whether that address sends."] | None = None,
	default_incoming: Annotated[str, "The shared mailbox mail to the workspace arrives in."] | None = None,
	default_outgoing: Annotated[str, "The shared mailbox the workspace sends from."] | None = None,
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest a change to how the workspace's mail is set up, as a card a
	workspace administrator approves: own mailboxes, the domains they may be
	at, whether addresses send, and the default shared mailboxes. Give only
	what changes. Read workspace_mail first."""
	from onedesk.one_mail import holders

	if not holders.may_do("policy"):
		return _not("suggest_mail_policy", "Only a workspace administrator changes how the workspace's mail is set up.")
	values = {
		"external": None if own_mailboxes is None else int(own_mailboxes),
		"domains": own_mailboxes_at,
		"personal_sends": None if new_addresses_send is None else int(new_addresses_send),
		"address": _account(address) if address else None,
		"address_sends": None if address_sends is None else int(address_sends),
		"incoming": _account(default_incoming) if default_incoming else None,
		"outgoing": _account(default_outgoing) if default_outgoing else None,
	}
	if address and not values["address"] or (address is None) != (address_sends is None):
		return _not("suggest_mail_policy", "Give address and address_sends together, the address as workspace_mail names it.")
	for said, found in ((default_incoming, values["incoming"]), (default_outgoing, values["outgoing"])):
		if said and not (found and frappe.db.get_value("Email Account", found, "one_shared")):
			return _not("suggest_mail_policy", f"{said} isn't one of the workspace's shared mailboxes.")
	if all(value is None for value in values.values()):
		return _not("suggest_mail_policy", "Say what changes.")
	yes = lambda on: None if on is None else (_("Yes") if on else _("No"))  # noqa: E731
	return _card(
		"mail_policy",
		_("How the Workspace's Mail Is Set Up"),
		[
			{"label": _("Own Mailboxes"), "value": yes(values["external"])},
			{"label": _("At"), "value": None if own_mailboxes_at is None else ", ".join(own_mailboxes_at) or _("Any domain")},
			{"label": _("New Addresses Send"), "value": yes(values["personal_sends"])},
			{"label": address or "", "value": None if values["address_sends"] is None else (_("Sends") if address_sends else _("Receives only"))},
			{"label": _("Default Incoming"), "value": default_incoming},
			{"label": _("Default Outgoing"), "value": default_outgoing},
		],
		why,
		"Say in one sentence what changes once approved. Nothing changes until they approve it.",
		**values,
	)


def company_domain(
	domain: Annotated[str, "The company's mail domain, such as rua.ae."],
	remove: Annotated[bool, "Remove it instead. Mailboxes connected at it keep their servers."] = False,
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest adding the company's mail domain, so people connect their
	mailbox there with its password alone, or removing one, as a card a
	workspace administrator approves. Its servers are found the way Setup
	finds them, and both are tried before it is kept."""
	from onedesk.one_mail import addresses, connect, holders

	if not holders.may_do("policy"):
		return _not("company_domain", "Only a workspace administrator sets the company's domains.")
	name = addresses.domain_of(domain)
	if remove:
		if not frappe.db.exists("Email Domain", name):
			return _not("company_domain", f"{name} isn't one of the company's domains (workspace_mail).")
		return _card(
			"domain",
			_("Remove {0}").format(name),
			[],
			why,
			"Say in one sentence what changes once approved. Nothing changes until they approve it.",
			domain=name,
			remove=1,
		)
	if "." not in name or name in connect.KNOWN:
		return _not("company_domain", f"{name} isn't a company's own domain.")
	servers = connect.servers_for(name)
	return _card(
		"domain",
		_("Add {0}").format(name),
		[
			{"label": _("Incoming"), "value": f"{servers.get('email_server')}:{servers.get('incoming_port')}"},
			{"label": _("Outgoing"), "value": f"{servers.get('smtp_server')}:{servers.get('smtp_port')}"},
		],
		why,
		"Say in one sentence what changes once approved, and that both servers are tried first. Nothing changes "
		"until they approve it.",
		domain=name,
		remove=0,
		servers={key: servers.get(key) for key in ("email_server", "incoming_port", "smtp_server", "smtp_port")},
	)


def default_mail_template(
	doctype: Annotated[str, "The kind of record, such as Sales Invoice."],
	template: Annotated[str, "The template, as workspace_mail_templates names it."],
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest the template the mail composer starts with on a kind of
	record, as a card a workspace administrator approves. Read
	workspace_mail_templates first."""
	from onedesk.one_mail import holders

	if not holders.may_do("templates"):
		return _not("default_mail_template", "Only whoever keeps the mail templates sets this.")
	if not frappe.db.exists("Email Template", template):
		return _not("default_mail_template", f"There is no template {template} (workspace_mail_templates).")
	if frappe.db.get_value("Email Template", template, "reference_doctype") not in (doctype, None, ""):
		return _not("default_mail_template", f"{template} is for another kind of record.")
	return _card(
		"template_default",
		_("Start {0} Mail with {1}").format(_(doctype), template),
		[],
		why,
		"Say in one sentence what changes once approved. Nothing changes until they approve it.",
		doctype=doctype,
		template=template,
	)


def approved(changes: dict) -> str:
	"""A card above approved: OneMail's own call, as whoever pressed Approve,
	so it is refused for them exactly as the page would refuse it."""
	from onedesk.one_mail import actions, api, connect, holders, linking, mail_templates, rules

	what = changes["what"]
	if what == "mail_rule":
		return make_rule(changes)
	if what == "conversations":
		account, act = changes["account"], changes["act"]
		names = api.names(account, changes["threads"])
		if act == "trash":
			trash = actions.folder_of(account, "Trash")
			names = [one for one in names if frappe.db.get_value("Communication", one, "one_folder") != trash]
			actions.delete(names)
		elif act in ("move", "archive"):
			folder = changes["folder"] if act == "move" else frappe.db.get_value(
				"Mail Folder", {"account": account, "kind": "Archive"}, "name"
			)
			actions.move(names, folder)
		elif act in ("read", "unread"):
			actions.mark(names, int(act == "read"))
		else:
			actions.star(names, int(act == "star"))
		return account
	if what == "folder":
		if changes["act"] == "make":
			parent = changes.get("parent")
			return actions.create_folder(changes["account"], changes["label"], parent)
		if changes["act"] == "rename":
			return actions.rename_folder(changes["folder"], changes["label"])
		actions.delete_folder(changes["folder"])
		return changes["account"]
	if what == "team":
		from onedesk.one_mail import team

		do, account, thread = changes["do"], changes["account"], changes["thread"]
		if do in ("assign", "unassign"):
			team.assign(account, thread, changes.get("person") if do == "assign" else None)
		elif do in ("done", "reopen"):
			team.done(account, thread, 1 if do == "done" else 0)
		elif do in ("snooze", "unsnooze"):
			team.snooze(account, thread, changes.get("until") if do == "snooze" else None)
		else:
			team.remind(account, thread, changes.get("until"))
		return thread
	if what == "filing":
		names = api.names(changes["account"], [changes["thread"]])
		if changes["off"]:
			linking.unfile(names, changes["doctype"], changes["name"])
		else:
			linking.file(names, changes["doctype"], changes["name"])
		return changes["name"]
	if what == "away":
		rules.set_away(
			changes["account"],
			changes["away"],
			until=changes.get("until"),
			message=changes.get("message"),
			from_date=changes.get("from_date"),
			to=changes.get("to"),
		)
		return changes["account"]
	if what == "rule_change":
		rule, act = changes["rule"], changes["act"]
		if act in ("on", "off"):
			rules.enable_rule(rule, int(act == "on"))
		elif act == "delete":
			rules.delete_rule(rule)
		else:
			rules.decide_rule(rule, int(act == "approve"))
		return rule
	if what == "sharing":
		account, user = changes["account"], changes["user"]
		if not changes["reads"]:
			holders.revoke(account, user)
			return account
		holders.grant(account, user, changes["sends"])
		if changes.get("may") is not None:
			holders.give(account, user, changes["may"])
		return account
	if what == "mail_policy":
		if changes.get("external") is not None:
			holders.set_external(changes["external"])
		if changes.get("domains") is not None:
			holders.set_allowed_domains(changes["domains"])
		if changes.get("personal_sends") is not None:
			holders.set_personal_sends(changes["personal_sends"])
		if changes.get("address"):
			holders.set_sends(changes["address"], changes["address_sends"])
		if changes.get("incoming") or changes.get("outgoing"):
			holders.set_defaults(changes.get("incoming"), changes.get("outgoing"))
		return registry.name("one_mail")
	if what == "domain":
		if changes["remove"]:
			connect.remove_domain(changes["domain"])
			return changes["domain"]
		return connect.add_domain(changes["domain"], **changes["servers"])
	if what == "template_default":
		mail_templates.set_default(changes["doctype"], changes["template"])
		return changes["template"]
	frappe.throw(_("That cannot be set."))


WORK = ("assign", "unassign", "done", "reopen", "snooze", "unsnooze", "remind")


def work_conversation(
	do: Annotated[str, "assign, unassign, done, reopen, snooze, unsnooze or remind."],
	thread: Annotated[str, "The conversation's thread, when known."] | None = None,
	subject: Annotated[str, "Words of its subject, to find it by, when the thread isn't known."] | None = None,
	person: Annotated[str, "Who to give it to, by their name or login, for assign."] | None = None,
	until: Annotated[str, "When, as YYYY-MM-DD HH:MM, for snooze and remind."] | None = None,
	mailbox: Annotated[str, "The mailbox it is in (my_mailboxes). Left out when the reader holds one."] | None = None,
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest giving a conversation to a colleague who holds its mailbox,
	marking it done or open again, snoozing it until a time, or being
	reminded then if nobody replies, as a card the reader approves. Name the
	conversation by words of its subject, as the reader said them; nothing
	needs finding first."""
	box = _held(mailbox)
	if not box and not mailbox and subject:
		box = next((one for one in _boxes_with(subject)), None)
	if not box:
		return _not("work_conversation", "Name one of the reader's mailboxes (my_mailboxes).")
	if not thread and subject:
		found = frappe.db.get_value(
			"Communication",
			{"email_account": box["name"], "subject": ["like", f"%{subject}%"], "one_folder": ["is", "set"]},
			["name", "one_thread"],
			order_by="communication_date desc",
			as_dict=True,
		)
		thread = found and (found.one_thread or found.name)
	if not thread:
		return _not("work_conversation", "Say the conversation's thread, or words of its subject.")
	if do not in WORK:
		return _not("work_conversation", "Say one of: " + ", ".join(WORK) + ".")
	if do == "assign" and not person:
		return _not("work_conversation", "Name who to give it to.")
	if do == "assign" and not frappe.db.exists("User", person):
		holders = frappe.get_all("User Email", filters={"email_account": box["name"]}, pluck="parent", distinct=True)
		named = [one for one in holders if person.lower() in (frappe.utils.get_fullname(one) or "").lower()]
		if len(named) != 1:
			return _not("work_conversation", f"Name one of the people who hold {box['email']}.")
		person = named[0]
	if do in ("snooze", "remind") and not until:
		return _not("work_conversation", "Say until when.")
	titles = {
		"assign": _("Give to {0}").format(frappe.utils.get_fullname(person) if person else ""),
		"unassign": _("Give to Nobody"),
		"done": _("Mark Done"),
		"reopen": _("Open Again"),
		"snooze": _("Snooze Until {0}").format(until or ""),
		"unsnooze": _("Back to Inbox"),
		"remind": _("Remind Me {0}").format(until or ""),
	}
	return _card(
		"team",
		titles[do],
		[{"label": _("Mailbox"), "value": box["email"]}, {"label": _("Conversation"), "value": _subject(box["name"], thread)}],
		why,
		"Say in one sentence what happens once approved. Nothing changes until they approve it.",
		account=box["name"],
		thread=thread,
		do=do,
		person=person,
		until=until,
	)


def _boxes_with(subject: str) -> list[dict]:
	"""The reader's mailboxes holding a conversation about this."""
	from onedesk.one_mail import holders

	return [
		one
		for one in holders.mailboxes()
		if frappe.db.exists("Communication", {"email_account": one["name"], "subject": ["like", f"%{subject}%"]})
	]


def mail_for_me() -> dict:
	"""What mail waits on the reader: conversations given to them and still
	open, open ones on shared mailboxes nobody has, their drafts, and
	conversations they snoozed or asked to be reminded about."""
	from onedesk.one_mail import holders

	me = frappe.session.user
	held = {one["name"]: one for one in holders.mailboxes()}
	if not held:
		return {"error": "The reader holds no mailbox."}
	rows = frappe.get_all(
		"Mail Conversation",
		filters={"account": ["in", list(held)]},
		fields=["account", "thread", "subject", "status", "_assign", "snoozed_until", "snoozed_by", "remind_at", "remind_by"],
	)
	mine = [one for one in rows if one.status != "Done" and me in (frappe.parse_json(one._assign or "[]") or [])]
	return {
		"given_to_me": [{"mailbox": held[one.account]["email"], "thread": one.thread, "subject": one.subject} for one in mine],
		"snoozed": [{"mailbox": held[one.account]["email"], "thread": one.thread, "subject": one.subject, "until": str(one.snoozed_until)} for one in rows if one.snoozed_until and one.snoozed_by == me],
		"reminders": [{"mailbox": held[one.account]["email"], "thread": one.thread, "subject": one.subject, "at": str(one.remind_at)} for one in rows if one.remind_at and one.remind_by == me],
		"drafts": frappe.get_all("Mail Draft", filters={"owner": me}, fields=["subject", "recipients", "modified"], order_by="modified desc", limit=10),
		"unassigned_shared": sum(
			1
			for one in rows
			if one.status != "Done" and held[one.account]["shared"] and not (frappe.parse_json(one._assign or "[]") or [])
		),
	}


READS = (
	"workspace_mail_templates",
	"open_conversation",
	"waiting_for_answer",
	"my_mailboxes",
	"mail_rules",
	"workspace_mail",
)
"""The tools OneAI reads here (registry/hooks.py lists them in one_ai_reads)."""


SUGGESTS = (
	"write_mail_template",
	"sign_mailbox",
	"draft_reply",
	"suggest_mail_rule",
	"sort_conversations",
	"change_folder",
	"file_conversation",
	"work_conversation",
	"mail_for_me",
	"suggest_away",
	"change_mail_rule",
	"share_mailbox",
	"suggest_mail_policy",
	"company_domain",
	"default_mail_template",
)
"""The tools OneAI suggests, each as a card a person applies here (registry/hooks.py lists them in one_ai_suggests)."""


INVOICES = ("Invoice", "Receipt", "Credit Note")
"""What the receptionist hands to OneBook's accountant: a bill to pay, a
receipt the company paid, a credit note against a bill."""
WORTH_READING = ("Action", "Information", "", None)
READ_AS = ["name", "kind", "verdict", "history", "state", "title"]


def is_invoice(reading: dict) -> bool:
	"""Whether a reading of a mail that arrived is a bill for the accountant:
	one of INVOICES, worth acting on, and not old mail read again. Pure."""
	return reading.get("kind") in INVOICES and reading.get("verdict") in WORTH_READING and not reading.get("history") and reading.get("state") == "Understood"


def readings_of(message: str) -> list[dict]:
	"""What Intake read of a message: the mail, its attachments, and their parts."""
	files = frappe.get_all("File", filters={"attached_to_doctype": "Communication", "attached_to_name": message}, pluck="name")
	found = frappe.get_all("Reading", filters={"source_doctype": "Communication", "source_name": message}, fields=READ_AS, order_by="creation asc")
	if files:
		found += frappe.get_all("Reading", filters={"source_doctype": "File", "source_name": ["in", files]}, fields=READ_AS, order_by="creation asc")
	at = [one.name for one in found]
	for _deeper in range(3):
		parts = frappe.get_all("Reading", filters={"part_of": ["in", at or [""]], "name": ["not in", [one.name for one in found] or [""]]}, fields=READ_AS, order_by="creation asc")
		if not parts:
			break
		found += parts
		at = [one.name for one in parts]
	return found


def incoming(message: str, asked_by: str | None = None) -> dict:
	"""The receptionist's first look at a mail that arrived, in a mailbox
	OneAI reads: which of what Intake read of it are invoices to hand on."""
	if not frappe.has_permission("Communication", "read", message):
		frappe.throw(_("Not allowed."), frappe.PermissionError)
	invoices = [one.name for one in readings_of(message) if is_invoice(one)]
	return {"message": message, "invoices": invoices, "next": [{"tool": "hand_on", "args": {"message": message, "reading": one, "to": ACCOUNTANT}} for one in invoices]}


def hand_on(message: str, reading: str, to: str = ACCOUNTANT, asked_by: str | None = None) -> dict:
	"""The receptionist hands an invoice to another app's agent, and says so
	on the mail, where its people read it (docs/ARC-AI.md, The agents)."""
	from onedesk.one.registry import agents
	from onedesk.one_ai.agents import door, users, work
	from onedesk.one_ai.reading.act import Action

	other = agents.get(to)
	if not other or gate.message_of(reading) != message:
		frappe.throw(_("Not allowed."), frappe.PermissionError)
	held = frappe.get_doc("Reading", reading)
	said = _("Handed to {0}: {1}").format(users.full_name(other), held.title or _(held.kind))
	row = door.act_for(
		"one_mail",
		"hand_on",
		Action("Comment", "Communication", message, {"content": said}, key=f"handed|{reading}|{to}", sure=True),
		asked_by=asked_by,
		reading=held,
	)
	return {"to": to, "reading": reading, "action": row, "next": [work.handing(to, {"reading": reading})]}
