"""The workspace layer, held: what a workspace may change about a form, and
what it may not.

Every row written through the Customize page, or by somebody frappe does not
let customize, is held here: nothing that runs, nothing that weakens a guard.
"""

import re

import frappe
from frappe import _

KINDS = (
	"Data",
	"Small Text",
	"Text",
	"Long Text",
	"Text Editor",
	"Int",
	"Float",
	"Currency",
	"Percent",
	"Check",
	"Date",
	"Datetime",
	"Time",
	"Duration",
	"Select",
	"Link",
	"Phone",
	"Rating",
	"Attach",
	"Attach Image",
	"Color",
	"Section Break",
	"Column Break",
	"Tab Break",
)

ADDED = (
	"reqd",
	"unique",
	"default",
	"description",
	"placeholder",
	"in_list_view",
	"in_standard_filter",
	"in_preview",
	"bold",
	"hidden",
	"read_only",
	"depends_on",
	"mandatory_depends_on",
	"read_only_depends_on",
	"fetch_from",
	"fetch_if_empty",
	"length",
	"non_negative",
	"precision",
	"no_copy",
	"allow_on_submit",
	"print_hide",
	"translatable",
	"set_only_once",
	"allow_in_quick_entry",
	"collapsible",
)

DATA_OPTIONS = ("", "Email", "Name", "Phone", "URL", "Barcode", "IBAN")

PROPERTIES = (
	"label",
	"hidden",
	"reqd",
	"in_list_view",
	"in_standard_filter",
	"in_preview",
	"bold",
	"description",
	"depends_on",
	"mandatory_depends_on",
	"read_only_depends_on",
	"collapsible",
	"field_order",
	"insert_after",
	"columns",
	"default",
	"placeholder",
	"read_only",
	"allow_in_quick_entry",
)

_TOKEN = re.compile(
	r"""\s*(?:
		(?P<field>doc\.[a-z_][a-z0-9_]*)
		|(?P<string>'[^'\\\n]*'|"[^"\\\n]*")
		|(?P<number>-?\d+(?:\.\d+)?)
		|(?P<word>true|false|null)
		|(?P<op>===|!==|==|!=|>=|<=|&&|\|\||[<>!()])
	)""",
	re.VERBOSE,
)


def plain(condition: str | None) -> bool:
	"""Whether a `depends_on` only compares the record's fields and plain
	values: a field's name, or `eval:` and such a comparison. Pure."""
	condition = (condition or "").strip()
	if not condition:
		return True
	if not condition.startswith("eval:"):
		return bool(re.fullmatch(r"[a-z_][a-z0-9_]*", condition))
	rest, last = condition[5:], None
	if not rest.strip():
		return False
	while rest.strip():
		found = _TOKEN.match(rest)
		if not found:
			return False
		if last == "field" and found.group("op") == "(":
			return False
		last = found.lastgroup
		rest = rest[found.end() :]
	return True


def held() -> bool:
	"""Whether the row being written is the workspace's: written through the
	Customize page, or by somebody frappe itself does not let customize."""
	return bool(frappe.flags.one_workspace_layer) or not frappe.has_permission("Custom Field", "write")


def _conditions(row, where: str) -> None:
	for key in ("depends_on", "mandatory_depends_on", "read_only_depends_on"):
		if not plain(row.get(key)):
			frappe.throw(
				_("{0}: a condition may only compare the record's fields with plain values.").format(where)
			)


def custom_field(doc, method=None) -> None:
	"""A field the workspace adds: something a person types or picks."""
	if not held():
		return
	where = doc.label or doc.fieldname
	if doc.fieldtype not in KINDS:
		frappe.throw(
			_("{0}: fields of type {1} can't be added.").format(where, _(doc.fieldtype))
		)
	if doc.get("is_virtual"):
		frappe.throw(_("{0}: computed fields can't be added.").format(where))
	if doc.get("permlevel") or doc.get("ignore_user_permissions"):
		frappe.throw(_("{0}: who can see a field is set by roles.").format(where))
	if doc.fieldtype == "Data" and (doc.options or "") not in DATA_OPTIONS:
		frappe.throw(
			_(
				"{0}: a text field may hold any text, or an email, a name, a phone number, a web address, a barcode or an IBAN."
			).format(where)
		)
	_conditions(doc, where)
	_fetched(doc, where)


