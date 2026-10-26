"""Lists: the short lists records pick their values from, each declared by
its module as `LISTS` in its `lists.py` (One's here, the Address Book's) and
kept at the end of the module's ControlCenter (public/js/lists.js). How it
works is in One's README, under lists.py."""

import importlib
import re

import frappe
from frappe import _, _lt

from onedesk.one import layer, roles, rules

LISTS = (
	("Salutation", _lt("Salutations"), _lt("Salutation")),
	("Gender", _lt("Genders"), _lt("Gender")),
	("Address Template", _lt("Address Templates"), _lt("Address Template")),
)

# The modules with lists, each with its folder, in the order a reader who
# sees several meets them.
HOMES = {
	"One": "one",
	"OneCRM": "one_crm",
	"OneBook": "one_book",
	"OneInventory": "one_inventory",
	"OneProject": "one_project",
	"OneHR": "one_hr",
	"OneStudio": "one_studio",
}

TAG = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)

FIELD = re.compile(r"\{\{-?\s*([a-z][a-z0-9_]*)\s*-?\}\}")
IF = re.compile(r"\{%-?\s*if\s+([a-z][a-z0-9_]*)\s*-?%\}")
END = re.compile(r"\{%-?\s*(endif|else)\s*-?%\}")

WORDS = re.compile(r"""\{\{-?\s*_\(\s*(?:"[^"{}%\\]*"|'[^'{}%\\]*')\s*\)\s*-?\}\}""")


def declared() -> dict[str, tuple]:
	"""Every module's `LISTS`, by module."""
	return {module: importlib.import_module(f"onedesk.{folder}.lists").LISTS for module, folder in HOMES.items()}


def kinds_of() -> list[tuple]:
	"""Every list as (module, doctype, plural, singular)."""
	return [(module, *one) for module, lists in declared().items() for one in lists]


def _modules() -> set[str]:
	"""The modules whose lists the reader keeps: all of them for an
	administrator, else each app they manage. One's and OneStudio's are the
	administrators' alone."""
	from onedesk.one.people import ALWAYS, APPS

	if roles.administers():
		return set(HOMES)
	held = set(frappe.get_roles())
	return {label for label, _code, _users, managers in APPS if label not in ALWAYS and label in HOMES and held & set(managers)}


def _open(doctype: str) -> bool:
	return frappe.db.exists("DocType", doctype) and frappe.has_permission(doctype, "read")


def listed() -> dict[str, list[str]]:
	"""Boot: the lists the reader may open, by module, for each module's
	ControlCenter and the nav pane beside a list."""
	mine = _modules()
	said = {}
	for module, doctype, _label, _one in kinds_of():
		if module in mine and _open(doctype):
			said.setdefault(module, []).append(doctype)
	return said


@frappe.whitelist()
def kinds(module: str) -> list[dict]:
	"""A module's lists the reader may open, with how many values each has:
	its ControlCenter's Lists and the nav pane's tree."""
	if module not in _modules():
		frappe.throw(_("Only administrators and the app's managers keep its lists."), frappe.PermissionError)
	return [
		{"doctype": doctype, "label": str(label), "count": frappe.db.count(doctype, _below_root(doctype))}
		for one, doctype, label, _one in kinds_of()
		if one == module and _open(doctype)
	]


def _below_root(doctype: str) -> dict:
	"""A tree's values, without the root they all hang from ("All Customer
	Groups"), which is erpnext's and is never picked."""
	meta = frappe.get_meta(doctype)
	return {meta.nsm_parent_field: ("is", "set")} if meta.is_tree else {}


# What OneAI offers on any list (`one_ai_suggestions`).
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


def suggestions() -> dict[str, list[dict]]:
	return {doctype: OFFERED for _module, doctype, _label, _one in kinds_of()}


def homes() -> dict[str, list[dict]]:
	"""`one_homes`: a value's form leads back to its module's Lists and its
	own list."""
	mine = _modules()
	return {
		doctype: [
			{"label": _("{0} Lists").format(module), "route": f"/desk/one?center=settings&module={module}&at=lists"},
			{"label": str(label), "route": f"/desk/{doctype.lower().replace(' ', '-')}"},
		]
		for module, doctype, label, _one in kinds_of()
		if module in mine
	}


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
