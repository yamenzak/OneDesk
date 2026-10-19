"""Retention Rua may still be owed from invoices made before One, asked on
the project itself until somebody answers.

Lately Rua held retention on invoices made in Excel and typed only the
amounts after it into the old app, so nothing the import reads says what a
client still holds. Each project that billed or was paid asks once, on its
Overview: Retention Held (how much and when it is due back, booked through
a Retention Before One) or No Retention Held. Answered, it says nothing.

Retention Held asks what the old app has: what was billed after the
retention came off, so the held work goes on top, or the full amount, so it
comes off one of the project's invoices. The dialog shows the project's
figures now and after, as they are typed.
"""

import frappe
from frappe import _, _lt
from frappe.utils import flt, fmt_money, formatdate

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


AFTER, FULL = "after", "full"


def _currency():
	company = frappe.db.get_default("company")
	return frappe.db.get_value("Company", company, "default_currency")


def _invoices(doc) -> list:
	"""The project's own invoices, newest first, that the old app may have
	for the full work."""
	from onedesk.one_project import retention

	names = retention.invoices("Sales Invoice", [doc.name])
	return frappe.get_all(
		"Sales Invoice",
		filters={"name": ["in", names or [""]], "is_return": 0, "net_total": [">", 0]},
		fields=["name", "posting_date", "net_total", "total_taxes_and_charges"],
		order_by="posting_date desc, creation desc",
	)


def _held_fields(doc) -> list[dict]:
	currency = _currency()
	invoices = _invoices(doc)
	fields = []
	if invoices:
		fields += [
			{
				"fieldname": "how",
				"fieldtype": "Select",
				"label": _("Old App Invoices"),
				"options": [
					{"value": AFTER, "label": _("Net of Retention")},
					{"value": FULL, "label": _("Including Retention")},
				],
				"default": AFTER,
				"reqd": 1,
			},
			{
				"fieldname": "taken_from",
				"fieldtype": "Select",
				"label": _("Invoice"),
				"options": [
					{
						"value": one.name,
						"label": f"{one.name} · {formatdate(one.posting_date)} · {fmt_money(one.net_total, currency=currency)}",
					}
					for one in invoices
				],
				"default": invoices[0].name,
				"depends_on": f"eval:doc.how=='{FULL}'",
				"mandatory_depends_on": f"eval:doc.how=='{FULL}'",
			},
		]
	return [
		*fields,
		{
			"fieldname": "amount",
			"fieldtype": "Currency",
			"label": _("Retention Amount"),
			"reqd": 1,
			"description": _("Excluding VAT"),
		},
		{"fieldname": "one_live", "label": _("Effect")},
		{"fieldname": "due_back", "fieldtype": "Date", "label": _("Due Back")},
		{"fieldname": "note", "fieldtype": "Small Text", "label": _("Note")},
	]


def _taken(doc, how, taken_from):
	if how != FULL:
		return None
	found = next((one for one in _invoices(doc) if one.name == taken_from), None)
	if not found:
		frappe.throw(_("Choose the invoice that includes the retention."))
	return found


def figures(billed, vat, owed, held, amount, taken=None) -> list[tuple[str, float, float]]:
	"""The project now and after the retention is recorded, as (what, now,
	after). Kept off what the old app has, the held work is added on top;
	inside one of its invoices, it comes off that invoice with its VAT,
	which is charged again when the retention is released. Pure."""
	amount = flt(amount)
	if taken:
		rate = (
			flt(taken["total_taxes_and_charges"]) / flt(taken["net_total"]) if flt(taken["net_total"]) else 0
		)
		after = (billed, vat - amount * rate, owed - amount * (1 + rate), held + amount)
	else:
		after = (billed + amount, vat, owed, held + amount)
	names = ("billed", "vat", "owed", "held")
	return [
		(name, flt(now, 2), flt(then, 2))
		for name, now, then in zip(names, (billed, vat, owed, held), after, strict=True)
	]


def _live(doc, amount=None, how=None, taken_from=None, **_rest) -> dict:
	from onedesk.one_project import retention

	names = retention.invoices("Sales Invoice", [doc.name])
	totals = frappe.get_all(
		"Sales Invoice",
		filters={"name": ["in", names or [""]]},
		fields=[
			{"SUM": "base_net_total", "as": "billed"},
			{"SUM": "base_total_taxes_and_charges", "as": "vat"},
			{"SUM": "outstanding_amount", "as": "owed"},
		],
	)[0]
	kept_back = frappe.get_all(
		"Sales Invoice Item",
		filters={"parent": ["in", names or [""]], "one_held": ["is", "set"], "docstatus": 1},
		fields=[{"SUM": "base_net_amount", "as": "total"}],
	)[0].total
	held = sum(value for kept in retention.withheld("Sales Invoice", names).values() for _due, value in kept)
	taken = _taken(doc, how, taken_from) if how == FULL and taken_from else None
	found = figures(
		flt(totals.billed) - flt(kept_back), flt(totals.vat), flt(totals.owed), held, amount, taken
	)
	labels = {
		"billed": _("Work Billed"),
		"vat": _("VAT"),
		"owed": _("Client Balance"),
		"held": _("Retention Held"),
	}
	if flt(amount) <= 0:
		return {"rows": [], "lines": []}
	rows = [{"label": labels[name], "now": now, "after": after} for name, now, after in found]
	money = fmt_money(flt(amount), currency=_currency())
	if taken:
		said = _("Credits {0} plus VAT on {1} and adds a held invoice. VAT is charged on release.")
		return {"rows": rows, "lines": [said.format(money, taken.name)]}
	said = _("Adds a held invoice of {0}. VAT is charged on release.")
	return {"rows": rows, "lines": [said.format(money)]}


def _held(doc, amount=None, due_back=None, note=None, how=None, taken_from=None) -> str:
	asked = _answering(doc)
	if flt(amount) <= 0:
		frappe.throw(_("Enter the retention amount, excluding VAT."))
	taken = _taken(doc, how, taken_from)
	made = frappe.get_doc(
		{
			"doctype": "Retention Before One",
			"project": doc.name,
			"amount": flt(amount),
			"due_back": due_back,
			"taken_from": taken.name if taken else None,
			"note": note,
		}
	)
	made.insert()
	made.submit()
	asked.answer, asked.retention = "Held", made.name
	asked.flags.ignore_permissions = True
	asked.save()
	money = fmt_money(amount, currency=_currency())
	if taken:
		return _("{0} moved from {1} to retention.").format(money, taken.name)
	return _("{0} recorded as retention.").format(money)


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
		"live": _live,
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
