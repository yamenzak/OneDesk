"""The rail is the person's (one/rail.py, docs/run/RUN.md P5.8 and P5.9):
an app AccessCenter puts somebody at no level in is never offered to them,
and their order and folders survive a changed shipped Dock."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

RAIL = tree.APP / "one" / "rail.py"
JS = tree.APP / "public" / "js"
HOOKS = tree.hooks()


def _load(names):
	space = {}
	for node in ast.parse(RAIL.read_text()).body:
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return space


APPS = [
	("OneBook", "book", ("Accounts User",), ("Accounts Manager",)),
	("OneCRM", "crm", ("Sales User",), ("Sales Manager",)),
	("OneMail", "mail", ("OneMail User",), ("OneMail Manager",)),
]


def test_an_app_at_no_level_is_unreached():
	nowhere = _load({"nowhere"})["nowhere"]
	held = {"Sales User", "All"}
	assert nowhere(APPS, held, {}, ("OneMail",)) == ["OneBook"], "a role without OneBook never sees it"
	assert nowhere(APPS, held | {"Bookkeeper"}, {"OneBook": ["Bookkeeper"]}, ("OneMail",)) == [], "a level of the workspace's own reaches it"
	assert nowhere(APPS, {"Accounts Manager"}, {}, ()) == ["OneCRM", "OneMail"]


def test_unreached_apps_leave_the_boot_and_their_centres_with_them():
	outside = (tree.APP / "one" / "outside.py").read_text()
	assert "off = set(apps.hidden()) | rail.unreached()" in outside, "their sidebars leave module_sidebars"
	versions = (tree.APP / "one" / "versions.py").read_text()
	assert "hidden = set(apps.hidden()) | rail.unreached()" in versions, "their Help and versions are off"
	assert '"onedesk.one.rail.boot"' in HOOKS
	extend = HOOKS.split("extend_bootinfo = [")[1].split("]")[0]
	assert extend.index("onedesk.one.rail.boot") > extend.index("onedesk.one.boot.boot_session"), "after the sidebars are settled"
	opened = _load({"opened"})["opened"]
	rows = [{"url": "/desk/one?center=account"}, {"url": "/desk/one?center=settings&module=One"}, {"link_to": "Note"}]
	assert opened(rows) == {"account", "settings"}
	source = RAIL.read_text()
	assert 'bootinfo["one_centres"] = [one for one in' in source


def test_an_order_takes_in_what_an_upgrade_adds_where_the_dock_puts_it():
	ordered = _load({"ordered"})["ordered"]
	shipped = ["One", "OneMail", "OneBook", "OneCRM"]
	mine = ["OneCRM", "One", "OneBook", "OneMail"]
	assert ordered(shipped, mine) == mine
	upgraded = ["One", "OneMail", "OneBook", "OneFactory", "OneCRM"]
	assert ordered(upgraded, mine) == ["OneCRM", "One", "OneBook", "OneFactory", "OneMail"], "beside the app before it"
	assert ordered(["OneNew", *upgraded], mine)[0] == "OneNew", "first, when nothing comes before it"
	assert ordered(shipped, []) == shipped, "no order is the shipped one"


def test_folders_survive_a_changed_shipped_dock():
	folded = _load({"folded"})["folded"]
	folders = [{"name": "Money", "apps": ["OneBook", "OneCRM"]}, {"name": "Old", "apps": ["OneGone"]}, {"name": " ", "apps": ["One"]}]
	before = {"One", "OneMail", "OneBook", "OneCRM"}
	assert folded(folders, before) == [{"name": "Money", "apps": ["OneBook", "OneCRM"]}]
	after = {"One", "OneMail", "OneBook", "OneCRM", "OneFactory"}
	assert folded(folders, after) == [{"name": "Money", "apps": ["OneBook", "OneCRM"]}], "an upgrade leaves them as they were"
	twice = [{"name": "A", "apps": ["OneBook"]}, {"name": "B", "apps": ["OneBook", "OneCRM"]}]
	assert folded(twice, before) == [{"name": "A", "apps": ["OneBook"]}, {"name": "B", "apps": ["OneCRM"]}], "an app in one folder only"


def test_order_is_frappes_dock_and_folders_are_ones_layer():
	arrange = (JS / "one_interface" / "arrange.js").read_text()
	assert '"frappe.desk.doctype.dock.dock.save_user_dock"' in arrange, "the person's order is frappe's user layer"
	assert 'items: "[]"' in arrange, "Reset saves the layer empty: frappe reads it as no opinion"
	folders = (JS / "one_interface" / "folders.js").read_text()
	assert 'SETTINGS: "One Rail"' in folders and "frappe.model.user_settings.save(this.SETTINGS" in folders
	assert 'SETTINGS = "One Rail"' in RAIL.read_text()
	companions = (tree.APP / "one" / "companions.py").read_text()
	assert "rail.ordered(" in companions and "def layer(order: list[str] | None = None)" in companions, "the workspace's order is the site layer"
	setup = (JS / "one" / "setup_center.js").read_text()
	assert '"save_workspace"' in setup and "frappe.boot.one_administers" in setup
	for name in ("folders.js", "arrange.js", "launcher.js"):
		assert f'"/assets/onedesk/js/one_interface/{name}"' in HOOKS, name


def test_the_launcher_is_the_apps_button_and_the_phones_apps():
	launcher = (JS / "one_interface" / "launcher.js").read_text()
	assert 'group(__("Recent")' in launcher, "recent first"
	assert "onedesk.interface.phone.found(pages, said)" in launcher, "it finds pages too"
	apps = (JS / "apps.js").read_text()
	assert "onedesk.rail.launcher()" in apps
	phone = (JS / "one_interface" / "phone.js").read_text()
	assert "onedesk.rail.draw($launcher" in phone, "on a phone the Apps sheet is the launcher"
