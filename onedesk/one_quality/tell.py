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


def resolved(doc, method=None) -> None:
	"""Non Conformance on_update: whoever raised it is told once it becomes
	Resolved, unless they resolved it themselves."""
	before = doc.get_doc_before_save()
	if doc.status != "Resolved" or not before or before.status == "Resolved" or doc.owner == frappe.session.user:
		return
	if doc.owner in NOT_PEOPLE or not frappe.db.get_value("User", doc.owner, "enabled"):
		return
	notify.notify(
		"Non Conformance Resolved",
		[doc.owner],
		record=("Non Conformance", doc.name),
		dedupe_on=["document_type", "document_name"],
		subject=doc.subject or doc.name,
		who=get_fullname(frappe.session.user),
	)


def overdue() -> None:
	"""Each morning: the steps of open quality actions due yesterday and
	still open, told once to whoever is responsible."""
	from frappe.utils import add_days, formatdate, getdate

	open_actions = frappe.get_all("Quality Action", filters={"status": "Open"}, pluck="name")
	if not open_actions:
		return
	for one in frappe.get_all(
		"Quality Action Resolution",
		filters={"parent": ["in", open_actions], "status": "Open", "completion_by": add_days(getdate(), -1), "responsible": ["is", "set"]},
		fields=["parent", "problem", "responsible", "completion_by"],
	):
		if one.responsible in NOT_PEOPLE or not frappe.db.get_value("User", one.responsible, "enabled"):
			continue
		notify.notify(
			"Quality Step Overdue",
			[one.responsible],
			record=("Quality Action", one.parent),
			sender="Administrator",
			problem=frappe.utils.strip_html(one.problem or "")[:120] or one.parent,
			action=one.parent,
			due=formatdate(one.completion_by),
		)
