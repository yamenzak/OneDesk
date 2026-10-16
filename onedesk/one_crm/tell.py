"""What OneCRM tells people: the next step on a lead or an opportunity come
due, to its owner, and a quotation a customer accepted or declined on the
portal, to whoever made it. Every notification's words are its file in
notifications/one_crm/."""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import now_datetime

from onedesk.one import notify
from onedesk.one_crm.next import OPEN, OWNER

#: How far back a step come due is still told: a day, so a scheduler that
#: stalled for a while misses nothing, and each step is told once by its key.
BACK = timedelta(days=1)


def due() -> None:
	"""Every five minutes: tell each owner of an open lead or opportunity whose
	next step has come due in the last day, once."""
	now = now_datetime()
	for doctype, owner in OWNER.items():
		for one in frappe.get_all(
			doctype,
			filters=[
				["status", "in", OPEN[doctype]],
				["one_next_on", ">", now - BACK],
				["one_next_on", "<=", now],
				[owner, "is", "set"],
			],
			fields=[
				"name",
				"title" if doctype == "Opportunity" else "lead_name as title",
				owner,
				"one_next_step",
				"one_next_on",
			],
		):
			key = f"one_crm:due:{doctype}:{one.name}:{one.one_next_on}"
			if frappe.cache.get_value(key):
				continue
			frappe.cache.set_value(key, 1, expires_in_sec=int(BACK.total_seconds()) * 2)
			notify.notify(
				"Next Step Due",
				one.get(owner),
				record=(doctype, one.name),
				sender="Administrator",
				step=one.one_next_step or _("Next Step"),
				title=one.title or one.name,
			)


def quotation_accepted(quotation, order, user: str, wanted: str) -> None:
	"""A customer accepted a quotation on the portal, told to whoever made it,
	with the draft order to check and submit."""
	notify.notify(
		"Quotation Accepted",
		quotation.owner,
		record=("Sales Order", order.name),
		sender=user,
		customer=quotation.customer_name or quotation.party_name,
		quotation=quotation.name,
		order=order.name,
		total=quotation.get_formatted("grand_total"),
		wanted=wanted,
	)


def quotation_declined(quotation, user: str, reason: str) -> None:
	"""A customer declined a quotation on the portal, told to whoever made it."""
	notify.notify(
		"Quotation Declined",
		quotation.owner,
		record=("Quotation", quotation.name),
		sender=user,
		customer=quotation.customer_name or quotation.party_name,
		quotation=quotation.name,
		reason=reason or _("They gave no reason."),
	)
