"""Masters, the short lists every app's records pick from (one/masters.py):
each kind is frappe's own list and form, and the kinds are a tree in the nav
pane (public/js/masters.js); and the shared Address Book in One's rail."""

import json
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "masters.py").read_text()
PAGE = tree.APP / "one" / "page" / "masters"
HOOKS = (tree.APP / "hooks.py").read_text()
TREE = (tree.APP / "public" / "js" / "masters.js").read_text()


def _regex():
	"""The tag patterns, read out of masters.py without frappe."""
	import re

	found = {}
	for name in ("TAG", "FIELD", "IF", "END", "WORDS"):
		line = next(one for one in SOURCE.splitlines() if one.startswith(f"{name} = re.compile("))
		found[name] = eval(line.split(" = ", 1)[1], {"re": re})
	return types.SimpleNamespace(**found)


def test_masters_are_granted_to_the_administrator_and_wired():
	kinds = SOURCE.split("KINDS = (", 1)[1].split("\n)\n", 1)[0]
	for doctype in (
		"Salutation",
		"Gender",
		"Print Heading",
		"Address Template",
		"Customer Group",
		"UOM",
		"Department",
	):
		assert f'"{doctype}", _lt(' in kinds, doctype
	assert {line.split('"')[1] for line in kinds.strip().splitlines()} == {
		"Shared",
		"OneCRM",
		"OneBook",
		"OneInventory",
		"OneProject",
		"OneHR",
	}
	for doctype in ("Sales Stage", "Leave Type", "Employee Grade", "Interview Type"):
		assert f'"{doctype}", _lt(' not in kinds, doctype
	assert 'MASTER = ("read", "write", "create", "delete")' in (tree.APP / "one" / "access.py").read_text()
	assert '"onedesk.one.access.settle"' in HOOKS
	assert '"Address Template": {"validate": "onedesk.one.masters.validate_address_template"}' in HOOKS
	settings = (tree.APP / "one" / "settings.py").read_text()
	assert '"lists"' not in settings and "address_templates" not in settings
	js = (tree.APP / "public" / "js" / "settings.js").read_text()
	assert "draw_lists" not in js and "draw_print_lists" not in js


def test_the_page_is_for_administrators_and_app_managers_and_only_opens_a_list():
	page = json.loads((PAGE / "masters.json").read_text())
	assert page["name"] == "masters" and page["module"] == "One"
	roles = {one["role"] for one in page["roles"]}
	assert roles == {
		"Workspace Administrator",
		"Accounts Manager",
		"Projects Manager",
		"Sales Manager",
		"Stock Manager",
		"Purchase Manager",
		"Item Manager",
		"HR Manager",
	}
	groups = SOURCE.split("def _groups(", 1)[1].split("\ndef ", 1)[0]
	assert "roles.administers()" in groups and "frappe.PermissionError" in groups
	js = (PAGE / "masters.js").read_text()
	assert 'frappe.set_route("List", kind)' in js and 'get_url_arg("type")' in js and ".last;" in js
	assert not (PAGE / "masters.css").exists()
	for gone in ("def values(", "def add(", "def rename(", "def used(", "HELD =", "LABEL ="):
		assert gone not in SOURCE, gone
	assert "ignore_permissions" not in SOURCE


def test_the_kinds_are_a_tree_beside_any_of_them():
	assert 'bootinfo["one_masters"] = masters.listed()' in (tree.APP / "one" / "boot.py").read_text()
	assert "onedesk.window.trees.push({ covers: onedesk.masters.covers, draw: onedesk.masters.draw })" in TREE
	assert '"/assets/onedesk/js/masters.js"' in HOOKS
	assert "win.tree({" in TREE and "count:" in TREE and "active:" in TREE
	homes = SOURCE.split("def homes(", 1)[1].split("\ndef ", 1)[0]
	assert '"route": "/desk/masters"' in homes and "f\"/desk/{doctype.lower()" in homes


