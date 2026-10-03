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
