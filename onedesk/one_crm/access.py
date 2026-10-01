"""Who may do what in OneCRM, where ERPNext's defaults do not fit.

- A **Sales User** could delete a deal but not a lead. A deal carries its
  stage history, its calls and its reasons for being lost, so deleting one is
  a Sales Manager's, as deleting a lead already was.
- A **Sales User** could only read a Prospect, so the person who makes a lead
  into a business could not write the business down. They may now create and
  edit one.

- Only a **System Manager** could make a Call Log. Sales people log calls by
  hand from a lead's or deal's page, and OneAI suggests one from what they
  said about a call, which they approve as themselves. They may now read,
  make and correct one.

- Only a **System Manager** could open what the Campaigns and Setup groups
  link to: Email Campaign, Email Group, Lead Source and Lead Assignment. A
  Sales Manager now runs them and a Sales User reads them (`GIVEN`).
- A **Sales Manager** keeps the Assignment Rules that share out leads and
  deals, and only those: a rule of theirs is on a lead or a deal, and decides
  by comparing the record's own fields with plain values, `utm_source ==
  "Website"`, never by code (`assignment_rule`).

Everybody in sales still sees every lead and deal: a small team shares its
pipeline, and one that does not can say so with User Permissions.

frappe's `update_permission_property` copies a doctype's standard permissions
into Custom DocPerm before changing one, which is what the Role Permissions
Manager does. Written once: a doctype that already has Custom DocPerm rows has
been decided by the workspace, and is left alone.
"""

import ast

import frappe
from frappe import _
from frappe.model import no_value_fields
from frappe.permissions import add_permission, update_permission_property

from onedesk.one import layer, roles

#: doctype: [(role, permission, value)]
CHANGES = {
	"Opportunity": [("Sales User", "delete", 0)],
	"Prospect": [("Sales User", "create", 1), ("Sales User", "write", 1)],
	"Call Log": [
		(role, ptype, 1) for role in ("Sales User", "Sales Manager") for ptype in ("read", "create", "write")
	],
}


#: What sales is given where erpnext gives only its System Manager.
GIVEN = {
	doctype: {"Sales User": roles.USE, "Sales Manager": roles.MANAGE}
	for doctype in ("Email Campaign", "Email Group", "Email Group Member", "UTM Source")
} | {"Assignment Rule": {"Sales Manager": roles.MANAGE}}

#: The kinds of record a Sales Manager's Assignment Rule shares out.
SHARED_OUT = ("Lead", "Opportunity")

#: An assignment rule's conditions, frappe evaluates with the record's
#: fields as names.
CONDITIONS = ("assign_condition", "unassign_condition", "close_condition")

#: What a plain condition is made of: the record's fields, plain values,
#: comparisons and the words that join them.
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
		frappe.throw(_("A rule of yours shares out leads or deals."))
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
