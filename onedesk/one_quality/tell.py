"""What OneQuality tells people (its kinds are in notifications.py)."""

import frappe
from frappe import _
from frappe.utils import get_fullname

from onedesk.one import notify
from onedesk.one.people import NOT_PEOPLE


def raised(doc, method=None) -> None:
	"""Non Conformance after_insert: the quality managers are told, but for
	whoever raised it."""
	managers = [
		user
		for user in frappe.get_all("Has Role", filters={"role": "Quality Manager", "parenttype": "User"}, pluck="parent")
		if user != doc.owner and user not in NOT_PEOPLE and frappe.db.get_value("User", user, ["enabled", "user_type"]) == (1, "System User")
	]
	if not managers:
		return
	notify.notify(
		"Non Conformance Raised",
		sorted(set(managers)),
		record=("Non Conformance", doc.name),
		dedupe_on=["document_type", "document_name"],
		subject=doc.subject or doc.name,
		who=get_fullname(doc.owner),
		procedure=doc.procedure or _("no procedure"),
	)
