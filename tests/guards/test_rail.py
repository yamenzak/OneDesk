"""The rail: every app of ours has a tile on it, every page opens in its own
app's rail, and every row at its top carries an icon frappe draws.

frappe's rail lists exactly what an app's Dock record names, so a sidebar the
record leaves out still opens by its address but has no tile, and nothing on
the rail is lit while it is open. OneMail was left out this way.

frappe keeps a route in the rail on screen when both rails are one app's, and
every One app is a rail of onedesk, so desk.js makes a page open in a rail
only when that rail lists it, and in its own otherwise (OVERRIDES.md, A page
of One's opens in its own app's rail). That holds only while each page is
listed in its own app's Sidebar: one listed nowhere, or only in another
app's, has no rail of its own to open in. A page opened from somewhere other
than a rail is named in UNLISTED with where it is opened from.

A link without an icon shows the bare list mark, as OneCRM's Lead and
Opportunity did, and a group drawn flat (indent 0) shows none, as One's own
groups did, unless it is a heading over rows that each draw their own (One's
Centers).
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

from tests.bench import icons

DOCK = tree.APP / "dock" / "onedesk" / "onedesk.json"

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


def _sidebar_files() -> list[tuple[Path, dict]]:
	found = [(path, json.loads(path.read_text(encoding="utf-8"))) for path in sorted(tree.APP.glob("**/sidebar/*/*.json"))]
	return [(path, said) for path, said in found if said.get("doctype") == "Sidebar"]


def sidebars() -> dict[str, tuple[str, set[str]]]:
	"""Every Sidebar of ours, by name, with its module and the pages it lists."""
	out = {}
	for _path, said in _sidebar_files():
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


def unmarked(name: str, items: list[dict], drawn: frozenset[str]) -> list[str]:
	"""What is wrong with the top rows of one rail. Pure."""
	wrong = []
	for at, row in enumerate(items):
		if row.get("child") or row.get("type") not in ("Link", "Section Break"):
			continue
		if row["type"] == "Section Break" and not row.get("indent"):
			under = []
			for one in items[at + 1 :]:
				if not one.get("child"):
					break
				under.append(one)
			if not under or not all(one.get("icon") for one in under):
				wrong.append(f"{name}: the group {row['label']} is drawn flat, without its icon")
		icon = row.get("icon")
		if not icon:
			wrong.append(f"{name}: {row['label']} has no icon")
		elif icon not in drawn:
			wrong.append(f"{name}: {row['label']}'s icon {icon!r} is not in frappe's set")
	return wrong


def untiled(dock: dict, ours: set[str]) -> list[str]:
	"""The sidebars of ours the Dock record names no tile for. Pure."""
	named = {row["link_to"] for row in dock["items"] if row["link_type"] == "Sidebar"}
	return sorted(ours - named)


def test_every_sidebar_of_ours_has_a_tile_on_the_rail():
	found = untiled(json.loads(DOCK.read_text()), {json.loads(path.read_text())["name"] for path in tree.APP.glob("*/sidebar/*/*.json")})
	assert not found, f"sidebars with no tile on the rail: {found}"


def test_every_page_opens_in_its_own_apps_rail():
	found = problems(pages(), sidebars(), UNLISTED)
	assert not found, "\n".join(found)


def test_a_page_listed_only_in_another_apps_rail_is_caught():
	example = problems({"onemail": "One Mail"}, {"One": ("One", {"onemail"})}, {})
	assert example == ["onemail (One Mail) is listed in One, not in a rail of One Mail"]


def asks_to_be_listed(desk: str) -> bool:
	"""Whether desk.js still opens a page in a rail only when it lists it. Pure."""
	return "shell_can_show(shell, route, opts = {})" in desk and "listed_only: true" in desk


def test_the_desk_still_asks_a_page_to_be_listed():
	assert asks_to_be_listed((tree.APP / "public" / "js" / "desk.js").read_text(encoding="utf-8"))


def test_the_tile_and_listing_rules_catch_their_examples():
	dock = {"items": [{"link_type": "Sidebar", "link_to": "One"}, {"link_type": "Page", "link_to": "OneMail"}]}
	assert untiled(dock, {"One", "OneMail"}) == ["OneMail"] and untiled(dock, {"One"}) == []
	assert asks_to_be_listed("shell_can_show(shell, route, opts = {}) { listed_only: true }")
	assert not asks_to_be_listed("shell_can_show(shell, route) {}")


def test_a_top_row_has_an_icon_frappe_draws():
	drawn = icons()
	if drawn is None:
		pytest.skip("frappe is not checked out beside this app")
	wrong = [one for path, said in _sidebar_files() for one in unmarked(path.name, said["items"], drawn)]
	assert not wrong, "\n".join(wrong)


def test_the_icon_rule_catches_its_example():
	rows = [
		{"type": "Link", "label": "Lead"},
		{"type": "Link", "label": "Deal", "icon": "nowhere"},
		{"type": "Section Break", "label": "Centers"},
		{"type": "Link", "label": "Access", "icon": "lock", "child": 1},
	]
	assert unmarked("crm.json", rows, frozenset({"lock"})) == [
		"crm.json: Lead has no icon",
		"crm.json: Deal's icon 'nowhere' is not in frappe's set",
		"crm.json: Centers has no icon",
	]
