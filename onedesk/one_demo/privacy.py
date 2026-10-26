"""One privacy request waiting for an administrator: Rania asked for a copy
of her data, so TrustCenter's Requests and the request itself have one to
show. No deletion is asked for; approving one would delete a demo person."""

import frappe

from onedesk.one_demo.base import as_user

ASKER = "rania@one.test"


def run(password=None):
	if frappe.db.exists("Personal Data Download Request", {"user": ASKER}):
		return
	from onedesk.one import privacy_copy

	with as_user(ASKER):
		privacy_copy.ask()
