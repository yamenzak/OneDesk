"""Forms: every form a workspace administrator may customize, in one place.

Customizing a form was reached only from the form itself (its menu's
Customize). OneStudio lists them all, by the app each belongs to, with what
the workspace has changed on each and how many extensions run on it, and
opens frappe's form on the Customize page (one/customize.py), which stays
what it was.
"""

import frappe
from frappe import _

from onedesk.one import roles
from onedesk.one.customize import REFUSED_MODULES


def _counts(doctype: str, field: str) -> dict:
	return {
		row[field]: row.n
		for row in frappe.get_all(doctype, fields=[field, {"COUNT": "*", "as": "n"}], group_by=field)
	}


def _apps() -> dict:
	"""Each kind of record a rail of One's links to, and the rail's module, in
	one read rather than one a kind."""
	rails = dict(
		frappe.get_all("Sidebar", filters={"app": "onedesk"}, fields=["name", "module"], as_list=True)
	)
	out = {}
	for row in frappe.get_all(
		"Sidebar Item",
		filters={"parenttype": "Sidebar", "link_type": "DocType", "parent": ["in", list(rails)]},
		fields=["parent", "link_to"],
		order_by="is_default_module desc, parent asc",
	):
		out.setdefault(row.link_to, rails[row.parent])
	return out


@frappe.whitelist()
def forms() -> list[dict]:
	"""The forms the reader may customize: each with its app, how many of
	its customizations are the workspace's, and how many extensions run on
	it. The changed ones first."""
	roles.require()
	from onedesk.one import audit

	apps = _apps()
	changed = _counts("Workspace Customization", "record_doctype")
	extended = _counts("Extension", "record_doctype")
	out = []
	for doctype in audit.kinds():
		meta = frappe.get_meta(doctype)
		if meta.istable or meta.issingle or meta.module in REFUSED_MODULES:
			continue
		module = apps.get(doctype)
		out.append(
			{
				"doctype": doctype,
				"label": _(doctype),
				"app": _(module) if module else _("Other Forms"),
				"changes": changed.get(doctype, 0),
				"extensions": extended.get(doctype, 0),
			}
		)
	return sorted(out, key=lambda one: (not (one["changes"] or one["extensions"]), one["app"], one["label"]))
