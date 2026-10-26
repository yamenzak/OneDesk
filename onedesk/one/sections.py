"""What a section of a centre is drawn from and saved back to: a doctype's
own fields, and each record as it was loaded, so a save made after somebody
else's is refused with frappe's own message."""

import frappe
from frappe import _, _lt

LABELS = {"mobile_no": _lt("Mobile"), "phone_no": _lt("Phone"), "city": _lt("City"), "state": _lt("State or Region")}


def as_opened(doc):
	"""The record as the page loaded it, for frappe's own `check_if_latest`,
	which refuses the save if it has changed since, with frappe's own message
	(Document.check_if_latest). A record the page did not send is saved as
	it is."""
	modified = (frappe.flags.one_opened or {}).get(f"{doc.doctype}:{doc.name}")
	if modified:
		doc.modified = modified
	return doc


def opened(*docs) -> list[dict]:
	"""What the page needs to save these back, and to hear when somebody else
	changes them: each record's doctype, name and modified."""
	return [{"doctype": doc.doctype, "name": doc.name, "modified": str(doc.modified)} for doc in docs if doc]


def fields(doctype: str, names: tuple) -> list[dict]:
	"""A doctype's own fields, as the page draws them: its labels, options and
	descriptions rather than a second copy of them here."""
	meta = frappe.get_meta(doctype)
	out = []
	for name in names:
		field = meta.get_field(name)
		if not field:
			continue
		out.append(
			{
				"fieldname": field.fieldname,
				"fieldtype": field.fieldtype,
				"label": str(LABELS[name]) if name in LABELS else _(field.label),
				"options": field.options,
				"description": _(field.description) if field.description else None,
			}
		)
	return out
