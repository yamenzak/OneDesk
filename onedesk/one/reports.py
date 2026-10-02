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


#: What each kind is listed under in a sidebar.
SECTIONS = {
	"Report": (SECTION, "file-chart-column"),
	"Dashboard": ("Dashboards", "layout-dashboard"),
	# A workspace's own record types (one_studio/record_types.py).
	"DocType": ("Your Records", "table-2"),
}


def _put(link_type: str, name: str, module: str, user: str | None) -> None:
	"""A report or a dashboard listed in one sidebar's layer, under its section."""
	label, icon = SECTIONS[link_type]
	layer = _layer(module, user)
	if any(row.link_type == link_type and row.link_to == name for row in layer.sidebar_items):
		return
	if not any(
		row.added and row.type == "Section Break" and row.label == label for row in layer.sidebar_items
	):
		layer.append(
			"sidebar_items",
			{
				"type": "Section Break",
				"label": label,
				"icon": icon,
				"indent": 1,
				"collapsible": 1,
				"added": 1,
			},
		)
	layer.append(
		"sidebar_items",
		{"type": "Link", "label": name, "link_type": link_type, "link_to": name, "child": 1, "added": 1},
	)
	layer.save(ignore_permissions=True)
	_redrawn(user)


def _take(link_type: str, name: str, users: tuple | None = None) -> None:
	"""A report or a dashboard taken out of the layers that list it: every
	layer, or the site's and these people's. Its section goes with the last."""
	label, _icon = SECTIONS[link_type]
	for parent in frappe.get_all(
		"Sidebar Item",
		filters={"parenttype": "Custom Sidebar", "link_type": link_type, "link_to": name},
		pluck="parent",
		distinct=True,
	):
		layer = frappe.get_doc("Custom Sidebar", parent)
		if users is not None and layer.user and layer.user not in users:
			continue
		kept = [
			row for row in layer.sidebar_items if not (row.link_type == link_type and row.link_to == name)
		]
		if not any(row.added and row.link_type == link_type for row in kept):
			kept = [
				row for row in kept if not (row.added and row.type == "Section Break" and row.label == label)
			]
		layer.set("sidebar_items", kept)
		layer.save(ignore_permissions=True)
		_redrawn(layer.user or None)


def placed(doc, method=None) -> None:
	"""Report.after_insert: a saved report put in its app's sidebar, under
	Saved Reports; for everybody when an administrator saved it. Show In
	moves it."""
	if doc.report_type != "Report Builder" or doc.is_standard == "Yes" or not doc.ref_doctype:
		return
	module = _module(doc.ref_doctype)
	if not module:
		return
	user = None if roles.administers(doc.owner) else doc.owner
	_put("Report", doc.name, module, user)
	frappe.publish_realtime("one_report_placed", {"report": doc.name}, user=doc.owner, after_commit=True)


def removed(doc, method=None) -> None:
	"""Report.on_trash and Dashboard.on_trash: out of every sidebar it was in."""
	_take(doc.doctype, doc.name)


# ------------------------------------------------------------------ Show In


def places() -> list[dict]:
	"""Where a report or a dashboard may be shown, as {module, label}: One, and
	each app the reader works in (every app, for an administrator)."""
	from frappe.boot import get_module_sidebars

	from onedesk.one.access import all_levels
	from onedesk.one.settings import APPS

	seen = get_module_sidebars()
	held = set(frappe.get_roles())
	own = all_levels()
	everything = roles.administers()
	names = ["One"] + [
		app
		for app, _icon, used, managed in APPS
		if everything or held & (set(used) | set(managed) | set(own.get(app, ())))
	]
	return [
		{"module": seen[name]["module"], "label": name} for name in names if seen.get(name, {}).get("module")
	]


def _kind(kind: str, name: str) -> str:
	"""The doctype a Show In names, refused to whoever may not move it."""
	if kind == "Report":
		doc = frappe.get_doc("Report", name)
		if doc.report_type != "Report Builder" or doc.is_standard == "Yes":
			frappe.throw(_("Only a saved report can be shown somewhere else."))
		if doc.owner != frappe.session.user and not roles.administers():
			frappe.throw(
				_("Only whoever saved a report, or an administrator, can move it."), frappe.PermissionError
			)
	elif kind == "Dashboard":
		roles.require()
		frappe.get_doc("Dashboard", name)
	else:
		frappe.throw(_("That cannot be set."))
	return kind


@frappe.whitelist()
def where(kind: str, name: str) -> dict:
	"""Where a report or a dashboard is listed for the reader, and where it may go."""
	_kind(kind, name)
	user = frappe.session.user
	now = {"module": None, "everybody": 0}
	for row in frappe.get_all(
		"Sidebar Item",
		filters={"parenttype": "Custom Sidebar", "link_type": kind, "link_to": name},
		fields=["parent"],
	):
		module, owner = frappe.db.get_value("Custom Sidebar", row.parent, ["module", "user"])
		if not owner or owner == user:
			now = {"module": module, "everybody": int(not owner)}
			if not owner:
				break
	return {**now, "places": places(), "administers": int(roles.administers())}


@frappe.whitelist(methods=["POST"])
def place(kind: str, name: str, module: str | None = None, everybody: int = 0) -> None:
	"""A report or a dashboard shown in one app's sidebar, for the reader or,
	by an administrator, for everybody; or in none (no `module`)."""
	_kind(kind, name)
	everybody = frappe.utils.cint(everybody)
	if everybody and not roles.administers():
		frappe.throw(_("Only an administrator can show it to everybody."), frappe.PermissionError)
	if module and module not in {one["module"] for one in places()}:
		frappe.throw(_("That cannot be set."))
	owner = frappe.db.get_value(kind, name, "owner")
	_take(kind, name, (frappe.session.user, owner))
	if module:
		_put(kind, name, module, None if everybody else frappe.session.user)


def _redrawn(user: str | None) -> None:
	"""Whoever sees the changed sidebar is told to fetch it again. frappe keeps
	each person's reports and dashboards for an hour (`DeskViews`) and draws a
	sidebar's link to one only from them, so those go first."""
	frappe.cache.delete_keys("user:*:has_role:Report")
	frappe.cache.delete_keys("user:*:allowed_dashboards")
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
