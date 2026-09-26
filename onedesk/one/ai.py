"""What OneAI offers on One's own pages, and what it is told about them.

Settings is a desk page, not a record: the panel has no doctype to go on, so
the page says where the reader is (`page` and `section` from oneai.js), and
this module turns that into the sentence the model is told and the
suggestions the panel offers. How to use each section is in `README.md`, which
OneAI reads through `how_to`.
"""

import json
from typing import Annotated

import frappe
from frappe import _, _lt

#: What the panel offers on a Settings section, keyed `page:<page>/<section>`.
SUGGESTIONS = {
	"page:settings/profile": [
		{
			"label": _lt("What is missing from my profile?"),
			"ask": _lt(
				"Look at my profile and my employee record, if I have one. What is empty or looks out of "
				"date, and what is each of those used for?"
			),
		},
		{
			"label": _lt("How do I fill this in?"),
			"ask": _lt(
				"Go through the Profile page with me: what each part is for, and what only HR can change."
			),
			"expects": "how_to",
		},
	],
	"page:settings/agreements": [
		{
			"label": _lt("What have I agreed to?"),
			"ask": _lt(
				"In plain words, what have I and my organisation agreed to, and what does it mean for my data?"
			),
			"expects": "agreement",
		},
		{
			"label": _lt("Who else sees my data?"),
			"ask": _lt(
				"Which other companies receive data from this workspace, what do they get, and where is it kept?"
			),
			"expects": "agreement",
		},
	],
	"page:settings/notifications": [
		{
			"label": _lt("What will I be told about?"),
			"ask": _lt("What can One tell me about, and which of those do I also get by email?"),
			"expects": "my_notifications",
		},
		{
			"label": _lt("Too many emails?"),
			"ask": _lt(
				"Which of the notifications I get by email could I leave to the bell, or have pushed instead? "
				"Say which to untick and why."
			),
			"expects": "my_notifications",
		},
	],
	"page:settings/mail": [
		{
			"label": _lt("Write my signature"),
			"ask": _lt(
				"Write a signature for the mailbox I send from, from my name, my job and how to reach me. Keep "
				"it short, and suggest it as a card I can approve."
			),
			"expects": "sign_mailbox",
		},
		{
			"label": _lt("Why is a mailbox not working?"),
			"ask": _lt("Are any of my mailboxes not working, why, and what do I do about it?"),
			"expects": "my_mailboxes",
		},
		{
			"label": _lt("How does mail work here?"),
			"ask": _lt(
				"How do my mailboxes work in One: which I have, which I send from, and how they sign?"
			),
			"expects": "how_to",
		},
	],
	"page:customize": [
		{
			"label": _lt("Suggest changes to this form"),
			"ask": _lt(
				"Look at the form I am customizing. What would make it quicker to fill in and to read: fields "
				"to hide, rename, require or move, and numbers worth showing under the title? Suggest them as "
				"one change I can apply."
			),
			"expects": "customize",
		},
		{
			"label": _lt("Add a field"),
			"ask": _lt("Help me add a field to this form. Ask me what it holds, then suggest it."),
			"expects": "customize",
		},
		{
			"label": _lt("How does customizing work?"),
			"ask": _lt("How does customizing a form work in One, and what can and cannot be changed?"),
			"expects": "how_to",
		},
	],
	"page:workspace-settings/notification_types": [
		{
			"label": _lt("Rewrite this notification"),
			"ask": _lt(
				"Rewrite the text of the notification I have open so it is short, plain and friendly, and "
				"keeps every slot it uses. Suggest it as a change I can apply."
			),
			"expects": "rewrite_notification",
		},
		{
			"label": _lt("Which should be emailed?"),
			"ask": _lt(
				"Look at the notifications One sends here. Which should people get by email as well as in the "
				"bell, and which are better left to the bell? Say why for each."
			),
			"expects": "notification_type",
		},
		{
			"label": _lt("Make a rule"),
			"ask": _lt(
				"Help me set up a notification rule. Ask me what should happen and who should be told, then "
				"suggest the rule."
			),
			"expects": "draft_notification",
		},
		{
			"label": _lt("How do notifications work?"),
			"ask": _lt("How do notifications work in One, and what can I change on this page?"),
			"expects": "how_to",
		},
	],
}


