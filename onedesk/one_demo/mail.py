"""The workspace's own address, which Layla and every later administrator
hold, and the mail a customer, a supplier and a hotel sent it this week.
OneAI does not read this mailbox; the owner's own address is the one it
reads (intake.py)."""

from email.message import EmailMessage
from email.utils import format_datetime, make_msgid

import frappe
from frappe.utils import add_days, get_datetime, now_datetime

#: from (name, address), subject, days ago, body
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


def run(password=None):
	from onedesk.one_demo.base import tag
	from onedesk.one_mail import addresses
	from onedesk.one_mail.inbound import Arrival

	account = addresses.ensure_workspace()
	if not account:
		return
	box = frappe.get_doc("Email Account", account)
	for sender, subject, days, body in MAILS:
		if frappe.db.exists("Communication", {"email_account": account, "subject": subject}):
			continue
		mail = EmailMessage()
		mail["From"] = f"{sender[0]} <{sender[1]}>"
		mail["To"] = box.email_id
		mail["Subject"] = subject
		mail["Date"] = format_datetime(get_datetime(add_days(now_datetime(), -days)).astimezone())
		mail["Message-ID"] = make_msgid(domain=sender[1].split("@")[1])
		mail.set_content(body)
		tag(Arrival(mail.as_bytes(), box).process())
	frappe.db.commit()
