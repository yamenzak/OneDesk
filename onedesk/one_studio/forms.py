"""Every form a workspace administrator may customize: its app, how many of
its customizations are the workspace's, and how many extensions run on it.
OneAI reads it (forms_here); people see OneStudio's Custom Fields list
(doctype/workspace_field).
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


#: Where no rail of One's links to a kind of record, the app its module
#: belongs to: an Account Category is OneBook's though no rail names it.
#: What is shared by every app (Setup, Contacts, Geo) stays Other Forms.
MODULES = {
	"Accounts": "One Book",
	"Regional": "One Book",
	"EDI": "One Book",
	"HR": "One HR",
	"Payroll": "One HR",
	"CRM": "One CRM",
	"Selling": "One CRM",
	"Support": "One CRM",
	"Telephony": "One CRM",
	"Stock": "One Inventory",
	"Buying": "One Inventory",
	"Manufacturing": "One Inventory",
	"Subcontracting": "One Inventory",
	"Assets": "One Inventory",
	"Maintenance": "One Inventory",
	"Quality Management": "One Inventory",
	"Projects": "One Project",
}


def _app(doctype: str, module: str, apps: dict) -> str | None:
	"""The app a form is under: the rail that links to it, else its module's,
	else its module when that is one of One's own (OneIntake, OneMail)."""
	if doctype in apps:
		return apps[doctype]
	if module in MODULES:
		return MODULES[module]
	return module if frappe.db.get_value("Module Def", module, "app_name") == "onedesk" else None


def _changed() -> dict:
	"""How many of each form's customizations are the workspace's: what the
	ledger names (fields, and changes to a field), and the rows marked as the
	workspace's in its head, its connections and its buttons."""
	out = _counts("Workspace Customization", "record_doctype")
	for child in ("Record Head Band", "Record Head Verb", "Record Head Chart", "Record Head Linked"):
		for doctype, n in _counted(child, {"parenttype": "Record Head", "custom": 1}).items():
			out[doctype] = out.get(doctype, 0) + n
	for child in ("DocType Link", "DocType Action"):
		for doctype, n in _counted(child, {"parenttype": "DocType", "custom": 1}).items():
			out[doctype] = out.get(doctype, 0) + n
	return out


def _counted(doctype: str, filters: dict) -> dict:
	return {
		row.parent: row.n
		for row in frappe.get_all(
			doctype, filters=filters, fields=["parent", {"COUNT": "*", "as": "n"}], group_by="parent"
		)
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
	from onedesk.one.settings import _mark

	apps = _apps()
	# Each app's mark, as Settings draws it (one/settings.py): the product's
	# name, OneCloud for One Storage, One's own for the forms every app shares.
	products = dict(
		frappe.get_all("Sidebar", filters={"app": "onedesk"}, fields=["module", "name"], as_list=True)
	)
	changed = _changed()
	extended = _counts("Extension", "record_doctype")
	out = []
	for doctype in audit.kinds():
		meta = frappe.get_meta(doctype)
		if meta.istable or meta.issingle or meta.module in REFUSED_MODULES:
			continue
		module = _app(doctype, meta.module, apps)
		out.append(
			{
				"doctype": doctype,
				"label": _(doctype),
				"app": _(module) if module else _("Other Forms"),
				"mark": _mark(products.get(module) or (module or "").replace(" ", "")),
				"changes": changed.get(doctype, 0),
				"extensions": extended.get(doctype, 0),
			}
		)
	return sorted(out, key=lambda one: (not (one["changes"] or one["extensions"]), one["app"], one["label"]))


@frappe.whitelist()
def extensions(doctype: str) -> list[dict]:
	"""The extensions that run on a form, for OneAI: what each
	does, where and when, and whether it is on. No code."""
	from onedesk.one.customize import may
	from onedesk.one_studio import extensions as kept

	may(doctype)
	return frappe.get_list(
		kept.EXTENSION,
		filters={"record_doctype": doctype},
		fields=["name", "title", "runs", "view", "event", "enabled", "explanation", "review"],
		order_by="enabled desc, modified desc",
	)
