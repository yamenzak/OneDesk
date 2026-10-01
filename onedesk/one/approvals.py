"""Approvals: the states a workspace's records move through, and who moves
them, for its administrators. docs/DESK-COVERAGE.md, stage 5.

An approval is frappe's own Workflow: its states, the actions between them,
and the role each action is for, drawn in frappe's workflow builder. The
workspace administrator is given Workflow, Workflow State and Workflow
Action Master, and the builder page through frappe's Custom Role.

Frappe trusts whoever writes a Workflow, because only its System Managers
may, and a workflow can run code: a transition's condition is Python, a
state's value can be an expression, a transition can run tasks (a Server
Script's method among them), and the field the workflow keeps its state in is
written on every record of the kind. A workflow written by somebody frappe
does not let customize (layer.held) is held to this:

- it is on a kind of record they can open, never frappe's own or One's;
- its transitions run no tasks, and a condition only compares the record's
  own fields with plain values (`doc.grand_total > 5000`), so a bill over a
  sum can go to a manager without a line of code;
- a state sets a field only to a plain value, and only a field anybody who
  may edit the record may set (the first permission level, not the record's
  own bookkeeping);
- it keeps its state in a field of its own, which is made here the first
  time, as frappe makes it but as the workspace, since the administrator may
  not add a field by hand.

Every approval, the workspace's or not, is told through One's hub: frappe's
own mail to whoever a step waits on is off (`send_email_alert`), and
`waiting` tells them on the bell, and by mail as they chose, as Approval
Waiting. One made without the builder (by OneAI, or by code) is laid out for
it, since frappe's builder stacks every step it has no place for on one spot.
"""

import ast
import json
import re

import frappe
from frappe import _
from frappe.model import no_value_fields, table_fields

from onedesk.one import layer, roles
from onedesk.one.customize import REFUSED_MODULES

GRANTS = {
	"Workflow": ("read", "write", "create", "delete"),
	"Workflow State": ("read", "write", "create"),
	"Workflow Action Master": ("read", "write", "create"),
}

#: frappe's workflow builder, a page whose only role is System Manager.
BUILDER = "workflow-builder"

#: Fields every record keeps for itself, which no state sets.
BOOKKEEPING = (
	"name",
	"owner",
	"creation",
	"modified",
	"modified_by",
	"docstatus",
	"idx",
	"amended_from",
	"naming_series",
)

FIELDNAME = re.compile(r"^[a-z][a-z0-9_]*$")


def settle() -> None:
	roles.grant(GRANTS)
	roles.open_page(BUILDER)


def _doctype(doctype: str):
	if not doctype or not frappe.db.exists("DocType", doctype):
		frappe.throw(_("There is no such kind of record."))
	meta = frappe.get_meta(doctype)
	if meta.istable or meta.issingle or meta.module in REFUSED_MODULES:
		frappe.throw(_("{0} does not take an approval this workspace sets.").format(_(doctype)))
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("You cannot open {0}.").format(_(doctype)), frappe.PermissionError)
	return meta


def validate(doc, method=None) -> None:
	"""Workflow validate: told through the hub, laid out, and, written by the
	workspace, held to what it may do."""
	doc.send_email_alert = 0
	_laid_out(doc)
	if not layer.held():
		return
	meta = _doctype(doc.document_type)
	for row in doc.transitions or []:
		if not plain_condition(meta, row.condition):
			frappe.throw(
				_(
					"{0} to {1}: a condition only compares the record's fields with plain values, such as doc.grand_total > 5000."
				).format(_(row.state), _(row.next_state))
			)
		if row.transition_tasks:
			frappe.throw(
				_("{0} to {1}: an action here runs nothing.").format(_(row.state), _(row.next_state))
			)
	for row in doc.states or []:
		if row.evaluate_as_expression:
			frappe.throw(
				_("{0}: a state sets a field to a plain value, not one worked out.").format(_(row.state))
			)
		if row.update_field:
			_settable(meta, row.update_field, doc.workflow_state_field, row.state)
	_state_field(doc, meta)


