"""Automations: what happens by itself when a record is made, changed or
reaches a date, for a workspace's administrators. docs/DESK-COVERAGE.md,
stage 6.

An automation is frappe's own Automation Flow: a trigger, the records it
matches, and steps (set a field, make a record, notify, assign, call a
webhook, wait). The workspace administrator is given Automation Flow, and
it is listed in One's sidebar, so its list and form keep One's rail.

Frappe trusts whoever writes a flow, because only its System Managers may.
A flow runs as Administrator unless told otherwise, its condition and an If
step's are Python, every step's values are Jinja with frappe's globals, and
a step can run a Server Script. A flow written by somebody frappe does not
let customize (layer.held) is held to this:

- it runs as whoever wrote it, so each step can do only what they could do
  by hand, and frappe's own permission checks decide;
- it decides by its field rules, never by code: no condition, no If step;
- it runs no script;
- a value names a field of a record, `{{ doc.customer_name }}`, and nothing
  else (as one/mail_templates.py holds a template);
- a webhook is sent over https (frappe already refuses internal addresses);
- it is on a kind of record they can open, never frappe's own or One's.

Automation Settings stays the operator's.

**Tell People** (`TellPeople`, one/automation_steps.py) is One's own step,
added through frappe's `automation_actions` hook: it tells people through the hub (one/notify.py),
on the bell and by mail as each chose, as Automation Notice, and fills a mail
template in as the composer does (one/mail_templates.py), from the record's
own fields. Frappe's Send Notification mails past the hub and renders a
template with only `doc`, so a template named by its fields prints its tags;
it is not offered to a workspace's own flows.
"""

import json
import re

import frappe
from frappe import _
from frappe.utils.translations import N_

from onedesk.one import layer, roles
from onedesk.one.customize import REFUSED_MODULES

GRANTS = {"Automation Flow": ("read", "write", "create", "delete")}

#: The steps a workspace's flow may take.
ACTIONS = (
	"SetFieldValue",
	"CreateDocument",
	"IncrementFieldValue",
	"TellPeople",
	"AssignToUser",
	"CallWebhook",
)
STEPS = ("Action", "Wait", "WaitForEvent")

#: A Jinja tag, as a value is read here.
TAG = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)

#: The one kind of tag a workspace writes: a field of a record the step knows.
FIELD = re.compile(r"\{\{-?\s*(doc|target|trigger|payload)\.[A-Za-z_][A-Za-z0-9_]*\s*-?\}\}")


def settle() -> None:
	roles.grant(GRANTS)


def _doctype(doctype: str) -> None:
	if not frappe.db.exists("DocType", doctype):
		frappe.throw(_("There is no such kind of record."))
	meta = frappe.get_meta(doctype)
	if meta.istable or meta.module in REFUSED_MODULES:
		frappe.throw(_("{0} does not take an automation this workspace sets.").format(_(doctype)))
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("You cannot open {0}.").format(_(doctype)), frappe.PermissionError)


def _strings(value):
	"""Every string in a value, however deep in JSON it sits."""
	if isinstance(value, str):
		parsed = None
		if value.strip()[:1] in ("{", "["):
			try:
				parsed = json.loads(value)
			except ValueError:
				parsed = None
		if parsed is not None:
			yield from _strings(parsed)
		else:
			yield value
	elif isinstance(value, dict):
		for key, one in value.items():
			yield from _strings(key)
			yield from _strings(one)
	elif isinstance(value, list):
		for one in value:
			yield from _strings(one)


def _plain(value, where: str) -> None:
	for text in _strings(value):
		for tag in TAG.findall(text):
			if not FIELD.fullmatch(tag):
				frappe.throw(
					_("{0}: a value can name a field of a record, as {1}, and nothing else.").format(
						where, "{{ doc.customer_name }}"
					)
				)


