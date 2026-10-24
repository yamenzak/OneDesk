"""Auto Reply is a mail rule now (rules_are_steps), so it is no longer an
ability of its own: its permission type goes. Its columns stay, unread."""

import frappe


def execute():
	frappe.db.delete("Permission Type", {"name": "email_account_mail_auto_reply"})
