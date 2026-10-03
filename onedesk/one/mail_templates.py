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
the record, `{{ customer_name }}`, and nothing else. Never `{{ doc.customer_name }}`:
the composer, the leave mails, the salary slip and the interview reminders all
render a template with the record's own fields and no `doc`, so that one fails
in every one of them. What the template already said stays as it was written,
so the leave mail hrms made on setup can have its wording changed without its
logic being refused.

OneMail writes with frappe's composer too, with no form behind it
(public/js/mail_compose.js): it is offered the templates for the record a
conversation is filed on, or those for any record, and `get_email_template`
fills one in from the record itself.
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

#: The one kind of tag a workspace adds: a field of the record, bare.
FIELD = re.compile(r"\{\{-?\s*([A-Za-z][A-Za-z0-9_]*)\s*-?\}\}")

#: The settings that name a template, and the kind of record each is sent about.
#: A template the apps made on setup for one of these says so (`settle`), so the
#: composer offers it there and not on every other kind.
NAMED_BY = (
	("HR Settings", "leave_approval_notification_template", "Leave Application"),
	("HR Settings", "leave_status_notification_template", "Leave Application"),
	("HR Settings", "interview_reminder_template", "Interview"),
	("HR Settings", "feedback_reminder_notification_template", "Interview"),
	("HR Settings", "exit_questionnaire_notification_template", "Exit Interview"),
	("Payroll Settings", "email_template", "Salary Slip"),
	("Delivery Settings", "dispatch_template", "Delivery Trip"),
)

#: The templates the apps make on setup, by the name each is made with, for a
#: workspace whose settings never named them. The name is translated when it is
#: made, so it is matched in English and in the workspace's language.
MADE_AS = (
	("Interview Reminder", "Interview"),
	("Interview Feedback Reminder", "Interview"),
	("Exit Questionnaire Notification", "Exit Interview"),
	("Dispatch Notification", "Delivery Trip"),
)

#: What a template is made of, subject first.
TEXT = ("subject", "response", "response_html")


def settle() -> None:
	roles.grant(GRANTS)
	_for_what()


def _for_what() -> None:
	"""Tell each template the apps made what kind of record it is sent about,
	where it does not say: by the setting that names it, or by the name it was
	made as. Frappe's composer offers a template with no kind on every record."""
	loose = set(
		frappe.get_all("Email Template", filters={"reference_doctype": ["is", "not set"]}, pluck="name")
	)
	found = {}
	for single, field, doctype in NAMED_BY:
		if frappe.db.exists("DocType", single):
			template = frappe.db.get_single_value(single, field)
			if template in loose:
				found[template] = doctype
	for english, doctype in MADE_AS:
		for name in {english, _(english)} & loose:
			found.setdefault(name, doctype)
	for name, doctype in found.items():
		if frappe.db.exists("DocType", doctype):
			frappe.db.set_value("Email Template", name, "reference_doctype", doctype, update_modified=False)


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
		name = found.group(1)
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
		frappe.throw(_("This record type doesn't exist."))
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


@frappe.whitelist()
def get_email_template(
	template_name: Annotated[str, "The template."],
	doc: Annotated[str | dict | None, "The record it is about, or its doctype and name."] = None,
	sender: Annotated[str | None, "The address it is sent from."] = None,
) -> dict:
	"""frappe's get_email_template, for a composer with no form behind it. OneMail
	passes the record a conversation is filed on as its doctype and name, and a
	new message none at all: the record is read here, as whoever writes, so its
	fields fill the template in, and a template with no record gets nothing."""
	if isinstance(doc, str):
		doc = frappe.parse_json(doc)
	doc = dict(doc or {})
	if doc.get("doctype") and doc.get("name") and set(doc) <= {"doctype", "name"}:
		held = frappe.get_doc(doc["doctype"], doc["name"])
		held.check_permission("read")
		doc = held.as_dict()
	template = frappe.get_doc("Email Template", template_name)
	template.check_permission("read")
	return template.get_formatted_email(frappe._dict(_shown(template, doc)), sender=sender)


def _shown(template, doc: dict) -> dict:
	"""A template that only names fields, as one written here does, gets each
	as the record shows it: 1,250.00 AED and 21-09-2026 rather than 1250.0 and
	2026-09-21, since it can say nothing else. One that does more, as some the
	apps made do, gets the values as frappe gives them, which it may work on."""
	tags = {tag for field in TEXT for tag in TAG.findall(template.get(field) or "")}
	names = [FIELD.fullmatch(tag) for tag in tags]
	if (
		not tags
		or not all(names)
		or not doc.get("doctype")
		or not frappe.db.exists("DocType", doc["doctype"])
	):
		return doc
	held = frappe.get_doc(doc)
	return {
		**doc,
		**{
			one.group(1): held.get_formatted(one.group(1))
			for one in names
			if held.meta.has_field(one.group(1))
		},
	}


def filled(template_name: str, doc) -> dict:
	"""A template's subject and message filled in from a record, as the composer
	fills it in: for one sent by an automation (one/automations.py)."""
	template = frappe.get_doc("Email Template", template_name)
	return template.get_formatted_email(frappe._dict(_shown(template, doc.as_dict() if doc else {})))