def validate(doc, method=None) -> None:
	"""Automation Flow validate: what an automation written by the workspace may do."""
	if not layer.held():
		return
	if doc.document_type:
		_doctype(doc.document_type)
	# It runs as whoever wrote it, never as Administrator or somebody else.
	doc.run_as = "Automation User"
	doc.automation_user = frappe.session.user
	if (doc.condition or "").strip():
		frappe.throw(_("An automation here decides by its field rules, not by code."))
	_plain(doc.filters, _("Match Fields"))
	for row in doc.actions or []:
		where = _("Step {0}").format(row.idx)
		if (row.step_type or "Action") not in STEPS or (row.step_condition or "").strip():
			frappe.throw(_("{0}: an automation here decides by its field rules, not by code.").format(where))
		if (row.step_type or "Action") == "Action" and row.action_type == "SendNotification":
			frappe.throw(
				_("{0}: tell people with Tell People, which goes through One's notifications.").format(where)
			)
		if (row.step_type or "Action") == "Action" and row.action_type not in ACTIONS:
			frappe.throw(_("{0}: an automation here runs no script.").format(where))
		_plain(row.params, where)
		_plain(row.related_condition, where)
		if row.action_type == "CreateDocument":
			made = (frappe.parse_json(row.params) or {}).get("doctype") if row.params else None
			if made and frappe.db.exists("DocType", made) and frappe.get_meta(made).module in REFUSED_MODULES:
				frappe.throw(_("{0}: {1} is not the workspace's to make.").format(where, _(made)))
		if row.action_type == "CallWebhook":
			url = ((frappe.parse_json(row.params) or {}).get("url") or "").strip() if row.params else ""
			if not url.lower().startswith("https://"):
				frappe.throw(_("{0}: a webhook is sent over https.").format(where))


#: The engine's own words for its steps, which it sends untranslated; named
#: here so they are translated, and `steps` sends them in the reader's language.
WORDS = (
	N_("Set Field Value"),
	N_("Set value of document fields."),
	N_("Create Document"),
	N_("Create a new document."),
	N_("Increment Field Value"),
	N_("Add a number to a field on the target document."),
	N_("Assign to User"),
	N_("Assign the document to user(s)."),
	N_("Call Webhook"),
	N_("Send an HTTP request to an external URL."),
	N_("Field"),
	N_("Value"),
	N_("Field Values"),
	N_("Document Type"),
	N_("Amount"),
	N_("Assign To"),
	N_("Description"),
	N_("URL"),
	N_("Method"),
	N_("Headers"),
	N_("Payload"),
	N_("Timeout (seconds)"),
	N_("Document owner"),
	N_("Assignees"),
)


def _said(action: dict) -> dict:
	"""A step as the editor shows it, in the reader's language. A copy: the
	schema is the action class's own."""
	label, about = action["label"], action["description"] or ""
	return {
		**action,
		"label": _(label),
		"description": _(about),
		"params_schema": [
			{**one, "label": _(said)} for one in action["params_schema"] for said in [one["label"]]
		],
	}


@frappe.whitelist()
def steps(doctype: str | None = None, trigger_type: str | None = None) -> dict:
	"""What a flow's step editor offers: frappe's own steps and what each takes
	(frappe.automation_engine.api, whose permission check this keeps), less
	Send Notification, which Tell People stands in for, and, for a flow the
	workspace writes, only what validate lets it keep. Waiting for an event is
	offered only when an app has said which events there are."""
	from frappe.automation_engine.api import get_automation_capabilities

	said = get_automation_capabilities(doctype or None, trigger_type or None)
	held = layer.held()
	return {
		"actions": [
			_said(one)
			for one in said["actions"]
			if one["action_type"] != "SendNotification" and (not held or one["action_type"] in ACTIONS)
		],
		"steps": [
			kind
			for kind in ("Action", "Wait", "WaitForEvent", "If")
			if (not held or kind in STEPS) and (kind != "WaitForEvent" or said["custom_events"])
		],
		"events": said["custom_events"],
	}


def described() -> list[dict]:
	"""Every automation as OneAI reads it: its kind, when it runs, what it
	narrows to, whether it is on, and its steps."""
	said = []
	for row in frappe.get_all("Automation Flow", fields=["name"], order_by="modified desc", limit=50):
		doc = frappe.get_doc("Automation Flow", row.name)
		said.append(
			{
				"name": doc.name,
				"title": doc.title,
				"for": doc.document_type,
				"when": doc.trigger_type,
				**({"field": doc.trigger_field} if doc.trigger_field else {}),
				**(
					{"date_field": doc.date_field, "days": doc.date_offset, "direction": doc.date_direction}
					if doc.date_field
					else {}
				),
				"only_when": frappe.parse_json(doc.filters) if doc.filters else [],
				"on": bool(doc.enabled),
				"steps": [
					{
						"do": one.action_type or one.step_type,
						"params": frappe.parse_json(one.params) if one.params else {},
					}
					for one in doc.actions
				],
			}
		)
	return said
