"""Frappe's, erpnext's and hrms's own desk, kept out of a workspace's.

The boot carries One's sidebars and workspaces only; the platform's own people
(`boot.platform`) keep frappe's whole desk.
"""

import frappe

APP = "onedesk"

#: The sidebar a record no other sidebar of One's lists lands in.
FIRST = "One"


def keep(bootinfo) -> None:
	"""`extend_bootinfo`: One's sidebars and workspaces, and nobody else's."""
	from onedesk.one.boot import platform

	if platform():
		return
	kept(bootinfo)
	# Import opens Data Import, the platform's; see docs/BACKLOG.md.
	if isinstance(bootinfo.get("user"), dict):
		bootinfo["user"]["can_import"] = []
	pages = (bootinfo.get("workspaces") or {}).get("pages")
	if isinstance(pages, list):
		bootinfo["one_elsewhere"] = sorted(
			# frappe.router.slug
			page["name"].lower().replace(" ", "-")
			for page in pages
			if page.get("app") != APP and page.get("name")
		)
		bootinfo["workspaces"]["pages"] = [page for page in pages if page.get("app") == APP]
		# A private workspace of one's own is frappe's furniture, not One's.
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


@frappe.whitelist()
def kind_of(name: str) -> bool:
	"""Whether a desk address names a kind of record. One the reader may not
	read is not in their boot, so frappe's router takes it for a page; it
	then says No access rather than Not Found (outside.js)."""
	name = (name or "").replace("-", " ").strip()
	return bool(name) and bool(frappe.db.exists("DocType", name))
