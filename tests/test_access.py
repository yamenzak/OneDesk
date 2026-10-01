"""Access (one/access.py): a level adds only what its app's own roles may do,
on kinds they work with; record access holds people to the kinds Access offers
and never shows or takes away HR's own; profiles are applied through People's
own access, keeping what else a person holds; OneAI reads it all. These read
the code that says so."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "access.py").read_text()
SETTINGS = (tree.APP / "one" / "settings.py").read_text()


def _body(name: str) -> str:
	return SOURCE.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_every_door_is_the_administrators():
	for name in (
		"level",
		"save_level",
		"delete_level",
		"for_doctype",
		"save_profile",
		"save_group",
		"remove_profile",
		"remove_group",
	):
		assert "roles.require()" in _body(name), name
	assert "roles.require()" in _body("_person")
	for name in ("hold", "let_go"):
		assert "_person(" in _body(name), name


def test_a_level_never_adds_past_its_apps_own_roles():
	save = _body("save_level")
	assert "allowed = kinds(app)" in save
	assert "past = chosen - allowed[doctype]" in save and "frappe.throw" in save
	kinds = _body("kinds")
	assert "REFUSED_MODULES" in kinds and "meta.istable" in kinds


def test_a_level_is_the_apps_user_and_itself():
	assert "return set(used) | {level}" in SETTINGS
	assert "own.get(name, ())" in SETTINGS


def test_record_access_stays_within_its_kinds():
	assert '"allow": ["in", RECORD_KINDS]' in _body("record_access")
	assert "doc.allow not in RECORD_KINDS" in _body("let_go")
	assert "Company" not in SOURCE.split("RECORD_KINDS = (", 1)[1].split(")", 1)[0]


def test_a_profile_keeps_what_else_a_person_holds():
	assert "_set_access(" in _body("put_on")
	assert "doc.unlock()" in _body("save_profile")


def test_oneai_reads_access():
	ai = (tree.APP / "one" / "ai.py").read_text()
	assert "def workspace_access(" in ai and '"page:workspace-settings/access"' in ai
	assert '"onedesk.one.ai.workspace_access"' in (tree.APP / "hooks.py").read_text()
