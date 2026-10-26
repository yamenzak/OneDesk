"""Reports and dashboards: what a workspace keeps of its own over its records.

Saved reports, dashboards and reports by mail, each frappe's own, without what
frappe trusts only to whoever may customize it.
"""

import frappe
from frappe import _

from onedesk.one import layer, roles

SECTION = "Saved Reports"


def _trusted() -> bool:
	"""Whoever frappe lets customize (one/layer.py): the operator, never a
	workspace."""
	return frappe.session.user == "Administrator" or not layer.held()


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


SECTIONS = {
	"Report": (SECTION, "file-chart-column"),
	"Dashboard": ("Dashboards", "layout-dashboard"),
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


def places() -> list[dict]:
	"""Where a report or a dashboard may be shown, as {module, label}: One, and
	each app the reader works in (every app, for an administrator)."""
	from frappe.boot import get_module_sidebars

	from onedesk.one.access import all_levels
	from onedesk.one.people import APPS

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
				_("Only the person who saved a report, or an administrator, can move it."), frappe.PermissionError
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
		frappe.throw(_("Only an administrator can show it to everyone."), frappe.PermissionError)
	if module and module not in {one["module"] for one in places()}:
		frappe.throw(_("That cannot be set."))
	owner = frappe.db.get_value(kind, name, "owner")
	_take(kind, name, (frappe.session.user, owner))
	if module:
		_put(kind, name, module, None if everybody else frappe.session.user)


def anchored(rows: list, shipped: list, named: set, key) -> list:
	"""A layer's arrangement with each row the app ships, and the layer never
	named, moved to just after the row the app ships before it. frappe keeps a
	row a layer does not name after the ones it does, so a row shipped after a
	layer was saved, or one that replaced a row it names, sank to the end of
	the rail. Pure over the arrangement, the shipped order and the named keys."""
	loose = {key(row): row for row in rows if key(row) in shipped and key(row) not in named}
	out = [row for row in rows if key(row) not in loose]
	for i, one in enumerate(shipped):
		if one not in loose:
			continue
		have = [key(row) for row in out]
		before = next((shipped[j] for j in range(i - 1, -1, -1) if shipped[j] in have), None)
		out.insert(have.index(before) + 1 if before else 0, loose[one])
	return out


def untouched(rows: list, before: list | None, key, added) -> bool:
	"""Whether a layer keeps the app's rows in the order the app shipped them
	last time, so nobody rearranged them. A layer saved before that order was
	first kept is taken as nobody's arrangement. Pure."""
	if before is None:
		return True
	ours = [key(row) for row in rows if not added(row) and key(row) in before]
	return ours == [one for one in before if one in ours]


def rebased(rows: list, shipped: list, key, added, child=lambda row: False) -> list:
	"""A layer nobody rearranged, in the order the app ships now: the app's
	rows in that order, the layer's own rows at the end (Your Records) still
	at the end, and any other of its own after the row it followed. A group of
	its own goes after the app's rows under that one too, so it never takes
	them in. Pure over the arrangement, the shipped order, a key, what the
	layer added and which rows sit under a group."""
	place = {one: i for i, one in enumerate(shipped)}
	theirs = [i for i, row in enumerate(rows) if not added(row) and key(row) in place]
	tail = rows[theirs[-1] + 1 :] if theirs else list(rows)
	out = sorted((rows[i] for i in theirs), key=lambda row: place[key(row)])
	before = None
	for row in rows[: len(rows) - len(tail)]:
		if added(row) or key(row) not in place:
			at = next((i for i, one in enumerate(out) if key(one) == before), -1) if before else -1
			if not child(row):
				while at + 1 < len(out) and child(out[at + 1]) and key(out[at + 1]) in place:
					at += 1
			out.insert(at + 1, row)
		before = key(row)
	return out + tail


SHIPPED = "one_sidebar_shipped"


def settle() -> None:
	"""after_migrate: every layer over One's sidebars with the rows an update
	shipped in the places the app ships them. A layer nobody rearranged follows
	the app's new order (`rebased`), and one somebody did keeps theirs, with
	new rows after the row the app ships before them (`anchored`). frappe's
	layer names every row once saved, so without this an app's new order never
	reached a workspace that had placed a report in its rail."""
	import json

	from frappe.desk.doctype.custom_sidebar.custom_sidebar import _save_customization, layer_arrangement
	from frappe.desk.doctype.sidebar.sidebar import get_module_base, item_key

	kept = json.loads(frappe.db.get_default(SHIPPED) or "{}")
	modules = set(frappe.get_all("Sidebar", filters={"app": "onedesk"}, pluck="module"))
	shipped = {module: [item_key(row) for row in get_module_base(module).rows] for module in modules}
	for one in frappe.get_all("Custom Sidebar", fields=["name", "module", "user"]):
		if one.module not in modules:
			continue
		user = one.user or None
		rows = layer_arrangement(one.module, user)
		if untouched(rows, kept.get(one.module), item_key, lambda row: row.get("added")):
			moved = rebased(rows, shipped[one.module], item_key, lambda row: row.get("added"), lambda row: bool(row.get("child")))
		else:
			named = {item_key(row) for row in frappe.get_doc("Custom Sidebar", one.name).sidebar_items}
			moved = anchored(rows, shipped[one.module], named, item_key)
		if [item_key(row) for row in moved] != [item_key(row) for row in rows]:
			_save_customization(one.module, moved, user=user)
			_redrawn(user)
	frappe.db.set_default(SHIPPED, json.dumps(shipped, sort_keys=True))


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

	from onedesk.one import outside

	said = module_payload()
	outside.kept(said)
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
