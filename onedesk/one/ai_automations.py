"""OneAI on automations (one/agent.py lists these tools): what runs by itself
and when, and a new automation suggested as a card."""

import json
from typing import Annotated

import frappe
from frappe import _

AUTOMATION_HELP = (
	"An automation does something by itself when a record of a kind is made, changed, submitted or reaches "
	"a date. when is one of: created, changed, field changed (with field, and from or to if it matters), "
	"submitted, cancelled, deleted, date (with date_field, days and before or after: runs that many days "
	"before or after the date). only_when narrows it to records whose fields match, each [field, operator, "
	"value] with operator one of = != > < >= <= like in. Steps run in order, each one of: {do: set, field, "
	"value} sets a field of the record; {do: tell, who, subject, message} or {do: tell, who, template} tells "
	"people on the bell and by mail, who being users' emails and @owner (who made the record) or @assignees; "
	"{do: assign, who, note} assigns the record to users named by email, never @owner. In subject, message and value, name a field of the "
	"record as {{ doc.fieldname }}. A template names fields itself, as the mail templates are written. It "
	"runs as whoever approves it, so each step can do only what they could do by hand."
)

WHEN = {
	"created": "Doc Created",
	"changed": "Doc Updated",
	"field changed": "Field Value Changed",
	"submitted": "Doc Submitted",
	"cancelled": "Doc Cancelled",
	"deleted": "Doc Deleted",
	"date": "Date Based",
}


def workspace_automations(
	doctype: Annotated[
		str, "A kind of record, such as Sales Invoice, to also read what an automation of it may use."
	]
	| None = None,
) -> dict:
	"""The workspace's automations, for its administrators: each one, the kind
	of record it watches, when it runs, what it narrows to, whether it is on,
	and its steps. For a kind of record, its fields, its date fields and the
	mail templates written for it. Read it before suggesting an automation."""
	from onedesk.one import roles
	from onedesk.one_studio import automations

	if not roles.administers():
		return {"error": "Only a workspace administrator sees the automations."}
	said = {"automations": automations.described(), "how_an_automation_is_made": AUTOMATION_HELP}
	if doctype:
		try:
			automations._doctype(doctype)
		except frappe.ValidationError as e:
			frappe.clear_last_message()
			return {"error": str(e)}
		meta = frappe.get_meta(doctype)
		said["kind"] = {
			"doctype": doctype,
			"submitted": bool(meta.is_submittable),
			"fields": [
				f"{df.fieldname} ({df.label}, {df.fieldtype})"
				for df in meta.fields
				if df.fieldtype not in frappe.model.no_value_fields and not df.permlevel and not df.hidden
			][:100],
			"date_fields": [df.fieldname for df in meta.fields if df.fieldtype in ("Date", "Datetime")],
			"mail_templates": frappe.get_all(
				"Email Template", filters={"reference_doctype": ["in", [doctype, ""]]}, pluck="name"
			),
		}
	return said


