"""Rua's numbers go on where the old app left them: the next invoice of
2026 after RC-INV-2600019 is RC-INV-2600020, and so for every record the
old app numbered. Each record type offers Rua's series first, and keeps
ERPNext's own after it."""

import re

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

SERIES = {
	"Sales Invoice": ("RC-INV-.YY.#####",),
	"Payment Request": ("RC-PRO-.YY.#####",),
	"Payment Entry": ("RC-REC-.YY.#####", "RC-PAY-.YY.#####"),
	"Purchase Order": ("RC-LPO-.YY.#####",),
	"Purchase Receipt": ("RUA-RCT-.YY.#####",),
	"Request for Quotation": ("RC-RFQ-.YY.#####",),
	"Quotation": ("RC-QTN-.YY.#####",),
	"Leave Application": ("RUA-LEV-.YY.#####",),
	"Employee": ("RC-EMP-.#####",),
}
NUMBERED = re.compile(r"^(?P<key>[A-Z]+-[A-Z]+-(?:\d\d)?)(?P<count>\d{5})$")


def run(run_):
	for doctype, ours in SERIES.items():
		offer(doctype, ours)
	counters()


def offer(doctype, ours):
	field = frappe.get_meta(doctype).get_field("naming_series")
	if not field:
		return
	theirs = [one for one in (field.options or "").split("\n") if one and one not in ours]
	make_property_setter(
		doctype,
		"naming_series",
		"options",
		"\n".join([*ours, *theirs]),
		"Text",
		validate_fields_for_doctype=False,
	)
	make_property_setter(
		doctype, "naming_series", "default", ours[0], "Text", validate_fields_for_doctype=False
	)


def counted(names) -> dict:
	"""The highest number taken under each series key. Pure."""
	top = {}
	for name in names:
		found = NUMBERED.match(name or "")
		if found:
			key, count = found.group("key"), int(found.group("count"))
			top[key] = max(top.get(key, 0), count)
	return top


def counters():
	names = frappe.get_all("Rua Import Record", pluck="target_name", limit=0)
	names += frappe.get_all("Rua Import Record", pluck="source_name", limit=0)
	for key, count in counted(names).items():
		current = frappe.db.get_value("Series", key, "current", order_by="name")
		if current is None:
			frappe.db.sql("insert into `tabSeries` (name, current) values (%s, %s)", (key, count))
		elif int(current) < count:
			frappe.db.sql("update `tabSeries` set current = %s where name = %s", (count, key))