def _settable(meta, fieldname: str, state_field: str, state: str) -> None:
	df = meta.get_field(fieldname)
	if (
		not df
		or fieldname in BOOKKEEPING
		or fieldname == state_field
		or df.fieldtype in no_value_fields
		or df.fieldtype in table_fields
		or df.permlevel
	):
		frappe.throw(_("{0}: a state cannot set {1}.").format(_(state), fieldname))


def _state_field(doc, meta) -> None:
	"""The field the workflow keeps its state in: a Link to Workflow State, made
	here the first time, as frappe's Workflow.on_update would make it."""
	fieldname = doc.workflow_state_field or "workflow_state"
	if not FIELDNAME.match(fieldname):
		frappe.throw(_("{0} cannot hold an approval's state.").format(fieldname))
	df = meta.get_field(fieldname)
	if df:
		if df.fieldtype != "Link" or df.options != "Workflow State":
			frappe.throw(_("{0} cannot hold an approval's state.").format(fieldname))
		return
	frappe.get_doc(
		{
			"doctype": "Custom Field",
			"dt": doc.document_type,
			"fieldname": fieldname,
			"label": fieldname.replace("_", " ").title(),
			"hidden": 1,
			"allow_on_submit": 1,
			"no_copy": 1,
			"fieldtype": "Link",
			"options": "Workflow State",
		}
	).insert(ignore_permissions=True)
	frappe.clear_cache(doctype=doc.document_type)


def approvals() -> list[dict]:
	"""Every approval, for Workspace > Approvals."""
	roles.require()
	rows = frappe.get_all(
		"Workflow", fields=["name", "workflow_name", "document_type", "is_active"], order_by="name asc"
	)
	steps = {}
	for row in frappe.get_all(
		"Workflow Transition", filters={"parenttype": "Workflow"}, fields=["parent"], limit=0
	):
		steps[row.parent] = steps.get(row.parent, 0) + 1
	return [dict(row, label=_(row.document_type), steps=steps.get(row.name, 0)) for row in rows]


#: What a condition may be made of: the record's fields, plain values, and the
#: comparisons and words that join them.
PLAIN = (
	ast.Expression,
	ast.Compare,
	ast.BoolOp,
	ast.And,
	ast.Or,
	ast.UnaryOp,
	ast.Not,
	ast.USub,
	ast.Attribute,
	ast.Name,
	ast.Load,
	ast.Constant,
	ast.Eq,
	ast.NotEq,
	ast.Lt,
	ast.LtE,
	ast.Gt,
	ast.GtE,
	ast.In,
	ast.NotIn,
	ast.Tuple,
	ast.List,
)


def plain_condition(meta, condition: str | None) -> bool:
	"""Whether a transition's condition only compares the record's own fields,
	`doc.<field>` of the first permission level, with plain values. Frappe runs
	it in its safe_eval with the record and globals of its own; this keeps it
	to the record. Pure but for the meta."""
	condition = (condition or "").strip()
	if not condition:
		return True
	try:
		tree = ast.parse(condition, mode="eval")
	except SyntaxError:
		return False
	names = attributes = 0
	for node in ast.walk(tree):
		if not isinstance(node, PLAIN):
			return False
		if isinstance(node, ast.Name):
			if node.id != "doc":
				return False
			names += 1
		if isinstance(node, ast.Attribute):
			if not isinstance(node.value, ast.Name) or node.value.id != "doc":
				return False
			df = meta.get_field(node.attr)
			if node.attr != "name" and (not df or df.permlevel or df.fieldtype in no_value_fields):
				return False
			attributes += 1
	# `doc` on its own is the whole record, not one of its fields.
	return names == attributes


