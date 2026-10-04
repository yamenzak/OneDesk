"""Masters: the short lists records pick their values from, in one place,
One's rail > Masters (page `masters`). A salutation, a gender, a customer group,
a unit, a department.

Each is frappe's or erpnext's own doctype. They are grouped by where they are
used: Shared for what every app's records pick (and the two a printed page
reads), then each app's own. An administrator sees every group; an app's
managers see their app's, and are given what erpnext keeps for a role of its
own (`_give_managers`). Whether a kind can be added to, renamed or removed is
frappe's own permission check, as anywhere else; the workspace administrator
is given the kinds frappe keeps for its System Manager (`settle`), so frappe's
"Create a new" under a field works for them too.

An address template is Jinja, run wherever an address is shown or printed, so
one the workspace writes (layer.held) is held to what a mail template is held
to: every tag it adds names a field of the address, bare, or is an `if` on one
and its `endif`, or a plain label in the reader's language. Every tag it
already had stays, so frappe's own per-country templates can be reworded.
"""

import re

import frappe
from frappe import _, _lt

from onedesk.one import layer, roles, rules

#: (group, doctype, label), in the order the page lists them. "Shared" is
#: the administrator's; an app's group is its managers' too.
KINDS = (
	("Shared", "Salutation", _lt("Salutations")),
	("Shared", "Gender", _lt("Genders")),
	("Shared", "Print Heading", _lt("Print Headings")),
	("Shared", "Address Template", _lt("Address Templates")),
	("OneCRM", "Customer Group", _lt("Customer Groups")),
	("OneCRM", "Territory", _lt("Territories")),
	("OneCRM", "Industry Type", _lt("Industries")),
	("OneCRM", "UTM Source", _lt("Lead Sources")),
	("OneCRM", "Sales Stage", _lt("Sales Stages")),
	("OneInventory", "Item Group", _lt("Item Groups")),
	("OneInventory", "Brand", _lt("Brands")),
	("OneInventory", "UOM", _lt("Units")),
	("OneInventory", "Supplier Group", _lt("Supplier Groups")),
	("OneHR", "Department", _lt("Departments")),
	("OneHR", "Designation", _lt("Designations")),
	("OneHR", "Branch", _lt("Branches")),
	("OneHR", "Employment Type", _lt("Employment Types")),
)

#: What the workspace administrator may do with each kind.
MANAGE = ("read", "write", "create", "delete")

#: Kinds that take more than a name, each with a dialog of its own on the page.
OWN_DIALOG = ("Print Heading", "Address Template")

#: Kinds named by more than their name: a department is "Sales - ONE", for
#: the company, and says "Sales".
LABEL = {"Department": "department_name"}

#: A Jinja tag, as a template is read here: each `{{ }}` and `{% %}` in it.
TAG = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)

#: The tags a workspace adds: a field, an `if` on one, and its end.
FIELD = re.compile(r"\{\{-?\s*([a-z][a-z0-9_]*)\s*-?\}\}")
IF = re.compile(r"\{%-?\s*if\s+([a-z][a-z0-9_]*)\s*-?%\}")
END = re.compile(r"\{%-?\s*(endif|else)\s*-?%\}")

#: A label in the reader's language, as frappe's own templates write one: {{ _("Phone") }}.
WORDS = re.compile(r"""\{\{-?\s*_\(\s*(?:"[^"{}%\\]*"|'[^'{}%\\]*')\s*\)\s*-?\}\}""")


#: Where settle keeps which (kind, role) an app's managers were given, so a
#: change made later in Access stands.
GIVEN = "onedesk_masters_given"


def settle() -> None:
	roles.grant(
		{doctype: MANAGE for _group, doctype, _label in KINDS if frappe.db.exists("DocType", doctype)}
	)
	_give_managers()


