"""Our assets reach people after a deploy. Frappe Cloud serves /assets as
immutable for a year, so every include carries a hash of its file
(one/stamp.py), and frappe.require asks with it too (theme.js)."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from onedesk.one import stamp

APP = Path(__file__).resolve().parent.parent / "onedesk"

INCLUDES = ("app_include_js", "app_include_css", "web_include_js", "web_include_css", "setup_wizard_requires")


def test_every_include_is_stamped():
	tree = ast.parse((APP / "hooks.py").read_text())
	held = {
		target.id: node.value
		for node in tree.body
		if isinstance(node, ast.Assign)
		for target in node.targets
		if isinstance(target, ast.Name) and target.id in INCLUDES
	}
	assert set(held) == set(INCLUDES)
	for name, value in held.items():
		assert isinstance(value, ast.Call) and value.func.id == "stamped", name


def test_an_address_carries_its_files_hash():
	said = stamp.stamped("/assets/onedesk/js/shell.js")
	assert said.startswith("/assets/onedesk/js/shell.js?v=") and len(said.split("=")[1]) == 10
	assert stamp.stamped("/assets/elsewhere/x.js") == "/assets/elsewhere/x.js"
	assert all("/dist/" not in one for one in stamp.versions())


def test_what_is_required_later_is_stamped_too():
	theme = (APP / "public" / "js" / "theme.js").read_text()
	assert "frappe.assets.bundled_asset = " in theme and "frappe.boot.one_assets" in theme
	assert 'bootinfo["one_assets"] = stamp.versions()' in (APP / "one" / "boot.py").read_text()
