"""OneAI on approvals (one/agent.py lists these tools): the approvals each
kind of record goes through, and a new one suggested as a card."""

from typing import Annotated

import frappe
from frappe import _

APPROVAL_HELP = (
	"An approval is the states a kind of record moves through and the steps between them. Each state is "
	"{state, submitted, editable_by, sets}: state a short word such as Pending, Approved or Rejected; "
	"submitted true for a state that submits the record (only for a kind that is submitted), so the "
	"approving step is what submits it; editable_by the role that may change the record in that state; sets "
	"{field, value}, a plain value an ordinary field takes on reaching it. The first state is where a new "
	"record starts. Each step is {from, action, to, by, when}: action a verb such as Approve, Reject or "
	"Send Back; by the role that may take it; when, if any, a condition comparing the record's own fields "
	"with plain values, as doc.grand_total > 5000 (and, or, not, ==, !=, <, >, <=, >=, in). Two steps "
	"with the same action and different when split by amount: Approve by the user role when "
	"doc.grand_total <= 5000, by the manager role when doc.grand_total > 5000. One approval is on per kind "
	"of record. Roles are named by role, as roles gives them. Every record must be able to finish whatever "
	"its values: where a condition splits a step by amount, every amount needs a step out of that state, "
	"and a small record should not be sent to a state only a large one can leave."
)


def workspace_approvals(
	doctype: Annotated[
		str, "A kind of record, such as Purchase Invoice, to also read what an approval of it may use."
	]
	| None = None,
) -> dict:
	"""The workspace's approvals, for its administrators: each approval, the
	kind of record it moves, whether it is on, its states and its steps (who
	takes each and when). For a kind of record, whether it is submitted, the
	roles a step may be for, and the fields a condition or a state may use.
	Read it before suggesting an approval."""
	from onedesk.one import roles
	from onedesk.one_studio import approvals

	if not roles.administers():
		return {"error": "Only a workspace administrator sees the approvals."}
	said = {"how_an_approval_is_made": APPROVAL_HELP, "roles": approvals.roles_offered()}
	said["approvals"] = approvals.described()
	if doctype:
		try:
			meta = approvals._doctype(doctype)
		except frappe.ValidationError as e:
			frappe.clear_last_message()
			return {"error": str(e)}
		said["kind"] = {
			"doctype": doctype,
			"submitted": bool(meta.is_submittable),
			"fields": [
				f"{df.fieldname} ({df.label}, {df.fieldtype})"
				for df in meta.fields
				if df.fieldtype
				in ("Currency", "Float", "Int", "Percent", "Select", "Link", "Data", "Check", "Date")
				and not df.permlevel
				and not df.hidden
			][:80],
		}
	return said


