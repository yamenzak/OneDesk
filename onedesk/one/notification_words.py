"""NotificationCenter's Words and Rules (docs/READY.md, mechanism 15): what
each notification One sends says and which channels it may use, and the
workspace's own rules (when something happens to a record, tell somebody).
Workspace administrators only. Nothing new is stored: it reads and writes
Notification Type and Notification."""

from typing import Annotated

import frappe
from frappe import _

from onedesk.one import brand, roles
from onedesk.one.sections import as_opened
from onedesk.one.sections import fields as fields_of
from onedesk.one.sections import opened as opened_of

NOTIFICATION_TYPE = (
	"enabled",
	"one_subject",
	"one_message",
	"one_allow_email",
	"one_allow_push",
)


@frappe.whitelist()
def load(
	section: Annotated[str, "Which section: words."],
	record: Annotated[str | None, "A type's name, rule:<name> or rule:new, or nothing for the list."] = None,
) -> dict:
	roles.require()
	if section != "words":
		frappe.throw(_("There is no such section."))
	return _notification_types(record)


@frappe.whitelist(methods=["POST"])
def save(
	section: Annotated[str, "Which section: words."],
	values: Annotated[str | dict, "What was changed."],
	opened: Annotated[str | list | None, "The records as the page loaded them: doctype, name and modified."] = None,
	record: Annotated[str | None, "The type or rule it is open on."] = None,
) -> dict:
	roles.require()
	if section != "words":
		frappe.throw(_("There is nothing to save here."))
	frappe.flags.one_opened = {f"{one['doctype']}:{one['name']}": one["modified"] for one in frappe.parse_json(opened) or []}
	record = _save_notification_type(record, frappe.parse_json(values) or {}) or record
	frappe.db.commit()
	return {**_notification_types(record), "record": record}


def _notification_types(record: str | None = None) -> dict:
	"""Every notification One sends, by app, and the workspace's own rules; or
	the type or rule that is open (`rule:` and its name, or `rule:new`)."""
	if record and record.startswith("rule:"):
		return _rule(record[5:])
	if record:
		return _notification_type(record)
	from onedesk.one import notify, rules

	declared = notify.declared()
	rows = frappe.get_all(
		"Notification Type",
		fields=["name", "enabled", "one_rule", *notify.FIELDS],
		order_by="one_app asc, name asc",
	)
	apps: dict[str, list] = {}
	for row in rows:
		if row.one_rule:
			continue
		one = declared.get(row.name) or {}
		apps.setdefault(row.one_app or "", []).append(
			{
				"name": row.name,
				"label": _(row.name),
				"about": _(row.one_about) if row.one_about else None,
				"to": notify.to(row.name),
				"enabled": row.enabled,
				"edited": bool(row.one_default_subject)
				and (row.one_subject != row.one_default_subject or row.one_message != row.one_default_message),
				"outside": row.one_outside,
				"required": bool(one.get("required")),
				"always": bool(one.get("always_mailed")),
				"ours": bool(one),
				"upstream": notify.upstream(one),
				"mailed_by": one["app"] if one.get("mailed_by") else "",
				"email": row.one_allow_email if one else 1,
				"email_default": row.one_email_default,
				"push": row.one_allow_push if one else 0,
				"push_default": row.one_push_default,
			}
		)
	made = frappe.get_all(
		"Notification",
		filters={"one_rule": 1},
		fields=["name", "enabled", "document_type", "event", "date_changed", "days_in_advance", "value_changed"],
		order_by="name asc",
	)
	return {
		"rules": [{"name": one.name, "enabled": one.enabled, "said": rules.said(one)} for one in made],
		"apps": [
			{"app": app, "mark": brand.mark(app), "types": types}
			for app, types in sorted(apps.items(), key=lambda one: (not one[0], one[0]))
		],
	}


