"""Mail templates: the words a workspace sends again and again, for its
administrators.

A template is frappe's own Email Template; one written by somebody frappe does
not let customize (layer.held) may add only fields of the record, bare.
"""

import re
from typing import Annotated

import frappe
from frappe import _

from onedesk.one import layer, rules
from onedesk.one.customize import REFUSED_MODULES

TAG = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)

FIELD = re.compile(r"\{\{-?\s*([A-Za-z][A-Za-z0-9_]*)\s*-?\}\}")

# A table's rows, repeated: `{% for row in items %}` … `{{ row.item_name }}` …
# `{% endfor %}`, which is all a workspace's template may do besides name fields.
LOOP = re.compile(r"\{%-?\s*for\s+([a-z_][a-z0-9_]*)\s+in\s+([A-Za-z][A-Za-z0-9_]*)\s*-?%\}")
END = re.compile(r"\{%-?\s*endfor\s*-?%\}")
ROW = re.compile(r"\{\{-?\s*([a-z_][a-z0-9_]*)\.([A-Za-z][A-Za-z0-9_]*)\s*-?\}\}")

# A table of the record laid out with the columns named, in one line:
# `{{ table(items, "item_name", "qty", "amount") }}`. What the `/` picker writes.
TABLE = re.compile(r"\{\{-?\s*table\(\s*([A-Za-z][A-Za-z0-9_]*)\s*((?:,\s*\"[A-Za-z][A-Za-z0-9_]*\"\s*)+)\)\s*-?\}\}")
COLUMN = re.compile(r"\"([A-Za-z][A-Za-z0-9_]*)\"")

# The columns a table is laid out with unless the writer picks others, where
# its rows have them: what an item line is.
COLUMNS = ("item_name", "qty", "rate", "amount")

NAMED_BY = (
	("HR Settings", "leave_approval_notification_template", "Leave Application"),
	("HR Settings", "leave_status_notification_template", "Leave Application"),
	("HR Settings", "interview_reminder_template", "Interview"),
	("HR Settings", "feedback_reminder_notification_template", "Interview"),
	("HR Settings", "exit_questionnaire_notification_template", "Exit Interview"),
	("Payroll Settings", "email_template", "Salary Slip"),
	("Delivery Settings", "dispatch_template", "Delivery Trip"),
)

MADE_AS = (
	("Leave Approval Notification", "Leave Application"),
	("Leave Status Notification", "Leave Application"),
	("Interview Reminder", "Interview"),
	("Interview Feedback Reminder", "Interview"),
	("Exit Questionnaire Notification", "Exit Interview"),
	("Dispatch Notification", "Delivery Trip"),
)

TEXT = ("subject", "response", "response_html")


def settle() -> None:
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


def used_by() -> dict[str, list[str]]:
	"""The settings that send each template, such as HR Settings for Leave
	Approval Notification: the mail those send stops if it goes."""
	found = {}
	for single, field, _doctype in NAMED_BY:
		if frappe.db.exists("DocType", single):
			template = frappe.db.get_single_value(single, field)
			if template and single not in found.get(template, []):
				found.setdefault(template, []).append(single)
	return found


def has_code(doc) -> bool:
	"""Whether a template holds more than fields of the record, such as the
	`{% set %}` and translated links the apps' own templates are written with."""
	return not all(_ours(tag) for tag in _tags(doc))


def _ours(tag: str) -> bool:
	"""A tag a workspace's template may hold: a field, a table, or a loop."""
	return bool(FIELD.fullmatch(tag) or TABLE.fullmatch(tag) or LOOP.fullmatch(tag) or END.fullmatch(tag) or ROW.fullmatch(tag))


def on_trash(doc, method=None) -> None:
	"""Email Template on_trash: a template a setting still sends is kept."""
	using = used_by().get(doc.name)
	if using:
		frappe.throw(
			_("{0} is used by {1}. Choose another template there first.").format(
				doc.name, ", ".join(_(one) for one in using)
			)
		)


def _tags(doc) -> set[str]:
	return {tag for field in TEXT for tag in TAG.findall(doc.get(field) or "")} if doc else set()


def table_of(doctype: str | None, fieldname: str) -> str | None:
	"""The kind of row a table field of the record holds, where a template may
	read it: a table at the first permission level."""
	from frappe.model import table_fields

	field = frappe.get_meta(doctype).get_field(fieldname) if doctype else None
	if field and field.fieldtype in table_fields and not field.permlevel:
		return field.options
	return None


