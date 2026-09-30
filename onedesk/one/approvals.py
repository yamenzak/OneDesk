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
- its transitions have no condition and run no tasks;
- a state sets a field only to a plain value, and only a field anybody who
  may edit the record may set (the first permission level, not the record's
  own bookkeeping);
- it keeps its state in a field of its own, which is made here the first
  time, as frappe makes it but as the workspace, since the administrator may
  not add a field by hand.
"""

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
	"""Workflow validate: what an approval written by the workspace may do."""
	if not layer.held():
		return
	meta = _doctype(doc.document_type)
	for row in doc.transitions or []:
		if (row.condition or "").strip():
			frappe.throw(
				_("{0} to {1}: an action here is taken by a role, not decided by code.").format(
					_(row.state), _(row.next_state)
				)
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
