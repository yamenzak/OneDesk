"""A workspace's desk is One's (one/outside.py): frappe's, erpnext's and
hrms's own sidebars and workspaces are left out of the boot for everyone but
the platform's own people, and their addresses and frappe's apps screen go to
One's Home. These read the code that says so."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "outside.py").read_text()


def test_the_boot_carries_ones_sidebars_and_workspaces_only():
	assert 'APP = "onedesk"' in SOURCE and 'FIRST = "One"' in SOURCE
	assert SOURCE.count("if platform():") == 2
	assert '(sidebar or {}).get("app") == APP' in SOURCE
	assert 'page.get("app") == APP' in SOURCE and '["has_create_access"] = False' in SOURCE
	assert "outside.keep(bootinfo)" in (tree.APP / "one" / "boot.py").read_text()
	# A sidebar swapped in after a change is held to the same.
	assert "outside.kept(said)" in (tree.APP / "one" / "reports.py").read_text()


def test_elsewhere_and_the_apps_screen_go_to_ones_home():
	desk = (tree.APP / "public" / "js" / "desk.js").read_text()
	assert 'for (const slug of frappe.boot.one_elsewhere) frappe.re_route[slug] = "one";' in desk
	assert 'frappe.re_route[""] = "one";' in desk
	assert 'page["name"].lower().replace(" ", "-")' in SOURCE


def test_menus_offer_no_screen_the_reader_cannot_open():
	"""Gap 5: each item that ends on a System Manager's screen is offered on
	frappe's own read check of it, and Import not at all."""
	js = (tree.APP / "public" / "js" / "outside.js").read_text()
	assert 'frappe.model.can_read("Audit Trail")' in js
	assert 'frappe.model.can_read("Auto Email Report")' in js
	assert 'frappe.model.can_read("Print Settings")' in js
	assert '"/assets/onedesk/js/outside.js"' in (tree.APP / "hooks.py").read_text()
	assert 'bootinfo["user"]["can_import"] = []' in SOURCE
	declutter = (tree.APP / "one" / "declutter.py").read_text()
	assert "\"System Health\": \"frappe.model.can_read('System Health Report')\"" in declutter


def test_frappes_furniture_editors_are_not_offered():
	"""Gap 6: Edit Sidebar and Manage Dock arrange frappe's sidebars and dock."""
	js = (tree.APP / "public" / "js" / "outside.js").read_text()
	assert '["edit-sidebar"]' in js and '["workspace-selector"]' in js
	assert "if (frappe.boot.one_elsewhere && frappe.ui.SidebarHeader && frappe.ui.Sidebar)" in js
