"""Days the workspace already agreed somebody would not be at work."""

import frappe
from frappe.utils import getdate

#: What an approved day predicts, and therefore what it is allowed to forgive.
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