def _laid_out(doc) -> None:
	"""A place in frappe's builder for every state and step of an approval saved
	without one: the states in columns by how many steps from the first they
	are, each step between the two it joins. The builder keeps it from then on."""
	if (doc.workflow_data or "").strip() not in ("", "[]", "null") or not doc.states:
		return
	ids, column = {}, {}
	for i, row in enumerate(doc.states, 1):
		row.workflow_builder_id = str(i)
		ids[row.state] = str(i)
	first = doc.states[0].state
	column[first] = 0
	reached = [first]
	while reached:
		at = reached.pop(0)
		for row in doc.transitions or []:
			if row.state == at and row.next_state in ids and row.next_state not in column:
				column[row.next_state] = column[at] + 1
				reached.append(row.next_state)
	for row in doc.states:
		column.setdefault(row.state, max(column.values()) + 1)
	steps_out = {row.state: 0 for row in doc.states}
	for row in doc.transitions or []:
		if row.state in steps_out:
			steps_out[row.state] += 1
	rows: dict[int, float] = {}
	place = {}
	for row in doc.states:
		depth = column[row.state]
		place[row.state] = {"x": 100 + depth * 560, "y": 100 + rows.get(depth, 0)}
		# The next state in the column goes below this one's stack of steps.
		rows[depth] = rows.get(depth, 0) + max(180, steps_out[row.state] * 90 + 60)
	nodes = [{"id": ids[row.state], "type": "state", "position": place[row.state]} for row in doc.states]
	# A state's steps stacked beside it, one under another, so two steps out of
	# the same state never sit on each other.
	out_of: dict[str, int] = {}
	for k, row in enumerate(doc.transitions or [], 1):
		if row.state not in ids or row.next_state not in ids:
			continue
		action = f"action-{k}"
		row.workflow_builder_id = action
		source = place[row.state]
		x = source["x"] + 260
		y = source["y"] + out_of.get(row.state, 0) * 90
		out_of[row.state] = out_of.get(row.state, 0) + 1
		nodes.append(
			{
				"id": action,
				"type": "action",
				"position": {"x": x, "y": y},
				"data": {"from_id": ids[row.state], "to_id": ids[row.next_state]},
			}
		)
		for edge_from, edge_to in ((ids[row.state], action), (action, ids[row.next_state])):
			nodes.append(
				{
					"id": f"edge-{edge_from}-{edge_to}",
					"type": "transition",
					"source": edge_from,
					"target": edge_to,
					"sourceHandle": "right",
					"targetHandle": "left",
					"updatable": True,
					"animated": True,
				}
			)
	doc.workflow_data = json.dumps(nodes)


def submitting(doc) -> dict | None:
	"""What an approval says about submitting `doc`: None when its kind has no
	approval on; otherwise the state it is in, and the action, if any, the
	reader may take to a submitted state."""
	from frappe.model.workflow import get_transitions, get_workflow, get_workflow_name

	if not get_workflow_name(doc.doctype):
		return None
	workflow = get_workflow(doc.doctype)
	submitted = {row.state for row in workflow.states if frappe.utils.cint(row.doc_status) == 1}
	action = next(
		(row.action for row in get_transitions(doc, workflow) if row.next_state in submitted),
		None,
	)
	return {"state": doc.get(workflow.workflow_state_field), "action": action}


def waiting(doc, method=None) -> None:
	"""Workflow Action after_insert: a record reached a step, so whoever holds a
	role the step is for, and may open the record, is told (Approval Waiting)."""
	from frappe.model.workflow import get_workflow_name

	from onedesk.one import notify

	if doc.status != "Open" or not doc.reference_doctype or not doc.reference_name:
		return
	workflow = get_workflow_name(doc.reference_doctype)
	if not workflow or not frappe.db.exists(doc.reference_doctype, doc.reference_name):
		return
	record = frappe.get_doc(doc.reference_doctype, doc.reference_name)
	state = record.get(frappe.db.get_value("Workflow", workflow, "workflow_state_field") or "workflow_state")
	held_by = [row.role for row in doc.get("permitted_roles") or []]
	if not held_by:
		return
	actions = frappe.get_all(
		"Workflow Transition",
		filters={"parent": workflow, "state": state, "allowed": ["in", held_by]},
		pluck="action",
	)
	people = {
		row.parent
		for row in frappe.get_all(
			"Has Role", filters={"role": ["in", held_by], "parenttype": "User"}, fields=["parent"], limit=0
		)
	}
	told = [
		one
		for one in sorted(people)
		if one not in ("Administrator", "Guest")
		and frappe.db.get_value("User", one, "enabled")
		and frappe.has_permission(record.doctype, "read", record, user=one)
	]
	if told:
		notify.notify(
			"Approval Waiting",
			told,
			record=(record.doctype, record.name),
			kind=_(record.doctype),
			record_name=record.name
			if (record.get_title() or record.name) == record.name
			else f"{record.name} ({record.get_title()})",
			state=_(state or ""),
			actions=", ".join(dict.fromkeys(_(one) for one in actions)) or _("move it on"),
		)


