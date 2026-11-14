"""A party's changed bank details wait for a second person (one/second.py):
a supplier's, customer's or employee's Bank Account whose numbers or bank
change, or a second account added, asks an Accounts Manager other than
whoever changed it, and the party is told at its own address. Until it is
approved nothing is paid to the party (unusual.py). A first account asks
nothing, since its first payment does."""

import frappe
from frappe import _

from onedesk.one import second
from onedesk.one_book import tell
from onedesk.one_book.unusual import ROLE, skipped

WATCHED = ("iban", "bank_account_no", "bank", "branch_code")


def changes(before, after, fields, labels) -> list[str]:
	"""Each watched field whose value was set and is now something else, as
	"IBAN •••• 1234 → •••• 9876", numbers masked. Pure on two dicts."""
	said = []
	for field in fields:
		was, now = (before.get(field) or "").strip(), (after.get(field) or "").strip()
		if was and was != now:
			said.append(f"{labels[field]} {_shown(field, was)} → {_shown(field, now)}")
	return said


def _shown(field: str, value: str) -> str:
	return second.masked(value) if field in ("iban", "bank_account_no", "bank_ac_no") else (value or "—")


def labels(doctype: str, fields) -> dict:
	meta = frappe.get_meta(doctype)
	return {field: _(meta.get_label(field)) for field in fields}


def changed(doc, method=None) -> None:
	"""Bank Account after_insert and on_update."""
	if doc.is_company_account or not doc.party_type or not doc.party or skipped():
		return
	before = doc.get_doc_before_save()
	if before:
		said = changes(before.as_dict(), doc.as_dict(), WATCHED, labels(doc.doctype, WATCHED))
	elif frappe.db.exists("Bank Account", {"party_type": doc.party_type, "party": doc.party, "name": ["!=", doc.name]}):
		said = [_("{0} added").format(doc.name)]
	else:
		return
	if said:
		from onedesk.one_hr import bank

		asked(doc.party_type, doc.party, said, reference=(doc.doctype, doc.name), role=bank.ROLE if doc.party_type == "Employee" else ROLE)


def asked(party_type: str, party: str, said: list[str], reference: tuple[str, str], role: str = ROLE):
	"""A party's changed bank details, waiting for a second person, who is
	told, and the party, who is told at their own address."""
	name = frappe.db.get_value(party_type, party, frappe.get_meta(party_type).title_field or "name") or party
	keyed = {"party_type": party_type, "party": party}
	waiting = frappe.db.get_value(second.DOCTYPE, {**keyed, "kind": "Bank Details", "status": second.WAITING}, "changes")
	merged = list(dict.fromkeys([*(waiting or "").splitlines(), *said]))
	row, _new = second.ask(
		"Bank Details",
		_("Bank details of {0}").format(name),
		merged,
		role,
		keyed,
		reference_doctype=reference[0],
		reference_name=reference[1],
		changes="\n".join(merged),
	)
	tell.bank_details_waiting(row, second.deciders(row), name, said)
	_tell_party(party_type, party, name)
	return row


def _tell_party(party_type: str, party: str, name: str) -> None:
	if party_type == "Employee":
		from onedesk.one_hr import bank

		bank.tell(party)
		return
	address = frappe.db.get_value(party_type, party, "email_id") if frappe.get_meta(party_type).has_field("email_id") else None
	if not address:
		return
	tell.bank_details_changed(address, name)
