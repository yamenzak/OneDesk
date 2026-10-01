"""Announcements (one/announcements.py): frappe's Note, posted by an
administrator, told to everybody, shown when they open One, with who has
read it. These read the code that says so."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "announcements.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()


def _body(name: str) -> str:
	return SOURCE.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_only_an_administrator_announces():
	assert 'LEVELS = {1: ("read", "write"), 2: ("read",)}' in SOURCE
	assert "roles.ADMINISTRATOR, level" in _body("settle")
	check = _body("validate")
	assert "doc.public or doc.notify_on_login" in check and "roles.administers()" in check
	assert "doc.public = 1" in _body("before_validate")
	note = HOOKS.split('"Note": {', 1)[1].split("},", 1)[0]
	for event in ("before_validate", "validate", "on_update"):
		assert f'"{event}": "onedesk.one.announcements.{event}"' in note, event


def test_everybody_is_told_once():
	told = _body("on_update")
	assert 'doc.has_value_changed("public") or doc.flags.in_insert' in told
	assert '"Announcement"' in told and "NOT_PEOPLE" in told
	assert '_lt("Announcement")' in (tree.APP / "one" / "notifications.py").read_text()


def test_it_pops_up_for_the_person_not_for_guest():
	shown = _body("boot")
	assert 'frappe.session.user == "Guest"' in shown and "is None" in shown and "_get_unseen_notes()" in shown
	assert '"onedesk.one.announcements.boot"' in HOOKS.split("extend_bootinfo = [", 1)[1].split("]", 1)[0]


def test_the_sidebar_reaches_it():
	sidebar = json.loads((tree.APP / "one" / "sidebar" / "one" / "one.json").read_text())
	links = {one["link_to"]: one["label"] for one in sidebar["items"] if one.get("link_type") == "DocType"}
	assert links["Note"] == "Announcements"
