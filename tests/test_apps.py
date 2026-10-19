"""Apps a workspace turns off: hidden from the rail, search and pickers, never
refused. See one/apps.py."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

APPS = tree.APP / "one" / "apps.py"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")
JS = (tree.APP / "public" / "js" / "apps.js").read_text(encoding="utf-8")


def _load(names):
	space = {}
	for node in ast.parse(APPS.read_text()).body:
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return space


def test_a_type_leaves_search_only_when_every_app_listing_it_is_off():
	unlisted = _load({"unlisted"})["unlisted"]
	lists = {"OneBook": {"Sales Invoice", "Customer"}, "OneCRM": {"Opportunity", "Customer"}, "OneTask": {"Task"}}
	assert unlisted(lists, {"OneCRM"}) == {"Opportunity"}, "Customer stays: OneBook lists it"
	assert unlisted(lists, {"OneCRM", "OneBook"}) == {"Opportunity", "Customer", "Sales Invoice"}
	assert unlisted(lists, set()) == set()


def test_turning_an_app_off_hides_and_never_refuses():
	"""Nothing in has_permission or frappe's disabled-app switch: OneIntake
	checks has_permission before it files, so a refusal would stop it."""
	source = APPS.read_text()
	assert "has_permission" not in source and "app_state" not in source
	assert '"onedesk.one.apps.boot"' in HOOKS
	assert '"frappe.desk.search.search_link": "onedesk.one.apps.search_link"' in HOOKS
	assert '"/assets/onedesk/js/apps.js"' in HOOKS
	assert "roles.require()" in source.split("def save(")[1].split("def ")[0], "a workspace administrator's"
	assert 'KEPT = ("One", "OneAdmin", "One Admin")' in source, "One's own Home and the operators' never go"
	companions = (tree.APP / "one" / "companions.py").read_text()
	assert "row.get(\"link_to\") not in off" in companions, "the site's Dock layer hides them"
	assert 'frappe.user.has_role("Workspace Administrator")' in JS and ".dock-user" in JS
	assert "build_options" in JS and 'frappe.ui.form.on("*"' in JS


def test_a_turned_off_apps_records_open_elsewhere():
	outside = (tree.APP / "one" / "outside.py").read_text()
	assert "name not in off" in outside and "apps.rehome(said)" in outside
	readme = (tree.APP / "one" / "README.md").read_text()
	assert "**Apps**, at the bottom of the rail" in readme.split("## Under the hood")[0], "how_to answers it"
