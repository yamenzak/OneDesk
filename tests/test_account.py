"""AccountCenter (docs/ONE.md): your own account and the workspace's, and who
may use which app (one/people.py). Pure parts."""

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

CENTER = tree.APP / "account_center" / "center.py"
PEOPLE = tree.APP / "one" / "people.py"
SCRIPT = tree.APP / "public" / "js" / "account_center" / "account_center.js"


def _load(path, names):
	space = {"_lt": lambda s: s, "_": lambda s: s}
	for node in ast.parse(path.read_text()).body:
		if isinstance(node, (ast.Import, ast.ImportFrom)):
			continue
		named = getattr(node, "name", None) or (getattr(node.targets[0], "id", None) if isinstance(node, ast.Assign) else None)
		if named in names:
			exec(ast.unparse(node), space)
	return space


A = _load(CENTER, {"SECTIONS", "PROFILE", "EMPLOYEE_OWN", "SHARED", "AT_WORK", "BANK", "PROFILE_PARTS", "_masked"})
P = _load(PEOPLE, {"level_of", "roles_for"})


def test_a_level_is_read_from_the_roles_a_person_holds():
	used, managed = ("Sales User",), ("Sales Manager",)
	assert P["level_of"]({"Sales Manager"}, used, managed) == "Manager"
	assert P["level_of"]({"Sales User", "Desk User"}, used, managed) == "User"
	assert P["level_of"]({"Desk User"}, used, managed) == "None"


def test_a_manager_uses_the_app_as_well():
	used, managed = ("Stock User", "Purchase User"), ("Stock Manager",)
	assert P["roles_for"]("Manager", used, managed) == {"Stock User", "Purchase User", "Stock Manager"}
	assert P["roles_for"]("User", used, managed) == {"Stock User", "Purchase User"}
	assert P["roles_for"]("None", used, managed) == set()


def test_every_section_has_a_loader_a_drawing_and_a_tab():
	source = CENTER.read_text()
	script = SCRIPT.read_text()
	for key, _label, _icon, group in A["SECTIONS"]:
		assert group in ("yours", "workspace")
		assert f'"{key}": _{key}' in source or key in A["PROFILE_PARTS"], key
		assert f"draw_{key}(" in script, key
		assert f'id: "{key}"' in script, key


def test_the_workspaces_sections_are_its_administrators():
	source = CENTER.read_text()
	for name in ("sign_out_everywhere", "send_reset", "set_enabled", "invite", "invite_again"):
		body = source.split(f"def {name}(", 1)[1].split("\n@frappe.whitelist", 1)[0]
		assert "roles.require()" in body, name
	assert re.search(r"if not _may_open\(section\):\s+roles\.require\(\)", source)
	opens = source.split("def _may_open(", 1)[1].split("\n\n\n", 1)[0]
	assert 'group == "yours" or roles.administers()' in opens and 'section == "plan" and _sees_plan()' in opens
	saves = source.split("def save(", 1)[1].split("\n\n\n", 1)[0]
	assert 'if section not in PROFILE_PARTS:\n\t\troles.require()' in saves
	assert '**{part: _profile for part in PROFILE_PARTS}' in source and '**{part: _save_profile for part in PROFILE_PARTS}' in saves


def test_a_person_changes_how_to_reach_them_and_never_their_job_or_their_pay():
	own = set(A["EMPLOYEE_OWN"]) | set(A["SHARED"].values())
	assert not own & set(A["AT_WORK"]), "HR sets a person's job"
	assert not own & set(A["BANK"]), "a changed bank account is how pay is stolen, so HR changes it"
	assert not own & {"ctc", "salary_mode", "status", "user_id", "relieving_date", "company"}


def test_what_both_records_say_is_asked_once_and_written_to_the_employee():
	assert set(A["SHARED"]) <= set(A["PROFILE"])
	assert not set(A["SHARED"]) & set(A["EMPLOYEE_OWN"])


def test_an_account_number_shows_its_last_four_only():
	assert A["_masked"]("DE89 3704 0044 0532 0130 00") == "•••• 3000"
	assert A["_masked"]("123") == "123"
	assert A["_masked"]("") == ""


def test_a_save_is_refused_if_the_record_changed_since_it_was_opened():
	"""Profile saves the login and the employee against the `modified` the
	centre loaded, so frappe's own check_if_latest refuses a stale save."""
	source = CENTER.read_text()
	body = source[source.index("def _save_both") :]
	body = body[: body.index("\ndef ")]
	assert body.count("sections.as_opened(") == 2
	assert '"opened"' in source and "sections.opened(user, employee)" in source


def test_a_section_is_an_editor_on_its_panel():
	script = SCRIPT.read_text()
	engine = (SCRIPT.parent.parent / "center_section.js").read_text()
	assert "extends onedesk.CenterSection" in script and "extends onedesk.shell.Editor" in engine
	assert "get_values(" not in script, "FieldGroup.get_values leaves a cleared field out, so it would never be cleared"
	page = engine.split("onedesk.center_section.page = ", 1)[1].split("\n};\n", 1)[0]
	for part in ("set_indicator", "clear_indicator", "set_primary_action", "clear_primary_action", "add_inner_button", "clear_inner_toolbar", "set_breadcrumbs"):
		assert part in page, part


def test_hr_hears_of_a_new_address_or_emergency_contact_and_a_contact_is_whole():
	source = CENTER.read_text()
	body = source[source.index("def _save_both") :]
	body = body[: body.index("\ndef ")]
	assert "person_to_be_contacted and employee.emergency_phone_number" in body
	assert body.index("frappe.throw(") < body.index("employee.save(")
	assert "_tell_hr(employee, was)" in body
	tell = source[source.index("def _tell_hr") :]
	tell = tell[: tell.index("\ndef ")]
	assert "hr.employee_details_changed(employee, said)" in tell
	told = (tree.APP / "one_hr" / "tell.py").read_text()
	tell = told[told.index("def employee_details_changed") :].split("\ndef ", 1)[0]
	assert '"Employee Details Changed"' in tell and '"HR Manager"' in tell
	assert "NOT_PEOPLE" in tell and "frappe.session.user" in tell, "not the bench account, not themselves"
	assert tree.notifications()["Employee Details Changed"]["module"] == "one_hr"


def test_a_link_opens_a_centre_on_a_section():
	desk = (tree.APP / "public" / "js" / "one_interface" / "centre.js").read_text()
	assert "onedesk.centers.open(asked.center, asked)" in desk
	assert "window.history.replaceState(null, \"\", window.location.pathname)" in desk
