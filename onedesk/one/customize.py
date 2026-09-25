"""The Customize page: a workspace changes a form the way frappe lets a System
Manager change one, and nothing it writes is code. docs/SHELL.md, decision 6.

What a workspace administrator changes here is frappe's own records, and one
of ours:

- **Fields**: a field's label, whether it is hidden, required or in the list,
  and the order of them all, as **Property Setters**; a field of the
  workspace's own, as a **Custom Field**, which it may change again or take
  away. A field the record came with may be hidden, never removed.
- **Above the fields**: rows of the doctype's **Record Head** (one/head.py):
  numbers in the band, verbs a module registered, and linked sections
  (one/linked.py). A module's own rows are shown and kept; the workspace's are
  marked `custom`, so a migrate keeps them too.
- **Connections and buttons**: the DocType's own Links and Actions, marked
  `custom` as frappe's Customize Form marks them. A button here only goes
  somewhere; one that runs something is a verb.

Every row is written under `frappe.flags.one_workspace_layer`, so the holds in
one/layer.py read it as the workspace's, and it is saved against the state
the page loaded (`state`), so two administrators do not overwrite each other.
What frappe does not mark (a custom field, a property setter) the page writes
into a ledger, **Workspace Customization**, and **Reset** takes back what the
ledger names and nothing else: a module's customizations are never the
workspace's to remove.
"""

import json
import re

import frappe
from frappe import _
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.utils import cint, cstr

from onedesk.one import head as heads
from onedesk.one import layer, roles

#: Modules that are the framework, or One itself, which no workspace changes.
REFUSED_MODULES = (
	"Core",
	"Custom",
	"Desk",
	"Integrations",
	"Printing",
	"Website",
	"Workflow",
	"Automation",
	"Email",
	"One",
	"One Admin",
	"One AI",
	"One Legal",
)

#: What the page changes about a field the record came with.
FIELD_PROPERTIES = ("label", "hidden", "reqd", "in_list_view")

#: The columns of each Record Head table the page edits.
HEAD_COLUMNS = {
	"band": (
		"label",
		"source",
		"field",
		"link_field",
		"of_doctype",
		"filters",
		"measure",
		"shown_when",
		"route",
		"tone",
		"hide_empty",
	),
	"verbs": ("verb", "label", "primary"),
	"linked": ("label", "link_field", "fields", "placed_in"),
}

#: Where a button may go: a route inside the desk, nothing that runs.
ROUTE = re.compile(r"/?(app/)?[A-Za-z0-9][A-Za-z0-9_\-/ ?=&%.]*")


def may(doctype: str) -> None:
	"""Only a workspace administrator, and only on a form of the business
	they may read: not a table, not a single, not the framework's."""
	roles.require()
	if not frappe.db.exists("DocType", doctype):
		frappe.throw(_("{0} is not a form here.").format(doctype))
	meta = frappe.get_meta(doctype)
	if meta.istable or meta.issingle or meta.module in REFUSED_MODULES:
		frappe.throw(_("{0} is not a form a workspace customizes.").format(_(doctype)))
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("You cannot open {0}.").format(_(doctype)), frappe.PermissionError)


# ------------------------------------------------------------------ the ledger


def _ledger(doctype: str, kind: str) -> set[str]:
	return set(
		frappe.get_all(
			"Workspace Customization", filters={"record_doctype": doctype, "kind": kind}, pluck="row"
		)
	)


def _note(doctype: str, kind: str, row: str) -> None:
	if not frappe.db.exists("Workspace Customization", {"record_doctype": doctype, "kind": kind, "row": row}):
		frappe.get_doc(
			{"doctype": "Workspace Customization", "record_doctype": doctype, "kind": kind, "row": row}
		).insert(ignore_permissions=True)


def _forget(doctype: str, kind: str, row: str) -> None:
	frappe.db.delete("Workspace Customization", {"record_doctype": doctype, "kind": kind, "row": row})


def state(doctype: str) -> str:
	"""The state of a doctype's customizations, as the page loaded it: a
	save made against another is refused."""
	said = []
	for table, where in (
		("Property Setter", "doc_type"),
		("Custom Field", "dt"),
		("Workspace Customization", "record_doctype"),
		("Record Head", "name"),
	):
		said.append(
			frappe.db.sql(f"select count(*), max(modified) from `tab{table}` where `{where}`=%s", doctype)[0]
		)
	for table in ("DocType Link", "DocType Action"):
		said.append(
			frappe.db.sql(
				f"select count(*), max(modified) from `tab{table}` where parent=%s and custom=1", doctype
			)[0]
		)
	return "|".join(f"{cint(count)}:{cstr(modified)}" for count, modified in said)


# ------------------------------------------------------------------ what the page is given