def _fetched(doc, where: str) -> None:
	"""A field filled from a record this one links to (`fetch_from`: the Link
	field, a dot, the field there) only shows what whoever saves may read: a
	Link field of this form, and a field of that record at no level above the
	first, of a kind that is not a secret."""
	if not doc.get("fetch_from"):
		return
	link, _dot, field = (doc.fetch_from or "").partition(".")
	through = frappe.get_meta(doc.dt).get_field(link)
	if not through or through.fieldtype != "Link" or not field:
		frappe.throw(_("{0}: a field is filled through a Link field of the same form.").format(where))
	there = frappe.get_meta(through.options).get_field(field)
	if not there or there.permlevel or there.fieldtype in ("Password", "Code", "HTML", "Button"):
		frappe.throw(
			_("{0}: {1} has no field {2} visible to everyone who can read it.").format(
				where, _(through.options), field
			)
		)
	if not frappe.has_permission(through.options, "read"):
		frappe.throw(_("{0}: you cannot read {1}.").format(where, _(through.options)))


DEFAULTS = ("default_print_format", "default_email_template")


def set_default(doctype: str, prop: str, value: str) -> None:
	"""A doctype's default print format or mail template, as frappe's own
	make_default writes it: a property setter, which this layer would refuse
	and which frappe writes as whoever calls it. The caller has checked the
	doctype and the value."""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	if prop not in DEFAULTS:
		frappe.throw(_("{0} can't be changed in a workspace.").format(prop))
	frappe.flags.one_default = prop
	try:
		make_property_setter(doctype, None, prop, value, "Data", for_doctype=True, is_system_generated=False)
	finally:
		frappe.flags.one_default = None
	frappe.clear_cache(doctype=doctype)


def property_setter(doc, method=None) -> None:
	"""A change to a field the workspace did not make."""
	if not held():
		return
	where = doc.field_name or doc.doc_type
	if (
		frappe.flags.one_numbering
		and doc.field_name == "naming_series"
		and doc.property in ("options", "default")
	):
		return
	if (
		frappe.flags.one_default
		and doc.doctype_or_field == "DocType"
		and doc.property == frappe.flags.one_default
	):
		return
	# Global Defaults hides or shows the rounded total and the amount in
	# words on every sale and purchase as its own on_update does
	# (one/control.py _save_amounts).
	if frappe.flags.one_amounts and doc.property in ("hidden", "print_hide", "read_only"):
		return
	if (
		frappe.flags.one_named_by
		and doc.doc_type == frappe.flags.one_named_by
		and doc.property in ("hidden", "reqd", "unique", "autoname", "naming_rule")
	):
		return
	if doc.property not in PROPERTIES:
		frappe.throw(_("{0}: {1} can't be changed in a workspace.").format(where, doc.property))
	if doc.property in ("depends_on", "mandatory_depends_on", "read_only_depends_on") and not plain(
		doc.value
	):
		frappe.throw(
			_("{0}: a condition may only compare the record's fields with plain values.").format(where)
		)
	if doc.property == "reqd" and not int(doc.value or 0) and doc.field_name:
		base = frappe.db.get_value("DocField", {"parent": doc.doc_type, "fieldname": doc.field_name}, "reqd")
		if base:
			frappe.throw(_("{0}: this field is required by the record itself.").format(where))


def script(doc, method=None) -> None:
	"""Code in every reader's browser, or on the server, is nobody's to write
	from a workspace."""
	if frappe.flags.one_workspace_layer:
		frappe.throw(_("A workspace customizes with fields and settings, never with code."))
