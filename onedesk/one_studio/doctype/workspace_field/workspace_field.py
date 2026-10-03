# Copyright (c) 2026, One and contributors
# For license information, please see license.txt

"""Custom Fields in OneStudio: every field this workspace added or changed,
one row a field, as frappe's own list draws it.

A virtual doctype: nothing is stored. Each row is read from the workspace's
ledger (one/customize.py). A field is changed only through OneAI.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from onedesk.one import customize, roles


def rows() -> list[frappe._dict]:
	"""Every field the workspace added to a form or changed on it."""
	from onedesk.one_studio import forms

	apps = forms._apps()
	out = []
	for doctype in frappe.get_all("Workspace Customization", pluck="record_doctype", distinct=True):
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		app = forms._app(doctype, meta.module, apps) or "Other Forms"
		modified = _modified(doctype)
		for one in customize.added(doctype):
			out.append(
				_row(
					doctype,
					app,
					one,
					"Changed" if one.get("came_with") else "Added",
					modified.get(one["fieldname"]),
				)
			)
		for one in customize.changed_fields(doctype):
			if any(row.form == doctype and row.fieldname == one["fieldname"] for row in out):
				continue
			df = meta.get_field(one["fieldname"])
			one["fieldtype"] = df.fieldtype if df else ""
			out.append(_row(doctype, app, one, "Changed", modified.get(one["fieldname"])))
	return out


def _row(doctype: str, app: str, one: dict, status: str, modified) -> frappe._dict:
	return frappe._dict(
		name=f"{doctype}-{one['fieldname']}",
		label=one.get("label") or one["fieldname"],
		form=doctype,
		fieldtype=one.get("fieldtype") or "",
		status=status,
		also_added_to=", ".join(_(other) for other in one.get("also_on") or []),
		app=app,
		fieldname=one["fieldname"],
		modified=modified,
		creation=modified,
		owner="Administrator",
		docstatus=0,
		_assign=None,
		_comments=None,
		_liked_by=None,
		_user_tags=None,
		_comment_count=0,
	)


def _modified(doctype: str) -> dict:
	"""When each field was last changed: its custom field's or its last
	property setter's time."""
	out = {}
	for row in frappe.get_all(
		"Custom Field", filters={"dt": doctype}, fields=["fieldname", "modified"]
	) + frappe.get_all(
		"Property Setter", filters={"doc_type": doctype}, fields=["field_name as fieldname", "modified"]
	):
		if row.fieldname and (row.fieldname not in out or row.modified > out[row.fieldname]):
			out[row.fieldname] = row.modified
	# A standard field added to other forms: when the last copy was made.
	for row in frappe.get_all(
		"Workspace Customization",
		filters={"record_doctype": doctype, "kind": "Custom Field"},
		fields=["row", "modified"],
	):
		fieldname = (row.row or "").rsplit("-", 1)[-1]
		if fieldname and (fieldname not in out or row.modified > out[fieldname]):
			out[fieldname] = row.modified
	return out


def _matches(row: frappe._dict, filters) -> bool:
	"""frappe's list filters, as a list of [doctype, field, op, value] or a
	dict, applied to one row."""
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	if isinstance(filters, dict):
		filters = [
			[None, field, *(value if isinstance(value, list | tuple) else ["=", value])]
			for field, value in filters.items()
		]
	for one in filters or []:
		field, op, value = one[-3], one[-2], one[-1]
		have = str(row.get(field) or "")
		op = (op or "=").lower()
		if op == "=" and have != str(value):
			return False
		if op == "!=" and have == str(value):
			return False
		if op in ("like", "not like"):
			found = str(value or "").strip("%").lower() in have.lower()
			if found != (op == "like"):
				return False
		if op in ("in", "not in"):
			values = value if isinstance(value, list | tuple) else str(value or "").split(",")
			if (have in [str(v).strip() for v in values]) != (op == "in"):
				return False
	return True


def _listed(filters=None, or_filters=None, order_by=None) -> list[frappe._dict]:
	if not roles.administers():
		return []
	out = [row for row in rows() if _matches(row, filters)]
	if or_filters:
		ors = frappe.parse_json(or_filters) if isinstance(or_filters, str) else or_filters
		out = [row for row in out if any(_matches(row, [one]) for one in ors)]
	field, _, way = (
		(order_by or "modified desc").replace("`tabWorkspace Field`.", "").replace("`", "").partition(" ")
	)
	field = field if field in ("label", "form", "fieldtype", "status", "app", "modified") else "modified"
	return sorted(out, key=lambda row: row.get(field) or "", reverse=(way or "desc").strip().lower() != "asc")


class WorkspaceField(Document):
	def db_insert(self, *args, **kwargs):
		frappe.throw(_("Ask OneAI to add a field."))

	def db_update(self, *args, **kwargs):
		frappe.throw(_("Ask OneAI to change a field."))

	def delete(self, *args, **kwargs):
		frappe.throw(_("Ask OneAI to remove a field."))

	def load_from_db(self):
		roles.require()
		found = next((row for row in rows() if row.name == self.name), None)
		if not found:
			frappe.throw(_("{0} not found").format(self.name), frappe.DoesNotExistError)
		super(Document, self).__init__(found)

	@staticmethod
	def get_list(filters=None, or_filters=None, order_by=None, start=0, page_length=20, **kwargs):
		listed = _listed(filters, or_filters, order_by)
		start = frappe.utils.cint(start)
		length = frappe.utils.cint(page_length) or len(listed)
		return listed[start : start + length]

	@staticmethod
	def get_count(filters=None, or_filters=None, **kwargs):
		return len(_listed(filters, or_filters))

	@staticmethod
	def get_stats(**kwargs):
		return {}
