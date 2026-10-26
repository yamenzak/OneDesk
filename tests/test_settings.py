"""Workspace Settings, what is left of it until stage 3 of docs/ONE.md, and
the centres its other sections moved to in stage 2. Pure parts."""

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


S = _load({"SECTIONS"})



def test_every_section_has_a_loader_and_a_drawing():
	source = SETTINGS.read_text()
	page = (tree.APP / "public" / "js" / "settings.js").read_text()
	for key, _label, _icon, group in S["SECTIONS"]:
		assert group == "workspace"
		assert f'"{key}": _{key}' in source, key
		assert f"draw_{key}(" in page, key


def test_what_moved_out_is_drawn_in_its_centre():
	"""docs/ONE.md, stage 2: each section a person or an administrator had in
	Settings is a tab of the centre or the module it belongs to, loaded and
	saved through that module, and the page for a person's own settings is
	gone."""
	js = tree.APP / "public" / "js"
	moved = {
		"draw_general(": (js / "one_control.js", tree.APP / "one" / "control.py"),
		"draw_holidays(": (js / "one_hr" / "hr_control.js", tree.APP / "one_hr" / "control.py"),
		"draw_link(": (js / "one_calendar" / "calendar_control.js", tree.APP / "one_calendar" / "control.py"),
		"draw_reads(": (js / "one_ai" / "ai_center.js", tree.APP / "one_ai" / "yours.py"),
		"draw_access(": (js / "access_center.js", tree.APP / "one" / "access_center.py"),
	}
	for drawn, (script, server) in moved.items():
		assert drawn in script.read_text() and "extends onedesk.CenterSection" in script.read_text(), script
		assert "def load(" in server.read_text(), server
		assert drawn not in (js / "settings.js").read_text(), drawn
	assert not (tree.APP / "one" / "page" / "settings").exists()


def test_every_workspace_section_is_for_its_administrators():
	source = SETTINGS.read_text()
	assert re.search(r'if _group\(section\) == "workspace":\s+roles\.require\(\)', source)


def test_the_sections_are_the_ones_sidebar_and_the_workspaces_only_for_its_administrators():
	import json

	rail = json.loads((tree.APP / "one" / "sidebar" / "one" / "one.json").read_text())
	linked = {(json.loads(item["route_options"])["section"], item["link_to"]) for item in rail["items"] if item.get("route_options")}
	for key, _label, _icon, _group in S["SECTIONS"]:
		assert (key, "workspace-settings") in linked, key
	assert not any(item.get("link_to") == "settings" for item in rail["items"]), "the rail still opens the old Settings page"
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
	assert not re.findall(r'"page:settings/(\w+)"', ai), "OneAI offers something on the old Settings page"
	labels = {key: str(label) for key, label, *_ in S["SECTIONS"]}
	for key in re.findall(r'"page:workspace-settings/(\w+)"', ai):
		assert key in keys, key
		heading = labels[key] if labels[key].startswith("Workspace ") else f"{labels[key]}, for the Workspace"
		assert f"### {heading}\n" in readme, f"Workspace › {labels[key]} is not in one/README.md"
