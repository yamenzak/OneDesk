"""Days the workspace already agreed somebody would not be at work.

An approved `Attendance Request` is the one thing in the product that says, in
advance and in writing, *this person is working somewhere else on these dates*.
The clock's network and place gates exist to catch exactly that shape — off the
office network, outside every location — so without this they would score a
working-from-home Tuesday the same way they score somebody clocking in from a
café they have never been near.

That is the whole of it: read the approval, hand it to `clock._signals`, and let
it drop the four complaints the approval predicted. The attempt still records
what every gate saw, and it now also records *which request* explains it, so the
row reads as an answer rather than as a score nobody can account for.

Nothing here decides anything. A request that was never submitted, or one that
was turned down, or one for a different week, is not an approval and this
returns nothing.
"""

import frappe
from frappe.utils import getdate

#: What an approved day predicts, and therefore what it is allowed to forgive.
#: Everything else the gates raise — an impossible journey, a shared browser, a
#: missing passkey — is about the person rather than the place, and an approved
#: request has nothing to say about any of it.
FORGIVES = ("network-unknown", "network-personal", "place-outside", "place-absent")


def approved(employee: str, on=None) -> str | None:
	"""The submitted Attendance Request covering this date, if there is one.

	Read with `ignore_permissions` on purpose: this is a gate reading the
	workspace's own decision about the person in front of it, not somebody
	reading a colleague's record, and nothing from here reaches a screen except
	through the attempt it is written onto.
	"""
	if not employee or not frappe.db.exists("DocType", "Attendance Request"):
		return None

	day = getdate(on)
	return frappe.db.get_value(
		"Attendance Request",
		{
			"employee": employee,
			"docstatus": 1,
			"from_date": ["<=", day],
			"to_date": [">=", day],
		},
		"name",
		order_by="creation desc",
	)


def forgive(signals: list[str]) -> list[str]:
	"""The same signals, less the ones an approved day accounts for."""
	return [one for one in signals if one not in FORGIVES]