def test_an_address_template_names_only_fields_of_the_address():
	rx = _regex()
	for fine in ("{{ city }}", "{% if state %}", "{%- endif -%}", "{% else %}"):
		assert rx.FIELD.fullmatch(fine) or rx.IF.fullmatch(fine) or rx.END.fullmatch(fine), fine
	for wrong in (
		"{{ frappe.db.get_value('User', 'x', 'api_key') }}",
		"{% for x in y %}",
		"{{ city|safe }}",
		"{% set a = 1 %}",
	):
		assert not (rx.FIELD.fullmatch(wrong) or rx.IF.fullmatch(wrong) or rx.END.fullmatch(wrong)), wrong
	assert rx.WORDS.fullmatch('{{ _("Phone") }}') and not rx.WORDS.fullmatch("{{ _(frappe.session.user) }}")
	assert not rx.WORDS.fullmatch('{{ _("x") ~ frappe.db.get_value("User", "a", "b") }}')
	check = SOURCE.split("def check_template(", 1)[1].split("\ndef ", 1)[0]
	assert 'rules.readable("Address")' in check and "tag in kept" in check
	assert "if not layer.held():" in SOURCE.split("def validate_address_template(", 1)[1]


def test_contacts_and_addresses_are_the_workspaces_not_onecrms():
	one = json.loads((tree.APP / "one" / "sidebar" / "one" / "one.json").read_text())["items"]
	labels = [item.get("label") for item in one]
	at = labels.index("Address Book")
	assert labels[at + 1 : at + 3] == ["Contacts", "Addresses"]
	assert all(item.get("is_default_module") for item in one[at + 1 : at + 3])
	crm = json.loads((tree.APP / "one_crm" / "sidebar" / "onecrm" / "onecrm.json").read_text())["items"]
	assert not {item.get("link_to") for item in crm} & {"Contact", "Address"}
	at = labels.index("Masters")
	assert at == labels.index("Setup") + 1 and "Lists" not in labels
	assert one[at]["link_type"] == "Page" and one[at]["link_to"] == "masters"


def test_a_master_has_one_home():
	"""What Masters holds is no longer linked from an app's rail or setup."""
	kinds = SOURCE.split("KINDS = (", 1)[1].split("\n)\n", 1)[0]
	held = {line.split('"')[3] for line in kinds.strip().splitlines()}
	places = [*tree.APP.glob("*/sidebar/*/*.json"), *tree.APP.glob("*/workspace/*/*.json")]
	for path in places:
		doc = json.loads(path.read_text())
		rows = doc.get("items") or doc.get("links") or []
		linked = {row.get("link_to") for row in rows if row.get("type") == "Link"}
		assert not linked & held, f"{path.name} links {sorted(linked & held)}, which Masters holds"
	assert '"DocType", "Sales Stage"' in (tree.APP / "one_crm" / "home.py").read_text()


def test_a_value_is_placed_and_renamed_however_it_is_made():
	"""A tree's value goes under its root on every path (the create dialog's
	form, a OneAI card), and a card that changes the field a value is named
	from renames it."""
	for doctype in ("Customer Group", "Territory", "Item Group", "Supplier Group", "Department"):
		assert f'"{doctype}": {{"before_insert": "onedesk.one.masters.place"}}' in HOOKS, doctype
	proposals = (tree.APP / "one_ai" / "proposals.py").read_text()
	assert "held = _renamed(held, changes)" in proposals and "frappe.rename_doc(held.doctype" in proposals


def test_oneai_offers_on_every_kinds_list():
	assert "SUGGESTIONS = {doctype: OFFERED for _group, doctype, _label, _one in KINDS}" in SOURCE
	ai = (tree.APP / "one" / "ai.py").read_text()
	assert "SUGGESTIONS.update(_masters.SUGGESTIONS)" in ai
	assert '"page:masters"' not in ai and 'said.get("page") == "masters"' not in ai


def test_each_group_has_its_apps_mark_and_folds():
	assert '"mark": brand.mark("" if group == "Shared" else group)' in SOURCE
	assert 'frappe.model.user_settings.save("Masters", "closed"' in TREE and "open });" in TREE and "twist: fold" in TREE
