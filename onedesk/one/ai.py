"""What OneAI offers on One's own pages, and what it is told about them.

Settings is a desk page, not a record: the panel has no doctype to go on, so
the page says where the reader is (`page` and `section` from oneai.js), and
this module turns that into the sentence the model is told and the
suggestions the panel offers. How to use each section is in `README.md`, which
OneAI reads through `how_to`.
"""

import json
import re
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
			"label": _lt("Suggest a letter head"),
			"ask": _lt(
				"Suggest a letter head drawn from our details in Workspace › General: the header and the "
				"footer presets that suit us, as the default."
			),
			"expects": "change_printing",
		},
		{
			"label": _lt("Tidy our footer"),
			"ask": _lt(
				"Look at our default letter head's footer and suggest a cleaner one: what it should show, "
				"which preset, and whether it needs a note."
			),
			"expects": "change_printing",
		},
		{
			"label": _lt("Design a letter head from our details"),
			"ask": _lt(
				"Design a letter head in HTML from the company's details in Workspace › General: the name "
				"and logo in the header, the address, phone and email in the footer, each after its icon."
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
	"page:workspace-settings/mail_templates": [
		{
			"label": _lt("Write a payment reminder"),
			"ask": _lt(
				"Write a polite mail template for Sales Invoice reminding the customer that an invoice is due, "
				"with its number, amount and due date."
			),
			"expects": "write_mail_template",
		},
		{
			"label": _lt("Tidy the leave mails"),
			"ask": _lt(
				"Read the leave approval and leave status mails and suggest clearer, friendlier wording for each, "
				"keeping what they already fill in."
			),
			"expects": "write_mail_template",
		},
		{
			"label": _lt("Which mails use a template?"),
			"ask": _lt("Which of our mail templates does a setting send, and which are only picked in the composer?"),
			"expects": "workspace_mail_templates",
		},
	],
	"page:workspace-settings/approvals": [
		{
			"label": _lt("Approve bills by amount"),
			"ask": _lt(
				"Suggest an approval for Purchase Invoices: a bill starts Pending, an accounts user approves it up "
				"to 5,000 and an accounts manager above that, and a manager may reject it."
			),
			"expects": "suggest_approval",
		},
		{
			"label": _lt("Who approves what?"),
			"ask": _lt("Which approvals are on, and who takes each step?"),
			"expects": "workspace_approvals",
		},
	],
	"Automation Flow": [
		{
			"label": _lt("Thank customers who pay"),
			"ask": _lt(
				"Set up an automation: when a Sales Invoice's status changes to Paid, tell its owner that the "
				"customer has paid, naming the invoice and the amount."
			),
			"expects": "suggest_automation",
		},
		{
			"label": _lt("What runs by itself?"),
			"ask": _lt("Which automations are on, what starts each, and what does each do?"),
			"expects": "workspace_automations",
		},
	],
	"Dashboard": [
		{
			"label": _lt("What do our dashboards show?"),
			"ask": _lt("Which dashboards do we have, and what does each chart and card count?"),
			"expects": "workspace_reports",
		},
	],
	"Auto Email Report": [
		{
			"label": _lt("Which reports go out by mail?"),
			"ask": _lt("Which reports are mailed, how often, and to whom?"),
			"expects": "workspace_reports",
		},
	],
	"Personal Data Download Request": [
		{
			"label": _lt("What would this copy give?"),
			"ask": _lt("What would this copy of their data give, kind by kind, and is any of it other people's or the company's confidential information I should withhold?"),
			"expects": "privacy_request",
		},
	],
	"Personal Data Deletion Request": [
		{
			"label": _lt("What would deleting them remove?"),
			"ask": _lt("If I approve this request, what is deleted, what is kept without their name, and is anything still theirs that somebody should take over first?"),
			"expects": "privacy_request",
		},
	],
	"Version": [
		{
			"label": _lt("What changed today?"),
			"ask": _lt("What was changed today, by whom, and does anything look out of place?"),
			"expects": "audit_log",
		},
	],
	"Activity Log": [
		{
			"label": _lt("Any odd sign-ins?"),
			"ask": _lt("In the last week, which sign-ins failed, and did anybody sign in from somewhere new?"),
			"expects": "audit_log",
		},
	],
	"Access Log": [
		{
			"label": _lt("What left as a file?"),
			"ask": _lt("What was exported or printed in the last week, by whom, and was any of it large?"),
			"expects": "audit_log",
		},
	],
	"Deleted Document": [
		{
			"label": _lt("What was deleted lately?"),
			"ask": _lt("What was deleted in the last week, by whom, and is any of it worth putting back?"),
			"expects": "recycle_bin",
		},
	],
	"page:workspace-settings/access": [
		{
			"label": _lt("Who can do what?"),
			"ask": _lt("What may each app's users, managers and our own levels do, and who is at each? Say anything that looks too wide."),
			"expects": "workspace_access",
		},
		{
			"label": _lt("Who sees only part?"),
			"ask": _lt("Who is held to a territory, a department or another record, and to which?"),
			"expects": "workspace_access",
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
	if said.get("page") == "workspace-settings" and said.get("section") == "access":
		return (
			"The reader administers this workspace and is on Workspace › Access: every level of each app, its user, "
			"its manager and the ones made between, and what each may do, the profiles (a job's apps and levels in one) and who is on each, "
			"and the groups and who is in each. A person's page also holds what records they are held to. "
			"workspace_access reads it all. How is in One's documentation under Access, for the Workspace (how_to)."
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
	somebody, and nothing else. Telling together with anything else (assign
	it, set a field, make a record, wait), or anything asked on the
	automations list, is an automation: suggest_automation. Only people who
	can open the record are ever told. Nothing is made until they approve it.
	Workspace administrators only."""
	from onedesk.one import roles as workspace
	from onedesk.one import rules
	from onedesk.one_ai import proposals

	if not workspace.administers():
		return {"error": "Only a workspace administrator makes notification rules."}
	if when not in rules.EVENTS:
		return {"error": f"When must be one of: {', '.join(rules.EVENTS)}.", "mend": "draft_notification"}
	if not frappe.db.exists("DocType", watches):
		return {"error": f"There is no kind of record called {watches}.", "mend": "draft_notification"}
	for text in (subject, message):
		wrong = rules.check_text(watches, text)
		if wrong:
			return {
				"error": f"{wrong} The fields it may use: {', '.join(rules.readable(watches))}.",
				"mend": "draft_notification",
			}
	recipients = [{"receiver_by_role": one} for one in roles or [] if one]
	if person:
		recipients.append({"receiver_by_document_field": person})
	if not recipients and not assignees:
		return {
			"error": "Say who is told: roles, a person on the record, or its assignees.",
			"mend": "draft_notification",
		}
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


def workspace_access() -> dict:
	"""Access, for this workspace's administrators: every level of each app,
	its user, manager and the ones made between, with what each may do and who
	is at it, the profiles
	with the levels they set and who is on them, the groups with their people,
	and who is held to which records."""
	from onedesk.one import access, roles

	if not roles.administers():
		return {"error": "Only a workspace administrator sees who may do what."}
	levels = []
	for app, names in access.all_levels().items():
		for tier in ["User", *names, "Manager"]:
			one = access.level(access.key_of(app, tier))
			levels.append(
				{
					"level": tier,
					"app": app,
					"made_by_the_workspace": bool(one["own"]),
					"may": {row["doctype"]: [access.SAID[r] for r in access.RIGHTS if row.get(r)] for row in one["rows"]},
					"people": one["people"],
				}
			)
	holds = frappe.get_all(
		"User Permission",
		filters={"allow": ["in", access.RECORD_KINDS]},
		fields=["user", "allow", "for_value", "applicable_for"],
		limit=200,
	)
	return {
		"levels": levels,
		"profiles": [
			{"profile": one["name"], "sets": {app: level for app, level in one["levels"].items() if level != "None"}, "people": one["people"]}
			for one in access.profiles()
		],
		"groups": [
			{"group": one["name"], "people": frappe.get_all("User Group Member", filters={"parent": one["name"], "parenttype": "User Group"}, pluck="user")}
			for one in access.groups()
		],
		"held_to": [
			{"person": one.user, "kind": one.allow, "record": one.for_value, "only_on": one.applicable_for or "everywhere"} for one in holds
		],
		"next": "Every level, User and Manager too, may be given or have taken away anything on the kinds its app works with. "
		"The administrator changes all of this on Workspace › Access, "
		"and a person's level, profile and what they are held to on their page under People.",
	}


def workspace_reports() -> dict:
	"""Reports and dashboards: the reports saved from a list (each one's kind
	of record, who saved it, and whether it is in everybody's sidebar), the
	dashboards with what each chart and card counts, and, for the workspace's
	administrators, the reports that go out by mail."""
	from onedesk.one import roles

	saved = frappe.get_list(
		"Report",
		filters={"report_type": "Report Builder", "is_standard": "No"},
		fields=["name", "ref_doctype", "owner"],
		limit=100,
	)
	placed = frappe.get_all(
		"Sidebar Item",
		filters={"parenttype": "Custom Sidebar", "link_type": "Report", "added": 1},
		fields=["link_to", "parent"],
	)
	# The site's layer has no user: what is in it, everybody sees.
	shared = {row.link_to for row in placed if not frappe.db.get_value("Custom Sidebar", row.parent, "user")}
	dashboards = []
	for name in frappe.get_list("Dashboard", filters={"is_standard": 0}, pluck="name", limit=50):
		doc = frappe.get_doc("Dashboard", name)
		said = {"dashboard": name, "charts": [], "cards": []}
		for row in doc.charts:
			chart = frappe.db.get_value(
				"Dashboard Chart", row.chart, ["chart_type", "document_type", "report_name", "based_on", "value_based_on", "group_by_based_on"], as_dict=True
			) or {}
			said["charts"].append({"chart": row.chart, **{k: v for k, v in chart.items() if v}})
		for row in doc.cards:
			card = frappe.db.get_value("Number Card", row.card, ["type", "document_type", "function", "report_name"], as_dict=True) or {}
			said["cards"].append({"card": row.card, **{k: v for k, v in card.items() if v}})
		dashboards.append(said)
	mailed = []
	if roles.administers():
		mailed = [
			{"report": one.report, "how_often": one.frequency, "to": one.email_to, "on": bool(one.enabled), "runs_as": one.user}
			for one in frappe.get_all(
				"Auto Email Report", fields=["report", "frequency", "email_to", "enabled", "user"], limit=100
			)
		]
	return {
		"saved_reports": [
			{"report": one.name, "of": one.ref_doctype, "saved_by": one.owner, "in_everybody's_sidebar": one.name in shared}
			for one in saved
		],
		"dashboards": dashboards,
		"reports_by_mail": mailed,
		"next": "A list's Report view is saved from its menu (Save As) and lands under Saved Reports in its app. "
		"Dashboards are under One › Dashboards; reports by mail under Workspace › Reports by Mail, set from a report's "
		"menu (Setup Auto Email). How is in One's documentation under Reports and dashboards (how_to).",
	}


def recycle_bin(
	days: Annotated[int, "How many days back to look, 30 if not said."] = 30,
) -> dict:
	"""The Recycle Bin as the reader sees it: what was deleted in the last days,
	of which kind, by whom and when, and whether it has been put back. Everybody
	sees what they deleted; an administrator also what others deleted, of what
	they may read."""
	since = frappe.utils.add_days(frappe.utils.now_datetime(), -max(1, min(int(days or 30), 365)))
	rows = frappe.get_list(
		"Deleted Document",
		filters={"creation": [">=", since]},
		fields=["name", "deleted_doctype", "deleted_name", "owner", "creation", "restored", "new_name"],
		order_by="creation desc",
		limit=100,
	)
	return {
		"deleted": [
			{
				"kind": one.deleted_doctype,
				"record": one.deleted_name,
				"deleted_by": one.owner,
				"when": str(one.creation),
				"put_back_as": one.new_name if one.restored else None,
				"open": f"/desk/deleted-document/{one.name}",
			}
			for one in rows
		],
		"next": "Restore on a deleted record, or on several ticked in the list, puts them back; how is in One's "
		"documentation under Recycle Bin (how_to).",
	}


def audit_log(
	what: Annotated[str, "changes, sign-ins or exports; changes if not said."] = "changes",
	kind: Annotated[str, "Only changes to, or exports of, this kind of record, such as Item."] | None = None,
	record: Annotated[str, "Only changes to this one record, by its name; give kind too."] | None = None,
	person: Annotated[str, "Only what this person did, by their address."] | None = None,
	days: Annotated[int, "How many days back to look, 7 if not said."] = 7,
) -> dict:
	"""The Audit Log, for a workspace administrator: who changed which record
	and each field from what to what, who signed in from where and whether it
	failed, or who exported or printed what. Only of the kinds of record the
	reader may read, never the system's own."""
	from onedesk.one import audit, roles

	if not roles.administers():
		return {
			"error": "Only a workspace administrator reads the Audit Log; a record's own timeline shows "
			"its changes."
		}
	since = frappe.utils.add_days(frappe.utils.now_datetime(), -max(1, min(int(days or 7), 365)))
	filters = {"creation": [">=", since]}
	if what == "sign-ins":
		if person:
			filters["user"] = person
		rows = frappe.get_list(
			"Activity Log",
			filters=filters,
			fields=["user", "operation", "status", "ip_address", "creation"],
			order_by="creation desc",
			limit=100,
		)
		said = [
			{
				"who": one.user,
				"did": one.operation,
				"failed": one.status != "Success",
				"from": one.ip_address,
				"when": str(one.creation),
			}
			for one in rows
		]
		return {"sign_ins": said, "open": "/desk/activity-log"}
	if what == "exports":
		if person:
			filters["user"] = person
		if kind:
			filters["export_from"] = kind
		rows = frappe.get_list(
			"Access Log",
			filters=filters,
			fields=["user", "export_from", "reference_document", "report_name", "file_type", "creation"],
			order_by="creation desc",
			limit=100,
		)
		said = [
			{
				"who": one.user,
				"kind": one.export_from,
				"record": one.reference_document,
				"report": one.report_name,
				"as": one.file_type,
				"when": str(one.creation),
			}
			for one in rows
		]
		return {"exports": said, "open": "/desk/access-log"}
	if person:
		filters["owner"] = person
	if kind:
		filters["ref_doctype"] = kind
	if record:
		filters["docname"] = record
	rows = frappe.get_list(
		"Version",
		filters=filters,
		fields=["name", "owner", "ref_doctype", "docname", "data", "creation"],
		order_by="creation desc",
		limit=60,
	)
	changes = []
	for one in rows:
		data = audit.seen(one.data, one.ref_doctype)
		meta = frappe.get_meta(one.ref_doctype)
		changes.append(
			{
				"who": one.owner,
				"kind": one.ref_doctype,
				"record": one.docname,
				"when": str(one.creation),
				"fields": [
					{"field": meta.get_label(f) or f, "from": o, "to": n}
					for f, o, n in (data.get("changed") or [])[:12]
				],
				"rows_added": len(data.get("added") or []),
				"rows_removed": len(data.get("removed") or []),
				"rows_changed": len(data.get("row_changed") or []),
				"open": f"/desk/version/{one.name}",
			}
		)
	return {
		"changes": changes,
		"next": "A change opens with every field it changed; Open on its row goes to the record.",
	}


def privacy_request(
	name: Annotated[str, "The request, by its name: a copy's id, or a deletion such as deleted-user-0001@example.com."],
) -> dict:
	"""For a workspace administrator: what a privacy request would give or do,
	without doing it. For a copy, each kind of data and how much of it. For a
	deletion, what approving it would do. What is deleted outright,
	where their name and address are taken out, what is still assigned to
	them, whether they have an employee record (HR's, which stays), and
	anything that stops it (the last administrator, the person billed)."""
	from onedesk.one import privacy, roles

	if not roles.administers():
		return {"error": "Only a workspace administrator decides privacy requests."}
	if frappe.db.exists(privacy.DOWNLOAD, name):
		from onedesk.one import privacy_copy

		return {
			**privacy_copy.review(name),
			"next": "Review and Send on the request: what is about the person always goes; mail, comments, "
			"to-dos, conversations, changes, exports and notifications may be withheld only to protect other "
			"people or the company's confidential information, with a reason the person is told.",
		}
	if not frappe.db.exists(privacy.DELETION, name):
		return {"error": f"There is no request {name}."}
	return {
		**privacy.preview(name),
		"next": "Approve and Delete, or Hold with a reason, on the request; how is in One's documentation "
		"under Privacy Requests (how_to).",
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
		# Who may close the workspace or take everything, whether it is
		# closing, and the full download (one/closing.py).
		"closing": said["closing"],
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
	its letter heads (which is the default, which are off, and each one's header
	and footer as they are now: the preset each is drawn from and what it shows,
	or the HTML or picture it was written as), the presets to choose from, the
	logo Workspace > General keeps, the print formats the workspace made, and for
	a kind of record the formats it may print with and the one it prints with
	unless another is chosen. Read it before suggesting a change."""
	from onedesk.one import letter_heads, printing, roles, settings

	if not roles.administers():
		return {"error": "Only a workspace administrator sees how documents are printed."}
	try:
		company = settings._company()
		said = {
			"letter_heads": [
				{
					**{key: one.get(key) for key in ("name", "is_default", "disabled", "standard")},
					"header": _letter_head_part(one, "header"),
					"footer": _letter_head_part(one, "footer"),
				}
				for one in printing.letter_heads()
			],
			"presets": {
				"header": {key: str(label) for key, label in letter_heads.PRESETS.items()},
				"footer": {
					**{key: str(label) for key, label in letter_heads.FEET.items()},
					"none": "None",
				},
				"header_shows": list(letter_heads.SHOWN),
				"footer_shows": [*letter_heads.FOOT_SHOWN, *letter_heads.SHOWN],
			},
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


#: A picture held inline in a letter head's HTML, shown to OneAI by what it is.
INLINE_PICTURE = re.compile(r'src="data:image/[^"]+"')


def _letter_head_part(one: dict, part: str) -> dict | None:
	"""A letter head's header or footer as it is now: the preset it is drawn from
	and its settings, or the HTML or picture it was written as. None for a
	letter head with no footer."""
	from onedesk.one import letter_heads

	top = part == "header"
	drawn = one.get("one_top" if top else "one_foot")
	if drawn:
		said = letter_heads.settings(drawn) if top else letter_heads.foot_settings(drawn)
		presets = letter_heads.PRESETS if top else letter_heads.FEET
		return {"drawn_from": said["preset"], "called": str(presets[said["preset"]]), "settings": said}
	source = one.get("source" if top else "footer_source") or "Image"
	html = one.get("content" if top else "footer")
	picture = one.get("image" if top else "footer_image")
	if source == "HTML" and (html or "").strip():
		# Inline pictures (the icons) are long and say nothing to read; [icon:name]
		# puts one back.
		return {"written_in": "HTML", "html": INLINE_PICTURE.sub('src="[inline picture]"', html)[:4000]}
	if picture:
		return {"picture": picture}
	return None


def change_printing(
	doctype: Annotated[str, "The kind of record whose default format changes, such as Sales Invoice."]
	| None = None,
	default_format: Annotated[
		str, "The format that kind prints with unless another is chosen: one of its formats."
	]
	| None = None,
	letter_head: Annotated[
		dict,
		"A letter head to make or change: {name} of an existing one (read workspace_printing first: it "
		"gives each one's header and footer as they are now), or {new_name} for a new one. The header: "
		"{preset}, one of workspace_printing's header presets, drawn from the company's details in "
		"Workspace > General, with {show} (a list of its header_shows), {logo_height} in pixels, {align} "
		"for Logo Only, and {line} 0 to leave out the line in the Brand Colour under it; this is what to "
		"suggest first. The footer: {foot}, an object with {preset} (one of its footer presets, or none "
		"for no footer), {show} (its footer_shows, logo included), {note} (a short line of their own, "
		"such as a thank-you; empty for none) and {line}. On a letter head that is there, give only what "
		"changes: the rest stays as it is, and the preset may be left out when its header or footer is "
		"already drawn from one. Or {logo}, 'company' for the logo Workspace > General keeps or a file "
		"URL the workspace already has; or {top_html} and {foot_html}, the header and footer written in "
		"plain HTML with inline styles (no template tags, no scripts, pictures only from this workspace's "
		"files), from the company's details workspace_printing gives, where [icon:phone] (any Lucide "
		"name: map-pin, mail, globe, receipt...) draws that icon in the Brand Colour. The page number is "
		"the print format's own, never the footer's. {default} true to make it the one printed unless "
		"another is chosen; {off} true to turn it off.",
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
			# A change to a letter head that is there is made to what it is now: the
			# settings named change, the rest stay as they are.
			was = (
				frappe.db.get_value("Letter Head", name, ["one_top", "one_foot"], as_dict=True)
				if name
				else frappe._dict()
			)
			top_said = {key: letter_head[key] for key in letter_heads.TOP_KEYS if key in letter_head}
			preset = top_said.get("preset")
			if preset and preset not in letter_heads.PRESETS:
				return {"error": f"{preset} is not a header preset; they are {', '.join(letter_heads.PRESETS)}."}
			if top_said and not preset and not was.one_top:
				return {
					"error": "Its header is not drawn from a preset (it is a picture or written by hand); "
					"give a preset to draw one, or top_html to write it."
				}
			foot_said = letter_head.get("foot") if isinstance(letter_head.get("foot"), dict) else None
			no_foot = bool(foot_said) and foot_said.get("preset") == "none"
			if foot_said and not no_foot:
				if foot_said.get("preset") and foot_said["preset"] not in letter_heads.FEET:
					return {
						"error": f"The footer's preset is one of {', '.join(letter_heads.FEET)}, or none."
					}
				if not foot_said.get("preset") and not was.one_foot:
					return {
						"error": "Its footer is not drawn from a preset; give a preset to draw one, "
						"or foot_html to write it."
					}
			if not name and not (letter_head.get("new_name") and (logo or top or preset)):
				return {"error": "A new letter head needs new_name, and a preset, a logo or top_html."}
			head = {"name": name}
			if not name:
				head["letter_head_name"] = letter_head["new_name"].strip()
				summary.append({"label": _("New Letter Head"), "value": head["letter_head_name"]})
			if top_said:
				before = letter_heads.settings(was.one_top) if was.one_top else None
				after = letter_heads.settings({**(before or {}), **top_said})
				if after != before:
					head["one_top"] = after
					head["source"] = "HTML"
					head["content"] = letter_heads.draw(after)
					summary.append({"label": _("Header"), "value": str(letter_heads.PRESETS[after["preset"]])})
			if logo and not top and not top_said:
				head["source"] = "Image"
				head["image"] = logo
				summary.append({"label": _("Logo"), "value": logo.rsplit("/", 1)[-1].split("?")[0]})
			if top:
				head["source"] = "HTML"
				head["content"] = print_html.letter_head_html(top, _("Header"))
				summary.append({"label": _("Header"), "value": _("Designed in HTML")})
			if no_foot and (was.one_foot or name is None or frappe.db.get_value("Letter Head", name, "footer")):
				head["one_foot"] = None
				head["footer_source"] = "HTML"
				head["footer"] = ""
				summary.append({"label": _("Footer"), "value": _("None")})
			elif foot_said and not no_foot:
				before = letter_heads.foot_settings(was.one_foot) if was.one_foot else None
				after = letter_heads.foot_settings({**(before or {}), **foot_said})
				if after != before:
					head["one_foot"] = after
					head["footer_source"] = "HTML"
					head["footer"] = letter_heads.draw_foot(after)
					summary.append({"label": _("Footer"), "value": str(letter_heads.FEET[after["preset"]])})
			if foot and not foot_said:
				head["footer_source"] = "HTML"
				head["footer"] = print_html.letter_head_html(foot, _("Footer"))
				summary.append({"label": _("Footer"), "value": _("Designed in HTML")})
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
	"{label, columns, keep_together, labels_beside} (label prints above it; keep_together keeps it on one "
	"page; labels_beside prints every field's label on its line, beside the value, as totals read). A column "
	"is a list of blocks, top to bottom, or {width, blocks} to give it its share of the section (widths are "
	"shares, such as 55 and 45). A block is: a fieldname of the record, printed as its label above its "
	"value; or {field, label, show_label: false|'inline', align: left|center|right, bold, show_empty, "
	"spread} for one printed another way (spread, in a labels_beside section, puts the label at the "
	"column's left edge and the value at its right); '---' for a line; {table: fieldname, columns: "
	"['item_name:45', 'qty:15', 'rate:20:Price', 'amount:20'], bordered, striped, show_label} for a table, "
	"lined between rows unless bordered (boxed) or striped, its label printed above only with show_label, "
	"each column a field of its rows with its share of the width (together at most 100) and, if it should "
	"read differently, its heading; {text: '...', align, bold} for fixed words; {space: 12} for room; "
	"{barcode: fieldname or '' with value, format: QR|CODE128|CODE39}; {image: url} for a file of this "
	"workspace; {linked: 'customer.customer_group'} for a field of the record a link field points at; "
	"{repeater: 'items', repeater_columns: [{template: [{t: 'f', v: 'item_name'}, {t: 's', v: ' x '}], "
	"width, align}]} for a table of rows written your own way; {divider: true}; or {html: '...'}. "
	"An empty column is []. heading is the title at the top in the same HTML, frappe's own when left out. "
	"An html block or heading is Jinja over this one record and nothing else: {{ doc.fieldname }}, "
	"{{ doc.get('fieldname') }}, {{ doc.get_formatted('grand_total') }} (a value as the form shows it, "
	"with its currency), {% for row in doc.items %}{{ row.item_name }} {{ row.get_formatted('amount') "
	"}}{% endfor %} with loop.index, loop.first and loop.last, {% if %}/{% elif %}/{% else %}, {% set x = "
	"... %}, arithmetic and comparisons, _('text') to translate, the tests defined, undefined, none, number, string, "
	"odd, even, divisibleby, eq, ne, lt, gt, le, ge and in, and only the filters abs, capitalize, center, "
	"count, default, escape, first, float, format, int, join, last, length, lower, replace, reverse, "
	"round, sort, string, striptags, sum, title, trim, truncate, upper and wordcount. Nothing else is "
	"there: no frappe, no frappe.db or get_all, no other record, no macros, includes or imports, no "
	"|safe, and no names that start with _; values are escaped, and scripts, forms and outside pictures "
	"are taken out. For a value from another record, print the field that links to it. How it should "
	"look: start from print_layout's starting_layout (or the format being changed) and change only what "
	"was asked. Unless they ask for a look of their own, it prints in the house style, frappe's print "
	"style spaced and toned as frappe-ui draws a page, so leave css out. When they do ask for a look (a "
	"colour, a font, a feel), write it as css over frappe's classes (.print-format-doc, .print-heading, "
	".section, .section-label, .field, .field .label, .field .value, .child-table .table th and td, "
	"[data-fieldname=...]) and it replaces the house style; with house_style true it is added over the "
	"house style instead, for a change to it. Their taste wins over the house's. The party and its "
	"address go on the left and the dates and references on the right; the items are one table, the "
	"description widest and the figures narrower; the totals sit under it on the right, in a "
	"labels_beside section with spread fields, and the amount in words on the left; terms and notes come "
	"last, each in a labelled section. The letter head already prints the company, so the body does not "
	"repeat it. A field frappe's own formats leave off the page says not printed; print it only when "
	"asked. Build it in this order, so the person can go on changing it in the builder: first the "
	"builder's own blocks, which cover most of any page; then, for a part they cannot draw (a stamp, a "
	"grid of terms, a figure worked out from the rows), one html block in its place among them; and "
	"only for a page designed from end to end, one html block across the whole body, with css. Never "
	"html for what a block already prints. In an html block the record's own number is doc.name, never "
	"its naming_series, and a figure, a date or a quantity is printed through get_formatted, never as "
	"the raw value."
)


def _how() -> str:
	"""LAYOUT_HELP, with every property of frappe's builder a block, a table, a
	section or the page may take by its own name, and the house's parts for
	an html block."""
	from onedesk.one import print_props, print_recipes

	return (
		f"{LAYOUT_HELP} {print_props.described()} Any of these may be set on the block, section, column or "
		"table column they belong to, beside the shorter words above; frappe's builder shows every one "
		"of them, so the person can go on changing them there. Whatever a property sets (a table's "
		"header colour is table_header_bg, a field's colour value_color, a section's background "
		"background) is set by the property, never by css, which frappe's own print style overrides. "
		"An html block in the house style is "
		f"built of the house's own classes and nothing else: {print_recipes.HOUSE_PARTS}. A look of "
		"their own writes its own classes in css instead."
	)

#: What a block may say about itself beyond what it is, in the shorter words a
#: model may write; any of frappe's own (print_props) may be written as well.
FIELD_OPTIONS = ("label", "show_label", "align", "bold", "show_empty", "spread")
ALIGN = ("left", "center", "right")

#: The words a block is made of, rather than frappe's properties of it.
SHORT = {"field", "fieldname", "table", "columns", "bordered", "striped", "html", "text", "space", "image"}
SHORT |= {"barcode", "format", "spread", "linked", "repeater", "divider", "value"}

NOT_A_BLOCK = (
	"A block is a fieldname, '---', or one of table, text, space, barcode, image, linked, repeater, divider "
	"or html."
)


def _block(one) -> dict:
	"""One block as a model writes it, as the builder stores it: the shorter
	words below, and any of frappe's own properties of that kind of block by
	their own names (print_props), each checked."""
	from onedesk.one import print_props

	if isinstance(one, str):
		return {"fieldtype": "Divider"} if one.strip("- ") == "" else {"fieldname": one.strip()}
	if not isinstance(one, dict):
		frappe.throw(_(NOT_A_BLOCK))
	if one.get("columns") and not one.get("table") and (one.get("field") or one.get("fieldname")):
		# {field: 'items', columns: [...]} can only mean the table.
		one = {**one, "table": one.get("field") or one.get("fieldname")}
	if one.get("columns") and not one.get("table"):
		frappe.throw(_("A table block names its table: {table: 'items', columns: ['item_name:45', 'qty:15']}."))
	where = str(one.get("table") or one.get("field") or one.get("fieldname") or "")
	if one.get("table"):
		columns = []
		for column in one.get("columns") or []:
			fieldname, _sep, rest = _column(column).partition(":")
			width, _sep, label = rest.partition(":")
			columns.append(
				{
					"fieldname": fieldname.strip(),
					**({"width": _share(width)} if _share(width) else {}),
					**({"label": label.strip()} if label.strip() else {}),
					**(
						print_props.taken(
							column, print_props.TABLE_COLUMN, f"{where}.{fieldname.strip()}", ours=SHORT
						)
						if isinstance(column, dict)
						else {}
					),
				}
			)
		if not columns:
			frappe.throw(_("The table {0} needs its columns.").format(one["table"]))
		return {
			"fieldname": one["table"],
			"table_columns": columns,
			# As frappe's own formats print a table: its columns say what it is.
			**({} if one.get("show_label") else {"show_label": "hide"}),
			# Lined unless boxed or striped is asked for; frappe boxes a table
			# unless told not to.
			"table_bordered": 1 if one.get("bordered") else 0,
			**({"table_style": "striped"} if one.get("striped") else {}),
			**print_props.taken(
				{key: value for key, value in one.items() if key != "show_label" or value in ("show", "hide")},
				print_props.TABLE,
				where,
				ours=SHORT,
			),
		}
	own = lambda kind: print_props.taken(one, print_props.BLOCKS[kind], kind, ours=SHORT)  # noqa: E731
	if "html" in one:
		return {"fieldtype": "HTML", "html": str(one["html"]), **own("HTML")}
	if "text" in one:
		return {"fieldtype": "Static Text", "text": str(one["text"]), **own("Static Text")}
	if "space" in one:
		return {"fieldtype": "Spacer", "height": frappe.utils.cint(one["space"]) or 10, **own("Spacer")}
	if one.get("divider"):
		return {"fieldtype": "Divider", **own("Divider")}
	if "image" in one:
		return {"fieldtype": "Image", "image_url": str(one["image"]), **own("Image")}
	if "barcode" in one:
		kind = str(one.get("format") or one.get("barcode_format") or "CODE128").upper()
		return {
			"fieldtype": "Barcode",
			"barcode_field": str(one.get("barcode") or ""),
			**({"barcode_value": str(one["value"])} if one.get("value") else {}),
			**own("Barcode"),
			"barcode_format": print_props.taken({"barcode_format": kind}, print_props.BLOCKS["Barcode"], "barcode")[
				"barcode_format"
			],
		}
	if one.get("linked"):
		return {"fieldtype": "Linked Field", "link_path": str(one["linked"]), **own("Linked Field")}
	if one.get("repeater"):
		return {"fieldtype": "Repeater", "source": str(one["repeater"]), **own("Repeater")}
	fieldname = one.get("field") or one.get("fieldname")
	if fieldname:
		name = str(fieldname).strip()
		block = {
			"fieldname": name,
			**print_props.taken(
				{key: value for key, value in one.items() if key not in ("show_label", "spread")},
				print_props.FIELD,
				name,
				ours=SHORT,
			),
		}
		if one.get("spread"):
			# Label at the left edge and value at the right, in a section whose
			# labels sit beside their values.
			block["label_justify"] = "space-between"
		# frappe's word for it: show, hide, or inline (beside the value).
		said = one.get("show_label")
		if said in ("inline", "show"):
			block["show_label"] = said
		elif said in (False, 0, "hide", "false"):
			block["show_label"] = "hide"
		return block
	frappe.throw(_(NOT_A_BLOCK))


def _parsed(text: str):
	"""Sections written as JSON text, or as the Python a model sometimes writes
	instead: True, False and None outside a string are JSON's words for them."""
	try:
		return json.loads(text)
	except ValueError:
		pass
	# A line break written into a string as it is, and a backslash before a
	# character JSON does not escape (an html block's own), are what a model
	# writes by hand: taken as the characters it meant.
	loose = json.JSONDecoder(strict=False)
	text = re.sub(r"\\(.)", lambda m: m[0] if m[1] in '"\\/bfnrtu' else "\\\\" + m[1], text, flags=re.S)
	try:
		# The sections and then something after them: the sections.
		return loose.raw_decode(text.strip())[0]
	except ValueError:
		pass
	# Outside strings only: split on quoted runs and mend the pieces between.
	parts = re.split(r'("(?:[^"\\]|\\.)*")', text)
	mended = "".join(
		part
		if n % 2
		else re.sub(r"\bTrue\b", "true", re.sub(r"\bFalse\b", "false", re.sub(r"\bNone\b", "null", part)))
		for n, part in enumerate(parts)
	)
	try:
		return loose.raw_decode(mended.strip())[0]
	except ValueError as e:
		frappe.throw(_("sections is not JSON: {0}.").format(str(e)))


def _share(value) -> int:
	"""A width as a share of the page: 45, "45" and "45%" alike."""
	return frappe.utils.cint(str(value or "").strip().rstrip("%").strip())


def _column(column) -> str:
	"""A table column as 'fieldname:width:Heading', however it was written:
	{field: 'qty', width: 15, label: 'Qty'} is the same column spelled out."""
	if not isinstance(column, dict):
		return str(column)
	fieldname, _sep, rest = str(column.get("field") or column.get("fieldname") or "").partition(":")
	width, _sep, label = rest.partition(":")
	width = str(_share(column.get("width") or width) or "")
	label = str(column.get("label") or label)
	return ":".join((fieldname, width, label)).rstrip(":")


def _linked(meta, path: str) -> list[str]:
	"""What is wrong with a linked field's path: one hop, a Link of this kind
	to a field of the kind it links to."""
	link, _sep, target = path.partition(".")
	field = meta.get_field(link)
	if not field or field.fieldtype != "Link" or not target:
		return [_("{0} is not a link field and one of its fields, such as customer.customer_group").format(path)]
	if not frappe.get_meta(field.options).has_field(target):
		return [_("{0} has no field {1}").format(field.options, target)]
	return []


def _repeated(meta, block: dict) -> list[str]:
	"""What is wrong with a repeater: its source a table of this kind, and every
	field its columns print a field of that table's rows."""
	source = meta.get_field(block.get("source"))
	if not source or source.fieldtype not in frappe.model.table_fields:
		return [_("{0} is not a table to repeat").format(block.get("source"))]
	rows = frappe.get_meta(source.options)
	return [
		_("{0} has no field {1}").format(source.options, part["v"])
		for column in block.get("repeater_columns") or []
		for part in column.get("template") or []
		if part.get("t") == "f" and not rows.has_field(part["v"])
	]


def _paired(column: list) -> list:
	"""A column as a model meant it: a table's fieldname written just before
	its columns, as "items", {"columns": [...]}, is that table once."""
	out = []
	for one in column:
		before = out[-1] if out else None
		if isinstance(one, dict) and one.get("columns") and isinstance(before, str):
			if one.get("table") in (None, before.strip()):
				out[-1] = {**one, "table": before.strip()}
				continue
		out.append(one)
	return out


def _built(sections, heading: str | None, doctype: str | None = None) -> dict:
	"""The builder's layout from sections as a model writes them, checked for
	what would print badly: an empty section, a table without columns or wider
	than the page, a field that is not a table given columns, a barcode of a
	field the kind does not have."""
	from frappe.printing.doctype.print_format.classic_converter import DEFAULT_PRINT_HEADING

	from onedesk.one import print_props, print_recipes

	if isinstance(sections, str):
		sections = _parsed(sections)
	if not isinstance(sections, list) or not sections:
		frappe.throw(_("sections is a list of sections, each a list of columns."))
	meta = frappe.get_meta(doctype) if doctype else None
	problems = []
	built = []
	for n, section in enumerate(sections, 1):
		label, keep, beside, props = "", False, False, {}
		if isinstance(section, dict):
			label, keep, beside = (
				section.get("label") or "",
				section.get("keep_together"),
				section.get("labels_beside"),
			)
			props = print_props.taken(
				section,
				print_props.SECTION,
				_("section {0}").format(label or n),
				ours={"label", "columns", "keep_together", "labels_beside"},
			)
			section = section.get("columns") or []
		if not isinstance(section, list):
			frappe.throw(_("A section is a list of columns, each a list of blocks."))
		widths = []
		columns = []
		for column in section:
			if isinstance(column, dict) and "blocks" in column:
				print_props.taken(column, print_props.COLUMN, _("a column"), ours={"blocks"})
				widths.append(_share(column.get("width")))
				column = column["blocks"]
			else:
				widths.append(0)
			columns.append(column if isinstance(column, list) else [column])
		blocks = [[_block(b) for b in _paired(c)] for c in columns]
		if not any(blocks):
			problems.append(_("section {0} is empty").format(label or n))
		for column in blocks:
			for block in column:
				if meta and block.get("table_columns"):
					field = meta.get_field(block["fieldname"])
					if field and field.fieldtype not in frappe.model.table_fields:
						problems.append(_("{0} is not a table").format(block["fieldname"]))
					width = sum(frappe.utils.cint(c.get("width")) for c in block["table_columns"])
					if width > 100:
						problems.append(
							_("the columns of {0} come to {1}%, more than the page").format(block["fieldname"], width)
						)
				elif meta and block.get("fieldname") and not block.get("fieldtype"):
					field = meta.get_field(block["fieldname"])
					if field and field.fieldtype in frappe.model.table_fields:
						problems.append(_("{0} is a table: give it its columns").format(block["fieldname"]))
				if (
					meta
					and block.get("fieldtype") == "Barcode"
					and block.get("barcode_field") not in ("", "name")
					and not meta.has_field(block["barcode_field"])
				):
					problems.append(_("there is no field {0} for the barcode").format(block["barcode_field"]))
				if meta and block.get("fieldtype") == "Linked Field":
					problems.extend(_linked(meta, block.get("link_path") or ""))
				if meta and block.get("fieldtype") == "Repeater":
					problems.extend(_repeated(meta, block))
		built.append(
			{
				"label": label,
				**({"keep_together": 1} if keep else {}),
				**({"field_orientation": "left-right"} if beside else {}),
				**props,
				"columns": [
					{"label": "", "fields": column, **({"width": width} if width else {})}
					for column, width in zip(blocks, widths, strict=True)
				],
			}
		)
	if doctype:
		printed = {
			block.get("fieldname") for section in built for c in section["columns"] for block in c["fields"]
		}
		written = " ".join(
			str(block.get("html") or block.get("text") or "")
			for section in built
			for c in section["columns"]
			for block in c["fields"]
		) + str(heading or "")
		missing = [one for one in print_recipes.essentials(doctype) if one not in printed and one not in written]
		if missing:
			problems.append(_("it does not print {0}").format(", ".join(missing)))
	if problems:
		frappe.throw(_("The layout would print badly: {0}.").format("; ".join(problems)))
	top = heading or DEFAULT_PRINT_HEADING
	return {
		"header": {"columns": [{"label": "", "fields": [{"fieldtype": "HTML", "label": "", "html": top}]}]},
		"sections": built,
		"footer": {"columns": [{"label": "", "fields": []}]},
	}


def _written(layout, meta=None) -> dict | None:
	"""A builder layout as a model writes one (_built's inverse): its sections,
	and its heading when it is not frappe's own."""
	from frappe.printing.doctype.print_format.classic_converter import DEFAULT_PRINT_HEADING

	if not isinstance(layout, dict):
		return None

	from onedesk.one import print_props

	def block(one: dict):
		kind = one.get("fieldtype")
		if one.get("table_columns"):
			rows = frappe.get_meta(one["options"]) if one.get("options") else None

			def column(c):
				said = [c.get("fieldname"), str(c.get("width") or "")]
				own = rows.get_field(c.get("fieldname")) if rows else None
				if c.get("label") and own and c["label"] != own.label:
					said.append(c["label"])
				written = ":".join(said).rstrip(":")
				more = print_props.stored(c, print_props.TABLE_COLUMN, left=("label", "width"))
				return {"field": written, **more} if more else written

			return {
				"table": one.get("fieldname"),
				"columns": [column(c) for c in one["table_columns"]],
				**({"bordered": True} if one.get("table_bordered") not in (0, False) else {}),
				**({"striped": True} if one.get("table_style") == "striped" else {}),
				**({"show_label": True} if one.get("show_label") not in (None, "hide") else {}),
				**print_props.stored(
					one, print_props.TABLE, left=("label", "show_label", "table_bordered", "table_style")
				),
			}
		more = print_props.stored(one, print_props.BLOCKS.get(kind) or {})
		if kind == "HTML":
			return {"html": one.get("html") or "", **more}
		if kind == "Static Text":
			return {"text": one.get("text") or "", **more}
		if kind == "Divider":
			return {"divider": True, **more} if more else "---"
		if kind == "Spacer":
			return {"space": one.get("height") or 10, **print_props.stored(one, print_props.BLOCKS[kind], ("height",))}
		if kind == "Image":
			return {"image": one.get("image_url") or "", **more}
		if kind == "Barcode":
			return {
				"barcode": one.get("barcode_field") or "",
				"format": one.get("barcode_format") or "CODE128",
				**({"value": one["barcode_value"]} if one.get("barcode_value") else {}),
				**print_props.stored(one, print_props.BLOCKS[kind], ("barcode_format", "barcode_value")),
			}
		if kind == "Linked Field":
			return {"linked": one.get("link_path") or "", **more}
		if kind == "Repeater":
			return {"repeater": one.get("source") or "", **more}
		own = meta.get_field(one.get("fieldname")) if meta and one.get("fieldname") else None
		options = print_props.stored(one, print_props.FIELD, left=("label", "show_label", "label_justify"))
		if one.get("show_label") == "hide":
			options["show_label"] = False
		elif one.get("show_label") == "inline":
			options["show_label"] = "inline"
		if own and one.get("label") and one["label"] != own.label:
			options["label"] = one["label"]
		if one.get("label_justify") == "space-between":
			options["spread"] = True
		elif one.get("label_justify"):
			options["label_justify"] = one["label_justify"]
		return {"field": one.get("fieldname"), **options} if options else one.get("fieldname")

	sections = []
	for section in layout.get("sections") or []:
		columns = []
		for column in section.get("columns") or []:
			said = [
				b for b in (block(one) for one in column.get("fields") or [] if isinstance(one, dict)) if b
			]
			columns.append({"width": column["width"], "blocks": said} if column.get("width") else said)
		if any(one.get("blocks") if isinstance(one, dict) else one for one in columns):
			beside = section.get("field_orientation") == "left-right"
			more = print_props.stored(
				section, print_props.SECTION, left=("label", "keep_together", "field_orientation")
			)
			if section.get("label") or section.get("keep_together") or beside or more:
				sections.append(
					{
						"label": section.get("label") or "",
						"columns": columns,
						**({"keep_together": True} if section.get("keep_together") else {}),
						**({"labels_beside": True} if beside else {}),
						**more,
					}
				)
			else:
				sections.append(columns)
	top = [
		one.get("html")
		for column in (layout.get("header") or {}).get("columns") or []
		for one in column.get("fields") or []
		if one.get("fieldtype") == "HTML"
	]
	heading = top[0] if top and top[0] != DEFAULT_PRINT_HEADING else None
	return {"sections": sections, **({"heading": heading} if heading else {})}


def _laid_out(doctype: str, sections, heading: str | None, existing) -> dict:
	"""The layout a design prints: the sections given; without them, a changed
	format's own layout as the builder left it (a restyle changes only its
	css), or a new one's starting layout."""
	from onedesk.one import print_recipes

	if sections:
		return _built(sections, heading, doctype)
	if existing and existing.format_data:
		if not heading:
			return json.loads(existing.format_data)
		written = _written(json.loads(existing.format_data), frappe.get_meta(doctype))
		return _built(written["sections"], heading, doctype)
	return _built(print_recipes.starting_layout(doctype), heading, doctype)


def _redo(doctype: str, error: str) -> dict:
	"""A design that did not hold, handed back with what to start again from,
	so a model that skipped print_layout, or wrote a block wrong, mends it in
	the next round rather than telling the person what went wrong inside."""
	from onedesk.one import print_recipes

	try:
		start = print_recipes.starting_layout(doctype)
	except (frappe.ValidationError, frappe.PermissionError, frappe.DoesNotExistError):
		frappe.clear_last_message()
		start = None
	return {
		"error": error,
		"mend": "design_print_format",
		"next": "Mend the sections and call design_print_format again; this is for you, not for them. Start "
		"from starting_layout and change only what they asked, or leave sections out for the starting "
		"layout as it is. When they asked for a look rather than a layout, leave sections out and send only "
		"css (over the classes css names) and font.",
		**({"starting_layout": start} if start else {}),
		"how": _how(),
	}


def _styled(css: str | None, house: bool | None, before: str | None) -> str | None:
	"""The css a format prints with: the house style unless a look was asked
	for, that look alone, or the house style with it over the top. A changed
	format left without css keeps its own."""
	from onedesk.one.print_recipes import HOUSE_CSS

	css = (css or "").strip()
	if house:
		return f"{HOUSE_CSS}\n{css}" if css else HOUSE_CSS
	if css:
		return css
	return before if before is not None else HOUSE_CSS


def _style_of(css: str | None) -> dict:
	"""A format's css as print_layout tells it: whether it is the house style,
	and whatever it carries beyond it."""
	from onedesk.one.print_recipes import HOUSE_CSS

	css = css or ""
	if css.startswith(HOUSE_CSS):
		return {"house_style": True, "css": css[len(HOUSE_CSS) :].strip() or None}
	return {"house_style": False, "css": css or None}


def print_layout(
	doctype: Annotated[str, "The kind of record, such as Sales Invoice."],
	print_format: Annotated[str, "A format of that kind to start from; its default when left out."] | None = None,
) -> dict:
	"""A kind of record's fields, the layout a format of it starts from, and one
	of its builder formats as sections, the way design_print_format takes them:
	read it before designing one. Workspace administrators only."""
	from onedesk.one import print_recipes, printing, roles
	from onedesk.one_ai import kind

	if not roles.administers():
		return {"error": "Only a workspace administrator designs how documents are printed."}
	try:
		printing._doctype(doctype)
		meta = frappe.get_meta(doctype)
		name = print_format or next(iter(printing.starts(doctype)), frappe._dict()).get("name")
		held = (
			frappe.db.get_value("Print Format", name, ["doc_type", "format_data", "css", "page_number", "font"], as_dict=True)
			if name
			else None
		)
		if held and held.doc_type != doctype:
			return {"error": f"{name} is not a format of {doctype}."}
		return {
			"doctype": doctype,
			# Every field and its type, each table's with its rows, as OneAI and
			# Intake read a kind: the same describer, told it is for a page.
			"fields": kind.fields(meta, printing=True),
			"starting_layout": print_recipes.starting_layout(doctype),
			"format": name,
			"written": _written(json.loads(held.format_data), meta) if held and held.format_data else None,
			**(_style_of(held.css) if held else {"house_style": True, "css": None}),
			"page_number": held.page_number if held else None,
			"font": held.font if held else None,
			"how": _how(),
		}
	except (frappe.ValidationError, frappe.PermissionError) as e:
		frappe.clear_last_message()
		return {"error": str(e)}


def design_print_format(
	doctype: Annotated[str, "The kind of record the format prints, such as Sales Invoice."],
	name: Annotated[str, "The format's name: a new one, or one of the workspace's own formats to change."],
	sections: Annotated[
		str,
		"The sections as JSON text, top to bottom: each a list of columns, each a list of blocks, as "
		"print_layout's how says: its starting_layout with only what they asked changed. Leave out to "
		"print the starting layout as it is, which is what a plain request for a good format wants, or, "
		"changing a format, to keep its layout and change only its look.",
	]
	| None = None,
	heading: Annotated[str, "The title at the top, as an HTML template of the record; frappe's own if left out."]
	| None = None,
	css: Annotated[
		str,
		"Leave out for the house style (a changed format keeps its own). Only for a look they asked for: "
		"css that replaces the house style, written over frappe's print classes and nothing else: "
		".print-format-doc (the page), .print-heading h2 and .print-heading .sub-heading (the title), "
		".section, .section-label, .field .label, .field .value, .child-table .table th, .child-table "
		".table td, .child-table .table tr.even td (every other row), and .field[data-fieldname=grand_total] "
		"for one field. No imports or outside URLs; a typeface is font.",
	]
	| None = None,
	font: Annotated[
		str,
		"A Google Font the whole page prints in, by its name, such as Playfair Display or Lora, when they "
		"ask for a typeface; frappe's own Inter when left out.",
	]
	| None = None,
	page: Annotated[
		dict,
		"The page's own settings, when they ask: font_size (the body, in pixels), margin_top, "
		"margin_bottom, margin_left, margin_right (in millimetres), show_label_colon, label_color and "
		"value_color (#rrggbb). Leave out to keep them.",
	]
	| None = None,
	house_style: Annotated[
		bool,
		"True to print in the house style with css added over it, for a change to the house look rather "
		"than a look of their own.",
	]
	| None = None,
	page_number: Annotated[
		str,
		"Where the page number prints on every page: Hide, Top Left, Top Center, Top Right, Bottom Left, "
		"Bottom Center or Bottom Right. Leave out to keep the format's own.",
	]
	| None = None,
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
		existing = frappe.db.get_value(
			"Print Format", name, ["standard", "doc_type", "css", "format_data"], as_dict=True
		)
		if existing and (existing.standard == "Yes" or existing.doc_type != doctype):
			return {"error": f"{name} is not a format of {doctype} this workspace made; choose another name."}
		doc = printing.format_doc(
			doctype,
			name,
			_laid_out(doctype, sections, heading, existing),
			_styled(css, house_style, (existing.css or "") if existing else None),
			letter_head,
			page_number,
			font,
			page,
		)
	except (frappe.ValidationError, frappe.PermissionError) as e:
		frappe.clear_last_message()
		return _redo(doctype, str(e))
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
				"format": {
					"doctype": doctype,
					"name": name,
					"format_data": doc.format_data,
					"css": doc.css,
					**({"page_number": doc.page_number} if page_number else {}),
					**({"font": doc.font} if font else {}),
					**({"page": page} if page else {}),
				},
				"default_format": name if make_default else None,
				"summary": summary,
			},
			why=why,
		),
		"state": "Proposed",
		"next": "Tell them See the Page on the card shows it on their latest record, and that once approved "
		"it opens in the print format builder from the record's Settings > Print Formats.",
	}



# ------------------------------------------------------------------ mail templates

#: What a template may say, for the model: the same words the editor's help gives.
TEMPLATE_HELP = (
	"A template is a subject and a message. Name a field of the record in double braces, bare, as "
	"{{ customer_name }} or {{ due_date }}: never {{ doc.customer_name }}, which frappe's composer, the leave "
	"mails and the salary slip all fail on. Nothing else in braces: no conditions, loops or filters. The "
	"message is plain sentences, a blank line between paragraphs. It ends with a closing line such as Kind "
	"regards and no name under it: the mailbox it is sent from signs it. Read workspace_mail_templates with "
	"the kind of record first, for the fields it may name."
)


def workspace_mail_templates(
	doctype: Annotated[str, "A kind of record, such as Sales Invoice, to also read the fields a template may name."]
	| None = None,
) -> dict:
	"""The workspace's mail templates, for its administrators: each one's
	subject and message as written, the kind of record it is for (none: any
	record), which kinds start the composer with it, and which setting sends
	it (the leave mails, the interview reminders). For a kind of record, the
	fields a template for it may name. Read it before suggesting one."""
	from onedesk.one import mail_templates, roles, rules

	if not roles.administers():
		return {"error": "Only a workspace administrator sees the mail templates."}
	named_by = {}
	for single, field, _kind in mail_templates.NAMED_BY:
		if frappe.db.exists("DocType", single):
			template = frappe.db.get_single_value(single, field)
			if template:
				named_by.setdefault(template, []).append(f"{_(single)}: {frappe.get_meta(single).get_label(field)}")
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
	name: Annotated[str, "An existing template to change, as workspace_mail_templates names it."] | None = None,
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
	from onedesk.one import mail_templates, roles, rules
	from onedesk.one_ai import proposals

	if not roles.administers():
		return {"mend": "write_mail_template", "error": "Only a workspace administrator writes mail templates."}
	if bool(name) == bool(new_name):
		return {"mend": "write_mail_template", "error": "Give name to change a template, or new_name for a new one."}
	held = frappe.get_doc("Email Template", name) if name and frappe.db.exists("Email Template", name) else None
	if name and not held:
		return {"mend": "write_mail_template", "error": f"There is no template {name}; read workspace_mail_templates for them."}
	if new_name and frappe.db.exists("Email Template", new_name.strip()):
		return {"mend": "write_mail_template", "error": f"{new_name} is already a template; change it by its name instead."}
	kind = (for_doctype or "").strip() or (held.reference_doctype if held else None) or None
	try:
		if kind:
			mail_templates._doctype(kind)
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {"mend": "write_mail_template", "error": str(e)}
	# Notification rules name a field as {{ doc.x }}; a template names it bare, and
	# the one is the other, so it is written the way that works.
	subject, message = (re.sub(r"\{\{-?\s*doc\.(\w+)\s*-?\}\}", r"{{ \1 }}", text or "") for text in (subject, message))
	if not kind and mail_templates.FIELD.search(subject + message):
		return {"mend": "write_mail_template", "error": "A template that names fields is for one kind of record: give for_doctype, such as Sales Invoice."}
	kept = mail_templates._tags(held)
	for text in (subject, message):
		wrong = mail_templates.check(kind, text, kept)
		if wrong:
			fields = f" Read workspace_mail_templates with doctype {kind} for the fields it may name." if kind else ""
			return {"mend": "write_mail_template", "error": wrong + fields}
	paragraphs = [one.strip() for one in re.split(r"\n\s*\n", message or "") if one.strip()]
	html = "".join(f"<p>{frappe.utils.escape_html(one).replace(chr(10), '<br>')}</p>" for one in paragraphs)
	changes = {"subject": subject.strip(), "reference_doctype": kind}
	changes["response_html" if held and held.use_html else "response"] = html
	proposal = (
		proposals.propose("Edit", "Email Template", changes=changes, record=held.name, why=why)
		if held
		else proposals.propose("Create", "Email Template", changes={"name": new_name.strip(), **changes}, why=why)
	)
	return {
		"proposal": proposal,
		"state": "Proposed",
		"next": "Tell them it is offered in the composer on "
		+ (f"a {kind}" if kind else "any record")
		+ " and in OneMail once they approve it, and that the record's Settings › Mail Templates makes it the "
		"one the composer starts with.",
	}


# ------------------------------------------------------------------ approvals

#: How an approval is made, for the model.
APPROVAL_HELP = (
	"An approval is the states a kind of record moves through and the steps between them. Each state is "
	"{state, submitted, editable_by, sets}: state a short word such as Pending, Approved or Rejected; "
	"submitted true for a state that submits the record (only for a kind that is submitted), so the "
	"approving step is what submits it; editable_by the role that may change the record in that state; sets "
	"{field, value}, a plain value an ordinary field takes on reaching it. The first state is where a new "
	"record starts. Each step is {from, action, to, by, when}: action a verb such as Approve, Reject or "
	"Send Back; by the role that may take it; when, if any, a condition comparing the record's own fields "
	"with plain values, as doc.grand_total > 5000 (and, or, not, ==, !=, <, >, <=, >=, in). Two steps "
	"with the same action and different when split by amount: Approve by the user role when "
	"doc.grand_total <= 5000, by the manager role when doc.grand_total > 5000. One approval is on per kind "
	"of record. Roles are named by role, as roles gives them. Every record must be able to finish whatever "
	"its values: where a condition splits a step by amount, every amount needs a step out of that state, "
	"and a small record should not be sent to a state only a large one can leave."
)


def workspace_approvals(
	doctype: Annotated[str, "A kind of record, such as Purchase Invoice, to also read what an approval of it may use."]
	| None = None,
) -> dict:
	"""The workspace's approvals, for its administrators: each approval, the
	kind of record it moves, whether it is on, its states and its steps (who
	takes each and when). For a kind of record, whether it is submitted, the
	roles a step may be for, and the fields a condition or a state may use.
	Read it before suggesting an approval."""
	from onedesk.one import approvals, roles

	if not roles.administers():
		return {"error": "Only a workspace administrator sees the approvals."}
	said = {"how_an_approval_is_made": APPROVAL_HELP, "roles": approvals.roles_offered()}
	said["approvals"] = approvals.described()
	if doctype:
		try:
			meta = approvals._doctype(doctype)
		except frappe.ValidationError as e:
			frappe.clear_last_message()
			return {"error": str(e)}
		said["kind"] = {
			"doctype": doctype,
			"submitted": bool(meta.is_submittable),
			"fields": [
				f"{df.fieldname} ({df.label}, {df.fieldtype})"
				for df in meta.fields
				if df.fieldtype in ("Currency", "Float", "Int", "Percent", "Select", "Link", "Data", "Check", "Date")
				and not df.permlevel
				and not df.hidden
			][:80],
		}
	return said


def suggest_approval(
	doctype: Annotated[str, "The kind of record, as its DocType name, such as Purchase Invoice."],
	states: Annotated[list[dict], "Every state, the first where a record starts. " + APPROVAL_HELP],
	steps: Annotated[list[dict], "Every step between states, as {from, action, to, by, when}."],
	name: Annotated[str, "An approval to change, as workspace_approvals names it."] | None = None,
	new_name: Annotated[str, "A new approval's name, such as Bill Approval."] | None = None,
	turn_on: Annotated[bool, "Whether it is on once approved; a kind has one approval on at a time."] = True,
	why: Annotated[str, "In a sentence, what the approval is for."] | None = None,
) -> dict:
	"""Suggest an approval, new or changed, as a card a workspace
	administrator approves: who moves a kind of record from state to state,
	and when. Read workspace_approvals first, with the kind. Nothing changes
	until they approve it, and it opens in the approval builder after.
	Workspace administrators only."""
	from frappe.model import no_value_fields

	from onedesk.one import approvals, roles
	from onedesk.one_ai import proposals

	if not roles.administers():
		return {"mend": "suggest_approval", "error": "Only a workspace administrator sets approvals."}
	# A name that is no approval of the kind is the new one's name.
	if name and not new_name and frappe.db.get_value("Workflow", name, "document_type") != doctype:
		name, new_name = None, name
	if not name and not new_name:
		new_name = _("{0} Approval").format(_(doctype))
	if name and new_name:
		return {"mend": "suggest_approval", "error": "Give name to change an approval, or new_name for a new one, not both."}
	try:
		meta = approvals._doctype(doctype)
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {"mend": "suggest_approval", "error": str(e)}
	if new_name and frappe.db.exists("Workflow", new_name.strip()):
		return {"mend": "suggest_approval", "error": f"{new_name} is already an approval; change it by its name instead."}
	offered = [one["role"] for one in approvals.roles_offered()]
	known = set(offered) | set(frappe.get_all("Role", pluck="name"))
	numbers = [
		df.fieldname for df in meta.fields if df.fieldtype in ("Currency", "Float", "Int", "Percent") and not df.permlevel
	][:20]
	rows, said = [], []
	for one in states or []:
		state = str(one.get("state") or "").strip()
		if not state:
			return {"mend": "suggest_approval", "error": "Every state needs a name."}
		submitted = bool(one.get("submitted"))
		if submitted and not meta.is_submittable:
			return {"mend": "suggest_approval", "error": f"{doctype} is not submitted, so no state submits it."}
		role = one.get("editable_by") or roles.ADMINISTRATOR
		if role not in known:
			return {"mend": "suggest_approval", "error": f"{role} is not a role; a state is editable by one of {', '.join(offered)}."}
		if submitted and not rows:
			return {"mend": "suggest_approval", "error": f"{state} is the first state, where a record starts as a draft; a later state submits it."}
		row = {"state": state, "doc_status": "1" if submitted else "0", "allow_edit": role}
		sets = one.get("sets") or {}
		if sets.get("field"):
			df = meta.get_field(sets["field"])
			if not df or df.permlevel or df.fieldtype in no_value_fields or sets["field"] in approvals.BOOKKEEPING:
				return {"mend": "suggest_approval", "error": f"{state} cannot set {sets['field']}."}
			row.update({"update_field": sets["field"], "update_value": str(sets.get("value") or "")})
		rows.append(row)
	if not rows:
		return {"mend": "suggest_approval", "error": "An approval needs at least one state."}
	names = {row["state"] for row in rows}
	moves = []
	for one in steps or []:
		start, action, end = (str(one.get(key) or "").strip() for key in ("from", "action", "to"))
		role = one.get("by")
		when = str(one.get("when") or "").strip()
		if start not in names or end not in names:
			return {"mend": "suggest_approval", "error": f"{start} to {end}: both must be among the states."}
		if not action or role not in known:
			return {"mend": "suggest_approval", "error": f"{start} to {end}: give an action and the role it is for, one of {', '.join(offered)}."}
		if not approvals.plain_condition(meta, when):
			return {
				"mend": "suggest_approval",
				"error": f"{start} to {end}: when compares the record's own fields with plain values, as "
				f"doc.grand_total > 5000; its number fields are {', '.join(numbers)}."
			}
		submits = {row["state"]: row["doc_status"] == "1" for row in rows}
		if submits[start] and not submits[end]:
			return {"mend": "suggest_approval", "error": f"{start} is submitted, so no step goes from it back to {end}, a draft; take {end} from an earlier state."}
		moves.append({"state": start, "action": action, "next_state": end, "allowed": role, "condition": when, "allow_self_approval": 1})
		said.append({"label": _(action), "value": _("{0} to {1}, by {2}").format(_(start), _(end), _(role)) + (f" ({when})" if when else "")})
	if not moves:
		return {"mend": "suggest_approval", "error": "An approval needs at least one step."}
	if name and approvals.unchanged(name, rows, moves, turn_on):
		return {"error": f"{name} is already set up exactly so; tell them it is right as it is and nothing changes."}
	called = [row["state"] for row in rows]
	summary = [{"label": _("States"), "value": ", ".join(_(one) for one in called)}, *said]
	summary.append({"label": _("On"), "value": _("Yes") if turn_on else _("No")})
	return {
		"proposal": proposals.propose(
			"Approval",
			doctype,
			changes={
				"state": approvals.state(doctype),
				"workflow": {
					"name": name,
					"workflow_name": (new_name or name or "").strip(),
					"states": rows,
					"transitions": moves,
					"is_active": bool(turn_on),
				},
				"summary": summary,
			},
			why=why,
		),
		"state": "Proposed",
		"next": "Tell them it opens in the approval builder once they approve it, that whoever a step waits on "
		"is told, and that records already made keep their state until somebody takes a step.",
	}


# ------------------------------------------------------------------ automations

#: How an automation is made, for the model.
AUTOMATION_HELP = (
	"An automation does something by itself when a record of a kind is made, changed, submitted or reaches "
	"a date. when is one of: created, changed, field changed (with field, and from or to if it matters), "
	"submitted, cancelled, deleted, date (with date_field, days and before or after: runs that many days "
	"before or after the date). only_when narrows it to records whose fields match, each [field, operator, "
	"value] with operator one of = != > < >= <= like in. Steps run in order, each one of: {do: set, field, "
	"value} sets a field of the record; {do: tell, who, subject, message} or {do: tell, who, template} tells "
	"people on the bell and by mail, who being users' emails and @owner (who made the record) or @assignees; "
	"{do: assign, who, note} assigns the record to users named by email, never @owner. In subject, message and value, name a field of the "
	"record as {{ doc.fieldname }}. A template names fields itself, as the mail templates are written. It "
	"runs as whoever approves it, so each step can do only what they could do by hand."
)

#: when, as the model writes it, to frappe's trigger.
WHEN = {
	"created": "Doc Created",
	"changed": "Doc Updated",
	"field changed": "Field Value Changed",
	"submitted": "Doc Submitted",
	"cancelled": "Doc Cancelled",
	"deleted": "Doc Deleted",
	"date": "Date Based",
}


def workspace_automations(
	doctype: Annotated[str, "A kind of record, such as Sales Invoice, to also read what an automation of it may use."]
	| None = None,
) -> dict:
	"""The workspace's automations, for its administrators: each one, the kind
	of record it watches, when it runs, what it narrows to, whether it is on,
	and its steps. For a kind of record, its fields, its date fields and the
	mail templates written for it. Read it before suggesting an automation."""
	from onedesk.one import automations, roles

	if not roles.administers():
		return {"error": "Only a workspace administrator sees the automations."}
	said = {"automations": automations.described(), "how_an_automation_is_made": AUTOMATION_HELP}
	if doctype:
		try:
			automations._doctype(doctype)
		except frappe.ValidationError as e:
			frappe.clear_last_message()
			return {"error": str(e)}
		meta = frappe.get_meta(doctype)
		said["kind"] = {
			"doctype": doctype,
			"submitted": bool(meta.is_submittable),
			"fields": [
				f"{df.fieldname} ({df.label}, {df.fieldtype})"
				for df in meta.fields
				if df.fieldtype not in frappe.model.no_value_fields and not df.permlevel and not df.hidden
			][:100],
			"date_fields": [df.fieldname for df in meta.fields if df.fieldtype in ("Date", "Datetime")],
			"mail_templates": frappe.get_all(
				"Email Template", filters={"reference_doctype": ["in", [doctype, ""]]}, pluck="name"
			),
		}
	return said


def suggest_automation(
	doctype: Annotated[str, "The kind of record it watches, as its DocType name, such as Sales Invoice."],
	when: Annotated[str, "created, changed, field changed, submitted, cancelled, deleted or date."],
	steps: Annotated[list[dict], "What it does, in order. " + AUTOMATION_HELP],
	title: Annotated[str, "What it is called, such as Thank customers for paying."] | None = None,
	name: Annotated[str, "An automation to change, as workspace_automations names it."] | None = None,
	field: Annotated[str, "For field changed: the field it watches."] | None = None,
	from_value: Annotated[str, "For field changed: only when it changes from this."] | None = None,
	to_value: Annotated[str, "For field changed: only when it changes to this."] | None = None,
	date_field: Annotated[str, "For date: the date field it counts from."] | None = None,
	days: Annotated[int, "For date: how many days before or after."] | None = None,
	before_or_after: Annotated[str, "For date: before or after."] | None = None,
	only_when: Annotated[list[list], "Records it applies to, each [field, operator, value]."] | None = None,
	turn_on: Annotated[bool, "Whether it is on once approved."] = True,
	why: Annotated[str, "In a sentence, what it is for."] | None = None,
) -> dict:
	"""Suggest an automation, new or changed, as a card a workspace
	administrator approves: something done by itself when a record is made,
	changed or reaches a date: telling people, assigning, setting a field, in
	any mix. Read workspace_automations first, with the kind.
	Nothing is made until they approve it, and it runs as them. Workspace
	administrators only."""
	from onedesk.one import automations, roles
	from onedesk.one_ai import proposals

	mend = {"mend": "suggest_automation"}
	if not roles.administers():
		return {"error": "Only a workspace administrator sets automations."}
	try:
		automations._doctype(doctype)
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {**mend, "error": str(e)}
	trigger = WHEN.get((when or "").strip().lower())
	if not trigger:
		return {**mend, "error": f"when is one of {', '.join(WHEN)}."}
	held = None
	if name:
		held = frappe.db.get_value("Automation Flow", {"name": name, "document_type": doctype}, "name") or frappe.db.get_value(
			"Automation Flow", {"title": name, "document_type": doctype}, "name"
		)
		if not held:
			title, name = title or name, None
	values = {
		"title": (title or "").strip() or _("{0} automation").format(_(doctype)),
		"document_type": doctype,
		"trigger_type": trigger,
		"enabled": 1 if turn_on else 0,
		"filters": json.dumps([list(one) for one in only_when or []]),
	}
	if trigger == "Field Value Changed":
		values.update({"trigger_field": field, "from_value": from_value or "", "to_value": to_value or ""})
	if trigger == "Date Based":
		values.update(
			{
				"date_field": date_field,
				"date_offset": abs(int(days or 0)),
				"date_direction": "Before" if (before_or_after or "").lower().startswith("b") else "After",
			}
		)
	rows, said = [], []
	for one in steps or []:
		do = (one.get("do") or "").strip().lower()
		who = one.get("who") or []
		who = [who] if isinstance(who, str) else list(who)
		if do == "set":
			rows.append({"step_type": "Action", "action_type": "SetFieldValue", "params": json.dumps({"field": one.get("field"), "value": str(one.get("value") or "")})})
			said.append({"label": _("Set"), "value": f"{one.get('field')} = {one.get('value')}"})
		elif do == "tell":
			params = {"recipients": who, "email_template": one.get("template") or "", "subject": one.get("subject") or "", "message": one.get("message") or ""}
			rows.append({"step_type": "Action", "action_type": "TellPeople", "params": json.dumps(params)})
			said.append({"label": _("Tell"), "value": ", ".join(who) + ": " + (one.get("template") or one.get("subject") or "")})
		elif do == "assign":
			# frappe's step assigns users by name; whoever made the record is a
			# stand-in only Tell People reads.
			if any(str(one_who).startswith("@") for one_who in who):
				return {
					**mend,
					"error": "Assign names people by their user, such as a@b.com; it cannot assign whoever made the "
					"record. Tell them instead, or name the people.",
				}
			rows.append({"step_type": "Action", "action_type": "AssignToUser", "params": json.dumps({"assign_to": who, "description": one.get("note") or ""})})
			said.append({"label": _("Assign"), "value": ", ".join(who)})
		else:
			return {**mend, "error": f"A step does set, tell or assign, not {do or 'nothing'}."}
	if not rows:
		return {**mend, "error": "An automation needs at least one step."}
	values["actions"] = rows
	# Checked as saving it would check it, frappe's own checks and the workspace's.
	try:
		trial = frappe.get_doc({"doctype": "Automation Flow", **values})
		trial.run_method("validate")
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {**mend, "error": frappe.utils.strip_html_tags(str(e))}
	summary = [{"label": _("When"), "value": _(trigger) + (f" ({field})" if field else "") + (f" ({date_field})" if date_field else "")}]
	if only_when:
		summary.append({"label": _("Only When"), "value": "; ".join(" ".join(str(x) for x in one) for one in only_when)})
	summary += said
	summary.append({"label": _("On"), "value": _("Yes") if turn_on else _("No")})
	proposal = (
		proposals.propose("Edit", "Automation Flow", changes=values, record=held, why=why)
		if held
		else proposals.propose("Create", "Automation Flow", changes=values, why=why)
	)
	return {
		"proposal": proposal,
		"state": "Proposed",
		"next": "Tell them it runs as them once they approve it, and opens in Automations to change there.",
	}

# The two tools that lay a page out are run by Print Design, not the chat: a
# small model lays a page out wrong, so the chat hands the conversation over
# the moment it reaches for one (one_ai/run.py, tools.action_of).
print_layout.action = design_print_format.action = "print_design"

# An approval is suggested by Workspace Setup, on a stronger model, for the same
# reason: its states, steps, roles and conditions have to fit together, and a small
# model sent back to mend one repeats it. A notification rule goes the same way,
# since a small model asked to tell somebody and assign the record reached for
# the rule, which cannot assign, rather than the automation.
suggest_approval.action = suggest_automation.action = draft_notification.action = "workspace_setup"