def _give_managers() -> None:
	"""An app's managers manage its masters. erpnext keeps several for a role
	of its own (Customer Group for its Sales Master Manager); One's managers
	are given them, once for each kind and role."""
	import json

	from frappe.permissions import add_permission, setup_custom_perms, update_permission_property

	from onedesk.one.settings import APPS

	managers = {label: roles_ for label, _code, _users, roles_ in APPS}
	given = set(json.loads(frappe.db.get_default(GIVEN) or "[]"))
	for group, doctype, _label in KINDS:
		if not frappe.db.exists("DocType", doctype):
			continue
		for role in managers.get(group, ()):
			key = f"{doctype}|{role}"
			if key in given or not frappe.db.exists("Role", role):
				continue
			setup_custom_perms(doctype)
			if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
				add_permission(doctype, role, 0)
			for ptype in MANAGE:
				update_permission_property(doctype, role, 0, ptype, 1, validate=False)
			given.add(key)
	frappe.db.set_default(GIVEN, json.dumps(sorted(given)))


def _groups() -> set[str]:
	"""The groups the reader may see: all of them for an administrator, else
	each app they manage."""
	from onedesk.one.settings import APPS

	if roles.administers():
		return {group for group, _doctype, _label in KINDS}
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


@frappe.whitelist()
def kinds() -> list[dict]:
	"""Every kind the reader may see, grouped, with how many values each has
	and what they may do with it."""
	groups = _groups()
	out = []
	for group, doctype, label in KINDS:
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
				"count": frappe.db.count(doctype, _below_root(doctype)),
				"create": bool(frappe.has_permission(doctype, "create")),
				"delete": bool(frappe.has_permission(doctype, "delete")),
				"rename": bool(meta.allow_rename and frappe.has_permission(doctype, "write")),
				"own_dialog": doctype in OWN_DIALOG,
			}
		)
	return out


@frappe.whitelist()
def values(doctype: str) -> list[dict]:
	"""A kind's values: their names, and for the two with more to them, the rest."""
	_kind(doctype)
	if doctype == "Print Heading":
		return frappe.get_list(
			doctype, fields=["name", "description", "modified"], order_by="name asc", limit=0
		)
	if doctype == "Address Template":
		return frappe.get_list(
			doctype,
			fields=["name", "country", "is_default", "template", "modified"],
			order_by="is_default desc, country asc",
			limit=0,
		)
	field = LABEL.get(doctype)
	fields = ["name", f"{field} as label"] if field else ["name"]
	return frappe.get_list(doctype, fields=fields, filters=_below_root(doctype), order_by="name asc", limit=0)


def _below_root(doctype: str) -> dict:
	"""A tree's values, without the root they all hang from ("All Customer
	Groups"), which is erpnext's and is never picked."""
	meta = frappe.get_meta(doctype)
	return {meta.nsm_parent_field: ("is", "set")} if meta.is_tree else {}


@frappe.whitelist(methods=["POST"])
def add(doctype: str, value: str) -> str:
	"""A new value of a kind that is only a name: a tree's goes under its root,
	a department belongs to the workspace's company. frappe checks whether the
	reader may make one."""
	_kind(doctype)
	value = (value or "").strip()
	if not value:
		frappe.throw(_("Give it a name."))
	meta = frappe.get_meta(doctype)
	doc = frappe.new_doc(doctype)
	if meta.autoname and meta.autoname.startswith("field:"):
		doc.set(meta.autoname.removeprefix("field:"), value)
	elif LABEL.get(doctype):
		# Named by its own code from the label (a department, for the company).
		doc.set(LABEL[doctype], value)
	else:
		# Named as it is asked to be (UTM Source).
		doc.set("__newname", value)
	if meta.is_tree:
		root = frappe.db.get_value(
			doctype, {"is_group": 1, meta.nsm_parent_field: ("in", ("", None))}, "name"
		)
		if root:
			doc.set(meta.nsm_parent_field, root)
	if meta.has_field("company") and not doc.get("company"):
		doc.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
			"Global Defaults", "default_company"
		)
	doc.insert()
	return doc.name


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
			# A settings page's default (Selling Settings' customer group).
			if meta.issingle:
				total += frappe.db.count("Singles", {"doctype": table, "field": field, "value": name})
				continue
			where = {field: name}
			# A Dynamic Link names the kind in another field.
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
