"""Every page of ours opens in its own app's rail.

frappe keeps a route in the rail on screen when both rails are one app's, and
every One app is a rail of onedesk, so desk.js makes a page open in a rail
only when that rail lists it, and in its own otherwise (OVERRIDES.md, A page
of One's opens in its own app's rail). That holds only while each page is
listed in its own app's Sidebar: one listed nowhere, or only in another
app's, has no rail of its own to open in. A page opened from somewhere other
than a rail is named in UNLISTED with where it is opened from.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

UNLISTED = {
	"document": "a document's editor, opened from its file",
	"presentation": "a presentation's editor, opened from its file",
	"workbook": "a workbook's editor, opened from its file",
	"legal": "the agreements, opened from the links in the dialog that asks to agree to them",
	"timers": "the running timers, opened from Timers on a phone, where the bar's popover has no room",
}


def pages() -> dict[str, str]:
	"""Every desk page of ours, by name, with its module."""
	out = {}
	for path in tree.APP.glob("*/page/*/*.json"):
		said = json.loads(path.read_text(encoding="utf-8"))
		if said.get("doctype") == "Page":
			out[said["name"]] = said.get("module")
	return out


def sidebars() -> dict[str, tuple[str, set[str]]]:
	"""Every Sidebar of ours, by name, with its module and the pages it lists."""
	out = {}
	for path in tree.APP.glob("**/sidebar/*/*.json"):
		said = json.loads(path.read_text(encoding="utf-8"))
		if said.get("doctype") != "Sidebar":
			continue
		listed = {item.get("link_to") for item in said.get("items") or [] if item.get("link_type") == "Page"}
		out[said["name"]] = (said.get("module"), listed)
	return out


def problems(pages: dict, sidebars: dict, unlisted: dict) -> list[str]:
	"""A page with no rail of its own, or an UNLISTED entry that is not true."""
	out = []
	for name, module in sorted(pages.items()):
		at = [rail for rail, (_module, listed) in sidebars.items() if name in listed]
		own = [rail for rail in at if sidebars[rail][0] == module]
		if name in unlisted:
			if at:
				out.append(f"{name} is in UNLISTED but {', '.join(at)} lists it")
		elif not own:
			out.append(f"{name} ({module}) is listed in {', '.join(at) or 'no rail'}, not in a rail of {module}")
	out += [f"{name} is in UNLISTED but is not a page of ours" for name in unlisted if name not in pages]
	return out


def test_every_page_opens_in_its_own_apps_rail():
	found = problems(pages(), sidebars(), UNLISTED)
	assert not found, "\n".join(found)


def test_a_page_listed_only_in_another_apps_rail_is_caught():
	example = problems({"onemail": "One Mail"}, {"One": ("One", {"onemail"})}, {})
	assert example == ["onemail (One Mail) is listed in One, not in a rail of One Mail"]


def test_the_desk_still_asks_a_page_to_be_listed():
	desk = (tree.APP / "public" / "js" / "desk.js").read_text(encoding="utf-8")
	assert "shell_can_show(shell, route, opts = {})" in desk and "listed_only: true" in desk