def suggest_automation(
	doctype: Annotated[str, "The record type it watches, by its name, such as Sales Invoice."],
	when: Annotated[str, "created, changed, field changed, submitted, cancelled, deleted or date."],
	steps: Annotated[list[dict], "What it does, in order. " + AUTOMATION_HELP],
	title: Annotated[str, "What it is called, such as Thank customers for paying."] | None = None,
	name: Annotated[str, "An automation to change, as workspace_automations names it."] | None = None,
	field: Annotated[str, "For field changed: the field it watches."] | None = None,
	from_value: Annotated[str, "For field changed: only when it changes from this."] | None = None,
	to_value: Annotated[str, "For field changed: only when it changes to this."] | None = None,
	date_field: Annotated[str, "For date: the date field it counts from."] | None = None,
	days: Annotated[int, "For date: how many days before or after."] | None = None,
	before_or_after: Annotated[str, "For date: before or after."] | None = None,
	only_when: Annotated[list[list], "Records it applies to, each [field, operator, value]."] | None = None,
	turn_on: Annotated[bool, "Whether it is on once approved."] = True,
	why: Annotated[str, "In a sentence, what it is for."] | None = None,
) -> dict:
	"""Suggest an automation, new or changed, as a card a workspace
	administrator approves: something done by itself when a record is made,
	changed or reaches a date: telling people, assigning, setting a field, in
	any mix. Read workspace_automations first, with the kind.
	Nothing is made until they approve it, and it runs as them. Workspace
	administrators only."""
	from onedesk.one import roles
	from onedesk.one_ai import proposals
	from onedesk.one_studio import automations

	mend = {"mend": "suggest_automation"}
	if not roles.administers():
		return {"error": "Only a workspace administrator sets automations."}
	try:
		automations._doctype(doctype)
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {**mend, "error": str(e)}
	trigger = WHEN.get((when or "").strip().lower())
	if not trigger:
		return {**mend, "error": f"when is one of {', '.join(WHEN)}."}
	held = None
	if name:
		held = frappe.db.get_value(
			"Automation Flow", {"name": name, "document_type": doctype}, "name"
		) or frappe.db.get_value("Automation Flow", {"title": name, "document_type": doctype}, "name")
		if not held:
			title, name = title or name, None
	values = {
		"title": (title or "").strip() or _("{0} automation").format(_(doctype)),
		"document_type": doctype,
		"trigger_type": trigger,
		"enabled": 1 if turn_on else 0,
		"filters": json.dumps([list(one) for one in only_when or []]),
	}
	if trigger == "Field Value Changed":
		values.update({"trigger_field": field, "from_value": from_value or "", "to_value": to_value or ""})
	if trigger == "Date Based":
		values.update(
			{
				"date_field": date_field,
				"date_offset": abs(int(days or 0)),
				"date_direction": "Before" if (before_or_after or "").lower().startswith("b") else "After",
			}
		)
	rows, said = [], []
	for one in steps or []:
		do = (one.get("do") or "").strip().lower()
		who = one.get("who") or []
		who = [who] if isinstance(who, str) else list(who)
		if do == "set":
			rows.append(
				{
					"step_type": "Action",
					"action_type": "SetFieldValue",
					"params": json.dumps({"field": one.get("field"), "value": str(one.get("value") or "")}),
				}
			)
			said.append({"label": _("Set"), "value": f"{one.get('field')} = {one.get('value')}"})
		elif do == "tell":
			params = {
				"recipients": who,
				"email_template": one.get("template") or "",
				"subject": one.get("subject") or "",
				"message": one.get("message") or "",
			}
			rows.append({"step_type": "Action", "action_type": "TellPeople", "params": json.dumps(params)})
			said.append(
				{
					"label": _("Notify"),
					"value": ", ".join(who) + ": " + (one.get("template") or one.get("subject") or ""),
				}
			)
		elif do == "assign":
			if any(str(one_who).startswith("@") for one_who in who):
				return {
					**mend,
					"error": "Assign names people by their user, such as a@b.com; it cannot assign whoever made the "
					"record. Tell them instead, or name the people.",
				}
			rows.append(
				{
					"step_type": "Action",
					"action_type": "AssignToUser",
					"params": json.dumps({"assign_to": who, "description": one.get("note") or ""}),
				}
			)
			said.append({"label": _("Assign"), "value": ", ".join(who)})
		else:
			return {**mend, "error": f"A step does set, tell or assign, not {do or 'nothing'}."}
	if not rows:
		return {**mend, "error": "An automation needs at least one step."}
	values["actions"] = rows
	try:
		trial = frappe.get_doc({"doctype": "Automation Flow", **values})
		trial.run_method("validate")
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {**mend, "error": frappe.utils.strip_html_tags(str(e))}
	summary = [
		{
			"label": _("When"),
			"value": _(trigger)
			+ (f" ({field})" if field else "")
			+ (f" ({date_field})" if date_field else ""),
		}
	]
	if only_when:
		summary.append(
			{"label": _("Conditions"), "value": "; ".join(" ".join(str(x) for x in one) for one in only_when)}
		)
	summary += said
	summary.append({"label": _("On"), "value": _("Yes") if turn_on else _("No")})
	proposal = (
		proposals.propose("Edit", "Automation Flow", changes=values, record=held, why=why)
		if held
		else proposals.propose("Create", "Automation Flow", changes=values, why=why)
	)
	return {
		"proposal": proposal,
		"state": "Proposed",
		"next": "Tell them it runs as them once they approve it, and opens in Automations to change there.",
	}




suggest_automation.action = "workspace_setup"
