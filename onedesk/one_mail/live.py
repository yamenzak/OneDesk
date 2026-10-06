"""OneMail, live: an open mailbox redraws when mail arrives or changes."""

import frappe

EVENT = "onemail_change"


def changed(*accounts: str) -> None:
	"""Say, after the commit, that these mailboxes changed."""
	accounts = {one for one in accounts if one}
	if not accounts:
		return
	held = getattr(frappe.local, "onemail_live", None)
	if held is None:
		held = set()
		frappe.local.onemail_live = held
		frappe.db.after_commit.add(_send)
	held |= accounts


def _send() -> None:
	accounts = getattr(frappe.local, "onemail_live", None) or set()
	frappe.local.onemail_live = None
	for account in accounts:
		for user in frappe.get_all(
			"User Email", filters={"email_account": account}, pluck="parent", distinct=True
		):
			frappe.publish_realtime(EVENT, {"account": account}, user=user, after_commit=False)


def inserted(doc, method=None) -> None:
	"""Communication after_insert: a message filed in a mailbox."""
	if doc.communication_medium == "Email" and doc.email_account:
		changed(doc.email_account)
