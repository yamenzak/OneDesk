"""What OneCRM tells people: the next step on a lead or an opportunity come
due, to its owner, and a quotation a customer accepted or declined on the
portal, to whoever made it. Every notification's words are its file in
notifications/one_crm/."""

from datetime import timedelta

import frappe
from frappe import _, _lt
from frappe.utils import now_datetime

from onedesk.one import notify
from onedesk.one_crm.next import OPEN, OWNER

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
				kind=_lt(doctype),
			)


def given(doc, method=None) -> None:
	"""Lead and Opportunity on_update: whoever is made its owner by somebody
	else is told. An Assignment Rule sets the owner without saving, and is
	told as frappe's own Assignment."""
	if frappe.flags.in_import or frappe.flags.in_install or frappe.flags.in_migrate:
		return
	field = OWNER[doc.doctype]
	owner = doc.get(field)
	if not owner or owner == frappe.session.user or not doc.has_value_changed(field):
		return
	notify.notify(
		"Given to You",
		owner,
		record=(doc.doctype, doc.name),
		who=frappe.utils.get_fullname(frappe.session.user),
		title=_title(doc),
	)


def arrived(doc, method=None) -> None:
	"""Lead after_insert: a lead nobody owns is told to sales."""
	if doc.get("lead_owner") or frappe.flags.in_import or frappe.flags.in_install:
		return
	from frappe.utils.user import get_users_with_role

	people = sorted(
		{*get_users_with_role("Sales User"), *get_users_with_role("Sales Manager")} - {frappe.session.user}
	)
	if people:
		notify.notify(
			"New Lead Waiting",
			people,
			record=("Lead", doc.name),
			sender="Administrator",
			title=_title(doc),
			source=_lt(doc.source) if doc.get("source") else _lt("Unknown"),
		)


def running_out() -> None:
	"""Each morning: an open quotation three days from its last day."""
	if not frappe.db.get_value("Notification Type", "Quotation Running Out", "enabled"):
		return
	from frappe.utils import add_days, formatdate, getdate

	for name in frappe.get_all(
		"Quotation",
		filters={"docstatus": 1, "status": "Open", "valid_till": add_days(getdate(), 3)},
		pluck="name",
	):
		quotation = frappe.get_doc("Quotation", name)
		notify.notify(
			"Quotation Running Out",
			_sellers(quotation),
			record=("Quotation", name),
			sender="Administrator",
			quotation=name,
			customer=quotation.customer_name or quotation.party_name,
			date=formatdate(quotation.valid_till),
			total=quotation.get_formatted("grand_total"),
		)


def _title(doc) -> str:
	return doc.get("title") or doc.get("lead_name") or doc.get("company_name") or doc.name


def _sellers(quotation) -> list[str]:
	"""Whoever made the quotation and the opportunity's owner, while they can
	sign in; the sales managers when neither can."""
	from frappe.utils.user import get_users_with_role

	people = [quotation.owner]
	if quotation.get("opportunity"):
		people.append(frappe.db.get_value("Opportunity", quotation.opportunity, "opportunity_owner"))
	found = frappe.get_all(
		"User", filters={"name": ["in", [one for one in people if one]], "enabled": 1}, pluck="name"
	)
	return found or get_users_with_role("Sales Manager")


def quotation_accepted(quotation, order, user: str, wanted: str) -> None:
	"""A customer accepted a quotation on the portal, told to whoever made it,
	with the draft order to check and submit."""
	notify.notify(
		"Quotation Accepted",
		_sellers(quotation),
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
		_sellers(quotation),
		record=("Quotation", quotation.name),
		sender=user,
		customer=quotation.customer_name or quotation.party_name,
		quotation=quotation.name,
		reason=reason or _("They gave no reason."),
	)


def they_replied(doc, method=None) -> None:
	"""Communication after_insert: mail in on a lead or an opportunity, told
	to its owner, wherever the mailbox it came to is."""
	from onedesk.one_crm.next import OWNER

	if doc.communication_type != "Communication" or doc.sent_or_received != "Received":
		return
	if doc.reference_doctype not in ("Lead", "Opportunity") or not doc.reference_name:
		return
	owner = frappe.db.get_value(doc.reference_doctype, doc.reference_name, OWNER[doc.reference_doctype])
	if owner and frappe.db.get_value("User", owner, "enabled"):
		record = frappe.get_doc(doc.reference_doctype, doc.reference_name)
		notify.notify(
			"They Replied",
			owner,
			record=(doc.reference_doctype, doc.reference_name),
			sender="Administrator",
			who=doc.sender_full_name or doc.sender or "",
			title=_title(record),
			subject=doc.subject or "",
		)


def contracts_ending() -> None:
	"""Each morning: a contract that ends in two weeks, told to whoever made
	it and the user it names. ERPNext marks it Inactive on the day."""
	from frappe.utils import add_days, formatdate, getdate

	for one in frappe.get_all(
		"Contract",
		filters={"docstatus": ["<", 2], "status": "Active", "end_date": add_days(getdate(), 14)},
		fields=["name", "owner", "party_user", "party_name", "end_date"],
	):
		people = frappe.get_all(
			"User", filters={"name": ["in", [one.owner, one.party_user]], "enabled": 1}, pluck="name"
		)
		if people:
			notify.notify(
				"Contract Expiring",
				people,
				record=("Contract", one.name),
				sender="Administrator",
				party=one.party_name,
				date=formatdate(one.end_date),
			)