def page(said: dict) -> str | None:
	"""The sentence the model is told about a Settings section: which records
	it is, and where its documentation is. Only the reader's own records, found
	on the server rather than taken from the browser."""
	if said.get("page") == "workspace-settings" and said.get("section") == "notification_types":
		return _notifications_page(said.get("record"))
	if said.get("page") == "customize":
		return _customize_page(said.get("record"))
	if said.get("page") != "settings":
		return None
	if said.get("section") == "notifications":
		return (
			"The reader is on Notifications in their own Settings: every kind of notification they can "
			"receive, which all reach their bell, and ticks for each they also want by email or pushed to the "
			"browsers they turned push on in. my_notifications reads what they get and how. They change the ticks themselves and save; how is in One's "
			"documentation under Settings › Notifications (how_to)."
		)
	if said.get("section") == "mail":
		return (
			"The reader is on Mail in their own Settings: the mailboxes they hold, which of them they send "
			"from and what each signs with, and any that stopped connecting. my_mailboxes reads them, with "
			"what a signature is made of; sign_mailbox suggests a signature as a card they approve. How it "
			"works is in One's documentation under Settings › Mail (how_to)."
		)
	if said.get("section") == "agreements":
		return (
			"The reader is on Agreements in Settings: every agreement One runs under, what they agreed to "
			"themselves, and what their organisation agreed to and who agreed for it. The text of each is "
			"what the agreement tool returns; how agreeing works is in One's documentation under OneLegal "
			"(how_to)."
		)
	if said.get("section") != "profile":
		return None
	from onedesk.one_hr import own

	user = frappe.session.user
	employee = own.employee_of()
	records = f"their own User record {user}" + (
		f" and their own Employee record {employee}" if employee else ""
	)
	return (
		f"The reader is on their Profile page in Settings, which edits {records}. "
		"They may change their name, gender, birth date, mobile, location, bio, language and time zone"
		+ (
			"; on the employee record, their addresses, personal email, emergency contact, marital status "
			"and blood group. Their job and bank details are HR's and cannot be changed there."
			if employee
			else "."
		)
		+ " How to use the page is in One's documentation under Settings › Profile (how_to)."
	)


def _customize_page(doctype: str | None) -> str:
	opened = (
		f" They have {doctype} open: its fields, the numbers under its title, its buttons, its linked "
		"sections and its connections. describe_type lists the form's fields."
		if doctype and frappe.db.exists("DocType", doctype)
		else " No form is open on it yet."
	)
	return (
		"The reader is on the Customize page, where a workspace administrator changes how a form looks "
		"for everybody." + opened + " customize suggests a change as a card they approve; it never writes "
		"code, never removes a field the form came with, and never changes who may see a field. How it "
		"works is in One's documentation under One › Customizing a Form (how_to)."
	)


def _notifications_page(record: str | None) -> str:
	open_on = (
		f" They have the notification type {record} open, with its text and channels."
		if record and frappe.db.exists("Notification Type", record)
		else " They are looking at the list of every notification type, by app."
	)
	return (
		"The reader is on Notifications in Workspace Settings, where an administrator decides what each "
		"notification One sends says and which channels it may use." + open_on + " notification_type reads a "
		"type's text, slots and channels; rewrite_notification suggests new text as a card they apply; "
		"draft_notification suggests a new rule (when something happens to a record, tell somebody). How "
		"it works is in One's documentation under Workspace Settings › Notifications (how_to)."
	)


