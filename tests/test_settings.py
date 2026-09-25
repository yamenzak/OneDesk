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


S = _load({"SECTIONS", "APPS", "LEVELS", "level_of", "roles_for", "PROFILE", "EMPLOYEE_OWN", "SHARED", "AT_WORK", "BANK", "_masked"})


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
	page = (tree.APP / "public" / "js" / "settings.js").read_text()
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


def test_the_sections_are_the_ones_sidebar_and_the_workspaces_only_for_its_administrators():
	import json

	rail = json.loads((tree.APP / "one" / "sidebar" / "one" / "one.json").read_text())
	linked = {(json.loads(item["route_options"])["section"], item["link_to"]) for item in rail["items"] if item.get("route_options")}
	for key, _label, _icon, group in S["SECTIONS"]:
		assert (key, "settings" if group == "you" else "workspace-settings") in linked, key
	page = json.loads((tree.APP / "one" / "page" / "workspace_settings" / "workspace_settings.json").read_text())
	assert [one["role"] for one in page["roles"]] == ["Workspace Administrator"]


def test_a_person_changes_how_to_reach_them_and_never_their_job_or_their_pay():
	own = set(S["EMPLOYEE_OWN"]) | set(S["SHARED"].values())
	assert not own & set(S["AT_WORK"]), "HR sets a person's job"
	assert not own & set(S["BANK"]), "a changed bank account is how pay is stolen, so HR changes it"
	assert not own & {"ctc", "salary_mode", "status", "user_id", "relieving_date", "company"}


def test_what_both_records_say_is_asked_once_and_written_to_the_employee():
	assert set(S["SHARED"]) <= set(S["PROFILE"])
	assert not set(S["SHARED"]) & set(S["EMPLOYEE_OWN"])


def test_an_account_number_shows_its_last_four_only():
	assert S["_masked"]("DE89 3704 0044 0532 0130 00") == "•••• 3000"
	assert S["_masked"]("123") == "123"
	assert S["_masked"]("") == ""


def test_a_save_is_refused_if_the_record_changed_since_it_was_opened():
	"""Profile saves the login and the employee against the `modified` the page
	loaded, so frappe's own check_if_latest refuses a stale save."""
	source = SETTINGS.read_text()
	body = source[source.index("def _save_profile") :]
	body = body[: body.index("\ndef ")]
	assert body.count("_as_opened(") == 2
	assert '"opened"' in source and "_opened(user, employee)" in source


def test_the_page_sends_every_field_and_behaves_like_a_form():
	# The form behaviour is the shell's Editor, which Settings extends.
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
