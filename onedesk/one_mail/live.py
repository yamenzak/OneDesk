"""OneMail, live: an open mailbox redraws when mail arrives or changes.

The event is `onemail_change` with the mailbox's name, sent to each person
who holds it and to nobody else, so it says nothing to anyone who may not
read that mailbox. Several changes in one request or job are one message per
mailbox, sent after the commit, so nobody re-reads a folder before the change
is in it.

Changes are announced where they are made (sync, the sweep, actions), not
from Communication hooks: most of them are `db.set_value`, which runs none.
"""

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