@frappe.whitelist()
def load(doctype: str) -> dict:
	may(doctype)
	meta = frappe.get_meta(doctype)
	mine = _ledger(doctype, "Custom Field")
	custom = {
		row.fieldname: row.name
		for row in frappe.get_all("Custom Field", filters={"dt": doctype}, fields=["name", "fieldname"])
	}
	fields = [
		{
			"fieldname": df.fieldname,
			"label": df.label or "",
			"fieldtype": df.fieldtype,
			"options": df.options if custom.get(df.fieldname) in mine else "",
			"hidden": cint(df.hidden),
			"reqd": cint(df.reqd),
			"in_list_view": cint(df.in_list_view),
			"mine": cint(custom.get(df.fieldname) in mine),
		}
		for df in meta.fields
	]
	head = frappe.get_doc("Record Head", doctype) if frappe.db.exists("Record Head", doctype) else None
	rows = {
		table: [
			{key: row.get(key) for key in columns} for row in (head.get(table) if head else []) if row.custom
		]
		for table, columns in HEAD_COLUMNS.items()
	}
	declared = sum(1 for table in heads.TABLES for row in (head.get(table) if head else []) if not row.custom)
	return {
		"doctype": doctype,
		"label": _(doctype),
		"token": state(doctype),
		"values": {
			"fields": fields,
			**rows,
			"links": frappe.get_all(
				"DocType Link",
				filters={"parent": doctype, "custom": 1},
				fields=["link_doctype", "link_fieldname", "group"],
				order_by="idx",
			),
			"actions": frappe.get_all(
				"DocType Action",
				filters={"parent": doctype, "custom": 1, "action_type": "Route"},
				fields=["label", "action", "group"],
				order_by="idx",
			),
		},
		"declared": declared,
		"declared_by": head.module if head and head.module else None,
		"choices": {
			"kinds": list(layer.KINDS),
			"verbs": sorted(name for name, verb in heads.verbs().items() if doctype in verb["doctypes"]),
			"measures": sorted(heads.measures()),
			"links": [df.fieldname for df in meta.fields if df.fieldtype == "Link"],
			"fields": [
				df.fieldname for df in meta.fields if df.fieldtype not in frappe.model.no_value_fields
			],
		},
	}


# ------------------------------------------------------------------ saved


@frappe.whitelist(methods=["POST"])
def save(doctype: str, values: str | dict, token: str) -> dict:
	"""Everything the page changed, in one transaction, held as the
	workspace's, and refused if somebody saved the doctype's customizations
	since the page loaded them."""
	may(doctype)
	if token != state(doctype):
		frappe.throw(
			_(
				"Somebody changed how {0} looks after you opened this. Refresh to see it; nothing was saved."
			).format(_(doctype)),
			frappe.TimestampMismatchError,
		)
	values = frappe.parse_json(values)
	frappe.flags.one_workspace_layer = True
	try:
		# Everything is checked before anything is written: adding a field
		# alters the table, which the database commits there and then, so a
		# refusal half-way would leave half a save.
		_check(doctype, values)
		_fields(doctype, values.get("fields") or [])
		_head(doctype, values)
		_links(doctype, values.get("links") or [])
		_actions(doctype, values.get("actions") or [])
	finally:
		frappe.flags.one_workspace_layer = False
	_changed(doctype)
	return load(doctype)


def _changed(doctype: str) -> None:
	frappe.clear_cache(doctype=doctype)
	frappe.cache.delete_value(heads.CACHE)


def _set(doctype: str, fieldname: str | None, prop: str, value) -> None:
	"""A property of a field, or of the form when `fieldname` is None, as a
	Property Setter the ledger names."""
	kind = frappe.get_meta("DocField").get_field(prop)
	setter = make_property_setter(
		doctype,
		fieldname,
		prop,
		value,
		kind.fieldtype if kind else "Data",
		for_doctype=fieldname is None,
		validate_fields_for_doctype=False,
		is_system_generated=False,
	)
	_note(doctype, "Property Setter", setter.name)


def _same(a, b) -> bool:
	return cstr(a if a is not None else "") == cstr(b if b is not None else "")


