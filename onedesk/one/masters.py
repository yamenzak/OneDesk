"""Masters: the short lists records pick their values from, in one place,
One's rail > Masters (page `masters`). A salutation, a gender, a customer group,
a unit, a department.
"""

import re

import frappe
from frappe import _, _lt

from onedesk.one import layer, roles, rules

KINDS = (
	("Shared", "Salutation", _lt("Salutations"), _lt("Salutation")),
	("Shared", "Gender", _lt("Genders"), _lt("Gender")),
	("Shared", "Print Heading", _lt("Print Headings"), _lt("Print Heading")),
	("Shared", "Address Template", _lt("Address Templates"), _lt("Address Template")),
	("OneCRM", "Customer Group", _lt("Customer Groups"), _lt("Customer Group")),
	("OneCRM", "Territory", _lt("Territories"), _lt("Territory")),
	("OneCRM", "Industry Type", _lt("Industries"), _lt("Industry")),
	("OneCRM", "Market Segment", _lt("Market Segments"), _lt("Market Segment")),
	("OneCRM", "UTM Source", _lt("Lead Sources"), _lt("Lead Source")),
	("OneCRM", "Opportunity Lost Reason", _lt("Lost Reasons"), _lt("Lost Reason")),
	("OneCRM", "Issue Type", _lt("Issue Types"), _lt("Issue Type")),
	("OneCRM", "Issue Priority", _lt("Issue Priorities"), _lt("Issue Priority")),
	("OneBook", "Tax Category", _lt("Tax Categories"), _lt("Tax Category")),
	("OneBook", "Finance Book", _lt("Finance Books"), _lt("Finance Book")),
	("OneInventory", "Item Group", _lt("Item Groups"), _lt("Item Group")),
	("OneInventory", "Brand", _lt("Brands"), _lt("Brand")),
	("OneInventory", "UOM", _lt("Units"), _lt("Unit")),
	("OneInventory", "UOM Category", _lt("Unit Categories"), _lt("Unit Category")),
	("OneInventory", "Item Attribute", _lt("Attributes"), _lt("Attribute")),
	("OneInventory", "Supplier Group", _lt("Supplier Groups"), _lt("Supplier Group")),
	("OneProject", "Project Type", _lt("Project Types"), _lt("Project Type")),
	("OneHR", "Department", _lt("Departments"), _lt("Department")),
	("OneHR", "Designation", _lt("Designations"), _lt("Designation")),
	("OneHR", "Branch", _lt("Branches"), _lt("Branch")),
	("OneHR", "Employment Type", _lt("Employment Types"), _lt("Employment Type")),
	("OneHR", "Skill", _lt("Skills"), _lt("Skill")),
	("OneHR", "KRA", _lt("Key Result Areas"), _lt("Key Result Area")),
	("OneHR", "Grievance Type", _lt("Grievance Types"), _lt("Grievance Type")),
	("OneHR", "Identification Document Type", _lt("ID Document Types"), _lt("ID Document Type")),
)

KEPT = {"lft", "rgt", "old_parent", "company"}

HELD = {"Item Attribute": {"item_attribute_values": _lt("Values")}}

LABEL = {"Department": "department_name"}

TAG = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)

FIELD = re.compile(r"\{\{-?\s*([a-z][a-z0-9_]*)\s*-?\}\}")
IF = re.compile(r"\{%-?\s*if\s+([a-z][a-z0-9_]*)\s*-?%\}")
END = re.compile(r"\{%-?\s*(endif|else)\s*-?%\}")

WORDS = re.compile(r"""\{\{-?\s*_\(\s*(?:"[^"{}%\\]*"|'[^'{}%\\]*')\s*\)\s*-?\}\}""")



def _groups() -> set[str]:
	"""The groups the reader may see: all of them for an administrator, else
	each app they manage."""
	from onedesk.one.settings import APPS

	if roles.administers():
		return {group for group, _doctype, _label, _one in KINDS}
	held = set(frappe.get_roles())
	mine = {label for label, _code, _users, managers in APPS if held & set(managers)}
	if not mine:
		frappe.throw(_("Only administrators and an app's managers see Masters."), frappe.PermissionError)
	return mine


