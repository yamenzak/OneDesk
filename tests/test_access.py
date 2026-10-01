"""Access (one/access.py): every level of an app, User and Manager too, may be
given or have taken away anything on the kinds the app works with, what a
right needs comes with it, and a record a level may make lets it pick what the
record must name; record access holds people to the kinds Access offers
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
		"new_level",
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


def test_a_level_stays_on_its_apps_kinds():
	save = _body("save_level")
	assert "allowed = set(kinds(app))" in save
	assert "doctype not in allowed" in save and "frappe.throw" in save
	kinds = _body("kinds")
	assert "REFUSED_MODULES" in kinds and "meta.istable" in kinds


def test_what_every_level_shares_sits_on_the_apps_user_roles():
	"""Every level holds the app's User roles, so taking something away from
	one level moves it off them: what all share stays there, and each level's
	own goes on its own roles, the plain user's on the companion role."""
	put = _body("_set")
	assert "shared = set.intersection(*have.values())" in put
	assert "_put(doctype, used, shared)" in put
	assert "_put(doctype, _carriers(app, one), have[one] - shared)" in put
	assert '"User": (companion(app),)' in _body("_carriers")
	assert "set(used) | {companion(app)}" in _body("_holds")


def test_a_right_brings_what_it_needs_and_a_record_what_it_names():
	assert '"cancel": {"read", "write", "submit"}' in SOURCE
	assert "_close(" in _body("_wanted")
	save = _body("save_level")
	assert "_picks(doctype)" in save and '| {"select"}' in save
	picks = _body("_picks")
	assert "df.reqd" in picks and "not df.hidden" in picks and "get_table_fields()" in picks


def test_a_plain_user_holds_the_companion_and_nobody_else_does():
	assert '"User": set(used) | set(alone)' in SETTINGS
	assert "return set(used) | {level}" in SETTINGS
	assert "set(alone)" in SETTINGS.split("def _set_access(", 1)[1].split("\ndef ", 1)[0]


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