def _fields(doctype: str, rows: list) -> None:
	meta = frappe.get_meta(doctype)
	current = {df.fieldname: df for df in meta.fields}
	custom = {
		row.fieldname: row.name
		for row in frappe.get_all("Custom Field", filters={"dt": doctype}, fields=["name", "fieldname"])
	}
	mine = _ledger(doctype, "Custom Field")
	order = []
	for row in rows:
		name = row.get("fieldname")
		if name in current:
			df = current[name]
			if cint(row.get("hidden")) and cint(row.get("reqd")) and not df.default:
				frappe.throw(
					_("{0} is required, so it cannot be hidden.").format(_(row.get("label") or name))
				)
			if custom.get(name) in mine:
				field = frappe.get_doc("Custom Field", custom[name])
				changed = [
					key
					for key in (*FIELD_PROPERTIES, "fieldtype", "options")
					if key in row and not _same(row[key], field.get(key))
				]
				for key in changed:
					field.set(key, row[key])
				if changed:
					field.save(ignore_permissions=True)
			else:
				for key in FIELD_PROPERTIES:
					if key in row and not _same(row[key], df.get(key)):
						_set(doctype, name, key, row[key])
			order.append(name)
			continue
		if row.get("fieldtype") not in ("Column Break", "Section Break", "Tab Break") and not row.get(
			"label"
		):
			frappe.throw(_("A new field needs a label."))
		field = frappe.get_doc(
			{
				"doctype": "Custom Field",
				"dt": doctype,
				"label": row.get("label"),
				"fieldname": None
				if row.get("label")
				else f"custom_{frappe.scrub(row.get('fieldtype'))}_{frappe.generate_hash(length=6)}",
				"fieldtype": row.get("fieldtype") or "Data",
				"options": row.get("options"),
				"reqd": cint(row.get("reqd")),
				"hidden": cint(row.get("hidden")),
				"in_list_view": cint(row.get("in_list_view")),
				"insert_after": order[-1] if order else None,
				"is_system_generated": 0,
			}
		).insert(ignore_permissions=True)
		_note(doctype, "Custom Field", field.name)
		order.append(field.fieldname)
	kept = set(order)
	for name, row_name in custom.items():
		if row_name in mine and name not in kept:
			frappe.delete_doc("Custom Field", row_name, ignore_permissions=True, force=True)
			_forget(doctype, "Custom Field", row_name)
	gone = [df for name, df in current.items() if name not in kept and custom.get(name) not in mine]
	if gone:
		frappe.throw(
			_("{0} came with the record, so it cannot be taken away. Hide it instead.").format(
				", ".join(_(df.label or df.fieldname) for df in gone)
			)
		)
	if order != [df.fieldname for df in meta.fields]:
		_set(doctype, None, "field_order", json.dumps(order))


def _check(doctype: str, values: dict) -> None:
	"""Every refusal the save could meet, met before it writes anything."""
	meta = frappe.get_meta(doctype)
	current = {df.fieldname: df for df in meta.fields}
	custom = {
		row.fieldname: row.name
		for row in frappe.get_all("Custom Field", filters={"dt": doctype}, fields=["name", "fieldname"])
	}
	mine = _ledger(doctype, "Custom Field")
	seen = set()
	for row in values.get("fields") or []:
		name = row.get("fieldname")
		label = _(row.get("label") or name or "")
		if name in current:
			seen.add(name)
			df = current[name]
			if cint(row.get("hidden")) and cint(row.get("reqd")) and not df.default:
				frappe.throw(_("{0} is required, so it cannot be hidden.").format(label))
			if custom.get(name) in mine:
				kind = row.get("fieldtype")
				if kind and kind not in layer.KINDS:
					frappe.throw(
						_("{0}: a workspace cannot add a field of the kind {1}.").format(label, _(kind))
					)
			elif "reqd" in row and not cint(row["reqd"]) and cint(df.reqd):
				if frappe.db.get_value("DocField", {"parent": doctype, "fieldname": name}, "reqd"):
					frappe.throw(_("{0}: this field is required by the record itself.").format(label))
			continue
		kind = row.get("fieldtype") or "Data"
		if kind not in layer.KINDS:
			frappe.throw(
				_("{0}: a workspace cannot add a field of the kind {1}.").format(label or "?", _(kind))
			)
		if kind not in ("Column Break", "Section Break", "Tab Break") and not row.get("label"):
			frappe.throw(_("A new field needs a label."))
	gone = [df for name, df in current.items() if name not in seen and custom.get(name) not in mine]
	if gone:
		frappe.throw(
			_("{0} came with the record, so it cannot be taken away. Hide it instead.").format(
				", ".join(_(df.label or df.fieldname) for df in gone)
			)
		)
	trial = frappe.get_doc(
		{
			"doctype": "Record Head",
			"record_doctype": doctype,
			**{table: [dict(row) for row in values.get(table) or []] for table in HEAD_COLUMNS},
		}
	)
	heads.validate(trial)
	for row in values.get("links") or []:
		other = row.get("link_doctype")
		if not other or not frappe.db.exists("DocType", other) or not frappe.has_permission(other, "read"):
			frappe.throw(_("Connections: {0} is not a form you can read.").format(other or "?"))
		if not frappe.get_meta(other).get_field(row.get("link_fieldname") or ""):
			frappe.throw(_("Connections: {0} has no field {1}.").format(_(other), row.get("link_fieldname")))
	for row in values.get("actions") or []:
		if not row.get("label") or not ROUTE.fullmatch((row.get("action") or "").strip()):
			frappe.throw(
				_("Buttons: {0} needs a label and a place in the desk to go.").format(row.get("label") or "?")
			)


