"""Point 1: a new workspace installs. What a fresh site tripped on when the
demo was first built on one, kept from coming back."""

import ast
import glob
import json
import os
import re
from pathlib import Path

import pytest
from tests.bench import APPS
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import tree  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"


def _doctypes() -> dict:
	found = {}
	for app in ("frappe", "erpnext", "hrms"):
		for path in glob.glob(str(APPS / app / app / "**/doctype/*/*.json"), recursive=True):
			if os.path.basename(os.path.dirname(path)) != os.path.basename(path)[:-5]:
				continue
			try:
				doc = json.loads(Path(path).read_text())
			except ValueError:
				continue
			if doc.get("doctype") == "DocType":
				found[doc["name"]] = doc
	return found


def hidden_mandatory(said: dict, doctypes: dict) -> list[str]:
	"""The fields one custom file hides that are mandatory with no default
	and not eased by the same file. Pure."""
	wrong = []
	setters = said.get("property_setters", [])
	ours = {(one["dt"], one["fieldname"]): one for one in said.get("custom_fields", [])}
	eased = {(p["doc_type"], p.get("field_name")) for p in setters if p["property"] in ("reqd", "default") and str(p["value"]) not in ("1", "")}
	for p in setters:
		if p["property"] != "hidden" or str(p["value"]) != "1" or not p.get("field_name"):
			continue
		key = (p["doc_type"], p["field_name"])
		field = ours.get(key) or next((f for f in doctypes.get(key[0], {}).get("fields", []) if f["fieldname"] == key[1]), None)
		if field and field.get("reqd") and not field.get("default") and key not in eased:
			wrong.append(f"{key[0]}.{key[1]}")
	return wrong


def test_no_shipped_customization_hides_a_mandatory_field():
	"""frappe refuses to sync a field that is hidden and mandatory with no
	default, and a new site's install stops there."""
	if not APPS.exists():
		pytest.skip("the other apps' sources are not beside this checkout")
	doctypes = _doctypes()
	wrong = []
	for path in APP.glob("**/custom/*.json"):
		wrong += [f"{path.relative_to(ROOT)}: {one}" for one in hidden_mandatory(json.loads(path.read_text()), doctypes)]
	assert not wrong, wrong


def _assigned(source: str) -> dict:
	"""The names a hooks.py assigns at its top, each with its value's node."""
	return {node.targets[0].id: node.value for node in ast.parse(source).body if isinstance(node, ast.Assign) and hasattr(node.targets[0], "id")}


def install_too_early(source: str) -> bool:
	"""Whether a hooks.py sets up in after_install, or not in after_sync. Pure."""
	names = set(_assigned(source))
	return "after_install" in names or "after_sync" not in names


def test_install_hooks_run_after_the_custom_fields_exist():
	"""frappe's after_install runs before an app's custom fields are synced,
	and much of what One sets up reads them; after_sync runs once they are."""
	assert not install_too_early(tree.hooks())


def only_migrated(source: str) -> list:
	"""What a hooks.py's after_migrate runs that its after_sync does not. Pure."""
	said = _assigned(source)
	return sorted(set(ast.literal_eval(said["after_migrate"])) - set(ast.literal_eval(said["after_sync"])))


def test_a_new_site_is_settled_as_a_migrated_one_is():
	"""Everything after_migrate sets up runs when the app is installed too:
	a new site is never migrated before its first person signs in."""
	left = only_migrated(tree.hooks())
	assert not left, left


def settled_with_the_company(source: str) -> bool:
	"""Whether a setup wizard's stages run settle, and settle runs after_sync's hooks. Pure."""
	stages = source[source.index("def get_setup_stages") : source.index("def settle")]
	return '"fn": settle' in stages and 'frappe.get_hooks("after_sync", app_name="onedesk")' in source


def test_a_new_workspace_is_settled_once_its_company_exists():
	"""The wizard makes the company after the install has run, and much of
	what the install sets up is about the company."""
	assert settled_with_the_company((APP / "one" / "setup_wizard.py").read_text())


