"""Retention Rua may still be owed from invoices made before One, asked on
the project itself until somebody answers.

Lately Rua held retention on invoices made in Excel and typed only the
amounts after it into the old app, so nothing the import reads says what a
client still holds. Each project that billed or was paid asks once, on its
Overview: Retention Held (how much and when it is due back, booked through
a Retention Before One) or No Retention Held. Answered, it says nothing.
"""

import frappe
from frappe import _, _lt
from frappe.utils import flt, fmt_money

CHECK = "Retention Check"


def _asking(doc):
	name = frappe.db.exists(CHECK, {"project": doc.name, "answer": "To Ask"})
	return frappe.get_doc(CHECK, name) if name else None


def said(doc) -> dict | None:
	if not _asking(doc):
		return None
	return {
		"text": _("Retention from before One"),
		"lines": [_("Is the client still holding retention on this project from invoices made outside One?")],
		"colour": "orange",
	}


def _answering(doc):
	if not frappe.has_permission(CHECK, "write"):
		frappe.throw(_("Only somebody in accounts answers this."), frappe.PermissionError)
	asked = _asking(doc)
	if not asked:
		frappe.throw(_("{0} has been answered already.").format(doc.project_name or doc.name))
	return asked


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
	asked = _answering(doc)
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
	asked.answer, asked.retention = "Held", made.name
	asked.flags.ignore_permissions = True
	asked.save()
	currency = frappe.db.get_value(
		"Company", made.get("company") or frappe.db.get_default("company"), "default_currency"
	)
	return _("{0} held as retention, owed until it is released.").format(fmt_money(amount, currency=currency))


def _none(doc) -> str:
	asked = _answering(doc)
	asked.answer = "None Held"
	asked.flags.ignore_permissions = True
	asked.save()
	return _("No retention held.")


def _asks(doc) -> bool:
	return bool(_asking(doc))


VERBS = {
	"rua.retention_held": {
		"doctypes": ["Project"],
		"label": _lt("Retention Held"),
		"action": _lt("Record"),
		"when": _asks,
		"fields": _held_fields,
		"run": _held,
	},
	"rua.no_retention": {
		"doctypes": ["Project"],
		"label": _lt("No Retention Held"),
		"when": _asks,
		"run": _none,
	},
}

NOTICES = {
	"rua.retention": {
		"doctypes": ["Project"],
		"said": said,
		"verbs": ["rua.retention_held", "rua.no_retention"],
	}
}
