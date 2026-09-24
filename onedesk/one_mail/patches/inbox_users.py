"""People who held a mailbox before stage 6 get Frappe's Inbox User role,
without which they cannot open its messages (one_mail/access.py)."""

import frappe

from onedesk.one_mail import addresses


def execute():
	held = frappe.get_all(
		"User Email",
		filters={
			"email_account": [
				"in",
				frappe.get_all("Email Account", filters={"one_hosted": 1}, pluck="name")
				+ frappe.get_all("Email Account", filters={"one_connected": 1}, pluck="name"),
			]
		},
		pluck="parent",
		distinct=True,
	)
	for user in held:
		if user in ("Administrator", "Guest") or frappe.db.exists(
			"Has Role", {"parent": user, "role": addresses.INBOX_USER}
		):
			continue
		holder = frappe.get_doc("User", user)
		addresses.inbox_user(holder)
		holder.flags.ignore_permissions = True
		holder.save()
