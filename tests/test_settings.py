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


S = _load({"SECTIONS", "OPENS"})




def test_every_section_has_a_loader_and_a_drawing():
	source = SETTINGS.read_text()
	page = (tree.APP / "public" / "js" / "settings.js").read_text()
	for key, _label, _icon, group in S["SECTIONS"]:
		assert group in ("you", "workspace")
		if key in S["OPENS"]:
			assert re.search(rf"const centre = \{{[^}}]*\b{key}:", page), f"{key} opens a centre, and settings.js doesn't"
			continue
		assert f'"{key}": _{key}' in source, key
		assert f"draw_{key}(" in page, key


def test_every_workspace_section_is_for_its_administrators():
	source = SETTINGS.read_text()
	assert re.search(r'if _group\(section\) == "workspace":\s+roles\.require\(\)', source)


def test_the_sections_are_the_ones_sidebar_and_the_workspaces_only_for_its_administrators():
	import json

	rail = json.loads((tree.APP / "one" / "sidebar" / "one" / "one.json").read_text())
	linked = {(json.loads(item["route_options"])["section"], item["link_to"]) for item in rail["items"] if item.get("route_options")}
	for key, _label, _icon, group in S["SECTIONS"]:
		if key in S["OPENS"]:
			continue
		assert (key, "settings" if group == "you" else "workspace-settings") in linked, key
	page = json.loads((tree.APP / "one" / "page" / "workspace_settings" / "workspace_settings.json").read_text())
	assert [one["role"] for one in page["roles"]] == ["Workspace Administrator"]






def test_the_page_sends_every_field_and_behaves_like_a_form():
	script = (tree.APP / "public" / "js" / "settings.js").read_text()
	shell = (tree.APP / "public" / "js" / "shell.js").read_text()
	assert "extends onedesk.shell.Editor" in script
	for source in (script, shell):
		assert "get_values(" not in source, "FieldGroup.get_values leaves a cleared field out, so it would never be cleared"
	for part in ("doc_subscribe", "doc_update", "beforeunload", "TimestampMismatchError", "save_action"):
		assert part in shell, part


def test_what_oneai_offers_on_settings_is_for_a_section_that_exists_and_is_documented():
	"""Point 7 of the passover: a screen OneAI offers anything on is one its
	README explains, since "How do I fill this in?" answers from there."""
	ai = (tree.APP / "one" / "ai.py").read_text()
	readme = (tree.APP / "one" / "README.md").read_text().split("## Under the hood", 1)[0]
	keys = {key for key, *_ in S["SECTIONS"]}
	offered = re.findall(r'"page:settings/(\w+)"', ai)
	assert offered
	labels = {key: str(label) for key, label, *_ in S["SECTIONS"]}
	for key in offered:
		assert key in keys, key
		assert f"### {labels[key]}" in readme, f"Settings › {labels[key]} is not in one/README.md"
	for key in re.findall(r'"page:workspace-settings/(\w+)"', ai):
		assert key in keys, key
		heading = labels[key] if labels[key].startswith("Workspace ") else f"{labels[key]}, for the Workspace"
		assert f"### {heading}\n" in readme, f"Workspace › {labels[key]} is not in one/README.md"
