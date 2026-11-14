"""A payment out of the ordinary waits for a second person (one/second.py):
a Pay above the company's Payment Approval Limit, the first to a party who
is not an employee, or to a party whose bank details changed lately. Saving
such a draft asks; Approve Payment submits it as whoever approved it. A
payment or journal entry to a party whose new bank details wait is
refused. Why not a Workflow is in one_book/AGENTS.md, Payment approval."""

import frappe
from frappe import _
from frappe.utils import cint, flt, fmt_money

from onedesk.one import second
from onedesk.one.company import company_currency

FIELDS = ("one_approve_above", "one_approve_first_payment", "one_approve_bank_days")

PAID = "Pay"

ROLE = "Accounts Manager"


def settings(company: str) -> dict:
	return frappe.db.get_value("Company", company, FIELDS, as_dict=True) or frappe._dict()


def skipped() -> bool:
	return bool(frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch or frappe.flags.in_demo)


def _paid_before(doc) -> bool:
	return bool(
		frappe.db.exists(
			"Payment Entry",
			{
				"payment_type": PAID,
				"party_type": doc.party_type,
				"party": doc.party,
				"company": doc.company,
				"docstatus": 1,
				"name": ["!=", doc.name],
			},
		)
	)


def reasons(doc) -> list[str]:
	"""Why a payment waits for a second person, each a short line, or
	nothing when it is ordinary."""
	if doc.payment_type != PAID or not doc.party_type or not doc.party or not doc.company:
		return []
	held = settings(doc.company)
	said = []
	above = flt(held.one_approve_above)
	if above and flt(doc.base_paid_amount) > above:
		said.append(_("Above {0}").format(fmt_money(above, currency=company_currency(doc.company))))
	if cint(held.one_approve_first_payment) and doc.party_type != "Employee" and not _paid_before(doc):
		said.append(_("First payment to {0}").format(doc.party_name or doc.party))
	days = cint(held.one_approve_bank_days)
	if days and second.changed_since(doc.party_type, doc.party, days):
		said.append(_("Bank details changed in the last {0} days").format(days))
	return said


def _keyed(doc) -> dict:
	return {"reference_doctype": doc.doctype, "reference_name": doc.name}


def title(doc) -> str:
	return _("Payment of {0} to {1}").format(
		fmt_money(doc.paid_amount, currency=doc.paid_from_account_currency), doc.party_name or doc.party
	)


def asked(doc, method=None) -> None:
	"""Payment Entry on_update: a draft out of the ordinary asks a second
	person, and one that no longer is stops asking."""
	if doc.docstatus != 0 or skipped():
		return
	said = reasons(doc)
	if not said:
		second.withdraw("Payment", _keyed(doc))
		return
	maker = doc.owner if not second.machine(doc.owner) else second.asker()
	row, new = second.ask(
		"Payment",
		title(doc),
		said,
		ROLE,
		_keyed(doc),
		company=doc.company,
		amount=doc.base_paid_amount,
		currency=company_currency(doc.company),
		party_type=doc.party_type,
		party=doc.party,
		asked_by=maker,
	)
	if new:
		from onedesk.one_book import tell

		tell.payment_waiting(row, second.deciders(row), doc, said)


def refused(doc, method=None) -> None:
	"""Payment Entry before_submit: a payment to a party whose new bank
	details wait is refused, and one out of the ordinary is submitted only
	by Approve Payment."""
	if skipped():
		return
	_not_held(doc.party_type, doc.party, doc.party_name)
	if frappe.flags.one_second_approved == doc.name:
		return
	said = reasons(doc)
	if said:
		frappe.throw(
			_("This payment waits for a second person to approve it: {0}.").format("; ".join(said)),
			title=_("Waiting for Approval"),
		)


def journal_refused(doc, method=None) -> None:
	"""Journal Entry before_submit: nothing is paid to a party whose new bank
	details wait, payroll's bank entry included."""
	if skipped():
		return
	for row in doc.accounts or []:
		_not_held(row.party_type, row.party)


def _not_held(party_type, party, name=None) -> None:
	if second.held(party_type, party):
		frappe.throw(
			_("Payments to {0} wait until their new bank details are approved.").format(name or party),
			title=_("Waiting for Approval"),
		)


def approved(row) -> None:
	"""Approve Payment: the payment submitted by whoever approved it, as
	themselves, so their right to submit it is checked."""
	doc = frappe.get_doc(row.reference_doctype, row.reference_name)
	if doc.docstatus != 0:
		frappe.throw(_("{0} is no longer a draft.").format(doc.name))
	frappe.flags.one_second_approved = doc.name
	try:
		doc.submit()
	finally:
		frappe.flags.one_second_approved = None
