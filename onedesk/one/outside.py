"""Frappe's, erpnext's and hrms's own desk, kept out of a workspace's.

One's rail and its sidebars are a workspace's whole desk. Frappe still boots
every sidebar and workspace a person may open, its own (Build, Users, Email,
Printing), erpnext's (Accounts, Selling, Stock, Home) and hrms's (Payroll,
Leaves), and its sidebar resolver picks among all of them: a record no One
sidebar lists, opened cold or reached from a frappe record, landed in
erpnext's or frappe's sidebar and rail, and their workspaces opened by address
and through search.

So the boot carries One's sidebars only, with One's first, and One's
workspaces only. A record no One sidebar lists stays in the sidebar it was
opened from, or One's when opened cold (frappe's own steps 5 and 6). The
workspaces taken out are named in `one_elsewhere`, and desk.js sends their
addresses, and frappe's apps screen, to One's Home.

The platform's own people (`boot.platform`) keep frappe's whole desk.
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