def roles_offered() -> list[dict]:
	"""The roles a step may be for, in One's words: each app's user and manager
	roles (one/settings.py APPS), and the workspace's administrators."""
	from onedesk.one import settings

	said = [{"role": roles.ADMINISTRATOR, "is": _("Workspace administrators")}]
	for product, _code, users, managers in settings.APPS:
		said += [{"role": one, "is": _("{0} users").format(product)} for one in users]
		said += [{"role": one, "is": _("{0} managers").format(product)} for one in managers]
	return said


def state(doctype: str) -> str:
	"""A token for the approvals on a kind of record as they are now, so a
	suggestion made before one changed is not applied over it."""
	rows = frappe.get_all(
		"Workflow", filters={"document_type": doctype}, fields=["name", "modified"], order_by="name"
	)
	return frappe.as_json([[row.name, str(row.modified)] for row in rows])


def make(doctype: str, values: dict) -> str:
	"""An approval, new or changed, from what OneAI suggested and the
	administrator approved: its states and actions made first if they are new
	words (frappe checks they exist before anything else), then the Workflow
	saved as its builder would, through `validate`."""
	_doctype(doctype)
	for row in values.get("states") or []:
		if not frappe.db.exists("Workflow State", row["state"]):
			frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": row["state"]}).insert()
	for row in values.get("transitions") or []:
		if not frappe.db.exists("Workflow Action Master", row["action"]):
			frappe.get_doc(
				{"doctype": "Workflow Action Master", "workflow_action_name": row["action"]}
			).insert()
	name = values.get("name")
	doc = frappe.get_doc("Workflow", name) if name else frappe.new_doc("Workflow")
	if not name:
		doc.workflow_name = values["workflow_name"]
		doc.document_type = doctype
	doc.set("states", values.get("states") or [])
	doc.set("transitions", values.get("transitions") or [])
	# Its steps changed, so the builder's old places for them no longer fit.
	doc.workflow_data = ""
	if values.get("is_active") is not None:
		doc.is_active = 1 if values["is_active"] else 0
	doc.save()
	return doc.name


def described() -> list[dict]:
	"""Every approval as OneAI reads it: its kind, whether it is on, its states
	and its steps, each with the role that takes it and when."""
	said = []
	for row in approvals():
		doc = frappe.get_doc("Workflow", row["name"])
		said.append(
			{
				"name": doc.name,
				"for": doc.document_type,
				"on": bool(doc.is_active),
				"states": [
					{
						"state": one.state,
						"submitted": one.doc_status == "1",
						"editable_by": one.allow_edit,
						**(
							{"sets": {"field": one.update_field, "value": one.update_value}}
							if one.update_field
							else {}
						),
					}
					for one in doc.states
				],
				"steps": [
					{
						"from": one.state,
						"action": one.action,
						"to": one.next_state,
						"by": one.allowed,
						**({"when": one.condition} if one.condition else {}),
					}
					for one in doc.transitions
				],
			}
		)
	return said


def unchanged(name: str, states: list[dict], transitions: list[dict], on: bool) -> bool:
	"""Whether an approval already has exactly these states, steps and switch."""
	held = frappe.get_doc("Workflow", name)
	state_keys = ("state", "doc_status", "allow_edit", "update_field", "update_value")
	step_keys = ("state", "action", "next_state", "allowed", "condition")

	def rows(given, keys):
		return [tuple(str(one.get(key) or "") for key in keys) for one in given]

	return (rows(held.states, state_keys), rows(held.transitions, step_keys), bool(held.is_active)) == (
		rows(states, state_keys),
		rows(transitions, step_keys),
		bool(on),
	)
