"""Settings: one place for what a person and a workspace set. Pure parts."""

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SETTINGS = tree.APP / "one" / "settings.py"


def _load(names):
	space = {"_lt": lambda s: s, "_": lambda s: s}
	for node in ast.parse(SETTINGS.read_text()).body:
		if isinstance(node, (ast.Import, ast.ImportFrom)):
			continue
		named = getattr(node, "name", None) or (getattr(node.targets[0], "id", None) if isinstance(node, ast.Assign) else None)
		if named in names:
			exec(ast.unparse(node), space)
	return space


S = _load({"SECTIONS", "APPS", "LEVELS", "level_of", "roles_for"})


def test_a_level_is_read_from_the_roles_a_person_holds():
	used, managed = ("Sales User",), ("Sales Manager",)
	assert S["level_of"]({"Sales Manager"}, used, managed) == "Manager"
	assert S["level_of"]({"Sales User", "Desk User"}, used, managed) == "User"
	assert S["level_of"]({"Desk User"}, used, managed) == "None"


def test_a_manager_uses_the_app_as_well():
	used, managed = ("Stock User", "Purchase User"), ("Stock Manager",)
	assert S["roles_for"]("Manager", used, managed) == {"Stock User", "Purchase User", "Stock Manager"}
	assert S["roles_for"]("User", used, managed) == {"Stock User", "Purchase User"}
	assert S["roles_for"]("None", used, managed) == set()


def test_every_section_has_a_loader_and_a_drawing():
	source = SETTINGS.read_text()
	page = (tree.APP / "one" / "page" / "settings" / "settings.js").read_text()
	for key, _label, _icon, group in S["SECTIONS"]:
		assert f'"{key}": _{key}' in source, key
		assert f"draw_{key}(" in page, key
		assert group in ("you", "workspace")


def test_every_workspace_section_is_for_its_administrators():
	source = SETTINGS.read_text()
	for name in ("set_access", "set_admin", "set_enabled", "invite"):
		body = source.split(f"def {name}(", 1)[1].split("\n@frappe.whitelist", 1)[0]
		assert "roles.require()" in body, name
	assert re.search(r'if _group\(section\) == "workspace":\s+roles\.require\(\)', source)
