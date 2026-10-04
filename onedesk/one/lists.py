"""Lists: the short choice lists every app's records pick from, and the two a
printed page reads, for a workspace's administrators.

Contacts, employees, users and leads all pick a Salutation and a Gender, so
those belong to the workspace, not to one app: Workspace > Lists. A Print
Heading ("Tax Invoice", "Proforma") and an Address Template only change what a
printed page says, so they are listed in Workspace > Printing. Each is frappe's
own doctype, kept for frappe's System Manager; the workspace administrator is
given it here (roles.grant), and frappe's "Create a new" under a field then
works for them too.

An address template is Jinja, run wherever an address is shown or printed, so
one the workspace writes (layer.held) is held to what a mail template is held
to: every tag it adds names a field of the address, bare, or is an `if` on one
and its `endif`, or a plain label in the reader's language. Every tag it already had stays, so frappe's own per-country
templates can be reworded.
"""

import re

import frappe
from frappe import _, _lt

from onedesk.one import layer, roles, rules

#: What the workspace administrator may do with each.
GRANTS = {
	"Salutation": ("read", "write", "create", "delete"),
	"Gender": ("read", "write", "create", "delete"),
	"Print Heading": ("read", "write", "create", "delete"),
	"Address Template": ("read", "write", "create", "delete"),
}

#: The lists on Workspace > Lists, in order.
LISTS = (
	("Salutation", _lt("Salutations"), _lt("No salutations")),
	("Gender", _lt("Genders"), _lt("No genders")),
)

#: A Jinja tag, as a template is read here: each `{{ }}` and `{% %}` in it.
TAG = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)

#: The tags a workspace adds: a field, an `if` on one, and its end.
FIELD = re.compile(r"\{\{-?\s*([a-z][a-z0-9_]*)\s*-?\}\}")
IF = re.compile(r"\{%-?\s*if\s+([a-z][a-z0-9_]*)\s*-?%\}")
END = re.compile(r"\{%-?\s*(endif|else)\s*-?%\}")

#: A label in the reader's language, as frappe's own templates write one: {{ _("Phone") }}.
WORDS = re.compile(r"""\{\{-?\s*_\(\s*(?:"[^"{}%\\]*"|'[^'{}%\\]*')\s*\)\s*-?\}\}""")


def settle() -> None:
	roles.grant(GRANTS)


def lists() -> list[dict]:
	"""Each list on Workspace > Lists: its kind, its name, whether a value can
	be renamed, and its values."""
	roles.require()
	return [
		{
			"doctype": doctype,
			"label": str(label),
			"empty": str(empty),
			"rename": bool(frappe.get_meta(doctype).allow_rename),
			"rows": [{"name": name} for name in frappe.get_all(doctype, pluck="name", order_by="name asc")],
		}
		for doctype, label, empty in LISTS
	]


def print_headings() -> list[dict]:
	return frappe.get_all("Print Heading", fields=["name", "description", "modified"], order_by="name asc")


def address_templates() -> list[dict]:
	return frappe.get_all(
		"Address Template",
		fields=["name", "country", "is_default", "template", "modified"],
		order_by="is_default desc, country asc",
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
