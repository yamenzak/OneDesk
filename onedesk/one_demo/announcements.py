"""Two announcements from the office, running along everybody's top bar: a
holiday closure and a change to how expenses are claimed."""

import frappe
from frappe.utils import add_days

from onedesk.one_demo.base import ago, as_user

OWNER = "wsadmin@one.test"

SAID = (
	(
		"Office closed on National Day",
		"<p>The office and the workshop are closed on 2 and 3 December. Site teams on the Bayview tower keep "
		"working; Samir has the rota.</p>",
	),
	(
		"Expenses now go through One",
		"<p>From this month, claim expenses in One under OneHR › Expenses, with a photo of the receipt. Paper "
		"claims are no longer accepted after the 25th.</p>",
	),
)


def run(password=None):
	with as_user(OWNER):
		for title, content in SAID:
			if frappe.db.exists("Note", {"title": title}):
				continue
			frappe.get_doc(
				{
					"doctype": "Note",
					"title": title,
					"content": content,
					"public": 1,
					"notify_on_login": 0,
					"expire_notification_on": f"{add_days(ago(0), 60)} 23:59:00",
				}
			).insert()