def _kind(doctype: str) -> tuple:
	found = next((one for one in KINDS if one[1] == doctype), None)
	if not found or found[0] not in _groups():
		frappe.throw(
			_("{0} is not one of the masters you manage.").format(_(doctype)), frappe.PermissionError
		)
	return found


def homes() -> dict[str, list[dict]]:
	"""`one_homes`: a value's form leads back to Masters and its list there."""
	groups = _groups()
	return {
		doctype: [
			{"label": _("Masters"), "route": "/desk/masters"},
			{"label": label, "route": f"/desk/masters?type={doctype}"},
		]
		for group, doctype, label, _one in KINDS
		if group in groups
	}


@frappe.whitelist()
def kinds() -> list[dict]:
	"""Every kind the reader may see, grouped, with how many values each has
	and what they may do with it."""
	from onedesk.one import settings

	groups = _groups()
	out = []
	for group, doctype, label, one in KINDS:
		if group not in groups or not frappe.db.exists("DocType", doctype):
			continue
		if not frappe.has_permission(doctype, "read"):
			continue
		meta = frappe.get_meta(doctype)
		out.append(
			{
				"group": group,
				"doctype": doctype,
				"label": str(label),
				"one": str(one),
				"mark": settings._mark("" if group == "Shared" else group),
				"count": frappe.db.count(doctype, _below_root(doctype)),
				"create": bool(frappe.has_permission(doctype, "create")),
				"delete": bool(frappe.has_permission(doctype, "delete")),
				"rename": bool(meta.allow_rename and frappe.has_permission(doctype, "write")),
				"name_field": _name_field(meta),
				"columns": _columns(meta),
				"tables": _has_tables(meta),
				"held": {field: str(label) for field, label in HELD.get(doctype, {}).items()},
			}
		)
	return out


@frappe.whitelist()
def values(doctype: str) -> list[dict]:
	"""A kind's values: their names, and what frappe's own list of them shows."""
	_kind(doctype)
	meta = frappe.get_meta(doctype)
	field = LABEL.get(doctype)
	fields = [
		"name",
		*([f"{field} as label"] if field else []),
		*(one["fieldname"] for one in _columns(meta)),
	]
	return frappe.get_list(doctype, fields=fields, filters=_below_root(doctype), order_by="name asc", limit=0)


def _name_field(meta) -> str:
	"""The field a value's name is typed in: the one frappe names it from, a
	department's label, or `__newname` for a kind named as it is asked to be."""
	if (meta.autoname or "").startswith("field:"):
		return meta.autoname.removeprefix("field:")
	return LABEL.get(meta.name) or "__newname"


def _columns(meta) -> list[dict]:
	"""What frappe's own list of a kind shows beside the name (in_list_view)."""
	left = {_name_field(meta)} | KEPT
	return [
		{"fieldname": df.fieldname, "label": _(df.label), "fieldtype": df.fieldtype, "options": df.options}
		for df in meta.fields
		if df.in_list_view
		and not df.hidden
		and df.fieldname not in left
		and df.fieldtype not in frappe.model.table_fields
	][:3]


def _has_tables(meta) -> bool:
	"""Whether a kind holds tables (a department's approvers, a customer
	group's accounts), which a dialog leaves to frappe's form."""
	held = HELD.get(meta.name, {})
	return any(df.fieldtype in frappe.model.table_fields and not df.hidden and df.fieldname not in held for df in meta.fields)


def _below_root(doctype: str) -> dict:
	"""A tree's values, without the root they all hang from ("All Customer
	Groups"), which is erpnext's and is never picked."""
	meta = frappe.get_meta(doctype)
	return {meta.nsm_parent_field: ("is", "set")} if meta.is_tree else {}


