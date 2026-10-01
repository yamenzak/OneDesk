"""Reports and dashboards: what a workspace keeps of its own over its records.
docs/DESK-COVERAGE.md, P2.

Three things, each frappe's own:

- **Saved reports.** A list's Report view, saved under a name, is frappe's
  `Report` of type Report Builder. Anybody may save one (frappe offers Save As
  to everybody, and its `save_report` only ever writes that type), and it goes
  in the sidebar of the app whose list it was: for everybody when a workspace
  administrator saved it, in the person's own sidebar otherwise, through
  frappe's own sidebar layers (`Custom Sidebar`). Deleted, it leaves.
- **Dashboards.** frappe's `Dashboard`, of its `Dashboard Chart` and `Number
  Card`, which a workspace administrator makes. Everybody sees them under One >
  Dashboards, and frappe shows each chart only to who may read what it counts.
- **Reports by mail.** frappe's `Auto Email Report`, which a workspace
  administrator sets from a report's menu (Setup Auto Email).

What frappe trusts to whoever may customize it, and a workspace does not get:

- a report of any type but Report Builder. A Custom Report runs the report it
  is a copy of with no check of who may open that one, and frappe leaves
  Script and Query reports to its Script Manager already;
- a chart or a card of type Custom, which runs code an app wrote and is free
  to read past the reader's permissions;
- a report by mail that runs as somebody else.

erpnext's own dashboards are its modules' (Accounts, Stock, CRM), with a
company on every chart; One > Dashboards lists the workspace's own.
"""

import frappe
from frappe import _

from onedesk.one import layer, roles

GRANTS = {
	"Report": ("read", "write", "create", "delete"),
	"Auto Email Report": ("read", "write", "create", "delete"),
	"Dashboard": ("read", "write", "create", "delete"),
	"Dashboard Chart": ("read", "write", "create", "delete"),
	"Number Card": ("read", "write", "create", "delete"),
}

#: What the section a saved report goes under is called in a sidebar.
SECTION = "Saved Reports"


def settle() -> None:
	"""The administrator's grants, and Save As for everybody: frappe's Desk
	User may read a Report and not make one."""
	from frappe.permissions import add_permission, setup_custom_perms, update_permission_property

	roles.grant(GRANTS)
	desk = "Desk User"
	where = {"parent": "Report", "role": desk, "permlevel": 0, "if_owner": 0}
	if frappe.db.get_value("Custom DocPerm", where, "create"):
		return
	setup_custom_perms("Report")
	if not frappe.db.exists("Custom DocPerm", where):
		add_permission("Report", desk, 0)
	update_permission_property("Report", desk, 0, "create", 1, validate=False)


def _trusted() -> bool:
	"""Whoever frappe lets customize (one/layer.py): the operator, never a
	workspace."""
	return frappe.session.user == "Administrator" or not layer.held()


# ------------------------------------------------------------------ guards (hooks.py doc_events)


def report_kept(doc, method=None) -> None:
	"""Report.validate: a workspace makes Report Builder reports only."""
	if _trusted() or doc.is_standard == "Yes":
		return
	if doc.report_type != "Report Builder":
		frappe.throw(_("A report saved here is a list's Report view, saved under a name."))


def chart_kept(doc, method=None) -> None:
	"""Dashboard Chart.validate and Number Card.validate: a chart or a card
	counts records, or reads a report; it runs no code of an app's own."""
	if _trusted() or doc.get("is_standard"):
		return
	kind = doc.chart_type if doc.doctype == "Dashboard Chart" else doc.type
	if kind == "Custom":
		frappe.throw(_("A chart or a card here counts records, or reads a report."))
	counted = doc.get("parent_document_type") or doc.get("document_type")
	if counted and not frappe.has_permission(counted, "read"):
		frappe.throw(_("You cannot open {0}.").format(_(counted)), frappe.PermissionError)
	if kind == "Report" and doc.get("report_name"):
		if not frappe.get_doc("Report", doc.report_name).is_permitted():
			frappe.throw(_("You cannot open {0}.").format(_(doc.report_name)), frappe.PermissionError)


def mail_kept(doc, method=None) -> None:
	"""Auto Email Report.validate: a report goes by mail as whoever last set
	it up would see it, and only a report they may open."""
	if _trusted():
		return
	doc.user = frappe.session.user
	if not frappe.get_doc("Report", doc.report).is_permitted():
		frappe.throw(_("You cannot open {0}.").format(_(doc.report)), frappe.PermissionError)


# ------------------------------------------------------------------ the sidebar


