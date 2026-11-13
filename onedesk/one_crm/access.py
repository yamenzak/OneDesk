"""Who may do what in OneCRM: its one ability, a Permission Type on CRM
Settings (one/rights.py, docs/ROLES.md), and what sales may do with deals,
Prospects, Call Logs, the Campaigns, Support and Setup groups and Assignment
Rules where ERPNext's defaults do not fit, written once per doctype.
"""

import ast

import frappe
from frappe import _, _lt
from frappe.model import no_value_fields
from frappe.permissions import add_permission, update_permission_property

from onedesk.one import layer, roles

APP = "OneCRM"

# Not everybody's: People gives it to whoever uses OneCRM.
USER = "Sales User"

DOCTYPE = "CRM Settings"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "merge",
		"group": WORKSPACE,
		"label": _lt("Merge Duplicate Leads"),
		"kind": "switch",
		"all": "crm_merge",
		"about": _lt("Fold a lead that is somebody already known into the one kept, which deletes it."),
	},
]

# Nothing of OneCRM's is given on one record.
SHARED = ()

# ERPNext's own roles and what each starts with, written once on migrate
# (rights.settle); merging deleted a lead, so it was a Sales Manager's, and still is.
DEFAULTS = {
	"Sales User": {},
	"Sales Manager": {"merge": 1},
}


CHANGES = {
	"Opportunity": [("Sales User", "delete", 0)],
	"Prospect": [("Sales User", "create", 1), ("Sales User", "write", 1)],
	"Call Log": [
		(role, ptype, 1) for role in ("Sales User", "Sales Manager") for ptype in ("read", "create", "write")
	],
}


GIVEN = {
	doctype: {"Sales User": roles.USE, "Sales Manager": roles.MANAGE}
	for doctype in ("Email Campaign", "Email Group", "Email Group Member", "UTM Source")
} | {
	"Assignment Rule": {"Sales Manager": roles.MANAGE},
	"Selling Settings": {role: ("read",) for role in ("Sales User", "Stock User", "Accounts User", "Projects User")},
	"Promotional Scheme": {"Sales User": roles.USE},
	"Party Specific Item": {"Sales User": roles.USE, "Sales Manager": roles.MANAGE},
	"Support Settings": {"Sales Manager": ("read", "write")},
	"Incoming Call Settings": {"Sales Manager": roles.MANAGE},
	"Telephony Call Type": {"Sales User": roles.USE, "Sales Manager": roles.MANAGE},
	"Communication Medium": {"Sales Manager": roles.MANAGE},
	"Sales Partner Type": {"Sales User": roles.USE, "Sales Manager": roles.MANAGE},
}

SUPPORT = ("Issue", "Warranty Claim", "Maintenance Schedule", "Maintenance Visit")
SUPPORT_LISTS = ("Issue Type", "Issue Priority", "Service Level Agreement")
GIVEN |= {doctype: {"Sales User": roles.WORK, "Sales Manager": roles.MANAGE} for doctype in SUPPORT}
GIVEN |= {doctype: {"Sales User": roles.USE, "Sales Manager": roles.MANAGE} for doctype in SUPPORT_LISTS}
SUPPORT_REPORTS = ("Issue Summary", "Issue Analytics", "First Response Time for Issues", "Support Hour Distribution")

SHARED_OUT = ("Lead", "Opportunity")

CONDITIONS = ("assign_condition", "unassign_condition", "close_condition")

PLAIN = (
	ast.Expression,
	ast.Compare,
	ast.BoolOp,
	ast.And,
	ast.Or,
	ast.UnaryOp,
	ast.Not,
	ast.USub,
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


def settle() -> None:
	roles.give(GIVEN)
	for report in SUPPORT_REPORTS:
		roles.open_report(report, "Sales User", "Sales Manager")
	for doctype, changes in CHANGES.items():
		if frappe.db.exists("Custom DocPerm", {"parent": doctype}):
			continue
		for role, ptype, value in changes:
			if not _has_row(doctype, role):
				add_permission(doctype, role, 0)
			update_permission_property(doctype, role, 0, ptype, value, validate=False)


def _has_row(doctype: str, role: str) -> bool:
	"""Whether the role has a rule on the doctype at level 0, standard or custom."""
	where = {"parent": doctype, "role": role, "permlevel": 0}
	return bool(frappe.db.exists("Custom DocPerm", where) or frappe.db.exists("DocPerm", where))


def plain(meta, condition: str | None) -> bool:
	"""Whether an assignment condition only compares the record's own fields
	of the first permission level with plain values. Pure but for the meta."""
	condition = (condition or "").strip()
	if not condition:
		return True
	try:
		tree = ast.parse(condition, mode="eval")
	except SyntaxError:
		return False
	for node in ast.walk(tree):
		if not isinstance(node, PLAIN):
			return False
		if isinstance(node, ast.Name) and node.id not in ("True", "False", "None", "name"):
			df = meta.get_field(node.id)
			if not df or df.permlevel or df.fieldtype in no_value_fields:
				return False
	return True


def _free(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return user == "Administrator" or frappe.has_permission("Custom Field", "write", user=user)


def assignment_rule(doc, method=None) -> None:
	"""Assignment Rule validate: a Sales Manager's shares out leads and deals,
	by the record's own fields."""
	if not layer.held():
		return
	if doc.document_type not in SHARED_OUT:
		frappe.throw(_("A rule of yours shares out leads or opportunities."))
	meta = frappe.get_meta(doc.document_type)
	for field in CONDITIONS:
		if not plain(meta, doc.get(field)):
			frappe.throw(
				_("{0} may only compare the record's fields with plain values, such as {1}.").format(
					_(doc.meta.get_label(field)), 'status == "Open"'
				)
			)


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	"""Assignment Rule: somebody frappe does not let customize reaches only
	the rules that share out leads and deals."""
	if _free(user):
		return True
	return not doc.document_type or doc.document_type in SHARED_OUT


def query(user: str | None = None) -> str | None:
	if _free(user):
		return None
	listed = ", ".join(frappe.db.escape(one) for one in SHARED_OUT)
	return f"`tabAssignment Rule`.`document_type` in ({listed})"
