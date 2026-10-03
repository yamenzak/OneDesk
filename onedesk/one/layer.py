"""The workspace layer, held: what a workspace may change about a form, and
what it may not.

A workspace customizes a form with frappe's own records (Custom Field and
Property Setter, the DocType's Links and Actions) and one of ours (Record
Head), on the Customize page (one/customize.py). Frappe trusts whoever writes
those, because only the people it lets customize can. A workspace administrator is not
that, so every row written through the Customize page, and any written by
somebody frappe does not let customize, is **held** here, as a workspace's
notification rule is (one/rules.py). docs/SHELL.md, decision 6.

- **Nothing that runs.** No virtual field (its options are Python), no HTML
  field (its options are markup the desk puts on the page), no button, and a
  `depends_on` that is a field's name or a comparison of fields and plain
  values, read by `plain` rather than run: the desk runs an `eval:` as
  JavaScript in every reader's browser, and a row anybody here may write that
  runs there turns "may customize a form" into "may act as whoever opens it".
  Client and Server Scripts are refused outright.
- **Nothing that weakens a guard.** No permission level, no ignoring user
  permissions, no field made optional that frappe made mandatory, no Link or
  table pointed somewhere else, and no field changed into another kind.
"""

import re

import frappe
from frappe import _

#: The kinds of field a workspace may add: what a person types or picks.
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

#: What a field the workspace adds may say about itself, besides its kind,
#: label, choices and place: how it is checked, shown, copied and carried.
#: Nothing here runs; `fetch_from` is held by `_fetched`.
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

#: What a Data field may hold besides any text, checked by frappe as it saves.
DATA_OPTIONS = ("", "Email", "Name", "Phone", "URL", "Barcode", "IBAN")

#: What a workspace may change about a field, or a form (`field_order`).
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

#: What a condition is written from: a field of the record, a plain value, a
#: comparison, and nothing that calls or reaches past the record.
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
		# A field followed by a bracket is a call, not a comparison.
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
			_("{0}: a workspace cannot add a field of the kind {1}.").format(where, _(doc.fieldtype))
		)
	if doc.get("is_virtual"):
		frappe.throw(_("{0}: a field worked out by code is not the workspace's to add.").format(where))
	if doc.get("permlevel") or doc.get("ignore_user_permissions"):
		frappe.throw(_("{0}: who may see a field is set by the roles, not here.").format(where))
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
			_("{0}: {1} has no field {2} that everybody who reads it may see.").format(
				where, _(through.options), field
			)
		)
	if not frappe.has_permission(through.options, "read"):
		frappe.throw(_("{0}: you cannot read {1}.").format(where, _(through.options)))


#: The doctype defaults a module may set through set_default.
DEFAULTS = ("default_print_format", "default_email_template")


def set_default(doctype: str, prop: str, value: str) -> None:
	"""A doctype's default print format or mail template, as frappe's own
	make_default writes it: a property setter, which this layer would refuse
	and which frappe writes as whoever calls it. The caller has checked the
	doctype and the value."""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	if prop not in DEFAULTS:
		frappe.throw(_("{0} is not the workspace's to change.").format(prop))
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
	# A doctype's series, written by Numbering (one/numbering.py), which has checked
	# the doctype is the workspace's and frappe's own update_series has checked each
	# series; only the naming_series field's options and default, and only from there.
	if (
		frappe.flags.one_numbering
		and doc.field_name == "naming_series"
		and doc.property in ("options", "default")
	):
		return
	# A doctype's default print format or mail template, set through set_default by
	# the module that has checked it (one/printing.py, one/mail_templates.py).
	if (
		frappe.flags.one_default
		and doc.doctype_or_field == "DocType"
		and doc.property == frappe.flags.one_default
	):
		return
	# How a kind of record is named, from Numbering (one/numbering.py set_naming_by),
	# which has checked the kind and the choice, and writes what Customize Form would:
	# the autoname and naming rule, the series shown or hidden, and the field a record
	# is named by made required and unique.
	if (
		frappe.flags.one_named_by
		and doc.doc_type == frappe.flags.one_named_by
		and doc.property in ("hidden", "reqd", "unique", "autoname", "naming_rule")
	):
		return
	if doc.property not in PROPERTIES:
		frappe.throw(_("{0}: {1} is not the workspace's to change.").format(where, doc.property))
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