def notification_type(
	name: Annotated[
		str, "The notification type, as it is listed, such as Letter Requested. Leave out for all."
	]
	| None = None,
) -> dict:
	"""What a notification One sends says, which slots its text may use, and
	which channels it may go out on. Without a name, every type, briefly.
	Workspace administrators only."""
	from onedesk.one import notify, roles

	if not roles.administers():
		return {"error": "Only a workspace administrator decides what notifications say."}
	declared = notify.declared()
	if not name:
		rows = frappe.get_all(
			"Notification Type",
			filters={"name": ["in", list(declared)]},
			fields=["name", "enabled", *notify.FIELDS],
		)
		return {
			"types": [
				{
					"name": one.name,
					"app": one.one_app,
					"about": one.one_about,
					"on": bool(one.enabled),
					"email_allowed": bool(one.one_allow_email),
					"email_for_new_people": bool(one.one_email_default),
					"outside": bool(one.one_outside),
					"words_of": notify.upstream(declared.get(one.name) or {}) or None,
					"mailed_by": (declared.get(one.name) or {}).get("mailed_by"),
				}
				for one in rows
			]
		}
	if name not in declared or not frappe.db.exists("Notification Type", name):
		return {"error": f"There is no notification type {name}. Call this without a name for the list."}
	doc = frappe.get_doc("Notification Type", name)
	return {
		"name": doc.name,
		"app": doc.one_app,
		"about": doc.one_about,
		"on": bool(doc.enabled),
		"subject": doc.one_subject,
		"message": doc.one_message,
		"default_subject": doc.one_default_subject,
		"default_message": doc.one_default_message,
		"slots": notify.slots(name),
		"email_allowed": bool(doc.one_allow_email),
		"push_allowed": bool(doc.one_allow_push),
		"outside": bool(doc.one_outside),
		"next": "The text is Jinja and may use only these slots, as {{ slot }}. The subject is one line; the "
		"message may be simple HTML. It is sent as written, in one language: write it in the workspace's.",
		**_whose(declared[name]),
	}


def _whose(one: dict) -> dict:
	"""For a type whose words are erpnext's or hrms's: whose, and what can be
	changed instead."""
	from onedesk.one import notify

	if one.get("mailed_by"):
		return {
			"mailed_by": one["mailed_by"],
			"next": f"{one['mailed_by']} mails this itself; only whether it is sent can be changed, where it has a switch.",
		}
	if notify.upstream(one):
		return {
			"words_of": notify.upstream(one),
			"next": "Its words are the app's own and cannot be rewritten here; its channels can be changed.",
		}
	return {}


def rewrite_notification(
	name: Annotated[str, "The notification type, as notification_type named it."],
	subject: Annotated[str, "The new subject: one line, Jinja, using only the type's slots as {{ slot }}."],
	message: Annotated[
		str, "The new message, or the current one unchanged. Simple HTML and Jinja; may be empty."
	]
	| None = None,
	why: Annotated[str, "In a sentence, what the new text does better."] | None = None,
) -> dict:
	"""Suggest new text for a notification One sends, as a card the
	administrator applies. Read it with notification_type first. Nothing
	changes until they approve it."""
	from onedesk.one import notify
	from onedesk.one_ai import proposals

	if name not in notify.declared():
		return {"error": f"There is no notification type {name}."}
	if notify.upstream(notify.declared()[name]):
		whose = notify.upstream(notify.declared()[name])
		return {"error": f"{name} is in {whose}'s own words; its text cannot be changed here."}
	for text in (subject, message):
		wrong = notify.check(name, text)
		if wrong:
			return {"error": str(wrong)}
	changes = {"one_subject": (subject or "").strip()}
	if message is not None:
		changes["one_message"] = message.strip()
	return {
		"proposal": proposals.propose("Edit", "Notification Type", changes=changes, record=name, why=why),
		"state": "Proposed",
	}


def my_notifications() -> dict:
	"""Every kind of notification the person asking can receive, what it is
	about, and whether it is also mailed and pushed to them, and in how many
	browsers push is on. Their own choices only."""
	from onedesk.one import notify

	user = frappe.session.user
	settings = frappe.db.get_value(
		"Notification Settings", user, ["enabled", "enable_email_notifications"], as_dict=True
	) or frappe._dict(enabled=1, enable_email_notifications=1)

	def chosen(field: str) -> set:
		return set(
			frappe.get_all(
				"Notification Type Preference",
				filters={"parenttype": "Notification Settings", "parentfield": field, "parent": user},
				pluck="notification_type",
			)
		)

	mailed, pushed = chosen(notify.EMAIL_FIELD), chosen(notify.PUSH_FIELD)
	return {
		"notifications_on": bool(settings.enabled),
		"email_on": bool(settings.enable_email_notifications),
		"push_browsers": frappe.db.count("Push Device", {"user": user}),
		"kinds": [
			{
				"name": one["label"],
				"app": one["app"],
				"about": one["about"],
				"by_email": bool(one["always"] or (one["allowed"] and one["name"] in mailed)),
				"by_push": bool(one["push"] and one["name"] in pushed),
				"email_may_change": one["allowed"],
				"push_may_change": one["push"],
			}
			for one in notify.choosable(user)
		],
		"next": "Everything reaches the bell. Push reaches only the browsers counted in push_browsers. "
		"Advise; the person ticks and saves the page themselves.",
	}


