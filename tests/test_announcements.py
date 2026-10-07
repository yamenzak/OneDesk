"""Announcements (one/announcements.py): frappe's Note, posted by an
administrator, told to everybody, shown when they open One, with who has
read it. The demo checks each; these read the wiring."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "announcements.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()


def _body(name: str, source: str = SOURCE) -> str:
	return source.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_only_an_administrator_announces():
	access = (tree.APP / "one" / "access.py").read_text()
	assert 'NOTE_LEVELS = {1: ("read", "write"), 2: ("read",)}' in access
	assert "roles.ADMINISTRATOR, level" in _body("_note_levels", access)
	note = HOOKS.split('"Note": {', 1)[1].split("},", 1)[0]
	for event in ("before_validate", "validate", "on_update"):
		assert f'"{event}": "onedesk.one.announcements.{event}"' in note, event


def test_everybody_is_told_once():
	assert "Announcement" in tree.notifications()


def test_it_pops_up_for_the_person_not_for_guest():
	assert '"onedesk.one.announcements.boot"' in HOOKS.split("extend_bootinfo = [", 1)[1].split("]", 1)[0]


def test_the_sidebar_reaches_it():
	sidebar = json.loads((tree.APP / "one" / "sidebar" / "one" / "one.json").read_text())
	links = {one["link_to"]: one["label"] for one in sidebar["items"] if one.get("link_type") == "DocType"}
	assert links["Note"] == "Announcements"