def _module(doctype: str) -> str | None:
	"""The module of the sidebar frappe opens a kind in for whoever is saving
	(`build_entity_module_map`), so the report sits where its list was; else
	the first of One's app sidebars that lists the kind."""
	from frappe.boot import build_entity_module_map, get_module_sidebars

	sidebars = get_module_sidebars()
	shell = build_entity_module_map(sidebars).get(doctype)
	if shell and sidebars.get(shell, {}).get("module"):
		return sidebars[shell]["module"]
	for name in frappe.get_all(
		"Sidebar Item",
		filters={"parenttype": "Sidebar", "link_type": "DocType", "link_to": doctype},
		pluck="parent",
		order_by="parent asc",
	):
		if frappe.db.get_value("Sidebar", name, "app") == "onedesk":
			return frappe.db.get_value("Sidebar", name, "module")
	return None


def _layer(module: str, user: str | None):
	"""The site's layer of a module's sidebar (`user` None) or one person's,
	made if there is none yet."""
	from frappe.desk.doctype.custom_sidebar.custom_sidebar import SITE_LAYER, get_customization

	have = get_customization(module, user)
	if have:
		return frappe.get_doc("Custom Sidebar", have.name)
	return frappe.new_doc("Custom Sidebar").update({"module": module, "user": user or SITE_LAYER})


def placed(doc, method=None) -> None:
	"""Report.after_insert: a saved report put in its app's sidebar, under
	Saved Reports; for everybody when an administrator saved it."""
	if doc.report_type != "Report Builder" or doc.is_standard == "Yes" or not doc.ref_doctype:
		return
	module = _module(doc.ref_doctype)
	if not module:
		return
	user = None if roles.administers(doc.owner) else doc.owner
	layer = _layer(module, user)
	if any(row.link_type == "Report" and row.link_to == doc.name for row in layer.sidebar_items):
		return
	if not any(
		row.added and row.type == "Section Break" and row.label == SECTION for row in layer.sidebar_items
	):
		layer.append(
			"sidebar_items",
			{
				"type": "Section Break",
				"label": SECTION,
				"icon": "file-chart-column",
				"indent": 1,
				"collapsible": 1,
				"added": 1,
			},
		)
	layer.append(
		"sidebar_items",
		{
			"type": "Link",
			"label": doc.name,
			"link_type": "Report",
			"link_to": doc.name,
			"child": 1,
			"added": 1,
		},
	)
	layer.save(ignore_permissions=True)
	_redrawn(user)


def removed(doc, method=None) -> None:
	"""Report.on_trash: a saved report out of every sidebar it was in, and its
	section with it when it was the last."""
	for name in frappe.get_all(
		"Sidebar Item",
		filters={"parenttype": "Custom Sidebar", "link_type": "Report", "link_to": doc.name},
		pluck="parent",
		distinct=True,
	):
		layer = frappe.get_doc("Custom Sidebar", name)
		kept = [
			row for row in layer.sidebar_items if not (row.link_type == "Report" and row.link_to == doc.name)
		]
		if not any(row.added and row.link_type == "Report" for row in kept):
			kept = [
				row
				for row in kept
				if not (row.added and row.type == "Section Break" and row.label == SECTION)
			]
		layer.set("sidebar_items", kept)
		layer.save(ignore_permissions=True)
		_redrawn(layer.user or None)


def _redrawn(user: str | None) -> None:
	"""Whoever sees the changed sidebar is told to fetch it again. frappe keeps
	each person's reports for an hour (`DeskViews`) and draws a sidebar's
	report only from them, so those go first."""
	frappe.cache.delete_keys("user:*:has_role:Report")
	frappe.publish_realtime("one_sidebars", {}, user=user, after_commit=True)


@frappe.whitelist()
def sidebars() -> dict:
	"""The reader's sidebars as frappe's boot has them, to swap in."""
	from frappe.desk.doctype.custom_sidebar.custom_sidebar import module_payload

	said = module_payload()
	reported(said.get("module_sidebars"))
	return said


def reported(sidebars: dict | None) -> None:
	"""Each report link a layer added given its type and kind, as frappe gives
	one an app shipped (`sidebar.filter_sidebar_items`): the sidebar draws a
	report link only with them, and frappe resolves layers' rows after that."""
	for sidebar in (sidebars or {}).values():
		for item in sidebar.get("items") or []:
			if item.get("link_type") != "Report" or item.get("report") or not item.get("link_to"):
				continue
			report = frappe.db.get_value(
				"Report",
				item["link_to"],
				["report_type", "ref_doctype", "disabled"],
				as_dict=True,
				cache=True,
			)
			if report and not report.disabled:
				item["report"] = {"report_type": report.report_type, "ref_doctype": report.ref_doctype}