def test_the_install_rules_catch_their_examples():
	doctype = {"Lead": {"fields": [{"fieldname": "source", "reqd": 1}]}}
	hiding = {"property_setters": [{"doc_type": "Lead", "field_name": "source", "property": "hidden", "value": "1"}]}
	assert hidden_mandatory(hiding, doctype) == ["Lead.source"]
	eased = {"property_setters": hiding["property_setters"] + [{"doc_type": "Lead", "field_name": "source", "property": "reqd", "value": "0"}]}
	assert hidden_mandatory(eased, doctype) == []
	assert install_too_early("after_install = ['x']\nafter_sync = ['y']\n")
	assert install_too_early("after_migrate = ['y']\n")
	assert not install_too_early("after_sync = ['y']\n")
	assert only_migrated("after_sync = ['a']\nafter_migrate = ['a', 'b']\n") == ["b"]
	assert only_migrated("after_sync = ['a', 'b']\nafter_migrate = ['a']\n") == []
	wizard = 'def get_setup_stages():\n\treturn [{"fn": settle}]\n\ndef settle():\n\tfrappe.get_hooks("after_sync", app_name="onedesk")\n'
	assert settled_with_the_company(wizard)
	assert not settled_with_the_company(wizard.replace('"fn": settle', '"fn": other'))
	standard = {"Lead": {"source", "status"}}
	assert lost_fields({"Lead": {"x": ("lead.json", "gone")}}, [], standard) == ["lead.json: Lead.x after gone"]
	setter = ("lead.json", {"doctype_or_field": "DocField", "doc_type": "Lead", "field_name": "gone", "property": "hidden"})
	assert lost_fields({}, [setter], standard) == ["lead.json: Lead.gone hidden"]
	assert lost_fields({"Lead": {"x": ("lead.json", "status")}}, [], standard) == []
	theirs = {"Task": "hrms.overrides.task.HRTask"}
	assert unextended({"Task": "onedesk.x.Task"}, theirs, lambda _path: "class Task(Document):") == ["Task"]
	assert unextended({"Task": "onedesk.x.Task"}, theirs, lambda _path: "from hrms.overrides.task import HRTask\nclass Task(HRTask):") == []


def test_every_shipped_field_lands_where_it_was_put():
	"""A custom field is placed after a field, and a property setter changes
	one. Upstream renames and drops fields, and frappe then puts ours at the
	end of the form, or sets a property on nothing, without a word. Read on
	every upstream checkpoint (docs/UPSTREAM.md)."""
	doctypes = _doctypes()
	if not doctypes:
		pytest.skip("no bench beside the app")
	ours, setters = {}, []
	for path in APP.glob("*/custom/*.json"):
		said = json.loads(path.read_text())
		for field in said.get("custom_fields") or []:
			ours.setdefault(field["dt"], {})[field["fieldname"]] = (path, field.get("insert_after"))
		setters += [(path, one) for one in said.get("property_setters") or []]
	standard = {name: {f.get("fieldname") for f in doc.get("fields", [])} for name, doc in doctypes.items()}
	hrms = set(re.findall(r'"fieldname": "(\w+)"', (APPS / "hrms" / "hrms" / "setup.py").read_text()))
	standard = {name: fields | hrms for name, fields in standard.items()}
	lost = lost_fields(ours, setters, standard)
	assert not lost, lost


def lost_fields(ours: dict, setters: list, standard: dict) -> list[str]:
	"""Our fields placed after a field the doctype lacks, and setters on a
	field it lacks. Pure."""
	lost = []
	for doctype, fields in ours.items():
		if doctype not in standard:
			continue
		known = standard[doctype] | set(fields)
		lost += [f"{Path(path).name}: {doctype}.{name} after {after}" for name, (path, after) in fields.items() if after and after not in known]
	for path, one in setters:
		doctype, field = one.get("doc_type"), one.get("field_name")
		if one.get("doctype_or_field") != "DocField" or doctype not in standard:
			continue
		if field not in standard[doctype] | set(ours.get(doctype, {})):
			lost.append(f"{Path(path).name}: {doctype}.{field} {one.get('property')}")
	return lost


def _overrides(hooks: str) -> dict:
	"""A hooks.py's override_doctype_class, read without importing it."""
	tree = ast.parse(hooks)
	for node in tree.body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "override_doctype_class":
			return ast.literal_eval(node.value)
	return {}


def test_an_overridden_controller_builds_on_the_apps_before_it():
	"""frappe keeps only the last app's class for a doctype, so a class One
	puts on a doctype erpnext or hrms already overrides must extend theirs,
	or theirs stops running."""
	ours = _overrides(tree.hooks())
	for app in ("erpnext", "hrms"):
		theirs = _overrides((APPS / app / app / "hooks.py").read_text())
		wrong = unextended(ours, theirs, lambda dotted: (APP.parent / Path(*dotted.split(".")[:-1]).with_suffix(".py")).read_text())
		assert not wrong, [f"{doctype}: {ours[doctype]} must extend {app}'s {theirs[doctype]}" for doctype in wrong]


def unextended(ours: dict, theirs: dict, source_of) -> list[str]:
	"""The doctypes both override where our class does not extend theirs;
	`source_of` reads our class's module from its dotted path. Pure."""
	wrong = []
	for doctype in sorted(set(ours) & set(theirs)):
		module, cls = theirs[doctype].rsplit(".", 1)
		source = source_of(ours[doctype])
		if not (f"from {module} import" in source and f"({cls})" in source):
			wrong.append(doctype)
	return wrong