def draft_notification(
	name: Annotated[str, "A short name people will know it by, such as Overdue Invoice."],
	watches: Annotated[str, "The kind of record, as its DocType name, such as Sales Invoice."],
	when: Annotated[str, "New, Save, Submit, Cancel, Days After, Days Before or Value Change."],
	subject: Annotated[str, "One line. Fields of the record as {{ doc.fieldname }}, and nothing else."],
	message: Annotated[str, "The detail under the bell and in the mail, the same way. May be empty."]
	| None = None,
	roles: Annotated[list[str], "Roles whose people are told."] | None = None,
	person: Annotated[str, "A field of the record naming a person to tell, such as owner."] | None = None,
	assignees: Annotated[bool, "Whether whoever the record is assigned to is told."] = False,
	days: Annotated[int, "For Days After or Days Before: how many days."] | None = None,
	date_field: Annotated[str, "For Days After or Days Before: the date field it counts from."] | None = None,
	value_field: Annotated[str, "For Value Change: the field whose change it watches."] | None = None,
	only_when: Annotated[list[list], "Conditions on the record's fields, each [field, operator, value]."]
	| None = None,
	why: Annotated[str, "In a sentence, what the rule is for."] | None = None,
) -> dict:
	"""Suggest a notification rule for the workspace, as a card the
	administrator applies: when something happens to a kind of record, tell
	somebody. Only people who can open the record are ever told. Nothing is
	made until they approve it. Workspace administrators only."""
	from onedesk.one import roles as workspace
	from onedesk.one import rules
	from onedesk.one_ai import proposals

	if not workspace.administers():
		return {"error": "Only a workspace administrator makes notification rules."}
	if when not in rules.EVENTS:
		return {"error": f"When must be one of: {', '.join(rules.EVENTS)}."}
	if not frappe.db.exists("DocType", watches):
		return {"error": f"There is no kind of record called {watches}."}
	for text in (subject, message):
		wrong = rules.check_text(watches, text)
		if wrong:
			return {"error": f"{wrong} The fields it may use: {', '.join(rules.readable(watches))}."}
	recipients = [{"receiver_by_role": one} for one in roles or [] if one]
	if person:
		recipients.append({"receiver_by_document_field": person})
	if not recipients and not assignees:
		return {"error": "Say who is told: roles, a person on the record, or its assignees."}
	changes = {
		"name": (name or "").strip(),
		"enabled": 1,
		"one_rule": 1,
		"channel": "System Notification",
		"document_type": watches,
		"event": when,
		"subject": subject,
		"message": message or "",
		"condition_type": "Filters",
		"filters": json.dumps([[watches, *one] for one in only_when or []]),
		"send_to_all_assignees": 1 if assignees else 0,
		"recipients": recipients,
	}
	if when in ("Days After", "Days Before"):
		changes.update({"date_changed": date_field, "days_in_advance": days or 0})
	if when == "Value Change":
		changes["value_changed"] = value_field
	return {
		"proposal": proposals.propose("Create", "Notification", changes=changes, why=why),
		"state": "Proposed",
		"next": "Tell them it appears under Workspace Settings, Notifications, Rules once they approve it.",
	}


