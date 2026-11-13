"""What OneAI offers on One's own pages, and what it is told about them. A
centre has no doctype to go on, so it says where the reader is (`page` and
`section` from oneai.js), and this turns that into the sentence the model is
told and the suggestions the panel offers; Help says how to use each. The
tools live beside it by area (ai_*.py), and READS and SUGGESTS list them for
hooks.py."""

import frappe
from frappe import _lt

# One's calls that change something, each a card OneAI suggests (none yet),
# or why it is not OneAI's to make (docs/READY.md, mechanism 11).
REACH = {}

NOT_FOR_AI = {
	"update_window.set_window": "When the workspace is offline for an update is an administrator's decision.",
	"update_window.update_now": "Taking the workspace offline for an update is an administrator's decision.",
	"setup_job.wake": "A new site's build asks it to set itself up from its signup, before anybody works in it.",
	"company.use": "Which company a person works in is their own choice, from the frame.",
	"unsubscribe.off": "A signed link in a mail, opened without signing in, while OneAI sets the same switch through NotificationCenter.",
	"setup_center.save": "A step's answers are the workspace's own setup, typed by whoever sets it up in SetupCenter.",
	"setup_center.finish": "Marking a step done is the word of whoever did it, never OneAI's.",
	"rail.save_workspace": "The order of the apps on everybody's rail is an administrator's choice in SetupCenter, never OneAI's.",
	"shortcut_center.save":"Which key does what is the reader's own choice in ShortcutCenter, never OneAI's.",
	"shortcut_center.reset": "Which key does what is the reader's own choice in ShortcutCenter, never OneAI's.",
	"avatars.pick": "How every record of a kind looks is an administrator's choice in One's settings, never OneAI's.",
	"access.change_ability": "What a role may do is an administrator's decision in AccessCenter, never OneAI's.",
	"access.rename_role": "Naming a role is an administrator's choice in AccessCenter, never OneAI's.",
	"access.make_level": "Making a role is an administrator's decision in AccessCenter, never OneAI's.",
	"access.remove_level": "Removing a role is an administrator's decision in AccessCenter, never OneAI's.",
	"access.hold": "Holding somebody to some records is an administrator's decision, never OneAI's.",
	"access.let_go": "Letting somebody see more is an administrator's decision, never OneAI's.",
	"access.new_profile": "An access profile is an administrator's to make, never OneAI's.",
	"access.remove_profile": "Removing an access profile is an administrator's decision, never OneAI's.",
	"access.new_group": "A group of people is an administrator's to make, never OneAI's.",
	"access.remove_group": "Removing a group is an administrator's decision, never OneAI's.",
	"access_center.put": "What a person may use is an administrator's decision, never OneAI's.",
	"access_center.give": "What a person may do on one record is decided by whoever may share it, never OneAI.",
	"access_center.save": "A role's access is saved by the administrator changing it, never by OneAI.",
	"announcements.hide": "Folding the announcements is the reader's own choice on their bar.",
	"announcements.stop": "Stopping an announcement takes it off everybody's top bar at once, so the administrator does it from the page.",
	"announcements.show": "Opening the folded announcements is the reader's own choice on their bar.",
	"announcements.shows": "Whether the bar runs news or announcements is the reader's own choice on their bar.",
	"control.save": "The workspace's own settings are saved by the administrator changing them, and OneAI suggests a letter head as a card instead.",
	"notification_center.choose": "How a person hears of something is theirs to choose, never OneAI's.",
	"notification_center.switch": "Turning a person's notifications off or on is theirs to do, never OneAI's.",
	"notification_center.set_type": "A notification's channels for everyone are an administrator's decision, and OneAI rewrites its words as a card instead.",
	"notification_words.save": "Words and Rules are saved by the administrator writing them, and OneAI drafts a rule or its words as a card instead.",
	"notification_words.preview_notification": "A preview changes nothing and is drawn for the person writing.",
	"notification_words.delete_rule": "Stopping a rule for good is an administrator's decision, never OneAI's.",
	"recycle.restore": "Putting a deleted record back is the reader's decision in the bin, never OneAI's.",
	"recycle.bulk_restore": "Putting deleted records back is the reader's decision in the bin, never OneAI's.",
	"start_again.start": "Deleting every transaction can't be undone, so only an administrator starts it, never OneAI.",
}

