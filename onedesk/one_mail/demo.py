"""The workspace's own address, which Layla and every later administrator
hold and Mariam answers from too, everybody's own address, the mail a
customer, a supplier and a hotel sent the workspace this week, and what
came to Mariam's and Nadia's own addresses.
OneAI does not read this mailbox; the owner's own address is the one it
reads (intake.py)."""

from email.message import EmailMessage
from email.utils import format_datetime, make_msgid

import frappe
from frappe.utils import add_days, get_datetime, now_datetime

from onedesk.one_demo.people import OWNER

MAILS = (
	(
		("Hessa Al Marri", "hessa@bayview.example"),
		"Lobby glazing at Bayview Tower",
		3,
		"Hello,\n\nWe are refitting the lobby at Bayview Tower and would like a price for a "
		"frameless glass entrance, about 12 metres wide, with two sliding doors. Drawings "
		"attached to follow. Could someone visit the site next week?\n\nHessa Al Marri\n"
		"Bayview Developments",
	),
	(
		("Priya Nair", "orders@gulfglass.example"),
		"Your order of laminated glass ships on Thursday",
		2,
		"Dear Sahara team,\n\nThe 10.76 mm laminated panels on your last order are cut and "
		"will leave our yard on Thursday morning. Please have someone at the workshop gate "
		"from 8.\n\nPriya Nair\nGulf Glass Industries",
	),
	(
		("Rashid Saeed", "rashid@marinahotels.example"),
		"Balcony doors sticking in rooms 1204 to 1210",
		1,
		"Hi,\n\nSeven balcony doors on the twelfth floor stick when they close. Could your "
		"maintenance team look at them this week? Guests are in, so mornings are best.\n\n"
		"Rashid Saeed\nMarina Hotels Group",
	),
)


# Mail to a person's own address: who it is for, who sent it, and when.
PERSONAL = (
	(
		"mariam@one.test",
		("Omar Haddad", "omar.haddad@mailbox.example"),
		"Application for the site supervisor role",
		2,
		"Dear Mariam,\n\nI saw the site supervisor opening on your careers page. I have nine "
		"years on curtain wall projects in Dubai and Abu Dhabi, most recently at Al Reem. "
		"My CV is attached.\n\nOmar Haddad",
	),
	(
		"mariam@one.test",
		("Lina Farouk", "lina@talentbridge.example"),
		"Two installers available from November",
		4,
		"Hi Mariam,\n\nTwo of our glazing installers finish their current project at the end of "
		"October. Both hold driving licences. Shall I send their profiles?\n\n"
		"Lina Farouk\nTalentBridge Recruitment",
	),
	(
		"nadia@one.test",
		("Priya Nair", "orders@gulfglass.example"),
		"Tinted glass samples for the Bayview lobby",
		1,
		"Dear Nadia,\n\nThe bronze and grey tint samples you asked for went out this morning by "
		"courier. The grey is the closer match to the renderings you sent.\n\n"
		"Priya Nair\nGulf Glass Industries",
	),
	(
		"nadia@one.test",
		("Hessa Al Marri", "hessa@bayview.example"),
		"Re: Lobby glazing at Bayview Tower",
		0,
		"Hello Nadia,\n\nThank you for the first sketches. The client prefers the version with "
		"the slimmer frame. Could we see it in the grey tint?\n\nHessa",
	),
)

# Who answers the workspace's own address besides the demo's owner.
ANSWERS = ("mariam@one.test",)


def run(password=None):
	from onedesk.one_mail import addresses

	account = addresses.ensure_workspace()
	if not account:
		return
	everybody()
	for user in (OWNER, *ANSWERS):
		if not frappe.db.exists("User Email", {"parent": user, "email_account": account}):
			addresses.hold(account, user)
	box = frappe.get_doc("Email Account", account)
	for sender, subject, days, body in MAILS:
		arrive(box, sender, subject, days, body)
	own = f"%.{addresses.slug()}@{addresses.domain()}"
	for user, sender, subject, days, body in PERSONAL:
		theirs = frappe.db.get_value("User Email", {"parent": user, "email_account": ["like", own]}, "email_account")
		if theirs:
			arrive(frappe.get_doc("Email Account", theirs), sender, subject, days, body)
	automations(account)
	frappe.db.commit()


AUTOMATIONS = (
	(
		"Supplier Invoices",
		[{"type": "if", "id": "i1", "test": {"any": False, "items": [{"field": "sender_is", "op": "is", "value": "Supplier"}, {"field": "attachment", "value": True}]}, "then": [{"type": "star"}, {"type": "link"}], "else": []}],
	),
	(
		"Newsletters",
		[{"type": "if", "id": "i1", "test": {"any": True, "items": [{"field": "from", "op": "contains", "value": "newsletter, noreply, no-reply"}, {"field": "text", "op": "contains", "value": "unsubscribe"}]}, "then": [{"type": "read"}], "else": []}],
	),
)
"""The workspace mailbox's rules, made by Layla in AutomationCenter after the
week's mail arrived, so they sort what comes next."""


def automations(account: str) -> None:
	from onedesk.one_demo.base import as_user, tag
	from onedesk.one_mail import blocks, rules

	for priority, (title, steps) in enumerate(AUTOMATIONS, 1):
		if frappe.db.exists("Automation", {"trigger": blocks.ARRIVES, "scope": account, "title": title}):
			continue
		with as_user(OWNER):
			made = rules.save_rule(account, {"title": title, "steps": steps, "priority": priority * 10})
		tag(frappe.get_doc("Automation", made))


def arrive(box, sender: tuple, subject: str, days: int, body: str) -> None:
	"""One mail into a mailbox, as the Worker hands it over, once."""
	from onedesk.one_demo.base import tag
	from onedesk.one_mail.inbound import Arrival

	if frappe.db.exists("Communication", {"email_account": box.name, "subject": subject}):
		return
	mail = EmailMessage()
	mail["From"] = f"{sender[0]} <{sender[1]}>"
	mail["To"] = box.email_id
	mail["Subject"] = subject
	mail["Date"] = format_datetime(get_datetime(add_days(now_datetime(), -days)).astimezone())
	mail["Message-ID"] = make_msgid(domain=sender[1].split("@")[1])
	mail.set_content(body)
	tag(Arrival(mail.as_bytes(), box).process())


def everybody() -> None:
	"""An address for each person, as adding them gives one (addresses.for_person,
	which waits for the mail Worker's secret, so a demo without one gives them
	here)."""
	from onedesk.one_mail import addresses

	own = f"%.{addresses.slug()}@{addresses.domain()}"
	for user, first in frappe.get_all(
		"User",
		filters={"user_type": "System User", "enabled": 1, "name": ["like", "%@one.test"]},
		fields=["name", "first_name"],
		as_list=True,
	):
		if not frappe.db.exists("User Email", {"parent": user, "email_account": ["like", own]}):
			addresses.give(user, addresses.free(addresses.suggested(first, user)))
