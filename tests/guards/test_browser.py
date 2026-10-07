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
	return {json.loads(path.read_text())["name"] for path in APP.glob("*/page/*/*.json") if path.parent.name != "__pycache__"}


def test_every_page_of_ours_is_opened_in_the_browser():
	opened = set(re.findall(r'page: "([^"]+)"', SCREENS))
	missing = _pages() - opened
	assert not missing, f"open these pages in tests/browser/screens.mjs: {sorted(missing)}"


def test_every_screen_is_opened_as_a_demo_person():
	people = (APP / "one_demo" / "people.py").read_text()
	who = set(re.findall(r'who: "([^"]+)"', SCREENS))
	assert who, "no screens"
	strangers = {one for one in who if f'"{one}"' not in people and one.split("@")[0] not in people}
	assert not strangers, strangers