def customize(
	doctype: Annotated[str, "The form, as its DocType name, such as Employee or Sales Invoice."],
	add: Annotated[
		list[dict],
		"New fields, each {label, kind, choices, after, required, in_list}. kind is Data, Select, Check, Date, "
		"Link, Currency, Phone, Small Text or another a person types; choices are a Select's options or a "
		"Link's form; after names the field it follows.",
	]
	| None = None,
	change: Annotated[
		list[dict],
		"Fields the form has, each {field, label, hidden, required, in_list, after}: field is its name or "
		"label, and only what is given changes.",
	]
	| None = None,
	band: Annotated[
		list[dict],
		"Numbers under the title, each {label, source, field, link_field, of_doctype, filters, measure, "
		"tone}. source is Field, Linked Field, Count, Sum or Measure.",
	]
	| None = None,
	linked: Annotated[
		list[dict],
		"Sections of a linked record's fields, edited on this form, each {label, through, fields, in_tab_of}: "
		"through is a Link field of this form, fields are the linked form's field names.",
	]
	| None = None,
	why: Annotated[str, "In a sentence, what the change is for."] | None = None,
) -> dict:
	"""Suggest a change to how a form looks, as a card the workspace
	administrator applies: fields added, renamed, hidden, required or moved,
	numbers under the title, and sections of a linked record's fields. Nothing
	that runs, and nothing changes until they approve it. Workspace
	administrators only."""
	from frappe.utils import strip_html

	from onedesk.one import customize as page
	from onedesk.one import roles as workspace
	from onedesk.one_ai import proposals

	if not workspace.administers():
		return {"error": "Only a workspace administrator customizes a form."}
	try:
		page.may(doctype)
		said = page.load(doctype)
		values, summary = said["values"], []
		fields = values["fields"]

		def find(name):
			key = frappe.scrub(str(name or ""))
			for row in fields:
				if name == row["fieldname"] or (key and key == frappe.scrub(row["label"] or "")):
					return row
			return None

		def missing(name) -> dict:
			shown = [f"{row['fieldname']} ({row['label']})" for row in fields if row["label"]]
			return {"error": f"{doctype} has no field {name}. Its fields: {', '.join(shown[:80])}."}

		def place(row, after) -> None:
			there = find(after)
			if row in fields:
				fields.remove(row)
			fields.insert(fields.index(there) + 1 if there else len(fields), row)

		for one in change or []:
			row = find(one.get("field"))
			if not row:
				return missing(one.get("field"))
			label = row["label"] or row["fieldname"]
			said_of, called = [], _(label)
			if one.get("label"):
				row["label"] = one["label"]
				said_of.append(_("called {0}").format(one["label"]))
			for key, prop, yes, no in (
				("hidden", "hidden", _("hidden"), _("shown")),
				("required", "reqd", _("required"), _("optional")),
				("in_list", "in_list_view", _("in the list"), _("not in the list")),
			):
				if one.get(key) is not None:
					row[prop] = 1 if one[key] else 0
					said_of.append(yes if one[key] else no)
			if one.get("after"):
				if not find(one["after"]):
					return missing(one["after"])
				place(row, one["after"])
				before = find(one["after"])["label"] or one["after"]
				said_of.append(_("after {0}").format(_(before)))
			summary.append({"label": called, "value": ", ".join(said_of)})

		for one in add or []:
			kind = one.get("kind") or "Data"
			choices = one.get("choices")
			row = {
				"fieldname": None,
				"label": one.get("label") or "",
				"fieldtype": kind,
				"options": "\n".join(choices) if isinstance(choices, list) else (choices or ""),
				"hidden": 0,
				"reqd": 1 if one.get("required") else 0,
				"in_list_view": 1 if one.get("in_list") else 0,
				"mine": 1,
			}
			if one.get("after") and not find(one["after"]):
				return missing(one["after"])
			place(row, one.get("after"))
			summary.append({"label": _("New field"), "value": f"{row['label']} ({_(kind)})"})

		for one in band or []:
			values["band"].append({key: one.get(key) for key in page.HEAD_COLUMNS["band"] if one.get(key)})
			summary.append({"label": _("Under the title"), "value": one.get("label") or ""})

		for one in linked or []:
			through = find(one.get("through"))
			if not through:
				return missing(one.get("through"))
			names = one.get("fields") or []
			values["linked"].append(
				{
					"label": one.get("label"),
					"link_field": through["fieldname"],
					"fields": "\n".join(names) if isinstance(names, list) else names,
					"placed_in": (find(one.get("in_tab_of")) or {}).get("fieldname"),
				}
			)
			summary.append({"label": _("Linked section"), "value": one.get("label") or ""})

		if not summary:
			return {"error": "Say what to change: add, change, band or linked."}
		# Everything the save would refuse, refused now, so the card that
		# reaches the administrator is one that applies.
		page._check(doctype, values)
	except (frappe.ValidationError, frappe.PermissionError) as refused:
		return {"error": strip_html(str(refused))}
	return {
		"proposal": proposals.propose(
			"Customize",
			doctype,
			changes={"values": values, "token": said["token"], "summary": summary},
			why=why,
		),
		"state": "Proposed",
		"next": "Tell them it changes the form for everybody once they approve it, and that Reset on the "
		"Customize page takes it back.",
	}


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