def _notification_type(name: str) -> dict:
	from onedesk.one import notify

	if not frappe.db.exists("Notification Type", name):
		frappe.throw(_("There is no notification type {0}.").format(name))
	doc = frappe.get_doc("Notification Type", name)
	one = notify.declared().get(name) or {}
	fields = fields_of("Notification Type", NOTIFICATION_TYPE)
	for field in fields:
		if field["fieldname"] == "one_message":
			field.update({"wrap": 1, "min_lines": 3, "max_lines": 12})
		if field["fieldname"] == "enabled":
			field["label"] = _("Send This")
			fixed = one.get("required") or (
				one.get("mailed_by") and not (one.get("switch") or one.get("notification"))
			)
			field["read_only"] = 1 if fixed else 0
	if one.get("mailed_by"):
		fields = [field for field in fields if field["fieldname"] == "enabled"]
	elif notify.upstream(one):
		fields = [field for field in fields if field["fieldname"] not in ("one_subject", "one_message")]
	return {
		"type": {
			"name": doc.name,
			"label": _(doc.name),
			"app": doc.one_app,
			"mark": brand.mark(doc.one_app),
			"about": _(doc.one_about) if doc.one_about else None,
			"to": notify.to(name),
			"ours": bool(one),
			"outside": doc.one_outside,
			"required": bool(one.get("required")),
			"always": bool(one.get("always_mailed")),
			"upstream": notify.upstream(one),
			"mailed_by": one["app"] if one.get("mailed_by") else "",
			"rule": one.get("rule") or "",
			"switch": bool(one.get("switch")),
			"notification": bool(one.get("notification")),
			"slots": notify.slots(name),
			"default_subject": doc.one_default_subject,
			"default_message": doc.one_default_message,
		},
		"fields": fields if one else [one for one in fields if one["fieldname"] == "enabled"],
		"values": {field: doc.get(field) for field in NOTIFICATION_TYPE},
		"opened": opened_of(doc),
	}


def _save_notification_type(name: str | None, values: dict) -> str | None:
	if name and name.startswith("rule:"):
		return f"rule:{_save_rule(name[5:], values)}"
	if not name or not frappe.db.exists("Notification Type", name):
		frappe.throw(_("There is nothing to save here."))
	doc = as_opened(frappe.get_doc("Notification Type", name))
	doc.update({field: values[field] for field in NOTIFICATION_TYPE if field in values})
	doc.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def preview_notification(
	name: Annotated[str, "The notification type."],
	subject: Annotated[str | None, "Its subject as it is being written."] = None,
	message: Annotated[str | None, "Its message as it is being written."] = None,
) -> dict:
	"""How a text being written reads, with each slot shown where it goes, and
	what is wrong with it if anything is. Rendered as notify renders it."""
	from markupsafe import Markup, escape

	from onedesk.one import notify

	roles.require()
	shown = {slot: Markup('<span class="os-slot">{0}</span>').format(escape(slot)) for slot in notify.slots(name)}
	out = {}
	for key, text in (("subject", subject), ("message", message)):
		wrong = notify.check(name, text)
		out[key] = None if wrong else notify._sandbox().from_string(text or "").render(shown)
		out[f"{key}_wrong"] = wrong
	return out


RULE = (
	"enabled",
	"document_type",
	"event",
	"date_changed",
	"days_in_advance",
	"value_changed",
	"filters",
	"subject",
	"message",
	"send_to_all_assignees",
)

RULE_CHANNELS = ("one_allow_email", "one_allow_push")


