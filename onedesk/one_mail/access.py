"""Who may open a message.

Frappe lets anybody with the Inbox User role open any Communication by its
name, and lists only the ones in mailboxes they hold. So a message whose name
was guessed or passed on would open, and so would its attachments, which
answer to it (one_storage/namespace.py `may`). This closes that: a message in
a mailbox opens for the people who hold the mailbox, and for whoever may read
the record it is filed on, since a record's mail is part of the record.

Holders get Frappe's Inbox User role with their first mailbox
(`addresses.hold`), which is what lets them open a message at all.
"""

import frappe


def allowed(doc, ptype=None, user=None, debug=False) -> bool:
	"""The has_permission hook for Communication. It can only refuse."""
	user = user or frappe.session.user
	if user == "Administrator" or doc.communication_medium != "Email" or not doc.email_account:
		return True
	if frappe.db.exists("User Email", {"parent": user, "email_account": doc.email_account}):
		return True
	if ptype == "read" and doc.reference_doctype and doc.reference_name:
		return bool(frappe.has_permission(doc.reference_doctype, "read", doc.reference_name, user=user))
	return False
