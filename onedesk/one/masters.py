"""Masters: the short lists records pick their values from. A salutation, a
gender, a customer group, a unit, a department.

Each is frappe's own list and form (docs/WINDOW.md, the screen contract); what
is ours is which they are, grouped by the app that uses them, as a tree in the
nav pane beside any one of them (public/js/masters.js), and One's rail >
Masters, which opens the one last open.
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


# What OneAI offers on any kind's list (`one_ai_suggestions`).
OFFERED = [
	{
		"label": _lt("Add several at once"),
		"ask": _lt(
			"I will paste a list. Suggest each line as a new value of the list I have open, leaving out any "
			"it already has."
		),
		"expects": "create_record",
	},
	{
		"label": _lt("What is this list for?"),
		"ask": _lt("What is the list I have open used for, on which records, and who may change it?"),
		"expects": "how_to",
	},
]

SUGGESTIONS = {doctype: OFFERED for _group, doctype, _label, _one in KINDS}


def homes() -> dict[str, list[dict]]:
	"""`one_homes`: a value's form leads back to Masters and its kind's list."""
	groups = _groups()
	return {
		doctype: [
			{"label": _("Masters"), "route": "/desk/masters"},
			{"label": str(label), "route": f"/desk/{doctype.lower().replace(' ', '-')}"},
		]
		for group, doctype, label, _one in KINDS
		if group in groups
	}


def listed() -> list[str]:
	"""Boot: the kinds the reader may open, for the nav pane's tree. None for
	whoever sees no Masters."""
	try:
		groups = _groups()
	except frappe.PermissionError:
		return []
	return [
		doctype
		for group, doctype, _label, _one in KINDS
		if group in groups and frappe.db.exists("DocType", doctype) and frappe.has_permission(doctype, "read")
	]


@frappe.whitelist()
def kinds() -> list[dict]:
	"""Every kind the reader may open, grouped, with how many values each has:
	the nav pane's tree."""
	from onedesk.one import settings

	groups = _groups()
	return [
		{
			"group": group,
			"doctype": doctype,
			"label": str(label),
			"mark": settings._mark("" if group == "Shared" else group),
			"count": frappe.db.count(doctype, _below_root(doctype)),
		}
		for group, doctype, label, _one in KINDS
		if group in groups and frappe.db.exists("DocType", doctype) and frappe.has_permission(doctype, "read")
	]


def _below_root(doctype: str) -> dict:
	"""A tree's values, without the root they all hang from ("All Customer
	Groups"), which is erpnext's and is never picked."""
	meta = frappe.get_meta(doctype)
	return {meta.nsm_parent_field: ("is", "set")} if meta.is_tree else {}


def place(doc, method=None) -> None:
	"""before_insert: a tree's new value goes under its root unless it names a
	parent, and a department is the workspace's company's. erpnext's forms do
	this in the browser, so a value made anywhere else (a OneAI card, the
	create dialog's own form) would otherwise be a second root, which frappe
	refuses."""
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