def _head(doctype: str, values: dict) -> None:
	"""The workspace's rows of the doctype's Record Head: a module's rows stay
	as they are, first."""
	rows = {table: values.get(table) or [] for table in HEAD_COLUMNS}
	there = frappe.db.exists("Record Head", doctype)
	if not there and not any(rows.values()):
		return
	head = frappe.get_doc("Record Head", doctype) if there else frappe.new_doc("Record Head")
	if not there:
		head.update({"record_doctype": doctype, "enabled": 1})
	for table, columns in HEAD_COLUMNS.items():
		head.set(table, [row for row in head.get(table) if not row.custom])
		for row in rows[table]:
			head.append(table, {**{key: row.get(key) for key in columns if key in row}, "custom": 1})
	if not head.module and not any(head.get(table) for table in heads.TABLES):
		if there:
			frappe.delete_doc("Record Head", doctype, ignore_permissions=True, force=True)
		return
	head.flags.ignore_permissions = True
	head.save()


def _links(doctype: str, rows: list) -> None:
	"""Connections: another doctype's records that link to this one."""
	frappe.db.delete("DocType Link", {"parent": doctype, "custom": 1})
	for at, row in enumerate(rows):
		other = row.get("link_doctype")
		if not other or not frappe.db.exists("DocType", other) or not frappe.has_permission(other, "read"):
			frappe.throw(_("Connections: {0} is not a form you can read.").format(other or "?"))
		if not frappe.get_meta(other).get_field(row.get("link_fieldname") or ""):
			frappe.throw(_("Connections: {0} has no field {1}.").format(_(other), row.get("link_fieldname")))
		frappe.get_doc(
			{
				"doctype": "DocType Link",
				"parent": doctype,
				"parenttype": "DocType",
				"parentfield": "links",
				"link_doctype": other,
				"link_fieldname": row.get("link_fieldname"),
				"group": row.get("group"),
				"custom": 1,
				"idx": 1000 + at,
			}
		).db_insert()


def _actions(doctype: str, rows: list) -> None:
	"""Buttons that go somewhere in the desk. One that runs something is a
	verb, which a module registers."""
	frappe.db.delete("DocType Action", {"parent": doctype, "custom": 1})
	for at, row in enumerate(rows):
		route = (row.get("action") or "").strip()
		if not row.get("label") or not ROUTE.fullmatch(route):
			frappe.throw(
				_("Buttons: {0} needs a label and a place in the desk to go.").format(row.get("label") or "?")
			)
		frappe.get_doc(
			{
				"doctype": "DocType Action",
				"parent": doctype,
				"parenttype": "DocType",
				"parentfield": "actions",
				"label": row.get("label"),
				"action_type": "Route",
				"action": route,
				"group": row.get("group"),
				"custom": 1,
				"idx": 1000 + at,
			}
		).db_insert()


# ------------------------------------------------------------------ taken back, and taken away


@frappe.whitelist(methods=["POST"])
def reset(doctype: str) -> dict:
	"""Everything the workspace changed about a form, taken back: what the
	ledger names, the head's own rows, and its connections and buttons."""
	may(doctype)
	for row in _ledger(doctype, "Custom Field"):
		if frappe.db.exists("Custom Field", row):
			frappe.delete_doc("Custom Field", row, ignore_permissions=True, force=True)
	for row in _ledger(doctype, "Property Setter"):
		frappe.db.delete("Property Setter", {"name": row})
	frappe.db.delete("Workspace Customization", {"record_doctype": doctype})
	_head(doctype, {})
	frappe.db.delete("DocType Link", {"parent": doctype, "custom": 1})
	frappe.db.delete("DocType Action", {"parent": doctype, "custom": 1})
	_changed(doctype)
	return load(doctype)


@frappe.whitelist()
def export(doctype: str) -> dict:
	"""What the workspace changed about a form, as the rows themselves: to keep,
	or to read."""
	may(doctype)
	return {
		"doctype": doctype,
		"custom_fields": [
			frappe.get_doc("Custom Field", row).as_dict(no_default_fields=True)
			for row in sorted(_ledger(doctype, "Custom Field"))
			if frappe.db.exists("Custom Field", row)
		],
		"property_setters": [
			frappe.get_doc("Property Setter", row).as_dict(no_default_fields=True)
			for row in sorted(_ledger(doctype, "Property Setter"))
			if frappe.db.exists("Property Setter", row)
		],
		**{key: value for key, value in load(doctype)["values"].items() if key != "fields"},
	}