SUGGESTIONS = {
	"page:account/profile": [
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
				"Go through my profile with me: what each part is for, and what only HR can change."
			),
			"expects": "how_to",
		},
	],
	"page:legal": [
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
	"page:notifications/everything": [
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
	"page:ai/yours": [
		{
			"label": _lt("What do you know about me?"),
			"ask": _lt(
				"What do you know about me? Say what you remember from our conversations, and what my "
				"workspace told you."
			),
			"expects": "recall",
		},
	],
	"page:onestudio/numbering": [
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
	"page:onestudio/printing": [
		{
			"label": _lt("Suggest a letter head"),
			"ask": _lt(
				"Suggest a letter head drawn from our details in One's ControlCenter (Company and Branding): the header and the "
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
				"Design a letter head in HTML from the company's details in One's ControlCenter (Company and Branding): the name "
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
	"page:onestudio/approvals": [
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
			"ask": _lt(
				"What would this copy of their data give, kind by kind, and is any of it other people's or the company's confidential information I should withhold?"
			),
			"expects": "privacy_request",
		},
	],
	"Personal Data Deletion Request": [
		{
			"label": _lt("What would deleting them remove?"),
			"ask": _lt(
				"If I approve this request, what is deleted, what is kept without their name, and is anything still theirs that somebody should take over first?"
			),
			"expects": "privacy_request",
		},
	],
	"Note": [
		{
			"label": _lt("Who has not read it?"),
			"ask": _lt("Who has not seen the latest announcement yet?"),
			"expects": "announcements",
		},
	],
	"Webhook": [
		{
			"label": _lt("Are the webhooks working?"),
			"ask": _lt("How did the webhooks' calls go this week, and why did any give up?"),
			"expects": "webhooks",
		},
	],
	"Webhook Request Log": [
		{
			"label": _lt("Why did these fail?"),
			"ask": _lt("Which webhook calls gave up this week, and what did the other system answer?"),
			"expects": "webhooks",
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
			"ask": _lt(
				"In the last week, which sign-ins failed, and did anybody sign in from somewhere new?"
			),
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
			"expects": "list_records",
		},
	],
	"page:access/access": [
		{
			"label": _lt("Who can do what?"),
			"ask": _lt(
				"What may each app's users, managers and our own levels do, and who is at each? Say anything that looks too wide."
			),
			"expects": "workspace_access",
		},
		{
			"label": _lt("Who sees only part?"),
			"ask": _lt("Who is held to a territory, a department or another record, and to which?"),
			"expects": "workspace_access",
		},
	],
	"page:account/people": [
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
	"page:account/plan": [
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
				"How long will our credits last at the rate we use them, and do any expire before we "
				"would use them?"
			),
			"expects": "workspace_plan",
		},
		{
			"label": _lt("What used the most credits this month?"),
			"ask": _lt("What used the most credits in the last thirty days, by model and by person?"),
			"expects": "workspace_plan",
		},
	],
	"page:account/domains": [
		{
			"label": _lt("Why is our domain not working?"),
			"ask": _lt(
				"Which of our own domains are not working, and what should we check or change in the DNS "
				"to fix each one?"
			),
			"expects": "workspace_plan",
		},
	],
	"page:ai/oneai": [
		{
			"label": _lt("What used the most credits?"),
			"ask": _lt("Which of OneAI's jobs used the most credits in the last thirty days?"),
			"expects": "workspace_oneai",
		},
	],
	"workspace:One": [
		{
			"label": _lt("What needs me today?"),
			"ask": _lt(
				"What needs me today? Look at my tasks, my meetings, what waits for me in Documents, OneAI's "
				"suggestions and what I have to approve, and say what to do first."
			),
			"expects": "my_day",
		},
	],
	"page:onehr/holidays": [
		{
			"label": _lt("Are our holidays ready for next year?"),
			"ask": _lt(
				"Look at our holiday list. When does it end, is there a list after it, is anything missing for "
				"our country, and who is on a list of their own?"
			),
			"expects": "workspace_holidays",
		},
	],
	"page:one/general": [
		{
			"label": _lt("Is signing in here safe enough?"),
			"ask": _lt(
				"Is signing in to this workspace safe enough? Look at our rules and at how people sign in, and "
				"say what to change."
			),
			"expects": "workspace_sign_in",
		},
	],
	"page:account/signin": [
		{
			"label": _lt("Is my account safe?"),
			"ask": _lt(
				"Is my account safe? Look at how I sign in and where I am signed in, and tell me what to do."
			),
			"expects": "my_sign_in",
		},
	],
	"page:onecalendar/link": [
		{
			"label": _lt("How do I add it?"),
			"ask": _lt("How do I add my calendar to Google Calendar, Apple Calendar or Outlook?"),
			"expects": "how_to",
		},
	],
	"page:notifications/words": [
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


#: The section a Settings page opens on when the address names none: its first.
# What every module's lists offer (one/lists.py).
from onedesk.one import lists as _lists  # noqa: E402

SUGGESTIONS.update(_lists.suggestions())

ONE_TABS = {"company": "Company", "branding": "Branding", "formats": "Region and Formats", "signin": "Sign-in", "sharing": "Sharing"}

OPENS_ON = {"onestudio": "numbering", "account": "profile", "one": "company", "notifications": "everything", "ai": "oneai"}


# What each centre on One's rail is, for the centres a section of their own
# says nothing more about.
CENTRES = {
	"setup": (
		"The reader is in SetupCenter: each app that has something to set up, with its steps done and "
		"waiting. A step with questions opens its form here; one without opens the settings that do it; "
		"Mark as Done sets a step aside. Apps that were just installed land on their steps. How is in One's "
		"Help under SetupCenter (how_to)."
	),
	"access": (
		"The reader is in AccessCenter: who may do what in the workspace. Roles and Profiles, then each app's "
		"roles and people, and who may open one record, and the Audit Log of every change, sign-in and export. "
		"Administrators change it there; how is in One's Help under Access and the Audit Log (how_to)."
	),
	"trust": (
		"The reader is in TrustCenter: the agreements the workspace agreed to and any change coming, the "
		"optional services and their switches, the companies that receive data and where, what is kept and "
		"for how long, and the requests for a copy or a deletion of someone's data. How it works is in "
		"TrustCenter's Help (how_to)."
	),
	"help": (
		"The reader is in HelpCenter: every app's Help pages, One's first, then the apps, then AccountCenter "
		"and TrustCenter. Answer from those pages (how_to)."
	),
	"updates": (
		"The reader is in UpdateCenter: when One next updates this workspace and the day and hour it updates "
		"in, which an administrator changes there or hurries with Update Now, then every app's versions, "
		"newest first, each with what changed for the people who use it, and what the next update brings. "
		"How it works is in One's Help under Updates (how_to)."
	),
	"shortcuts": (
		"The reader is in ShortcutCenter: every app's keyboard shortcuts, by where they work, and the keys "
		"they chose for them. Which key does what is theirs to change there, never OneAI's."
	),
}


def page(said: dict) -> str | None:
	"""The sentence the model is told about a Settings section: which records
	it is, and where its documentation is. Only the reader's own records, found
	on the server rather than taken from the browser."""
	if said.get("page") in CENTRES and not said.get("section"):
		return CENTRES[said["page"]]
	if said.get("page") == "setup":
		return CENTRES["setup"] + f" They are on {said['section']}'s steps."
	said = {**said, "section": said.get("section") or OPENS_ON.get(said.get("page"), "")}
	if said.get("section") == "lists":
		return _lists_page(said.get("page"))
	if said.get("page") == "account" and said.get("section") == "devices":
		return (
			"The reader administers the workspace and is on Devices in AccountCenter: every browser "
			"somebody signed in on, with who signed in last, when and from where, and how many passkeys it "
			"holds. They name one and set it Shared (nobody's passkey is made there) or Assigned to one "
			"person (theirs may be), or mark it Lost or Retired. How it works is in AccountCenter's Help "
			"under People and Devices (how_to)."
		)
	if said.get("page") == "onestudio" and said.get("section") == "numbering":
		return (
			"The reader administers this workspace and is on Numbering in OneStudio's ControlCenter: each kind of record named "
			"from a series, the series it may take (the first is the default), the name the next one gets and the "
			"number its counter has reached, and the naming rules. workspace_numbering reads it, for one kind or "
			"all; change_numbering suggests a new series, a default or a counter as a card they approve. How is in "
			"One's documentation under Numbering, for the Workspace (how_to)."
		)
	if said.get("page") == "onestudio" and said.get("section") == "printing":
		return (
			"The reader administers this workspace and is on Printing in OneStudio's ControlCenter: its letter heads (which is the "
			"default and what each header and footer shows), and for each kind of record the formats it may print "
			"with and the one it prints with by default. workspace_printing reads it; change_printing suggests a "
			"change as a card they approve. How is in One's documentation under Printing, for the Workspace (how_to)."
		)
	if said.get("page") == "onestudio" and said.get("section") == "approvals":
		return (
			"The reader administers this workspace and is on Approvals in OneStudio's ControlCenter: each approval, the kind of "
			"record it moves, whether it is on, its states and its steps, who takes each and when. "
			"workspace_approvals reads them; suggest_approval suggests one as a card they approve. How is in One's "
			"documentation under Approvals, for the Workspace (how_to)."
		)
	if said.get("page") == "notifications" and said.get("section") == "words":
		return _notifications_page(said.get("record"))
	if said.get("page") == "account" and said.get("section") == "people":
		return (
			"The reader administers this workspace and is on People in AccountCenter: everybody on it, which of "
			"OneCRM, OneBook, OneInventory, OneProject and OneHR each may use and as a user or a manager, who "
			"administers it, and when each was last active. workspace_people reads it all. They change a person "
			"by clicking them, and turn off, sign out or send a password reset from there; how is in AccountCenter's "
			"Help under People and Devices (how_to)."
		)
	if said.get("page") == "access" and said.get("section") == "audit":
		return (
			"The reader administers this workspace and is on the Audit Log in AccessCenter: who changed which "
			"record, who signed in and from where, and what was exported or printed, newest first, filtered by "
			"kind, each row opening the entry itself. Nothing here can be changed; the entries are what "
			"happened. How to read it is in One's documentation under AccessCenter (how_to)."
		)
	if said.get("page") == "access" and said.get("section") == "access":
		return (
			"The reader administers this workspace and is on Roles and Profiles in AccessCenter: every level of each app, its user, "
			"its manager and the ones made between, and what each may do, the profiles (a job's apps and levels in one) and who is on each, "
			"and the groups and who is in each. A person's page also holds what records they are held to. "
			"workspace_access reads it all. How is in One's documentation under AccessCenter (how_to)."
		)
	if said.get("page") == "account" and said.get("section") == "plan":
		return (
			"The reader administers this workspace and is on Plan and Credits in AccountCenter: its plan and what is "
			"added to it, its seats, storage and database, and its credits (what is left, held by calls running now, used in the last thirty "
			"days, and what expires when). workspace_plan reads it all, with the last thirty days by model and "
			"by person, and the cheapest ways to have what it uses now. They change the plan from the page head, and "
			"add seats, storage, database or credits from the button on each one's tile; how is in AccountCenter's Help under Plan and "
			"Credits (how_to)."
		)
	if said.get("page") == "one-hub":
		from onedesk.one import registry

		return (
			f"The reader is on {registry.name('one_hub')}: every centre they may open, a tile each with what it is for, "
			"and a search over them. A tile opens its centre over the page; the arrow at the right of the top bar "
			"lists the same centres from any screen."
		)
	if said.get("page") == "one":
		return (
			"The reader is on One's Home: what waits for their approval in every app (leave, expense claims and "
			"approval steps), the announcements running, the apps with a version they have not opened, and for an "
			"administrator the workspace at a glance (people against seats, apps on, storage, credits) and what "
			"in it needs them. Tasks, meetings and documents are on their own apps' homes; my_day reads them all. "
			"How is in One's Help under Home (how_to)."
		)
	if said.get("page") == "onehr" and said.get("section") == "holidays":
		return (
			"The reader administers this workspace and is on Holidays in OneHR's ControlCenter: the holiday list in force "
			"(its first and last day, the days off each week, the country and its public holidays), whether a list "
			"follows it, and how many people are on a list of their own. Leave, attendance, check-ins, the calendar "
			"and deadlines count around these days. workspace_holidays reads it all. They add, rename or remove a "
			"holiday in the table and save from the page head, make next year's list or use another list from the "
			"page head. Asked to add, rename or remove a holiday or a day the workplace is closed, or to change the "
			"days off, change_holidays suggests it as a card they approve. How is in OneHR's Help under "
			"Holidays (how_to)."
		)
	if said.get("page") == "ai" and said.get("section") == "oneai":
		return (
			"The reader administers this workspace and is on OneAI in AICenter: which records get a summary at "
			"the top, each switched on or off by clicking it, with Knowledge and Credit Usage in the page head. "
			"workspace_oneai reads it, with what each of OneAI's jobs used in the last thirty days. One picks the "
			"models OneAI runs on and what it is told; nothing about either is set in a workspace."
		)
	if said.get("page") == "account" and said.get("section") == "domains":
		return (
			"The reader administers this workspace and is on Domains in AccountCenter: the addresses it opens at in a "
			"browser. The one One gives it always works; their own domain works once a CNAME record points it at "
			"that address, as the page shows, and Cloudflare has issued its certificate, usually minutes later. A "
			"TXT record at _one.<domain> with the same value proves the domain is theirs where the CNAME cannot "
			"be read, as behind a proxy; until one of the two is read the domain is not routed. A "
			"bare domain such as acme.com needs a DNS provider that flattens a CNAME (ALIAS); otherwise use a "
			"subdomain. "
			"The main address is the one sign-in, invitations and links in mail use. workspace_plan reads each "
			"domain under domains, with its status and the target. They add one from the page head and make it the main address or "
			"remove it from its row; how is in AccountCenter's Help under Plan and Credits (how_to)."
		)
	if said.get("page") == "one" and said.get("section") in ONE_TABS:
		return (
			f"The reader administers this workspace and is on {ONE_TABS[said['section']]} in One's ControlCenter. Its tabs are "
			"Company (what it was made with, contact details, the address and the address at the foot of mails), Branding "
			"(the logo for printed documents, the brand and frame colours), Region and Formats (language, time zone, formats, "
			"rounded totals and totals in words), Sign-in (two-factor, passkey and email link sign-in, passwords and their "
			"expiry, how long a session lasts, one device at a time, the lockout after wrong passwords) and Sharing "
			"(calendar links and record sharing). workspace_sign_in reads the rules and how people sign in. Each tab saves "
			"its own; how is in One's documentation under the Workspace's Settings (how_to)."
		)
	at = (said.get("page"), said.get("section"))
	if at == ("notifications", "everything"):
		return (
			"The reader is on Everything in NotificationCenter: whether they get notifications at all, "
			"whether they also get them by email, whether new mail on a record they were given is mailed "
			"to them, and push in this browser. Each app's notifications, with an Email and a Push switch "
			"each, are under each app's row in Apps. my_notifications reads what they get and how. They change the switches "
			"themselves; how is in One's Help under NotificationCenter (how_to)."
		)
	if at == ("ai", "yours"):
		return (
			"The reader is on Yours in AICenter: the facts you keep for them, each with when and the record "
			"it is about, which they add, edit and forget there; and, to read only, what the workspace's "
			"administrators wrote for everybody. recall, with no words, reads both. How it works is in "
			"OneAI's Help (how_to)."
		)
	if at == ("account", "signin"):
		return (
			"The reader is on Sign-in in AccountCenter: their password, their passkey, whether two-factor "
			"sign-in applies to them, every place they are signed in with a Sign Out each, and their last "
			"sign-ins. my_sign_in reads it all. They change things themselves on the page; how is in AccountCenter's "
			"Help under Your Account (how_to)."
		)
	if at == ("onecalendar", "link"):
		from onedesk.one_calendar import feed

		if not feed.allowed():
			return (
				"The reader is on Your Calendar Link in OneCalendar's ControlCenter, but this workspace does "
				"not allow calendar links: its administrators switched them off under Sharing in "
				"One's ControlCenter, so nobody can have one. Say so rather than explaining how to add one."
			)
		return (
			"The reader is on Your Calendar Link in OneCalendar's ControlCenter: a private link to their "
			"calendar that another calendar app reads, with a button for Google Calendar, Apple Calendar and "
			"Outlook, what the link carries, and when an app last read it. They make it, copy it, replace it "
			"or switch it off themselves. How to add it to each app is in OneCalendar's Help under In Google, "
			"Apple or Outlook (how_to)."
		)
	if at == ("ai", "reads"):
		return (
			"The reader is on What OneAI Reads in AICenter: the mailboxes they hold and the shared "
			"folders they may change, each with a switch for whether OneAI reads what arrives in it. They "
			"switch them themselves; everything OneAI reads, for every mailbox and folder, is an "
			"administrator's, under AICenter › Reading. How it works is in OneAI's Help (how_to)."
		)
	if at != ("account", "profile"):
		return None
	from onedesk.one_hr import own

	user = frappe.session.user
	employee = own.employee_of()
	records = f"their own User record {user}" + (
		f" and their own Employee record {employee}" if employee else ""
	)
	return (
		f"The reader is on their Profile in AccountCenter, which edits {records}. "
		"They may change their name, gender, birth date, mobile, location, bio, language and time zone"
		+ (
			"; on the employee record, their addresses, personal email, emergency contact, marital status "
			"and blood group. Their job and bank details are HR's and cannot be changed there."
			if employee
			else "."
		)
		+ " How to use it is in AccountCenter's Help under Your Account (how_to)."
	)


def _lists_page(page: str | None) -> str | None:
	"""Lists, at the end of a module's ControlCenter (one/lists.py): the
	module's lists the reader keeps, by name."""
	from onedesk.one import lists

	module = next((one for one in lists.HOMES if one.lower() == page), None)
	if not module:
		return None
	names = [str(label) for doctype, label, _one in lists.declared()[module] if doctype in lists.listed().get(module, ())]
	return (
		f"The reader is on Lists in {module}'s ControlCenter: the short lists {module}'s records pick their values "
		f"from ({', '.join(names) or 'none they keep'}), each with how many values it has, and each opening as its "
		"own list, where they add, rename or remove a value. Asked to add several values at once, suggest each as "
		"a new record of that list (create_record), leaving out the ones it has. How is in One's documentation "
		"under Lists (how_to)."
	)


def _notifications_page(record: str | None) -> str:
	open_on = (
		f" They have the notification type {record} open, with its text and channels."
		if record and frappe.db.exists("Notification Type", record)
		else " They are looking at the list of every notification type, by app."
	)
	return (
		"The reader is on Words and Rules in NotificationCenter, where an administrator decides what each "
		"notification One sends says and which channels it may use." + open_on + " notification_type reads a "
		"type's text, slots and channels; rewrite_notification suggests new text as a card they apply; "
		"draft_notification suggests a new rule (when something happens to a record, tell somebody). How "
		"it works is in One's documentation under Workspace Notifications (how_to)."
	)


READS = (
	"ai_numbering.workspace_numbering",
	"ai_printing.workspace_printing",
	"ai_approvals.workspace_approvals",
	"ai_automations.workspace_automations",
	"ai_print_design.print_layout",
	"ai_workspace.my_sign_in",
	"ai_workspace.workspace_sign_in",
	"ai_workspace.workspace_people",
	"ai_workspace.workspace_access",
	"ai_workspace.workspace_reports",
	"ai_workspace.audit_log",
	"ai_workspace.webhooks",
	"ai_workspace.announcements",
	"ai_workspace.privacy_request",
	"ai_workspace.workspace_plan",
	"ai_workspace.workspace_oneai",
	"ai_workspace.workspace_intake",
	"ai_workspace.workspace_holidays",
	"ai_workspace.my_day",
	"ai_notifications.notification_type",
	"ai_notifications.my_notifications",
)
"""The tools OneAI reads here (registry/hooks.py lists them in one_ai_reads)."""


SUGGESTS = (
	"ai_notifications.rewrite_notification",
	"ai_notifications.draft_notification",
	"ai_numbering.change_numbering",
	"ai_printing.change_printing",
	"ai_print_design.design_print_format",
	"ai_approvals.suggest_approval",
	"ai_automations.suggest_automation",
	"ai_customize.customize",
	"ai_workspace.change_holidays",
)
"""The tools OneAI suggests, each as a card a person applies here (registry/hooks.py lists them in one_ai_suggests)."""