@frappe.whitelist(methods=["POST"])
def add(doctype: str, values: str | dict) -> str:
	"""A new value, from its dialog (`place` puts it under its tree's root).
	frappe checks whether the reader may make one."""
	_kind(doctype)
	values = frappe.parse_json(values) or {}
	meta = frappe.get_meta(doctype)
	field = _name_field(meta)
	value = str(values.get(field) or "").strip()
	if not value:
		frappe.throw(_("Give it a name."))
	doc = frappe.new_doc(doctype)
	editable = {
		df.fieldname
		for df in meta.fields
		if df.fieldtype not in frappe.model.no_value_fields and df.fieldname not in KEPT
	}
	editable.update(HELD.get(doctype, {}))
	doc.update({key: one for key, one in values.items() if key in editable})
	if field == "__newname":
		doc.set("__newname", value)
	else:
		doc.set(field, value)
	doc.insert()
	return doc.name


def place(doc, method=None) -> None:
	"""before_insert: a tree's new value goes under its root unless it names a
	parent, and a department is the workspace's company's. erpnext's forms do
	this in the browser, so a value made anywhere else (Masters, a OneAI card)
	would otherwise be a second root, which frappe refuses."""
	meta = frappe.get_meta(doc.doctype)
	if meta.is_tree and not doc.get(meta.nsm_parent_field):
		root = frappe.db.get_value(
			doc.doctype, {"is_group": 1, meta.nsm_parent_field: ("in", ("", None))}, "name"
		)
		if root and root != doc.name:
			doc.set(meta.nsm_parent_field, root)
	if meta.has_field("company") and not doc.get("company"):
		doc.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
			"Global Defaults", "default_company"
		)


@frappe.whitelist(methods=["POST"])
def rename(doctype: str, name: str, value: str) -> str:
	"""A value renamed, as frappe renames anything: every record that uses it
	follows. frappe checks the reader may, and that the kind may be renamed."""
	_kind(doctype)
	value = (value or "").strip()
	if not value:
		frappe.throw(_("Give it a name."))
	field = LABEL.get(doctype)
	new = frappe.rename_doc(doctype, name, value) if value != name else name
	if field:
		_relabel(doctype, new, field, value)
	return new


def _relabel(doctype: str, name: str, field: str, value: str) -> None:
	doc = frappe.get_doc(doctype, name)
	if doc.get(field) != value:
		doc.set(field, value)
		doc.save()


@frappe.whitelist()
def used(doctype: str, name: str) -> int:
	"""How many records use a value, by every field that links to its kind."""
	_kind(doctype)
	from frappe.desk.form.linked_with import get_linked_doctypes

	frappe.has_permission(doctype, doc=name, throw=True)
	total = 0
	for linked, info in get_linked_doctypes(doctype).items():
		fields = info.get("fieldname") or []
		table = info.get("child_doctype") or linked
		meta = frappe.get_meta(table)
		if meta.is_virtual:
			continue
		for field in fields if isinstance(fields, list) else [fields]:
			if meta.issingle:
				total += frappe.db.count("Singles", {"doctype": table, "field": field, "value": name})
				continue
			where = {field: name}
			if info.get("doctype_fieldname"):
				where[info["doctype_fieldname"]] = doctype
			total += frappe.db.count(table, where)
	return total


def check_template(text: str | None, kept: set[str]) -> str | None:
	"""What is wrong with an address template, or None."""
	fields = set(rules.readable("Address"))
	for tag in TAG.findall(text or ""):
		if tag in kept or END.fullmatch(tag) or WORDS.fullmatch(tag):
			continue
		found = FIELD.fullmatch(tag) or IF.fullmatch(tag)
		if not found:
			return _("An address template can name a field of the address, as {{ city }}, and nothing else.")
		if found.group(1) not in fields:
			return _("An address has no field {0}.").format(found.group(1))
	return None


def validate_address_template(doc, method=None) -> None:
	"""Address Template validate: what a template the workspace writes may say."""
	if not layer.held():
		return
	before = doc.get_doc_before_save()
	kept = set(TAG.findall(before.template or "")) if before else set()
	wrong = check_template(doc.template, kept)
	if wrong:
		frappe.throw(wrong)
