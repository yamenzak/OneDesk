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
	_conditions(doc, where)


def property_setter(doc, method=None) -> None:
	"""A change to a field the workspace did not make."""
	if not held():
		return
	where = doc.field_name or doc.doc_type
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