def _rule(name: str) -> dict:
	"""A rule of the workspace's, as a form: what it watches, when it fires,
	who is told, what it says, and the channels people may add."""
	from onedesk.one import rules

	new = name == "new"
	if not new and not frappe.db.exists("Notification", {"name": name, "one_rule": 1}):
		frappe.throw(_("There is no rule {0}.").format(name))
	doc = rules.blank() if new else rules.get(name)
	if new:
		doc.update({"enabled": 1, "event": "New", "channel": "System Notification", "message": ""})
	kind = (
		frappe.db.get_value("Notification Type", doc.name, RULE_CHANNELS, as_dict=True) if not new else None
	)
	fields = fields_of("Notification", RULE)
	said = {
		"enabled": (_("Send This"), None),
		"document_type": (_("Record Type"), _("Only record types you can open.")),
		"event": (_("When"), None),
		"date_changed": (_("The Date"), None),
		"days_in_advance": (_("Days"), None),
		"value_changed": (_("The Field"), None),
		"subject": (_("Subject"), _("One line. {{ doc.field }} puts a field of the record in.")),
		"message": (_("Message"), _("The notification detail and the email body. Optional.")),
		"send_to_all_assignees": (_("Assignees"), None),
	}
	for field in fields:
		label, description = said.get(field["fieldname"], (None, None))
		if label:
			field["label"] = str(label)
		field["description"] = str(description) if description else None
		name_of = field["fieldname"]
		if name_of == "event":
			field["options"] = [{"value": one, "label": _(one)} for one in rules.EVENTS]
		if name_of in ("date_changed", "days_in_advance"):
			field["depends_on"] = (
				"eval:doc.document_type && ['Days After', 'Days Before'].includes(doc.event)"
			)
		if name_of == "value_changed":
			field["depends_on"] = "eval:doc.document_type && doc.event === 'Value Change'"
		if name_of == "filters":
			field["hidden"] = 1
		if name_of == "message":
			field.update({"wrap": 1, "min_lines": 3, "max_lines": 12})
	roles_all = [
		one
		for one in frappe.get_all(
			"Role", filters={"disabled": 0, "desk_access": 1}, pluck="name", order_by="name asc"
		)
		if one not in ("Administrator", "Guest")
	]
	fields += [
		{
			"fieldname": "rule_name",
			"fieldtype": "Data",
			"label": str(_("Name")),
			"reqd": 1,
			"read_only": 0 if new else 1,
			"description": str(_("How people will know it when they choose how to get it.")),
		},
		{
			"fieldname": "roles",
			"fieldtype": "MultiSelectList",
			"label": str(_("People With the Role")),
			"options": [{"value": one, "label": _(one), "description": ""} for one in roles_all],
		},
		{
			"fieldname": "person_field",
			"fieldtype": "Select",
			"label": str(_("The Person on the Record")),
			"options": [],
		},
		*[
			{"fieldname": one, "fieldtype": "Check", "label": label}
			for one, label in (
				("one_allow_email", str(_("Email Allowed"))),
				("one_allow_push", str(_("Push Allowed"))),
			)
		],
	]
	values = {one: doc.get(one) for one in RULE}
	values.update(
		{
			"rule_name": "" if new else doc.name,
			"roles": [row.receiver_by_role for row in doc.recipients or [] if row.receiver_by_role],
			"person_field": next(
				(
					row.receiver_by_document_field
					for row in doc.recipients or []
					if row.receiver_by_document_field
				),
				"",
			),
			"one_allow_email": kind.one_allow_email if kind else 1,
			"one_allow_push": kind.one_allow_push if kind else 1,
		}
	)
	return {
		"rule": {
			"name": "" if new else doc.name,
			"new": new,
			"said": rules.said(doc) if doc.document_type else "",
		},
		"fields": fields,
		"values": values,
		"options": rules.fields_of(doc.document_type) if doc.document_type else None,
		"opened": [] if new else opened_of(doc),
	}


def _save_rule(name: str, values: dict) -> str:
	"""Make or change a rule. Returns its name."""
	from onedesk.one import rules

	new = name == "new"
	if new:
		doc = rules.blank()
		doc.name = (values.get("rule_name") or "").strip()
		if not doc.name:
			frappe.throw(_("Give the rule a name."))
		if frappe.db.exists("Notification", doc.name) or frappe.db.exists("Notification Type", doc.name):
			frappe.throw(_("There is already a notification called {0}.").format(doc.name))
	else:
		if not frappe.db.exists("Notification", {"name": name, "one_rule": 1}):
			frappe.throw(_("There is no rule {0}.").format(name))
		doc = as_opened(rules.get(name))
	doc.update({one: values[one] for one in RULE if one in values})
	doc.update({"one_rule": 1, "channel": "System Notification", "condition_type": "Filters"})
	roles_wanted = (
		frappe.parse_json(values.get("roles"))
		if isinstance(values.get("roles"), str)
		else values.get("roles")
	)
	rows = [{"receiver_by_role": one} for one in roles_wanted or [] if one]
	if values.get("person_field"):
		rows.append({"receiver_by_document_field": values["person_field"]})
	doc.set("recipients", rows)
	if new:
		doc.insert(ignore_permissions=True, set_name=doc.name)
	else:
		doc.save(ignore_permissions=True)
	kind = frappe.get_doc("Notification Type", doc.name)
	kind.update({one: frappe.utils.cint(values.get(one)) for one in RULE_CHANNELS if one in values})
	# A rule has no module to say who starts with a channel on: everybody
	# does, where it is allowed, until they turn it off.
	kind.one_email_default, kind.one_push_default = kind.one_allow_email, kind.one_allow_push
	kind.save(ignore_permissions=True)
	return doc.name


@frappe.whitelist(methods=["POST"])
def delete_rule(name: Annotated[str, "The rule."]) -> dict:
	"""Stop a rule for good, and its notification type with it."""
	roles.require()
	if not frappe.db.exists("Notification", {"name": name, "one_rule": 1}):
		frappe.throw(_("There is no rule {0}.").format(name))
	frappe.delete_doc("Notification", name, ignore_permissions=True)
	frappe.db.commit()
	return load("words")
