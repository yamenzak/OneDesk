"""Who may open a message.

A message in a mailbox opens for the people who hold the mailbox, and
nobody else, though Frappe lets anybody with Inbox User open any
Communication by its name."""

import frappe


def allowed(doc, ptype=None, user=None, debug=False) -> bool:
	"""The has_permission hook for Communication. It can only refuse."""
	user = user or frappe.session.user
	if user == "Administrator" or doc.communication_medium != "Email" or not doc.email_account:
		return True
	return bool(frappe.db.exists("User Email", {"parent": user, "email_account": doc.email_account}))