def suggest_approval(
	doctype: Annotated[str, "The record type, by its name, such as Purchase Invoice."],
	states: Annotated[list[dict], "Every state, the first where a record starts. " + APPROVAL_HELP],
	steps: Annotated[list[dict], "Every step between states, as {from, action, to, by, when}."],
	name: Annotated[str, "An approval to change, as workspace_approvals names it."] | None = None,
	new_name: Annotated[str, "A new approval's name, such as Bill Approval."] | None = None,
	turn_on: Annotated[bool, "Whether it is on once approved; a kind has one approval on at a time."] = True,
	why: Annotated[str, "In a sentence, what the approval is for."] | None = None,
) -> dict:
	"""Suggest an approval, new or changed, as a card a workspace
	administrator approves: who moves a kind of record from state to state,
	and when. Read workspace_approvals first, with the kind. Nothing changes
	until they approve it, and it opens in the approval builder after.
	Workspace administrators only."""
	from frappe.model import no_value_fields

	from onedesk.one import roles
	from onedesk.one_ai import proposals
	from onedesk.one_studio import approvals

	if not roles.administers():
		return {"mend": "suggest_approval", "error": "Only a workspace administrator sets approvals."}
	if name and not new_name and frappe.db.get_value("Workflow", name, "document_type") != doctype:
		name, new_name = None, name
	if not name and not new_name:
		new_name = _("{0} Approval").format(_(doctype))
	if name and new_name:
		return {
			"mend": "suggest_approval",
			"error": "Give name to change an approval, or new_name for a new one, not both.",
		}
	try:
		meta = approvals._doctype(doctype)
	except frappe.ValidationError as e:
		frappe.clear_last_message()
		return {"mend": "suggest_approval", "error": str(e)}
	if new_name and frappe.db.exists("Workflow", new_name.strip()):
		return {
			"mend": "suggest_approval",
			"error": f"{new_name} is already an approval; change it by its name instead.",
		}
	offered = [one["role"] for one in approvals.roles_offered()]
	known = set(offered) | set(frappe.get_all("Role", pluck="name"))
	numbers = [
		df.fieldname
		for df in meta.fields
		if df.fieldtype in ("Currency", "Float", "Int", "Percent") and not df.permlevel
	][:20]
	rows, said = [], []
	for one in states or []:
		state = str(one.get("state") or "").strip()
		if not state:
			return {"mend": "suggest_approval", "error": "Every state needs a name."}
		submitted = bool(one.get("submitted"))
		if submitted and not meta.is_submittable:
			return {
				"mend": "suggest_approval",
				"error": f"{doctype} is not submitted, so no state submits it.",
			}
		role = one.get("editable_by") or roles.ADMINISTRATOR
		if role not in known:
			return {
				"mend": "suggest_approval",
				"error": f"{role} is not a role; a state is editable by one of {', '.join(offered)}.",
			}
		if submitted and not rows:
			return {
				"mend": "suggest_approval",
				"error": f"{state} is the first state, where a record starts as a draft; a later state submits it.",
			}
		row = {"state": state, "doc_status": "1" if submitted else "0", "allow_edit": role}
		sets = one.get("sets") or {}
		if sets.get("field"):
			df = meta.get_field(sets["field"])
			if (
				not df
				or df.permlevel
				or df.fieldtype in no_value_fields
				or sets["field"] in approvals.BOOKKEEPING
			):
				return {"mend": "suggest_approval", "error": f"{state} cannot set {sets['field']}."}
			row.update({"update_field": sets["field"], "update_value": str(sets.get("value") or "")})
		rows.append(row)
	if not rows:
		return {"mend": "suggest_approval", "error": "An approval needs at least one state."}
	names = {row["state"] for row in rows}
	moves = []
	for one in steps or []:
		start, action, end = (str(one.get(key) or "").strip() for key in ("from", "action", "to"))
		role = one.get("by")
		when = str(one.get("when") or "").strip()
		if start not in names or end not in names:
			return {"mend": "suggest_approval", "error": f"{start} to {end}: both must be among the states."}
		if not action or role not in known:
			return {
				"mend": "suggest_approval",
				"error": f"{start} to {end}: give an action and the role it is for, one of {', '.join(offered)}.",
			}
		if not approvals.plain_condition(meta, when):
			return {
				"mend": "suggest_approval",
				"error": f"{start} to {end}: when compares the record's own fields with plain values, as "
				f"doc.grand_total > 5000; its number fields are {', '.join(numbers)}.",
			}
		submits = {row["state"]: row["doc_status"] == "1" for row in rows}
		if submits[start] and not submits[end]:
			return {
				"mend": "suggest_approval",
				"error": f"{start} is submitted, so no step goes from it back to {end}, a draft; take {end} from an earlier state.",
			}
		moves.append(
			{
				"state": start,
				"action": action,
				"next_state": end,
				"allowed": role,
				"condition": when,
				"allow_self_approval": 1,
			}
		)
		said.append(
			{
				"label": _(action),
				"value": _("{0} to {1}, by {2}").format(_(start), _(end), _(role))
				+ (f" ({when})" if when else ""),
			}
		)
	if not moves:
		return {"mend": "suggest_approval", "error": "An approval needs at least one step."}
	if name and approvals.unchanged(name, rows, moves, turn_on):
		return {
			"error": f"{name} is already set up exactly so; tell them it is right as it is and nothing changes."
		}
	called = [row["state"] for row in rows]
	summary = [{"label": _("States"), "value": ", ".join(_(one) for one in called)}, *said]
	summary.append({"label": _("On"), "value": _("Yes") if turn_on else _("No")})
	return {
		"proposal": proposals.propose(
			"Approval",
			doctype,
			changes={
				"state": approvals.state(doctype),
				"workflow": {
					"name": name,
					"workflow_name": (new_name or name or "").strip(),
					"states": rows,
					"transitions": moves,
					"is_active": bool(turn_on),
				},
				"summary": summary,
			},
			why=why,
		),
		"state": "Proposed",
		"next": "Tell them it opens in the approval builder once they approve it, that whoever a step waits on "
		"is told, and that records already made keep their state until somebody takes a step.",
	}




suggest_approval.action = "workspace_setup"