def check(doctype: str | None, text: str | None, kept: set[str]) -> str | None:
	"""What is wrong with a template's subject or message, or None. Every tag in
	it is one it already had, names a field of the record, or repeats one of
	its tables with fields of the rows."""
	from frappe.utils.jinja import get_jenv

	allowed = set(rules.readable(doctype)) if doctype else None
	globals_ = get_jenv().globals
	rows = []
	for tag in TAG.findall(text or ""):
		loop, end, row = LOOP.fullmatch(tag), END.fullmatch(tag), ROW.fullmatch(tag)
		if loop:
			child = table_of(doctype, loop.group(2))
			if not child and tag not in kept:
				if not doctype:
					return _("Choose For to repeat a table's rows.")
				return _("{0} has no table {1}.").format(_(doctype), loop.group(2))
			rows.append((loop.group(1), child))
			continue
		if end:
			if not rows:
				return _("Each {% endfor %} closes a {% for %}.")
			rows.pop()
			continue
		if tag in kept:
			continue
		if table := TABLE.fullmatch(tag):
			child = table_of(doctype, table.group(1))
			if not child:
				if not doctype:
					return _("Choose For to show a table's rows.")
				return _("{0} has no table {1}.").format(_(doctype), table.group(1))
			readable = rules.readable(child)
			for column in COLUMN.findall(table.group(2)):
				if column not in readable:
					return _("{0} has no field {1}.").format(_(child), column)
			continue
		if row:
			child = next((one for name, one in reversed(rows) if name == row.group(1)), False)
			if child is False:
				return _("{0} is used outside the rows it repeats.").format(row.group(1))
			if child and row.group(2) not in rules.readable(child):
				return _("{0} has no field {1}.").format(_(child), row.group(2))
			continue
		found = FIELD.fullmatch(tag)
		if not found:
			return _("A template can name a field of the record, as {{ customer_name }}, and nothing else.")
		name = found.group(1)
		if allowed is not None and name not in allowed:
			return _("{0} has no field {1}.").format(_(doctype), name)
		if allowed is None and name in globals_:
			return _("{0} is not a field.").format(name)
	if rows:
		return _("Each {% for %} needs an {% endfor %}.")
	return None


@frappe.whitelist()
def fields_of(doctype: Annotated[str, "The kind of record."]) -> dict:
	"""What a template for a kind of record may name, for the `/` picker: the
	record's fields, and each table with its rows' fields and the columns it
	is laid out with unless the writer picks others."""
	from frappe.model import no_value_fields, table_fields

	_may_keep()
	_doctype(doctype)

	def listed(of: str) -> list[dict]:
		meta = frappe.get_meta(of)
		return [
			{"fieldname": f.fieldname, "label": _(f.label), "shown": int(bool(f.in_list_view))}
			for f in meta.fields
			if f.label and f.fieldtype not in no_value_fields and f.fieldtype not in table_fields and not f.permlevel
		]

	meta = frappe.get_meta(doctype)
	return {
		"fields": [{"fieldname": "name", "label": _("ID"), "shown": 1}, *listed(doctype)],
		"tables": [
			{
				"fieldname": f.fieldname,
				"label": _(f.label),
				"fields": (rows := listed(f.options)),
				"columns": _columns(rows),
			}
			for f in meta.fields
			if f.label and table_of(doctype, f.fieldname)
		],
	}


def _columns(rows: list[dict]) -> list[str]:
	names = [one["fieldname"] for one in rows]
	picked = [name for name in COLUMNS if name in names]
	return picked if len(picked) >= 2 else [one["fieldname"] for one in rows if one["shown"]][:4] or names[:3]


def _table(rows, *names) -> str:
	"""A table of the record as it is mailed: the columns named, under their
	labels, figures to the right, the values as the record shows them."""
	from markupsafe import Markup, escape

	rows = [row for row in rows or [] if isinstance(row, dict)]
	if not rows or not names:
		return Markup("")
	meta = frappe.get_meta(rows[0]["doctype"]) if rows[0].get("doctype") else None

	def field(name):
		return meta.get_field(name) if meta else None

	def right(name):
		return bool(field(name) and field(name).fieldtype in ("Currency", "Float", "Int", "Percent"))

	cell = "padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:{}"
	head = "".join(
		f'<th style="{cell.format("right" if right(name) else "left")};font-weight:600">'
		f"{escape(_(field(name).label) if field(name) else name)}</th>"
		for name in names
	)
	body = "".join(
		"<tr>"
		+ "".join(
			f'<td style="{cell.format("right" if right(name) else "left")}">'
			f'{escape("" if row.get(name) is None else row.get(name))}</td>'
			for name in names
		)
		+ "</tr>"
		for row in rows
	)
	return Markup(
		f'<table style="border-collapse:collapse;width:100%"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
	)


