"""Frappe's, erpnext's and hrms's own desk, kept out of a workspace's.

The boot carries One's sidebars and workspaces only; the platform's own people
(`boot.platform`) keep frappe's whole desk.
"""

import frappe

APP = "onedesk"

FIRST = "One"


def keep(bootinfo) -> None:
	"""`extend_bootinfo`: One's sidebars and workspaces, and nobody else's."""
	from onedesk.one.boot import platform

	if platform():
		return
	kept(bootinfo)
	if isinstance(bootinfo.get("user"), dict):
		bootinfo["user"]["can_import"] = []
	pages = (bootinfo.get("workspaces") or {}).get("pages")
	if isinstance(pages, list):
		bootinfo["one_elsewhere"] = sorted(
			page["name"].lower().replace(" ", "-")
			for page in pages
			if page.get("app") != APP and page.get("name")
		)
		bootinfo["workspaces"]["pages"] = [page for page in pages if page.get("app") == APP]
		bootinfo["workspaces"]["has_create_access"] = False


def kept(said: dict) -> None:
	"""One's sidebars only, One's first, and the records they own. Also what
	`reports.sidebars` swaps in when a sidebar changes."""
	from onedesk.one.boot import platform

	if platform():
		return
	sidebars = said.get("module_sidebars")
	if not isinstance(sidebars, dict):
		return
	ours = {name: sidebar for name, sidebar in sidebars.items() if (sidebar or {}).get("app") == APP}
	order = sorted(ours, key=lambda name: name != FIRST)
	said["module_sidebars"] = {name: ours[name] for name in order}
	owned = said.get("entity_module")
	if isinstance(owned, dict):
		said["entity_module"] = {entity: shell for entity, shell in owned.items() if shell in ours}
	placed(said)


def placed(said: dict) -> None:
	"""Where each record opens, worked out again over One's sidebars alone.
	frappe maps every route to a sidebar on the server (`build_canonical_shells`)
	before this runs, so its map still names erpnext's and hrms's; the same
	ladder over what is left puts a Project Template in OneProject rather than in
	a sidebar the reader is not given."""
	from frappe.desk.desk_views import DeskViews
	from frappe.desk.doctype.sidebar.sidebar import build_canonical_shells

	default = ((said.get("user") or {}).get("default_workspace") or {}).get("name")
	said["canonical_shell"], said["home_shell"] = build_canonical_shells(
		said["module_sidebars"], said.get("entity_module") or {}, DeskViews(), default_workspace=default
	)
	inherited(said)


def inherited(said: dict) -> None:
	"""A record type or a report no sidebar of One's lists, of a module whose
	own sidebar is erpnext's, opens in the sidebar One keeps that module's work
	in (`one_module_heirs`), where the ladder would put it in the reader's home."""
	from frappe.desk.doctype.sidebar.sidebar import linked_entities

	heirs = frappe.get_hooks("one_module_heirs") or {}
	shells = said.get("canonical_shell") or {}
	if not heirs:
		return
	sidebars = said["module_sidebars"]
	listed = {entity for sidebar in sidebars.values() for item in sidebar.get("items") or [] for entity in linked_entities(item)}
	for kind, filters in (("DocType", {"istable": 0}), ("Report", {})):
		placed = shells.get(kind)
		if not isinstance(placed, dict):
			continue
		for name, module in frappe.get_all(
			kind, filters={"module": ["in", list(heirs)], **filters}, fields=["name", "module"], as_list=True
		):
			shell = next((one for one in heirs[module] if one in sidebars), None)
			if shell and name in placed and name not in listed:
				placed[name] = shell


@frappe.whitelist()
def kind_of(name: str) -> bool:
	"""Whether a desk address names a kind of record. One the reader may not
	read is not in their boot, so frappe's router takes it for a page; it
	then says No access rather than Not Found (outside.js)."""
	name = (name or "").replace("-", " ").strip()
	return bool(name) and bool(frappe.db.exists("DocType", name))
