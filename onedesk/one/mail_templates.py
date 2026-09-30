"""Mail templates: the words a workspace sends again and again, for its
administrators. docs/DESK-COVERAGE.md, stage 4.

A template is frappe's own Email Template: a subject and a message, for one
kind of record or for any, picked in the mail composer or named by a setting
(HR Settings' leave mails, the interview reminders). Frappe renders it as
Jinja with its template globals, as whoever sends it, so whoever writes one
can make it read anything that person may read and put it in the mail.
Frappe gives writing one to its System Managers only.

The workspace administrator is given Email Template, and a template written
by somebody frappe does not let customize (layer.held) is held to what a
workspace rule's text is held to (one/rules.py): what it adds names a field of
the record, `{{ customer_name }}` or `{{ doc.customer_name }}`, and nothing
else. What the template already said stays as it was written, so the leave
mail hrms made on setup can have its wording changed without its logic being
refused.
"""

import re
from typing import Annotated

import frappe
from frappe import _

from onedesk.one import layer, roles, rules
from onedesk.one.customize import REFUSED_MODULES

GRANTS = {"Email Template": ("read", "write", "create", "delete")}

#: A Jinja tag, as the template is read here: each `{{ }}` and `{% %}` in it.
TAG = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)

#: The one kind of tag a workspace adds: a field, bare or on `doc`.
FIELD = re.compile(r"\{\{-?\s*(doc\.)?([A-Za-z][A-Za-z0-9_]*)\s*-?\}\}")

#: What a template is made of, subject first.
TEXT = ("subject", "response", "response_html")


def settle() -> None:
	roles.grant(GRANTS)


def _tags(doc) -> set[str]:
	return {tag for field in TEXT for tag in TAG.findall(doc.get(field) or "")} if doc else set()


def check(doctype: str | None, text: str | None, kept: set[str]) -> str | None:
	"""What is wrong with a template's subject or message, or None. Every tag in
	it is one it already had, or names a field of the record."""
	from frappe.utils.jinja import get_jenv

	allowed = set(rules.readable(doctype)) if doctype else None
	globals_ = get_jenv().globals
	for tag in TAG.findall(text or ""):
		if tag in kept:
			continue
		found = FIELD.fullmatch(tag)
		if not found:
			return _("A template can name a field of the record, as {{ customer_name }}, and nothing else.")
		name = found.group(2)
		if allowed is not None and name not in allowed:
			return _("{0} has no field {1}.").format(_(doctype), name)
		if allowed is None and name in globals_:
			return _("{0} is not a field.").format(name)
	return None


def validate(doc, method=None) -> None:
	"""Email Template validate: what a template written by the workspace may say."""
	if not layer.held():
		return
	if doc.reference_doctype:
		_doctype(doc.reference_doctype)
	kept = _tags(doc.get_doc_before_save())
	for label, field in (
		(_("Subject"), "subject"),
		(_("Message"), "response"),
		(_("Message"), "response_html"),
	):
		wrong = check(doc.reference_doctype, doc.get(field), kept)
		if wrong:
			frappe.throw(_("{0}: {1}").format(label, wrong))


def _doctype(doctype: str) -> None:
	if not doctype or not frappe.db.exists("DocType", doctype):
		frappe.throw(_("There is no such kind of record."))
	if frappe.get_meta(doctype).module in REFUSED_MODULES:
		frappe.throw(_("{0} is not mailed from templates this workspace sets.").format(_(doctype)))
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("You cannot open {0}.").format(_(doctype)), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def set_default(
	doctype: Annotated[str, "The kind of record."],
	template: Annotated[str, "The template the composer starts with for it."],
) -> None:
	"""The template the mail composer starts with for a kind of record."""
	roles.require()
	_doctype(doctype)
	if frappe.get_meta(doctype).custom:
		frappe.throw(_("{0} is not mailed from templates this workspace sets.").format(_(doctype)))
	if frappe.db.get_value("Email Template", template, "reference_doctype") not in (doctype, None, ""):
		frappe.throw(_("{0} is not a template for {1}.").format(template, _(doctype)))
	layer.set_default(doctype, "default_email_template", template)


@frappe.whitelist()
def default(doctype: Annotated[str, "The kind of record."]) -> str | None:
	"""The template the composer starts with for a kind of record."""
	roles.require()
	_doctype(doctype)
	return frappe.get_meta(doctype).default_email_template


def templates() -> list[dict]:
	"""Every mail template, for Workspace > Mail Templates, with the kinds of
	record each is the default for."""
	roles.require()
	defaults = {}
	for row in frappe.get_all(
		"Property Setter",
		filters={"property": "default_email_template", "doctype_or_field": "DocType"},
		fields=["doc_type", "value"],
	):
		defaults.setdefault(row.value, []).append(_(row.doc_type))
	rows = frappe.get_all(
		"Email Template",
		fields=["name", "subject", "reference_doctype", "modified"],
		order_by="name asc",
	)
	return [
		dict(
			row,
			label=_(row.reference_doctype) if row.reference_doctype else "",
			default_for=defaults.get(row.name, []),
		)
		for row in rows
	]
