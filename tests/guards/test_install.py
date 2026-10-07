"""Point 1: a new workspace installs. What a fresh site tripped on when the
demo was first built on one, kept from coming back."""

import ast
import glob
import json
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
APPS = Path("/home/frappe/bench1/apps")


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


def test_no_shipped_customization_hides_a_mandatory_field():
	"""frappe refuses to sync a field that is hidden and mandatory with no
	default, and a new site's install stops there."""
	if not APPS.exists():
		pytest.skip("the other apps' sources are not beside this checkout")
	doctypes = _doctypes()
	wrong = []
	for path in APP.glob("**/custom/*.json"):
		said = json.loads(path.read_text())
		setters = said.get("property_setters", [])
		ours = {(one["dt"], one["fieldname"]): one for one in said.get("custom_fields", [])}
		eased = {(p["doc_type"], p.get("field_name")) for p in setters if p["property"] in ("reqd", "default") and str(p["value"]) not in ("1", "")}
		for p in setters:
			if p["property"] != "hidden" or str(p["value"]) != "1" or not p.get("field_name"):
				continue
			key = (p["doc_type"], p["field_name"])
			field = ours.get(key) or next((f for f in doctypes.get(key[0], {}).get("fields", []) if f["fieldname"] == key[1]), None)
			if field and field.get("reqd") and not field.get("default") and key not in eased:
				wrong.append(f"{path.relative_to(ROOT)}: {key[0]}.{key[1]}")
	assert not wrong, wrong


def test_install_hooks_run_after_the_custom_fields_exist():
	"""frappe's after_install runs before an app's custom fields are synced,
	and much of what One sets up reads them; after_sync runs once they are."""
	tree = ast.parse((APP / "hooks.py").read_text())
	names = {node.targets[0].id for node in tree.body if isinstance(node, ast.Assign) and hasattr(node.targets[0], "id")}
	assert "after_install" not in names
	assert "after_sync" in names


def test_a_new_site_is_settled_as_a_migrated_one_is():
	"""Everything after_migrate sets up runs when the app is installed too:
	a new site is never migrated before its first person signs in."""
	tree = ast.parse((APP / "hooks.py").read_text())
	hooks = {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in ("after_sync", "after_migrate")}
	assert set(hooks["after_migrate"]) <= set(hooks["after_sync"]), sorted(set(hooks["after_migrate"]) - set(hooks["after_sync"]))


def test_a_new_workspace_is_settled_once_its_company_exists():
	"""The wizard makes the company after the install has run, and much of
	what the install sets up is about the company."""
	source = (APP / "one" / "setup_wizard.py").read_text()
	stages = source[source.index("def get_setup_stages") : source.index("def settle")]
	assert '"fn": settle' in stages
	assert 'frappe.get_hooks("after_sync", app_name="onedesk")' in source


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
	# What hrms adds to erpnext's doctypes as custom fields when it installs.
	hrms = set(re.findall(r'"fieldname": "(\w+)"', (APPS / "hrms" / "hrms" / "setup.py").read_text()))
	standard = {name: fields | hrms for name, fields in standard.items()}
	lost = []
	for doctype, fields in ours.items():
		if doctype not in standard:
			continue
		known = standard[doctype] | set(fields)
		lost += [f"{path.name}: {doctype}.{name} after {after}" for name, (path, after) in fields.items() if after and after not in known]
	for path, one in setters:
		doctype, field = one.get("doc_type"), one.get("field_name")
		if one.get("doctype_or_field") != "DocField" or doctype not in standard:
			continue
		if field not in standard[doctype] | set(ours.get(doctype, {})):
			lost.append(f"{path.name}: {doctype}.{field} {one.get('property')}")
	assert not lost, lost
