"""OneInventory, OneProject, OneTask, OneBook and OneCRM call a thing what ERPNext
calls it, the name Ctrl+K finds (docs/WORDING.md, On a Screen): a rail row
says the doctype's, report's or page's own name, or what ERPNext's own sidebar
calls that same link, and a field keeps ERPNext's label."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
APPS = Path("/home/frappe/bench1/apps")

RAILS = {
	"one_inventory": "oneinventory",
	"one_project": "oneproject",
	"one_task": "onetask",
	"one_book": "onebook",
	"one_crm": "onecrm",
}

#: The pages a module opens on, titled for the module.
HOMES = ("inventory", "my-tasks", "books")

#: The custom files whose labels are these three modules' to keep: their own,
#: and Timesheet's, which sits on OneProject's rail and is OneHR's file.
CUSTOM = [APP / module / "custom" for module in RAILS] + [APP / "one_hr" / "custom" / "timesheet.json"]


def _pages() -> dict[str, str]:
	"""Every page of ours by its route, with its title."""
	found = {}
	for path in APP.glob("*/page/*/*.json"):
		said = json.loads(path.read_text(encoding="utf-8"))
		if said.get("doctype") == "Page":
			found[said["name"]] = said.get("title") or said["name"]
	return found


def _theirs() -> set[tuple]:
	"""What ERPNext's own sidebars call a link: (label, kind, target, filters)."""
	found = set()
	for path in (APPS / "erpnext" / "erpnext" / "workspace_sidebar").glob("*.json"):
		for row in json.loads(path.read_text(encoding="utf-8")).get("items", []):
			if row.get("type") == "Link" and row.get("link_to"):
				found.add((row["label"], row.get("link_type"), row["link_to"]))
	return found


def test_a_rail_row_says_what_it_opens():
	pages = _pages()
	theirs = _theirs()
	wrong = []
	for module, rail in RAILS.items():
		items = json.loads((APP / module / "sidebar" / rail / f"{rail}.json").read_text(encoding="utf-8"))["items"]
		for row in items:
			if row.get("type") != "Link" or not row.get("link_to"):
				continue
			kind, target = row.get("link_type"), row["link_to"]
			wanted = target if kind in ("DocType", "Report") else pages.get(target) if kind == "Page" else None
			# A module's own home page is titled for the module and its row says
			# what it opens on: Home, My Tasks.
			if (row["label"], kind, target) in theirs:
				continue
			if wanted is not None and row["label"] != wanted and not (kind == "Page" and target in HOMES):
				wrong.append(f"{rail}: {row['label']!r} opens {kind} {target!r}, called {wanted!r}")
	assert not wrong, "\n".join(wrong)


def _upstream_labels() -> dict[tuple[str, str], str | None]:
	labels = {}
	for app in ("frappe", "erpnext", "hrms"):
		for path in (APPS / app).glob(f"{app}/*/doctype/*/*.json"):
			try:
				said = json.loads(path.read_text(encoding="utf-8"))
			except ValueError:
				continue
			if not isinstance(said, dict) or said.get("doctype") != "DocType":
				continue
			for field in said.get("fields", []):
				labels[(said["name"], field["fieldname"])] = field.get("label")
	return labels


@pytest.fixture(scope="module")
def upstream():
	if not (APPS / "erpnext").exists():
		pytest.skip("erpnext is not checked out beside this app")
	return _upstream_labels()


def test_a_field_keeps_erpnexts_label(upstream):
	"""A capital fixed or a section heading left blank is allowed; other words
	are a rename."""
	wrong = []
	for place in CUSTOM:
		for path in [place] if place.is_file() else sorted(place.glob("*.json")):
			for setter in json.loads(path.read_text(encoding="utf-8")).get("property_setters", []):
				if setter["property"] != "label" or setter.get("doctype_or_field") != "DocField":
					continue
				key = (setter["doc_type"], setter["field_name"])
				if key not in upstream or not setter["value"]:
					continue
				theirs = upstream[key] or ""
				if setter["value"].lower() != theirs.lower():
					wrong.append(f"{path.name}: {key[0]}.{key[1]} is {setter['value']!r}, ERPNext says {theirs!r}")
	assert not wrong, "\n".join(wrong)