@frappe.whitelist()
def preview(
	subject: Annotated[str | None, "The subject as written."] = None,
	response: Annotated[str | None, "The message as written."] = None,
	response_html: Annotated[str | None, "The message, written in HTML."] = None,
	use_html: Annotated[int, "Whether it is written in HTML."] = 0,
	doctype: Annotated[str | None, "The kind of record it is for."] = None,
	name: Annotated[str | None, "The record to fill it in from."] = None,
	template: Annotated[str | None, "The template it is a draft of, if saved."] = None,
) -> dict:
	"""A template as it would be sent, filled in from one record, before it is
	saved: what the Preview button shows. Checked as saving would check it."""
	_may_keep()
	doc = {}
	if doctype:
		_doctype(doctype)
		if name:
			held = frappe.get_doc(doctype, name)
			held.check_permission("read")
			doc = held.as_dict()
	draft = frappe.get_doc(
		{
			"doctype": "Email Template",
			"subject": subject or "",
			"response": response or "",
			"response_html": response_html or "",
			"use_html": int(use_html or 0),
			"reference_doctype": doctype,
		}
	)
	if layer.held():
		kept = _tags(frappe.get_doc("Email Template", template)) if template and frappe.db.exists("Email Template", template) else set()
		for field in ("subject", "response_html" if draft.use_html else "response"):
			wrong = check(doctype, draft.get(field), kept)
			if wrong:
				return {"error": wrong}
	try:
		return draft.get_formatted_email(frappe._dict(_shown(draft, doc)))
	except Exception as error:
		return {"error": _("This template can't be filled in: {0}").format(str(error))}


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
	_may_keep()
	_doctype(doctype)
	if frappe.get_meta(doctype).custom:
		frappe.throw(_("{0} is not mailed from templates this workspace sets.").format(_(doctype)))
	if frappe.db.get_value("Email Template", template, "reference_doctype") not in (doctype, None, ""):
		frappe.throw(_("{0} is not a template for {1}.").format(template, _(doctype)))
	layer.set_default(doctype, "default_email_template", template)


@frappe.whitelist()
def default(doctype: Annotated[str, "The kind of record."]) -> str | None:
	"""The template the composer starts with for a kind of record."""
	_may_keep()
	_doctype(doctype)
	return frappe.get_meta(doctype).default_email_template


@frappe.whitelist()
def templates() -> list[dict]:
	"""Every mail template, for Workspace > Mail Templates, with the kinds of
	record each is the default for, the settings that send it, and whether it
	holds code."""
	_may_keep()
	defaults = {}
	for row in frappe.get_all(
		"Property Setter",
		filters={"property": "default_email_template", "doctype_or_field": "DocType"},
		fields=["doc_type", "value"],
	):
		defaults.setdefault(row.value, []).append(_(row.doc_type))
	rows = frappe.get_all(
		"Email Template",
		fields=["name", "subject", "reference_doctype", "modified", "response", "response_html"],
		order_by="name asc",
	)
	using = used_by()
	return [
		dict(
			name=row.name,
			subject=row.subject,
			reference_doctype=row.reference_doctype,
			modified=row.modified,
			label=_(row.reference_doctype) if row.reference_doctype else "",
			default_for=defaults.get(row.name, []),
			used_by=[_(one) for one in using.get(row.name, [])],
			code=int(has_code(row)),
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
	from frappe.email.doctype.email_template.email_template import get_email_template as theirs

	shown = _shown(frappe.get_doc("Email Template", template_name), doc)
	return theirs(template_name, frappe._dict(shown), sender=sender)


def _shown(template, doc: dict) -> dict:
	"""A template that only names fields and repeats tables, as one written
	here does, gets each as the record shows it: 1,250.00 EUR and 21-09-2026
	rather than 1250.0 and 2026-09-21, in its rows too, since it can say
	nothing else. One that does more, as some the apps made do, gets the
	values as frappe gives them, which it may work on."""
	tags = {tag for field in TEXT for tag in TAG.findall(template.get(field) or "")}
	if (
		not tags
		or not all(_ours(t) for t in tags)
		or not doc.get("doctype")
		or not frappe.db.exists("DocType", doc["doctype"])
	):
		return {**doc, "table": _table}
	held = frappe.get_doc(doc)
	text = "".join(template.get(field) or "" for field in TEXT)
	tables = {}
	stack = []
	for tag in TAG.findall(text):
		if laid := TABLE.fullmatch(tag):
			tables.setdefault(laid.group(1), set()).update(COLUMN.findall(laid.group(2)))
		elif loop := LOOP.fullmatch(tag):
			stack.append(loop.groups())
			tables.setdefault(loop.group(2), set())
		elif END.fullmatch(tag) and stack:
			stack.pop()
		elif (row := ROW.fullmatch(tag)) and stack:
			table = next((t for name, t in reversed(stack) if name == row.group(1)), None)
			if table:
				tables[table].add(row.group(2))
	shown = {
		one.group(1): held.get_formatted(one.group(1))
		for one in map(FIELD.fullmatch, tags)
		if one and held.meta.has_field(one.group(1))
	}
	for table, names in tables.items():
		if held.meta.has_field(table):
			shown[table] = [
				{**row.as_dict(), **{name: row.get_formatted(name) for name in names if row.meta.has_field(name)}}
				for row in held.get(table) or []
			]
	return {**doc, **shown, "table": _table}


def filled(template_name: str, doc) -> dict:
	"""A template's subject and message filled in from a record, as the composer
	fills it in: for one sent by an automation (one/automations.py)."""
	template = frappe.get_doc("Email Template", template_name)
	return template.get_formatted_email(frappe._dict(_shown(template, doc.as_dict() if doc else {})))


def _may_keep() -> None:
	"""Refuse anyone whose role doesn't keep the mail templates (OneMail's
	Mail Templates ability)."""
	from onedesk.one_mail import holders

	holders._admin("templates")
