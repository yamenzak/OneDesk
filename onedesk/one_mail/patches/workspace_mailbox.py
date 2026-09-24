"""Hosted mailboxes made before stage 4: the workspace's address becomes the
workspace's (`one_shared`), and every hosted mailbox gets its six folders."""

import frappe

from onedesk.one_mail import actions, addresses


def execute():
	own = addresses.workspace_address()
	for account in frappe.get_all("Email Account", filters={"one_hosted": 1}, fields=["name", "email_id"]):
		actions.standard(account.name)
		if account.email_id == own:
			frappe.db.set_value("Email Account", account.name, "one_shared", 1, update_modified=False)
