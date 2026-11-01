"""How a record type is drawn is declared once, in ready.MODULES under
"interface", and the renderer reads nothing else (frappe.boot.one_interface).

These fail when a declaration names an icon frappe does not draw, a tab or a
field its record type does not have, a head card or a track no head row or
chart of the declaring module's heads.py gives, or more than four cards.
"""

import importlib.util
import json
import re
from functools import cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APPS = ROOT.parent
SPRITE = APPS / "frappe" / "frappe" / "public" / "icons" / "lucide" / "icons.svg"


def _ready():
	spec = importlib.util.spec_from_file_location("ready", ROOT / "onedesk" / "one" / "ready.py")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


READY = _ready()
DECLARED = READY.interface()


@cache
def _fields(doctype: str) -> dict | None:
	"""A record type's fields by name, as its own JSON and One's custom
	fields declare them. None when the type's JSON is not on this bench."""
	scrub = doctype.lower().replace(" ", "_")
	found = next(APPS.glob(f"*/*/*/doctype/{scrub}/{scrub}.json"), None)
	if not found:
		return None
	fields = {one["fieldname"]: one for one in json.loads(found.read_text())["fields"]}
	for path in (ROOT / "onedesk").glob("**/custom_field.json"):
		fields.update({one["fieldname"]: one for one in json.loads(path.read_text()) if one.get("dt") == doctype})
	return fields


@cache
def _fieldnames(doctype: str) -> set[str] | None:
	"""A record type's fields as its own JSON and One's custom fields name
	them. None when the type's JSON is not on this bench."""
	scrub = doctype.lower().replace(" ", "_")
	found = next(APPS.glob(f"*/*/*/doctype/{scrub}/{scrub}.json"), None)
	if not found:
		return None
	names = {one["fieldname"] for one in json.loads(found.read_text())["fields"]}
	for path in (ROOT / "onedesk").glob("**/custom_field.json"):
		names |= {one["fieldname"] for one in json.loads(path.read_text()) if one.get("dt") == doctype}
	return names | {"__details"}


def test_every_icon_is_one_frappe_draws():
	if not SPRITE.exists():
		pytest.skip("frappe's icons are not on this bench")
	drawn = set(re.findall(r'<symbol[^>]*id="(?:icon-)?([\w-]+)"', SPRITE.read_text()))
	wrong = [
		f"{doctype} {kind} {name}: {icon}"
		for doctype, said in DECLARED.items()
		for kind in ("tabs", "fields")
		for name, icon in said[kind].items()
		if icon not in drawn
	] + [f"{doctype} link {one['label']}: {one['icon']}" for doctype, said in DECLARED.items() for one in said["links"] if one["icon"] not in drawn]
	assert not wrong, "Icons frappe does not draw:\n" + "\n".join(wrong)


def test_every_tab_and_field_is_its_record_types_own():
	wrong = []
	for doctype, said in DECLARED.items():
		names = _fieldnames(doctype)
		if names is None:
			continue
		wrong += [f"{doctype}: {name}" for kind in ("tabs", "fields") for name in said[kind] if name not in names]
	assert not wrong, "Named but not on the record type:\n" + "\n".join(wrong)


def test_every_card_and_track_is_a_row_its_module_declares():
	wrong = []
	for doctype, said in DECLARED.items():
		module = READY.MODULES[said["module"]]
		heads = (ROOT / "onedesk" / module["folder"] / "heads.py").read_text(encoding="utf-8")
		keys = [card["key"] for card in said["cards"]] + ([said["track"]] if said["track"] else [])
		for key in keys:
			given = re.search(rf'"(?:measure|field|chart)": "{re.escape(key)}"|_lt\("{re.escape(key)}"\)', heads)
			if not given:
				wrong.append(f"{doctype}: {key}")
	assert not wrong, "Cards and tracks no head row gives:\n" + "\n".join(wrong)


def test_a_head_has_at_most_four_cards():
	assert all(len(said["cards"]) <= 4 for said in DECLARED.values())


def test_a_strip_counts_a_field_its_record_type_has_and_names_only_its_values():
	wrong = []
	for doctype, said in DECLARED.items():
		fields = _fields(doctype)
		if fields is None:
			continue
		states = said["states"]
		field = fields.get(states["field"])
		if not field:
			wrong.append(f"{doctype}: no field {states['field']}")
			continue
		if field.get("fieldtype") == "Select":
			values = set((field.get("options") or "").split("\n"))
			wrong += [f"{doctype}: {states['field']} has no {one}" for one in states["order"] + states["hide"] if one not in values]
	assert not wrong, "Strips that name what is not there:\n" + "\n".join(wrong)


def test_a_link_opens_a_record_type_that_exists_and_carries_real_fields():
	wrong = []
	for doctype, said in DECLARED.items():
		ours = _fieldnames(doctype)
		for one in said["links"]:
			target = one["new"] or one["list"]
			theirs = _fieldnames(target)
			if theirs is None:
				wrong.append(f"{doctype}: {one['label']} opens {target}, which is not on this bench")
				continue
			wrong += [f"{doctype}: {target} has no {field}" for field in one["with"] if field not in theirs]
			if ours is not None:
				named = list(one["with"].values()) + [rule[0] for rule in one["when"]]
				wrong += [f"{doctype}: {one['label']} reads {field}, which it does not have" for field in named if field not in ours | {"name"}]
				wrong += [f"{doctype}: {one['label']} says {rule[1]}" for rule in one["when"] if rule[1] not in ("=", "!=", "in")]
	assert not wrong, "Links that go nowhere:\n" + "\n".join(wrong)
