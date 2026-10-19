"""What each project still has to settle from the old app, said on the
project itself until somebody says it is settled.

The import leaves three kinds of loose end on a project (`importer/settle.py`):
money received and not invoiced yet, payments left out because they were
entered twice, and retention Rua may have held on invoices made in Excel.
The project's head says what is open in one line, and its buttons settle
it there: the retention held (a Retention Before One), none held, the
advance confirmed, or all of it settled. A project with nothing open says
nothing.
"""

import frappe
from frappe import _, _lt
from frappe.utils import flt, fmt_money

SETTLEMENT = "Rua Settlement"


def _of(doc):
	name = frappe.db.exists(SETTLEMENT, {"project": doc.name, "settled": 0})
	return frappe.get_doc(SETTLEMENT, name) if name else None


def said(doc) -> dict | None:
	"""The line on the project: what is still open, or None."""
	held = _of(doc)
	if not held:
		return None
	parts = []
	if held.advance_state == "To Confirm":
		parts.append(
			_("{0} received and not invoiced yet.").format(fmt_money(held.advance, currency=_currency()))
		)
	if held.copies:
		parts.append(
			_("{0} payments entered twice were left out ({1}).").format(
				held.copies, fmt_money(held.copies_amount, currency=_currency())
			)
		)
	if held.retention_state == "To Ask":
		parts.append(_("Is the client still holding retention on invoices made outside One?"))
	if not parts:
		return None
	return {"text": _("To settle from the old app"), "lines": parts, "colour": "orange"}


def _currency():
	return frappe.db.get_value("Company", frappe.db.get_default("company"), "default_currency")


def _settling(doc):
	if not frappe.has_permission(SETTLEMENT, "write"):
		frappe.throw(_("Only somebody in accounts settles what the old app left."), frappe.PermissionError)
	held = _of(doc)
	if not held:
		frappe.throw(_("Nothing is left to settle on {0}.").format(doc.project_name or doc.name))
	return held


def _close(held) -> None:
	"""Settled once nothing is left to ask: no retention question, no advance
	to confirm and no copies to acknowledge."""
	if held.retention_state != "To Ask" and held.advance_state != "To Confirm" and not held.copies:
		held.settled = 1
	held.flags.ignore_permissions = True
	held.save()


def _asks_retention(doc) -> bool:
	held = _of(doc)
	return bool(held and held.retention_state == "To Ask")


def _asks_advance(doc) -> bool:
	held = _of(doc)
	return bool(held and held.advance_state == "To Confirm")


def _held_fields(doc) -> list[dict]:
	return [
		{
			"fieldname": "amount",
			"fieldtype": "Currency",
			"label": _("Retention Held"),
			"reqd": 1,
			"description": _("What the client still holds, before VAT."),
		},
		{
			"fieldname": "due_back",
			"fieldtype": "Date",
			"label": _("Due Back"),
			"description": _("When the client is due to pay it back, if anybody knows."),
		},
		{"fieldname": "note", "fieldtype": "Small Text", "label": _("Note")},
	]


def _held(doc, amount=None, due_back=None, note=None) -> str:
	held = _settling(doc)
	if flt(amount) <= 0:
		frappe.throw(_("Say how much retention the client holds, before VAT."))
	made = frappe.get_doc(
		{
			"doctype": "Retention Before One",
			"project": doc.name,
			"amount": flt(amount),
			"due_back": due_back,
			"note": note,
		}
	)
	made.insert()
	made.submit()
	held.retention_state, held.retention = "Held", made.name
	_close(held)
	return _("{0} held as retention, owed until it is released.").format(
		fmt_money(amount, currency=_currency())
	)


def _none(doc) -> str:
	held = _settling(doc)
	held.retention_state = "None Held"
	_close(held)
	return _("No retention held.")


def _advance(doc) -> str:
	held = _settling(doc)
	held.advance_state = "Confirmed"
	_close(held)
	return _("Kept as an advance until its invoice is made.")


def _all(doc) -> str:
	held = _settling(doc)
	held.settled = 1
	held.flags.ignore_permissions = True
	held.save()
	return _("Settled.")


def _open(doc) -> bool:
	return bool(_of(doc))


VERBS = {
	"rua.retention_held": {
		"doctypes": ["Project"],
		"label": _lt("Retention Held"),
		"action": _lt("Record"),
		"when": _asks_retention,
		"fields": _held_fields,
		"run": _held,
	},
	"rua.no_retention": {
		"doctypes": ["Project"],
		"label": _lt("No Retention Held"),
		"when": _asks_retention,
		"run": _none,
	},
	"rua.advance_confirmed": {
		"doctypes": ["Project"],
		"label": _lt("It's an Advance"),
		"when": _asks_advance,
		"run": _advance,
	},
	"rua.settled": {
		"doctypes": ["Project"],
		"label": _lt("All Settled"),
		"when": _open,
		"run": _all,
	},
}

NOTICES = {
	"rua.settle": {
		"doctypes": ["Project"],
		"said": said,
		"verbs": ["rua.retention_held", "rua.no_retention", "rua.advance_confirmed", "rua.settled"],
	}
}
