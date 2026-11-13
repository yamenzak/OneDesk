"""Point 1: the key screens are opened in a browser on the demo, as their
people (tests/browser). Every desk page of ours is among them, and each is
opened as somebody who works in the demo. These read the files."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
SCREENS = (ROOT / "tests" / "browser" / "screens.mjs").read_text()


def _pages() -> set[str]:
	"""A workspace's pages. OneAdmin's exist only on the admin site, which has no demo."""
	return {json.loads(path.read_text())["name"] for path in APP.glob("*/page/*/*.json") if path.parent.name != "__pycache__" and "one_admin" not in path.parts}


def unopened(pages: set[str], screens: str) -> list[str]:
	"""The pages screens.mjs never opens. Pure."""
	return sorted(pages - set(re.findall(r'page: "([^"]+)"', screens)))


def test_every_page_of_ours_is_opened_in_the_browser():
	missing = unopened(_pages(), SCREENS)
	assert not missing, f"open these pages in tests/browser/screens.mjs: {missing}"


def strangers(screens: str, people: str) -> set[str]:
	"""Who screens.mjs opens a screen as that the demo's people.py does not make. Pure."""
	who = set(re.findall(r'who: "([^"]+)"', screens))
	return {one for one in who if f'"{one}"' not in people and one.split("@")[0] not in people}


def test_every_screen_is_opened_as_a_demo_person():
	people = (APP / "one_demo" / "people.py").read_text()
	assert re.findall(r'who: "([^"]+)"', SCREENS), "no screens"
	found = strangers(SCREENS, people)
	assert not found, found


def test_the_browser_rules_catch_their_examples():
	screens = '{ page: "one-home", who: "ana@demo.one" },\n{ page: "timers", who: "nobody@else.one" },'
	assert unopened({"one-home", "one-stock"}, screens) == ["one-stock"]
	assert strangers(screens, 'PEOPLE = ("ana", "sam")') == {"nobody@else.one"}
