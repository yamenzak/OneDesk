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
			"label": _lt("Write my bio"),
			"ask": _lt(
				"Write a short bio for my profile from my job, my department and what I work on, and suggest it "
				"as a change to my profile I can approve."
			),
			"expects": "edit_record",
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
	"page:settings/memory": [
		{
			"label": _lt("What do you know about me?"),
			"ask": _lt(
				"What do you know about me? Say what you remember from our conversations, and what my "
				"workspace told you."
			),
			"expects": "my_memories",
		},
	],
	"page:workspace-settings/numbering": [
		{
			"label": _lt("Is any numbering out of step?"),
			"ask": _lt(
				"Look at how each kind of record is numbered. Is any counter behind the records already made, "
				"or any series that looks mistyped?"
			),
			"expects": "workspace_numbering",
		},
		{
			"label": _lt("Number invoices by year"),
			"ask": _lt(
				"Suggest numbering new Sales Invoices as INV-, the year and a five-digit number that starts again "
				"each year, keeping the series already in use."
			),
			"expects": "change_numbering",
		},
	],
	"page:workspace-settings/printing": [
		{
			"label": _lt("Suggest a letter head top"),
			"ask": _lt(
				"Suggest a letter head whose top is one of the presets drawn from our details in "
				"Workspace › General, the one that suits us, as the default."
			),
			"expects": "change_printing",
		},
		{
			"label": _lt("Design a letter head from our details"),
			"ask": _lt(
				"Design a letter head in HTML from the company's details in Workspace › General: the name "
				"and logo at the top, the address, phone and email at the foot."
			),
			"expects": "change_printing",
		},
		{
			"label": _lt("Design a clean invoice format"),
			"ask": _lt(
				"Design a clean, modern print format for Sales Invoice: the customer and dates at the top, "
				"the items as a table, and the totals on the right."
			),
			"expects": "design_print_format",
		},
		{
			"label": _lt("Which format do invoices print with?"),
			"ask": _lt("Which print format do Sales Invoices print with, and which others could they use?"),
			"expects": "workspace_printing",
		},
	],
	"page:workspace-settings/people": [
		{
			"label": _lt("Who has access to what?"),
			"ask": _lt(
				"Who in this workspace can use which apps, and who administers it? Say anything that looks too wide."
			),
			"expects": "workspace_people",
		},
		{
			"label": _lt("Who has not signed in lately?"),
			"ask": _lt(
				"Who has not signed in for a month or more, and should any of them be turned off to free a seat?"
			),
			"expects": "workspace_people",
		},
	],
	"page:workspace-settings/plan": [
		{
			"label": _lt("Are we on the cheapest plan?"),
			"ask": _lt(
				"Is our plan, with what is added to it, the cheapest way to have what we use now? If not, what "
				"should we change to and what would it save?"
			),
			"expects": "workspace_plan",
		},
		{
			"label": _lt("How long will our credits last?"),
			"ask": _lt(
				"How long will our OneAI credits last at the rate we use them, and do any expire before we "
				"would use them?"
			),
			"expects": "workspace_plan",
		},
		{
			"label": _lt("What used the most credits this month?"),
			"ask": _lt("What used the most OneAI credits in the last thirty days, by model and by person?"),
			"expects": "workspace_plan",
		},
	],
	"page:workspace-settings/domains": [
		{
			"label": _lt("Why is our domain not working?"),
			"ask": _lt(
				"Which of our own domains are not working, and what should we check or change in the DNS "
				"to fix each one?"
			),
			"expects": "workspace_domains",
		},
	],
	"page:workspace-settings/oneai": [
		{
			"label": _lt("Which actions cost the most?"),
			"ask": _lt("Which of OneAI's actions used the most credits in the last thirty days, and on which models?"),
			"expects": "workspace_oneai",
		},
		{
			"label": _lt("Is there a cheaper model that would do?"),
			"ask": _lt(
				"For the actions we use most, is there a cheaper model on offer that would do the job, and what "
				"would it save?"
			),
			"expects": "workspace_oneai",
		},
	],
	"page:workspace-settings/intake": [
		{
			"label": _lt("Is OneIntake set up well for us?"),
			"ask": _lt(
				"Look at OneIntake's settings and this month's numbers. Is anything set in a way that sends too "
				"much to a person, or lets too much through, and what would you change?"
			),
			"expects": "workspace_intake",
		},
	],
	# Home: what waits for the reader today, across every product.
	"workspace:One": [
		{
			"label": _lt("What needs me today?"),
			"ask": _lt(
				"What needs me today? Look at my tasks, my meetings, what waits for me in OneIntake, OneAI's "
				"suggestions and what I have to approve, and say what to do first."
			),
			"expects": "my_day",
		},
	],
	"page:workspace-settings/holidays": [
		{
			"label": _lt("Are our holidays ready for next year?"),
			"ask": _lt(
				"Look at our holiday list. When does it end, is there a list after it, is anything missing for "
				"our country, and who is on a list of their own?"
			),
			"expects": "workspace_holidays",
		},
	],
	"page:workspace-settings/general": [
		{
			"label": _lt("Is signing in here safe enough?"),
			"ask": _lt(
				"Is signing in to this workspace safe enough? Look at our rules and at how people sign in, and "
				"say what to change."
			),
			"expects": "workspace_sign_in",
		},
	],
	"page:settings/signin": [
		{
			"label": _lt("Is my account safe?"),
			"ask": _lt(
				"Is my account safe? Look at how I sign in and where I am signed in, and tell me what to do."
			),
			"expects": "my_sign_in",
		},
	],
	"page:settings/calendar": [
		{
			"label": _lt("How do I add it?"),
			"ask": _lt(
				"How do I add my calendar link to Google Calendar, Apple Calendar or Outlook, on my computer "
				"and my phone, and what does it carry?"
			),
			"expects": "how_to",
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
	if said.get("page") == "workspace-settings" and said.get("section") == "people":
		return (
			"The reader administers this workspace and is on Workspace › People: everybody on it, which of "
			"OneCRM, OneBook, OneInventory, OneProject and OneHR each may use and as a user or a manager, who "
			"administers it, and when each was last active. workspace_people reads it all. They change a person "
			"by clicking them, and turn off, sign out or send a password reset from there; how is in One's "
			"documentation under People, for the Workspace (how_to)."
		)
	if said.get("page") == "workspace-settings" and said.get("section") == "plan":
		return (
			"The reader administers this workspace and is on Workspace › Plan and Credits: its plan and what is "
			"added to it, its seats, storage and database, and its OneAI credits (what is left, held by calls running now, used in the last thirty "
			"days, and what expires when). workspace_plan reads it all, with the last thirty days by model and "
			"by person, and the cheapest ways to have what it uses now. They change the plan from the page head, and "
			"add seats, storage, database or credits from Add; how is in One's documentation under Plan and "
			"Credits, for the Workspace (how_to)."
		)
	if said.get("page") == "workspace-settings" and said.get("section") == "intake":
		return (
			"The reader administers this workspace and is on OneIntake › Settings: this month's numbers (arrived, "
			"handled by OneAI, needed a person, waiting now, undone), and what OneIntake may do: read files "
			"attached to records and how many pages of a scan, and which mailboxes and folders it reads; the confidence floor below which things wait for a "
			"person, and the audit; filing, and how many quiet minutes before it acts; and the books, household "
			"and submitting matching e-invoices; and what it does by itself in OneHR. workspace_intake reads it all. They change a switch or a number "
			"and save from the page head; how is in One's documentation under OneIntake Settings, for the Workspace (how_to)."
		)
	if said.get("workspace") == "One":
		return (
			"The reader is on One's Home: today's numbers for them (tasks due or late, meetings today, documents "
			"waiting in OneIntake, OneAI suggestions waiting for their approval, leave and expense claims waiting "
			"on them as approver), each opening its list, and for an administrator what in the workspace needs "
			"them. my_day reads it all, with the first tasks. How is in One's documentation under Home (how_to)."
		)
	if said.get("page") == "workspace-settings" and said.get("section") == "holidays":
		return (
			"The reader administers this workspace and is on Workspace › Holidays: the holiday list in force "
			"(its first and last day, the days off each week, the country and its public holidays), whether a list "
			"follows it, and how many people are on a list of their own. Leave, attendance, check-ins, the calendar "
			"and deadlines count around these days. workspace_holidays reads it all. They add, rename or remove a "
			"holiday in the table and save from the page head, make next year's list or use another list from the "
			"page head. Asked to add, rename or remove a holiday or a day the workplace is closed, or to change the "
			"days off, change_holidays suggests it as a card they approve. How is in One's documentation under "
			"Holidays, for the Workspace (how_to)."
		)
	if said.get("page") == "workspace-settings" and said.get("section") == "oneai":
		return (
			"The reader administers this workspace and is on OneAI › Actions: each thing OneAI does, the product "
			"it works for, the model it runs on (chosen here, or the default One picked) and the credits it used "
			"in the last thirty days. workspace_oneai reads it all, with the models on offer for each and what "
			"they cost per thousand words read and written. They change an action by clicking it: a model, "
			"instructions added to it (added, never replacing what it does), Try It, which runs it once and "
			"uses credits, and Use the Default; how is in One's documentation under OneAI Actions, for the "
			"Workspace (how_to)."
		)
	if said.get("page") == "workspace-settings" and said.get("section") == "domains":
		return (
			"The reader administers this workspace and is on Workspace › Domains: the addresses it opens at in a "
			"browser. The one One gives it always works; their own domain works once a CNAME record points it at "
			"that address, as the page shows, and Cloudflare has issued its certificate, usually minutes later. A "
			"bare domain such as acme.com needs a DNS provider that flattens a CNAME (ALIAS); otherwise use a "
			"subdomain. "
			"The main address is the one sign-in, invitations and links in mail use. workspace_domains reads each "
			"domain, its status and the target. They add one from the page head and make it the main address or "
			"remove it from its row; how is in One's documentation under Domains, for the Workspace (how_to)."
		)
	if said.get("page") == "workspace-settings" and said.get("section") == "general":
		return (
			"The reader administers this workspace and is on Workspace › General: what it was made with, its "
			"logo for printed documents, its language, time zone and formats, the rules for signing in "
			"(two-factor, passkey and email link sign-in, one device at a time, how long a session lasts, "
			"passwords and their expiry, the lockout after wrong passwords), calendar links and record sharing. workspace_sign_in reads the rules and how people sign in. They change them on "
			"the page and save; how is in One's documentation under General, for the Workspace (how_to)."
		)
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
	if said.get("section") == "memory":
		return (
			"The reader is on What OneAI Remembers in their own Settings: the facts you keep for them, each "
			"with when and the record it is about, which they add, edit and forget there; and, to read only, "
			"what the workspace's administrators wrote for everybody. my_memories reads both. How it works "
			"is in One's documentation under Settings › What OneAI Remembers (how_to)."
		)
	if said.get("section") == "signin":
		return (
			"The reader is on Sign-in in their own Settings: their password, their passkey, whether two-factor "
			"sign-in applies to them, every place they are signed in with a Sign Out each, and their last "
			"sign-ins. my_sign_in reads it all. They change things themselves on the page; how is in One's "
			"documentation under Settings › Sign-in (how_to)."
		)
	if said.get("section") == "calendar":
		from onedesk.one_calendar import feed

		if not feed.allowed():
			return (
				"The reader is on Calendar in their own Settings, but this workspace does not allow calendar "
				"links: its administrators switched them off under Workspace › General › Calendar Links, so "
				"nobody can have one. Say so rather than explaining how to add one."
			)
		return (
			"The reader is on Calendar in their own Settings: a private link to their calendar that another "
			"calendar app reads, with a button for Google Calendar, Apple Calendar and Outlook, what the link "
			"carries, and when an app last read it. They make it, copy it, replace it or switch it off "
			"themselves. How to add it to each app is in One's documentation under Settings › Calendar, and "
			"OneCalendar's under Subscribe (how_to)."
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
					"sent_to": notify.to(one.name) or None,
					"on": bool(one.enabled),
					"email_allowed": bool(one.one_allow_email),
					"email_for_new_people": bool(one.one_email_default),
					"outside": bool(one.one_outside),
					"words_of": notify.upstream(declared.get(one.name) or {}) or None,
					"mailed_by": one.one_app if (declared.get(one.name) or {}).get("mailed_by") else None,
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
		"sent_to": notify.to(doc.name) or None,
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
	"""For a type whose words are another product's: whose, and what can be
	changed instead."""
	from onedesk.one import notify

	if one.get("mailed_by"):
		return {
			"mailed_by": one["app"],
			"next": f"{one['app']} mails this itself; only whether it is sent can be changed, where it has a switch.",
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


def workspace_people() -> dict:
	"""Everybody on this workspace, for its administrators: which apps each
	may use and at what level, who administers it, when each was last active,
	who is turned off, and the seats."""
	from onedesk.one import roles, settings

	if not roles.administers():
		return {"error": "Only a workspace administrator sees everybody's access."}
	said = settings._people()
	return {
		"seats": said["seats"] or "no limit",
		"used": said["used"],
		"people": [
			{
				"name": one.full_name or one.name,
				"address": one.name,
				"on": bool(one.enabled),
				"administrator": one.admin,
				"apps": {app: level for app, level in one.access.items() if level != "None"},
				"last_active": str(one.last_active) if one.last_active else "never",
			}
			for one in said["people"]
		],
		"next": "Everybody has One, OneCloud, OneMail, OneTask and OneCalendar anyway. Name people by name. "
		"The administrator changes a person on Workspace › People by clicking them.",
	}


def workspace_intake() -> dict:
	"""OneIntake's settings and this month, for the workspace's administrators:
	each setting with what it means now, and what arrived, what OneAI handled,
	what needed a person, what waits and what was undone."""
	from onedesk.one import roles, settings

	if not roles.administers():
		return {"error": "Only a workspace administrator sees OneIntake's settings."}
	said = settings._intake()
	labels = {one["fieldname"]: one["label"] for one in said["fields"]}
	return {
		"settings": {labels.get(name, name): value for name, value in said["values"].items()},
		"meaning": {
			"confidence_floor": "what OneAI is less sure of than this percentage waits for a person",
			"quiet_minutes": "0 means OneAI acts on a matter at once",
			"household": "on means no draft bills or invoices at all",
			"submit_matching_e_invoices": "on means OneAI submits e-invoices from known suppliers that match an order",
		},
		"this_month": said["month"],
		"mailboxes_read": [
			{"mailbox": one["email"], "on_behalf_of": one["for"]} for one in said["mailboxes"] if one["on"]
		],
		"mailboxes_not_read": [one["email"] for one in said["mailboxes"] if not one["on"]],
		"folders_read": [{"folder": one["path"], "on_behalf_of": one["for"]} for one in said["folders"]],
	}


def workspace_holidays() -> dict:
	"""The holiday list in force, for the workspace's administrators: its days,
	when it ends, the list after it if any, the public holidays the country
	has that it lacks, and how many people are on a list of their own."""
	from onedesk.one import holidays, roles, settings

	if not roles.administers():
		return {"error": "Only a workspace administrator sees the workspace's holidays."}
	said = settings._holidays()
	if said.get("empty"):
		return {"holiday_list": None, "meaning": "no list: every day is a working day for leave and attendance"}
	listed = said["list"]
	values = said["values"]
	missing = []
	if values.get("country"):
		held = {one["holiday_date"] for one in values["holidays"]}
		try:
			found = holidays.country_holidays(values["country"], listed["from_date"], listed["to_date"], values.get("subdivision"))
		except Exception:
			found = []
		missing = [one for one in found if one["holiday_date"] not in held]
	return {
		"holiday_list": listed["name"],
		"from": listed["from_date"],
		"to": listed["to_date"],
		"days_left": listed["days_left"],
		"days_off_each_week": listed["weekly"],
		"country": values.get("country"),
		"public_holidays": values["holidays"],
		"next_list": said["next"],
		"meaning": "with no next list, from the day after the last day every day counts as a working day for leave and attendance",
		"country_holidays_not_in_the_list": missing,
		"people_on_their_own_list": said["elsewhere"],
	}


def my_day() -> dict:
	"""What waits for the reader today, as One's Home counts it: tasks due or
	late (with the first few), meetings today, documents waiting in OneIntake,
	OneAI suggestions waiting for their approval, approvals waiting on them,
	and for an administrator what in the workspace needs them."""
	from onedesk.one import home

	return home.my_day()


def change_holidays(
	add: Annotated[
		list[dict],
		"Days to add or rename, each {date, name}: date as YYYY-MM-DD. A closure of several days is one entry per day.",
	]
	| None = None,
	remove: Annotated[list[str], "Dates to take off the list, as YYYY-MM-DD."] | None = None,
	days_off: Annotated[
		list[str],
		"The week's days off from now on, in English (Monday to Sunday): every one of them, not only a new one.",
	]
	| None = None,
	why: Annotated[str, "In a sentence, what the change is for."] | None = None,
) -> dict:
	"""Suggest a change to the workspace's holidays, as a card a workspace
	administrator approves: a public holiday or a day the workplace is closed
	added, renamed or removed, and the week's days off (a weekend of two is
	two days). Read workspace_holidays first. The dates go on the list whose
	year holds them. Nothing changes until they approve it. Workspace
	administrators only."""
	from frappe.utils import formatdate, getdate

	from onedesk.one import holidays, roles, settings
	from onedesk.one_ai import proposals

	if not roles.administers():
		return {"error": "Only a workspace administrator changes the workspace's holidays."}
	given = [one.get("date") for one in (add or []) if isinstance(one, dict)] + list(remove or [])
	try:
		days = [getdate(day) for day in given]
	except Exception:
		return {"error": "Give every date as YYYY-MM-DD."}
	covering = set()
	for day in days:
		found = holidays.covering(day)
		if not found:
			return {
				"error": f"No holiday list holds {day}. Next year's list is made with Make Next Year's List on "
				"Workspace › Holidays; suggest this once it is there."
			}
		covering.add(found)
	if len(covering) > 1:
		return {"error": f"Those dates are on {len(covering)} lists ({', '.join(sorted(covering))}); suggest each list's days apart."}
	target = covering.pop() if covering else holidays.in_force()
	if not target:
		return {"error": "The workspace has no holiday list yet."}
	said = settings._holidays(target)
	values = said["values"]
	rows = {one["holiday_date"]: one["description"] for one in values["holidays"]}
	was_off = list(said["list"]["weekly"])
	summary = []
	for one in add or []:
		day, name = str(getdate(one.get("date"))), (one.get("name") or "").strip()
		if not name:
			return {"error": f"Give {day} a name, such as the holiday or why the workplace is closed."}
		label = _("Rename") if day in rows else _("Add")
		if rows.get(day) == name:
			continue
		value = f"{formatdate(day)} · {name}"
		summary.append({"label": label, "value": _("{0} (was {1})").format(value, rows[day]) if day in rows else value})
		rows[day] = name
	for one in remove or []:
		day = str(getdate(one))
		if day not in rows:
			return {"error": f"{day} is not a holiday on {target}. A weekly day off is changed with days_off."}
		summary.append({"label": _("Remove"), "value": f"{formatdate(day)} · {rows.pop(day)}"})
	off = was_off
	if days_off is not None:
		named = {day.lower(): day for day in holidays.WEEK}
		wrong = [one for one in days_off if str(one).strip().lower() not in named]
		if wrong:
			return {"error": f"{', '.join(map(str, wrong))}: say a weekday in English, Monday to Sunday."}
		off = [day for day in holidays.WEEK if day.lower() in {str(one).strip().lower() for one in days_off}]
		if off != was_off:
			summary.append(
				{
					"label": _("Days Off Each Week"),
					"value": _("{0} (was {1})").format(
						", ".join(_(day) for day in off) or _("none"), ", ".join(_(day) for day in was_off) or _("none")
					),
				}
			)
	if not summary:
		return {"error": "That is what the list already says, so there is nothing to change. Say it is right as it is."}
	return {
		"proposal": proposals.propose(
			"Holidays",
			"Holiday List",
			changes={
				"modified": said["opened"][0]["modified"],
				"values": {
					"weekly_offs": off,
					"country": values.get("country"),
					"subdivision": values.get("subdivision"),
					"holidays": [{"holiday_date": day, "description": name} for day, name in sorted(rows.items())],
				},
				"summary": summary,
			},
			record=target,
			why=why,
		),
		"state": "Proposed",
		"next": "Tell them leave, attendance, check-ins, the calendar and deadlines count around it once they "
		"approve it, and that Workspace › Holidays shows the whole list.",
	}


def workspace_oneai() -> dict:
	"""OneAI's actions, for the workspace's administrators: each action, its
	product, its model (chosen or the default), what is added to it, what it
	used in the last thirty days, and the models on offer for it with what they
	cost per thousand words read and written."""
	from onedesk.one import roles, settings

	if not roles.administers():
		return {"error": "Only a workspace administrator sees OneAI's actions."}
	said = settings._oneai()
	catalogue = said["catalogue"]

	def named(one):
		offered = catalogue.get(one["capability"]) or []
		picked = next((m for m in offered if m["name"] == one["model"]), None) if one["model"] else None
		fallback = next((m for m in offered if m.get("default")), None)
		return picked, fallback, offered

	actions = []
	for one in said["actions"]:
		picked, fallback, offered = named(one)
		runs = picked or fallback
		actions.append(
			{
				"action": one["label"],
				"product": one["product"],
				"model": runs["label"] if runs else one["model"],
				"chosen_here": bool(one["model"]),
				"costs_now": {"per_1000_words_read": runs.get("read"), "per_1000_words_written": runs.get("written")}
				if runs
				else None,
				"added_instructions": one["extra"] or None,
				"last_30_days": {"credits": one["credits"], "calls": one["calls"]},
				"could_run_on": [
					{"model": m["label"], "maker": m["maker"], "read": m.get("read"), "written": m.get("written")}
					for m in offered
				][:12],
			}
		)
	return {"actions": sorted(actions, key=lambda one: one["last_30_days"]["credits"], reverse=True)}


#: What each status of a domain means, for the model.
DOMAIN_STATES = {
	"Active": "working",
	"Pending": "added; waiting for its CNAME to point at the workspace's own address (cname_target) and for "
	"Cloudflare to issue its certificate, which it does by itself within minutes of the record being right",
	"Broken": "Cloudflare gave up issuing its certificate, almost always because the CNAME was never made or "
	"points elsewhere; fix the record, then remove the domain and add it again",
	"Gone": "Cloudflare no longer has it; remove it and add it again",
}


def workspace_domains() -> dict:
	"""The workspace's addresses, for its administrators: each domain, whether
	it works and what that means, which is the main address, and the CNAME
	target a domain of its own has to point at."""
	from onedesk.one import roles, settings

	if not roles.administers():
		return {"error": "Only a workspace administrator sees the domains."}
	said = settings._domains()
	return {
		"cname_target": said["target"],
		"domains": [
			{
				"domain": one["domain"],
				"given_by_one": bool(one["given"]),
				"main_address": bool(one["primary"]),
				"status": one["status"],
				"means": DOMAIN_STATES.get(one["status"], "not working"),
				"cloudflare_says": one.get("problem"),
			}
			for one in said["domains"]
		],
		"as_of": str(said["last_heard"]) if said["last_heard"] else None,
	}


def workspace_plan() -> dict:
	"""The workspace's plan and OneAI credits, for its administrators: plan,
	seats, storage, credits left, held, used in the last thirty days and what
	expires when, the last thirty days by model and by person, and the ledger:
	what came in and what OneAI used each day."""
	from frappe.utils import add_days, getdate

	from onedesk.one import roles, settings
	from onedesk.one_ai.report.ai_credits import ai_credits

	if not roles.administers():
		return {"error": "Only a workspace administrator sees the plan and the credits."}
	said = settings._plan()
	held = said["account"]
	end = getdate()
	cut = {}
	for by in ("Model", "Person"):
		try:
			_columns, rows, *_rest = ai_credits.execute(
				{"from_date": add_days(end, -29), "to_date": end, "by": by}
			)
		except frappe.ValidationError:
			# The account could not be reached: the cached numbers still answer.
			rows = []
		cut[by.lower()] = rows[:10]
	return {
		"standing": (said["state"] or {}).get("label"),
		"news": (said["said"] or {}).get("text"),
		"plan": held["plan"],
		"a_month": held["monthly"],
		"seats": {"used": said["used"], "of": held["seats"] or "no limit"},
		"storage": said["storage"],
		"database": said["database"],
		"added_to_the_plan": said["add_ons"],
		"cheapest_for_what_is_used": _cheapest(said),
		"credits": {
			"left": held["credits_balance"],
			"held": held["credits_held"],
			"used_in_30_days": held["credits_month"],
			"expiring": held["credits_expiring"],
			"expire_on": str(held["credits_expires_on"]) if held["credits_expires_on"] else None,
		},
		"last_30_days": cut,
		# What came in and what went out each day, newest first.
		"ledger": (said["ledger"] or [])[:40],
		"as_of": str(held["last_heard"]) if held["last_heard"] else None,
		"next": "The plan's monthly credits expire at the end of the month and are used first; bought credits never expire. Credits "
		"are bought from Buy Credits in the page head of Workspace › Plan and Credits.",
	}


def _cheapest(said: dict) -> list | None:
	"""The three cheapest ways to have what the workspace uses now, from the
	account's calculator (one_admin/plans.py). No AI call; None when the
	account cannot be reached."""
	from onedesk.one import account

	held = said["account"]
	gb = 1000 * 1000 * 1000
	needs = {
		"seats": said["used"],
		"storage_gb": -(-(held["storage_bytes"] or 0) // gb),
		"database_gb": -(-(held["database_bytes"] or 0) // gb),
	}
	try:
		quoted = account.plans_quote(needs)
	except Exception:
		return None
	return [
		{
			"plan": one["label"],
			"add_ons": [f"{extra['count']} × {extra['label']}" for extra in one["extras"]],
			"a_month": one["monthly"],
			"against_now": one["change"],
		}
		for one in quoted.get("options", [])[:3]
	]


def workspace_sign_in() -> dict:
	"""How people sign in to this workspace, for its administrators: the rules
	(two-factor and for whom, passkey and email link sign-in, one device at a
	time, how long a session lasts unused, the password rule, the lockout,
	password expiry, whether records may be shared) and how people follow them: how many people
	there are, how many administer it, whose password is over a year old, and
	the failed sign-ins of the last week."""
	from frappe.utils import add_days, add_to_date, now_datetime

	from onedesk.one import roles, settings

	if not roles.administers():
		return {"error": "Only a workspace administrator sees how everybody signs in."}
	system = frappe.get_single("System Settings")
	people = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User", "name": ["not in", ("Administrator", "Guest")]},
		pluck="name",
	)
	year_ago = add_to_date(now_datetime(), years=-1)
	stale = [
		one.name
		for one in frappe.get_all(
			"User",
			filters={"name": ["in", people or [""]]},
			fields=["name", "last_password_reset_date", "creation"],
		)
		if (one.last_password_reset_date and str(one.last_password_reset_date) < str(year_ago.date()))
		or (not one.last_password_reset_date and one.creation < year_ago)
	]
	failed = frappe.get_all(
		"Activity Log",
		filters={
			"operation": "Login",
			"status": ["!=", "Success"],
			"creation": [">", add_days(now_datetime(), -7)],
		},
		fields=["user", "ip_address", "creation"],
		order_by="creation desc",
		limit=20,
	)
	return {
		"two_factor": settings._two_factor(system),
		"two_factor_by": system.two_factor_method if system.enable_two_factor_auth else None,
		"passkey_sign_in": bool(system.get("one_login_with_passkey")),
		"email_link_sign_in": bool(system.login_with_email_link),
		"one_device_at_a_time": bool(system.deny_multiple_sessions),
		"lockout": f"after {system.allow_consecutive_login_attempts or 'unlimited'} wrong passwords, for {system.allow_login_after_fail or 60} seconds",
		"passwords_expire_after_days": system.force_user_to_reset_password or None,
		"record_sharing": not system.disable_document_sharing,
		"signed_out_after_unused": system.session_expiry or "240:00",
		"password_rule": f"score {system.minimum_password_score} of 4"
		if system.enable_password_policy
		else "any password",
		"people": len(people),
		"administrators": len([one for one in people if roles.administers(one)]),
		"passwords_over_a_year_old": len(stale),
		"failed_sign_ins_last_week": [
			{"user": one.user, "address": one.ip_address, "on": str(one.creation)} for one in failed
		],
		"next": "Say plainly what is fine and what to change, most important first. Two-factor for everybody, "
		"or at least administrators, is the usual advice; failed sign-ins from one address are worth naming. "
		"They change the rules themselves under Workspace › General › Signing In.",
	}


def my_memories() -> dict:
	"""Everything OneAI keeps for the person asking, with when and the record
	each is about, and the titles of what the workspace's administrators wrote
	for everybody. For "what do you know about me?"."""
	from onedesk.one import settings

	said = settings._memory()
	return {
		"remembered": [
			{"fact": one.fact, "about": one.about_title, "kept": str(one.creation)} for one in said["facts"]
		],
		"workspace_told": said["knowledge"],
		"next": "Say it plainly, in their words. They add, correct and forget memories on Settings › What "
		"OneAI Remembers; what the workspace told you is its administrators' to change.",
	}


def my_sign_in() -> dict:
	"""How the person asking signs in and where they are signed in: when their
	password last changed, whether they have a passkey and what it is for,
	whether two-factor sign-in applies to them, the devices they are signed in
	on, and their last sign-ins, failed ones included."""
	from onedesk.one import signin

	said = signin.facts()
	return {
		"password_last_changed": str(said["password_changed"])
		if said["password_changed"]
		else "never recorded",
		"passkey": None if said["employee"] is None else bool(said["passkey"]),
		"passkey_also_signs_in": said["passkey_signs_in"],
		"two_factor": said["two_factor"],
		"signed_in_on": [
			{
				"device": one["device"],
				"address": one["address"],
				"last_used": str(one["last_used"]),
				"this_one": one["here"],
			}
			for one in said["sessions"]
		],
		"recent_sign_ins": [
			{"failed": one["failed"], "address": one["address"], "on": str(one["on"])}
			for one in said["recent"]
		],
		"next": "Say plainly what looks fine and what to do: an old password, no two-factor, places they do not "
		"recognise, failed sign-ins they did not make. They change it themselves on Settings › Sign-in.",
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


# ------------------------------------------------------------------ numbering

#: How frappe reads a series, for the model: every part it understands.
SERIES_HELP = (
	"A series is parts joined by dots, read left to right. Text is kept as written (INV-, SO/, -). "
	"YYYY is the year (2026), YY the year's last two digits (26), MM the month (01-12), DD the day, "
	"JJJ the day of the year (001-366), WW the week of the year; FY is the fiscal year (2025-2026) and "
	"TFY its short form, ABBR the company's abbreviation; {fieldname} or a bare fieldname is that field "
	"of the record (such as {branch}), and timestamp the moment it is made. The number is # once per "
	"digit (##### gives 00001), must follow a dot, and only the first run of # counts. The number "
	"restarts whenever the text before it changes, so INV-.YYYY.-.#### starts at 0001 each year and "
	"INV-.YYYY.-.MM.-.#### each month. Only letters, digits, spaces, - / _ . # { } are allowed. "
	"Examples: INV-.YYYY.-.#####, SO/.YY./.####, .ABBR.-QTN-.#####, EMP-.{department}.-.###."
)


#: How frappe names a new record, for the model: every way this workspace may choose.
NAMING_HELP = (
	"A new record is named one of these ways, as frappe offers them. Naming Series: the next name in one "
	"of its series (only a kind with a Naming Series field). field:<fieldname>: the value of that field, "
	"which becomes required and unique, so only a field no two records will share, such as a title or a "
	"code; the fields offered are named_by.fields. An expression: a pattern written as a series is, such "
	"as PRJ-.YYYY.-.#### for a kind with no series field, its prefix no other kind's. prompt: typed by "
	"whoever makes the record. hash: a random name. A Customer, Supplier, Item, Employee or Campaign names "
	"itself, so its choices are its app's own (named_by.kinds). A kind One's own code makes (named_by.made) "
	"is never typed by hand and only named by a field that code always fills. Naming Rules come first: a record whose "
	"fields match a rule is named by the rule's prefix and its own counter, whatever else is chosen; the "
	"highest priority matching rule wins. Nothing renames a record already made: every change applies to "
	"records made afterwards, and old ones keep their names."
)


def workspace_numbering(
	doctype: Annotated[str, "The kind of record, as its DocType name, such as Sales Invoice. Empty lists them all."]
	| None = None,
) -> dict:
	"""How a kind of record is named, for the workspace's administrators:
	what a new one is named by and what else it may be (`named_by`), each
	series it may take its name from (the first is the default) with the name
	the next one gets, the number its counter has reached and the highest
	number records already use (`used`), which a counter may never go below,
	and its naming rules with what each must match. Empty: every kind of
	record numbered by a series. Read it before suggesting a change."""
	from onedesk.one import numbering, roles

	if not roles.administers():
		return {"error": "Only a workspace administrator sees how records are numbered."}
	try:
		if not doctype:
			return {"kinds": numbering.doctypes()}
		return {
			"doctype": doctype,
			"named_by": numbering.naming_by(doctype),
			"series": numbering.series(doctype),
			"rules": numbering.naming_rules(doctype),
			"how_a_record_is_named": NAMING_HELP,
			"how_a_series_is_written": SERIES_HELP,
		}
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {"error": str(e)}


def _rule_said(doc) -> str:
	"""A naming rule, in a line: its prefix and what it matches."""
	matches = ", ".join(f"{one.field} {one.condition} {one.value}" for one in doc.conditions or [])
	said = _("{0} with {1} digits").format(doc.prefix, doc.prefix_digits)
	return _("{0}, when {1}").format(said, matches) if matches else _("{0}, for every record").format(said)


def change_numbering(
	doctype: Annotated[str, "The kind of record, as its DocType name, such as Sales Invoice."],
	series: Annotated[
		list[str],
		"Every series it may be named by, the default first, when they change: the whole list, not only a new "
		"one. Only a kind with a Naming Series field. " + SERIES_HELP,
	]
	| None = None,
	move: Annotated[
		list[dict],
		"Counters to move on, each {series, to}: the next name continues after `to`. Never below what the "
		"counter has reached or the highest number records already use.",
	]
	| None = None,
	name_by: Annotated[
		str,
		"What a new one is named by: Naming Series, field:<fieldname> from named_by.fields, an expression such "
		"as PRJ-.YYYY.-.####, prompt, hash, or one of named_by.kinds for a kind that names itself. "
		+ NAMING_HELP,
	]
	| None = None,
	rules: Annotated[
		list[dict],
		"Naming rules to add, change or remove, each {name?, prefix, digits, priority, disabled, conditions, "
		"delete}: name only for an existing rule (from workspace_numbering), delete true to remove it; prefix "
		"the text before the number written as a series is but with no #, such as RET-.YYYY.-; digits 1-10; "
		"conditions [{field, condition, value}] all of which must match, condition one of = != > < >= <=, "
		"field an ordinary field of the record, none meaning every record; the higher priority wins.",
	]
	| None = None,
	why: Annotated[str, "In a sentence, what the change is for."] | None = None,
) -> dict:
	"""Suggest how a kind of record is named, as a card a workspace
	administrator approves: named by a series, one of its fields, an
	expression, typed or random; its series added, changed, reordered (the
	first is the default) or removed; a series' counter moved on, to start a
	new year at 1000 or to carry on after records brought in from elsewhere;
	and its naming rules added, changed or removed. Read workspace_numbering
	first, and check `used` before moving a counter. Nothing changes until
	they approve it, and records already made keep their names. Workspace
	administrators only."""
	from onedesk.one import numbering, roles
	from onedesk.one_ai import proposals

	if not roles.administers():
		return {"error": "Only a workspace administrator changes how records are numbered."}
	try:
		numbering._meta(doctype)
		now = numbering.series(doctype)
		was = [row["series"] for row in now]
		wanted = [one.strip() for one in series or [] if one and one.strip()] or was
		if series and not frappe.get_meta(doctype).get_field("naming_series"):
			return {"error": f"{doctype} has no series; name it by an expression instead."}
		if series and not wanted:
			return {"error": f"{doctype} needs at least one series."}
		if wanted != was:
			numbering.check(doctype, wanted)
		moves, summary, changed_rules = [], [], []
		if wanted != was:
			summary.append({"label": _("Series"), "value": _("{0} (was {1})").format(", ".join(wanted), ", ".join(was))})
		named = numbering.naming_by(doctype)
		name_by = (name_by or "").strip() or None
		if name_by and not named:
			return {"error": f"{doctype} is named by its own code, so only its rules can change."}
		if name_by and name_by != named["value"]:
			if name_by not in numbering.choices(named):
				if named["app"] or name_by.startswith("field:"):
					return {"error": f"{doctype} cannot be named by {name_by}; the choices are {', '.join(numbering.choices(named))}."}
				numbering.check_pattern(doctype, name_by)
			summary.append(
				{
					"label": _("Named By"),
					"value": _("{0} (was {1})").format(numbering.label(named, name_by), numbering.label(named, named["value"])),
				}
			)
		else:
			name_by = None
		rows = {row["series"]: row for row in now}
		for one in move or []:
			name, to = (one.get("series") or "").strip(), frappe.utils.cint(one.get("to"))
			if name not in wanted:
				return {"error": f"{name} is not one of {doctype}'s series: {', '.join(wanted)}."}
			row = rows.get(name) or {"current": 0, "used": 0}
			floor = max(row["current"], row["used"])
			if to < floor:
				return {"error": f"{name} has reached {floor}; a lower number would repeat a name already used."}
			if to == row["current"]:
				continue
			moves.append({"series": name, "to": to})
			summary.append({"label": name, "value": _("Continues after {0} (was {1})").format(to, row["current"])})
		for one in rules or []:
			if one.get("delete"):
				if not one.get("name") or not frappe.db.exists("Document Naming Rule", {"name": one["name"], "document_type": doctype}):
					return {"error": f"{one.get('name')} is not a rule of {doctype}."}
				changed_rules.append({"name": one["name"], "delete": True})
				summary.append({"label": _("Rule"), "value": _("Remove {0}").format(one["name"])})
				continue
			doc = numbering.rule_doc(doctype, one)
			changed_rules.append({key: one.get(key) for key in ("name", "prefix", "digits", "priority", "disabled", "conditions")})
			summary.append({"label": _("Rule") if one.get("name") else _("New Rule"), "value": _rule_said(doc)})
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {"error": str(e)}
	if not summary:
		return {"error": "That is how it is numbered already, so there is nothing to change. Say it is right as it is."}
	return {
		"proposal": proposals.propose(
			"Numbering",
			doctype,
			changes={
				"state": numbering.state(doctype),
				"series": wanted if wanted != was else None,
				"move": moves,
				"name_by": name_by,
				"rules": changed_rules,
				"summary": summary,
			},
			why=why,
		),
		"state": "Proposed",
		"next": "Tell them it applies to records made after they approve it, that records already made keep "
		"their names, and that the record's Settings › Numbering shows it.",
	}


# ------------------------------------------------------------------ printing


def workspace_printing(
	doctype: Annotated[str, "A kind of record, such as Sales Invoice, to also read its formats and default."]
	| None = None,
) -> dict:
	"""How the workspace's documents look on paper, for its administrators:
	its letter heads (which is the default, which are off), the logo Workspace
	> General keeps, the print formats the workspace made, and for a kind of
	record the formats it may print with and the one it prints with unless
	another is chosen. Read it before suggesting a change."""
	from onedesk.one import printing, roles, settings

	if not roles.administers():
		return {"error": "Only a workspace administrator sees how documents are printed."}
	try:
		company = settings._company()
		said = {
			"letter_heads": [
				{
					key: one.get(key)
					for key in ("name", "is_default", "disabled", "image", "standard", "source")
				}
				for one in printing.letter_heads()
			],
			"company_logo": company.company_logo if company else None,
			# What a letter head is written from: Workspace > General's On Documents.
			"company": _on_documents(company),
			"workspace_formats": printing.formats(),
		}
		if doctype:
			printing._doctype(doctype)
			said["doctype"] = doctype
			said["default_format"] = frappe.get_meta(doctype).default_print_format
			said["formats"] = frappe.get_all(
				"Print Format",
				filters={"doc_type": doctype, "disabled": 0},
				fields=["name", "standard", "print_format_builder_beta as made_in_the_builder"],
				order_by="name asc",
			)
		return said
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {"error": str(e)}


def change_printing(
	doctype: Annotated[str, "The kind of record whose default format changes, such as Sales Invoice."]
	| None = None,
	default_format: Annotated[
		str, "The format that kind prints with unless another is chosen: one of its formats."
	]
	| None = None,
	letter_head: Annotated[
		dict,
		"A letter head to make or change: {name} of an existing one, or {new_name} for a new one; {preset}, "
		"one of classic, centred, banner, minimal or logo, to draw its top from the company's details in "
		"Workspace > General (with {show}, a list of name, address, phone, email, website, tax_id, and "
		"{logo_height} in pixels), which is what to suggest first; or {logo}, "
		"'company' for the logo Workspace > General keeps or a file URL the workspace already has; or "
		"{top_html} and {foot_html}, the top and foot of the page written in plain HTML with inline styles "
		"(no template tags, no scripts, pictures only from this workspace's files), from the company's "
		"details workspace_printing gives; {default} true to make it the one printed unless another is "
		"chosen; {off} true to turn it off.",
	]
	| None = None,
	why: Annotated[str, "In a sentence, what the change is for."] | None = None,
) -> dict:
	"""Suggest how documents are printed, as a card a workspace administrator
	approves: which format a kind of record prints with by default, a letter
	head, made from the workspace's logo or designed in HTML from its details,
	or which letter head is the default. A format's own layout is
	design_print_format. Read workspace_printing first. The card shows the
	page before it is approved; nothing changes until they approve it.
	Workspace administrators only."""
	from onedesk.one import letter_heads, print_html, printing, roles, settings
	from onedesk.one_ai import proposals

	if not roles.administers():
		return {"error": "Only a workspace administrator changes how documents are printed."}
	summary, head = [], None
	try:
		if default_format:
			if not doctype:
				return {"error": "Say which kind of record prints with that format."}
			printing._doctype(doctype)
			if frappe.db.get_value("Print Format", default_format, "doc_type") != doctype:
				return {
					"error": f"{default_format} is not a format of {doctype}; read workspace_printing for its formats."
				}
			was = frappe.get_meta(doctype).default_print_format
			if was != default_format:
				summary.append(
					{
						"label": _("Prints With"),
						"value": _("{0} (was {1})").format(default_format, was or _("Standard")),
					}
				)
			else:
				default_format = None
		if letter_head:
			name = (letter_head.get("name") or "").strip() or None
			if name and not frappe.db.exists("Letter Head", name):
				return {"error": f"There is no letter head {name}; read workspace_printing for them."}
			logo = letter_head.get("logo")
			if logo == "company":
				company = settings._company()
				logo = company.company_logo if company else None
				if not logo:
					return {"error": "Workspace > General has no logo yet; ask them to add one there first."}
			top, foot = letter_head.get("top_html"), letter_head.get("foot_html")
			preset = letter_head.get("preset")
			if preset and preset not in letter_heads.PRESETS:
				return {"error": f"{preset} is not a preset; they are {', '.join(letter_heads.PRESETS)}."}
			if not name and not (letter_head.get("new_name") and (logo or top or preset)):
				return {"error": "A new letter head needs new_name, and a preset, a logo or top_html."}
			head = {"name": name}
			if not name:
				head["letter_head_name"] = letter_head["new_name"].strip()
				summary.append({"label": _("New Letter Head"), "value": head["letter_head_name"]})
			if preset:
				head["one_top"] = letter_heads.settings(
					{key: letter_head.get(key) for key in ("preset", "show", "logo_height", "align")}
				)
				head["source"] = "HTML"
				head["content"] = letter_heads.draw(head["one_top"])
				summary.append({"label": _("Top"), "value": str(letter_heads.PRESETS[preset])})
			if logo and not top and not preset:
				head["source"] = "Image"
				head["image"] = logo
				summary.append({"label": _("Logo"), "value": logo.rsplit("/", 1)[-1].split("?")[0]})
			if top:
				head["source"] = "HTML"
				head["content"] = print_html.letter_head_html(top, _("Top"))
				summary.append({"label": _("Top"), "value": _("Designed in HTML")})
			if foot:
				head["footer_source"] = "HTML"
				head["footer"] = print_html.letter_head_html(foot, _("Foot"))
				summary.append({"label": _("Foot"), "value": _("Designed in HTML")})
			if letter_head.get("default") is not None:
				head["is_default"] = 1 if letter_head["default"] else 0
				summary.append({"label": _("Default"), "value": _("Yes") if head["is_default"] else _("No")})
			if letter_head.get("off") is not None:
				head["disabled"] = 1 if letter_head["off"] else 0
				summary.append({"label": _("Off"), "value": _("Yes") if head["disabled"] else _("No")})
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {"error": str(e)}
	if not summary:
		return {
			"error": "That is how it prints already, so there is nothing to change. Say it is right as it is."
		}
	return {
		"proposal": proposals.propose(
			"Printing",
			doctype if default_format else "Letter Head",
			changes={
				"state": printing.state(doctype if default_format else None),
				"default_format": default_format,
				"letter_head": head,
				"summary": summary,
			},
			why=why,
		),
		"state": "Proposed",
		"next": "Tell them See the Page on the card shows it before they approve it, that it applies once "
		"they do, and that Workspace › Printing shows it.",
	}


def _on_documents(company) -> dict:
	"""The company as a printed page shows it (Workspace > General > On Documents)."""
	from onedesk.one import settings

	if not company:
		return {}
	address = settings._company_address(company)
	return {
		"name": company.company_name,
		"phone": company.phone_no,
		"email": company.email,
		"website": company.website,
		"address": [
			one
			for one in (
				*(address.get(key) for key in settings.ADDRESS),
				company.country,
			)
			if one
		]
		if address
		else [company.country],
	}


#: How a print format is written, for a model writing one.
LAYOUT_HELP = (
	"sections is a list of sections, top to bottom. A section is a list of columns side by side, or "
	"{label, columns}. A column is a list of blocks, top to bottom. A block is a fieldname of the record "
	"(printed as its label and value); '---' for a line; {table: fieldname, columns: ['item_name:50', "
	"'qty:15', 'amount:35']} for a table with each column's share of the width; {text: '...'} for fixed "
	"words; {space: 12} for room; {image: url} for a file of this workspace; or {html: '...'}, a Jinja "
	"template of the record only: {{ doc.fieldname }}, {{ doc.get_formatted('grand_total') }}, "
	"{% for row in doc.items %}...{% endfor %}, {% if %}, _('text') and plain filters; values are "
	"escaped, and scripts, forms and outside pictures are taken out. An empty column is []. heading is "
	"the title at the top in the same HTML, frappe's own when left out. css is the format's stylesheet, "
	"with no imports or outside URLs."
)


def _block(one) -> dict:
	"""One block as a model writes it, as the builder stores it."""
	if isinstance(one, str):
		return {"fieldtype": "Divider"} if one.strip("- ") == "" else {"fieldname": one.strip()}
	if not isinstance(one, dict):
		frappe.throw(_("A block is a fieldname, '---', or one of table, text, space, image or html."))
	if one.get("table"):
		columns = []
		for column in one.get("columns") or []:
			fieldname, _sep, width = str(column).partition(":")
			columns.append({"fieldname": fieldname.strip(), **({"width": frappe.utils.cint(width)} if width else {})})
		return {"fieldname": one["table"], "table_columns": columns}
	if "html" in one:
		return {"fieldtype": "HTML", "html": str(one["html"])}
	if "text" in one:
		return {"fieldtype": "Static Text", "text": str(one["text"])}
	if "space" in one:
		return {"fieldtype": "Spacer", "height": frappe.utils.cint(one["space"]) or 10}
	if "image" in one:
		return {"fieldtype": "Image", "image_url": str(one["image"])}
	if one.get("fieldname"):
		return {"fieldname": one["fieldname"]}
	frappe.throw(_("A block is a fieldname, '---', or one of table, text, space, image or html."))


def _built(sections, heading: str | None) -> dict:
	"""The builder's layout from sections as a model writes them."""
	from frappe.printing.doctype.print_format.classic_converter import DEFAULT_PRINT_HEADING

	if isinstance(sections, str):
		sections = frappe.parse_json(sections)
	if not isinstance(sections, list) or not sections:
		frappe.throw(_("sections is a list of sections, each a list of columns."))
	built = []
	for section in sections:
		label = ""
		if isinstance(section, dict):
			label, section = section.get("label") or "", section.get("columns") or []
		if not isinstance(section, list):
			frappe.throw(_("A section is a list of columns, each a list of blocks."))
		columns = [column if isinstance(column, list) else [column] for column in section]
		built.append({"label": label, "columns": [{"label": "", "fields": [_block(b) for b in c]} for c in columns]})
	top = heading or DEFAULT_PRINT_HEADING
	return {
		"header": {"columns": [{"label": "", "fields": [{"fieldtype": "HTML", "label": "", "html": top}]}]},
		"sections": built,
		"footer": {"columns": [{"label": "", "fields": []}]},
	}


def _written(layout) -> dict | None:
	"""A builder layout as a model writes one (_built's inverse): its sections,
	and its heading when it is not frappe's own."""
	from frappe.printing.doctype.print_format.classic_converter import DEFAULT_PRINT_HEADING

	if not isinstance(layout, dict):
		return None

	def block(one: dict):
		kind = one.get("fieldtype")
		if one.get("table_columns"):
			return {
				"table": one.get("fieldname"),
				"columns": [
					f"{c.get('fieldname')}:{c.get('width')}" if c.get("width") else c.get("fieldname")
					for c in one["table_columns"]
				],
			}
		if kind == "HTML":
			return {"html": one.get("html") or ""}
		if kind == "Static Text":
			return {"text": one.get("text") or ""}
		if kind == "Divider":
			return "---"
		if kind == "Spacer":
			return {"space": one.get("height") or 10}
		if kind == "Image":
			return {"image": one.get("image_url") or ""}
		return one.get("fieldname")

	sections = []
	for section in layout.get("sections") or []:
		columns = [
			[b for b in (block(one) for one in column.get("fields") or [] if isinstance(one, dict)) if b]
			for column in section.get("columns") or []
		]
		if any(columns):
			sections.append({"label": section["label"], "columns": columns} if section.get("label") else columns)
	top = [
		one.get("html")
		for column in (layout.get("header") or {}).get("columns") or []
		for one in column.get("fields") or []
		if one.get("fieldtype") == "HTML"
	]
	heading = top[0] if top and top[0] != DEFAULT_PRINT_HEADING else None
	return {"sections": sections, **({"heading": heading} if heading else {})}


def print_layout(
	doctype: Annotated[str, "The kind of record, such as Sales Invoice."],
	print_format: Annotated[str, "A format of that kind to start from; its default when left out."] | None = None,
) -> dict:
	"""A kind of record's fields and one of its builder formats as sections, the
	way design_print_format takes them: read it before designing one.
	Workspace administrators only."""
	from onedesk.one import printing, roles
	from onedesk.one_ai import kind

	if not roles.administers():
		return {"error": "Only a workspace administrator designs how documents are printed."}
	try:
		printing._doctype(doctype)
		meta = frappe.get_meta(doctype)
		name = print_format or next(iter(printing.starts(doctype)), frappe._dict()).get("name")
		held = frappe.db.get_value("Print Format", name, ["doc_type", "format_data", "css"], as_dict=True) if name else None
		if held and held.doc_type != doctype:
			return {"error": f"{name} is not a format of {doctype}."}
		return {
			"doctype": doctype,
			"fields": kind.fields_of(meta, most=150),
			"tables": {
				table.fieldname: kind.fields_of(frappe.get_meta(table.options), most=30)
				for table in meta.get_table_fields()
			},
			"format": name,
			"written": _written(json.loads(held.format_data)) if held and held.format_data else None,
			"css": held.css if held else None,
			"how": LAYOUT_HELP,
		}
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {"error": str(e)}


def design_print_format(
	doctype: Annotated[str, "The kind of record the format prints, such as Sales Invoice."],
	name: Annotated[str, "The format's name: a new one, or one of the workspace's own formats to change."],
	sections: Annotated[
		str,
		"The sections as JSON text, top to bottom: each a list of columns, each a list of blocks, as "
		"print_layout's how says. Example: [[['customer_name'], ['posting_date', 'due_date']], "
		"[[{\"table\": \"items\", \"columns\": [\"item_name:60\", \"qty:15\", \"amount:25\"]}]], [[], ['grand_total']]]",
	],
	heading: Annotated[str, "The title at the top, as an HTML template of the record; frappe's own if left out."]
	| None = None,
	css: Annotated[str, "The format's own stylesheet, if it needs one."] | None = None,
	letter_head: Annotated[str, "The letter head it prints with, if not the default."] | None = None,
	make_default: Annotated[bool, "True to make it the one this kind prints with."] | None = None,
	why: Annotated[str, "In a sentence, what the design is for."] | None = None,
) -> dict:
	"""Suggest a print format for any kind of record, as a card a workspace
	administrator approves: laid out as frappe's print format builder lays one
	out, from sections of columns of blocks. Read print_layout first. It is
	checked as the builder's own save checks it; the card shows the page on
	the kind's latest record before it is approved, and the format then opens
	in the builder like any other. Workspace administrators only."""
	from onedesk.one import printing, roles
	from onedesk.one_ai import proposals

	if not roles.administers():
		return {"error": "Only a workspace administrator designs how documents are printed."}
	name = (name or "").strip()
	if not name:
		return {"error": "Give the format a name."}
	try:
		existing = frappe.db.get_value("Print Format", name, ["standard", "doc_type"], as_dict=True)
		if existing and (existing.standard == "Yes" or existing.doc_type != doctype):
			return {"error": f"{name} is not a format of {doctype} this workspace made; choose another name."}
		doc = printing.format_doc(doctype, name, _built(sections, heading), css, letter_head)
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {"error": str(e)}
	summary = [
		{"label": _("Changed Format") if existing else _("New Format"), "value": name},
		{"label": _("Sections"), "value": str(len(frappe.parse_json(doc.format_data).get("sections") or []))},
	]
	if make_default:
		summary.append({"label": _("Prints With"), "value": name})
	return {
		"proposal": proposals.propose(
			"Printing",
			doctype,
			changes={
				"state": printing.state(doctype, name),
				"format": {"doctype": doctype, "name": name, "format_data": doc.format_data, "css": doc.css},
				"default_format": name if make_default else None,
				"summary": summary,
			},
			why=why,
		),
		"state": "Proposed",
		"next": "Tell them See the Page on the card shows it on their latest record, and that once approved "
		"it opens in the print format builder from the record's Settings > Print Formats.",
	}
