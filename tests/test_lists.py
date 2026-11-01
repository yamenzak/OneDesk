"""Lists, the short lists a module's records pick from (one/lists.py): each
module declares its own in its `lists.py`, its ControlCenter ends with
Lists, each is frappe's own list and form with the module's other lists in
the nav pane beside it (public/js/lists.js); and the Address Book in One's
rail."""

import ast
import json
import re
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "lists.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()
JS = (tree.APP / "public" / "js" / "lists.js").read_text()


def _regex():
	"""The tag patterns, read out of lists.py without frappe."""
	import re

	found = {}
	for name in ("TAG", "FIELD", "IF", "END", "WORDS"):
		line = next(one for one in SOURCE.splitlines() if one.startswith(f"{name} = re.compile("))
		found[name] = eval(line.split(" = ", 1)[1], {"re": re})
	return types.SimpleNamespace(**found)


def _homes() -> dict[str, str]:
	body = SOURCE.split("HOMES = ", 1)[1].split("\n}\n", 1)[0] + "\n}"
	return ast.literal_eval(body)


def _declared() -> dict[str, list[str]]:
	"""Each module's lists, by module, read out of its lists.py."""
	said = {}
	for module, folder in _homes().items():
		source = (tree.APP / folder / "lists.py").read_text()
		body = source.split("LISTS = (", 1)[1].split("\n)", 1)[0]
		said[module] = re.findall(r'\("([^"]+)", _lt\(', body)
	return said


def test_each_module_declares_its_own_lists():
	said = _declared()
	assert said["One"] == ["Salutation", "Gender", "Address Template"]
	assert said["OneStudio"] == ["Print Heading"]
	assert "Department" in said["OneHR"] and "Customer Group" in said["OneCRM"] and "UOM" in said["OneInventory"]
	assert said["OneProject"] == ["Project Type"] and "Tax Category" in said["OneBook"]
	every = [doctype for doctypes in said.values() for doctype in doctypes]
	assert len(every) == len(set(every)) == 29, every
	for doctype in ("Sales Stage", "Leave Type", "Employee Grade", "Interview Type"):
		assert doctype not in every, doctype
	assert not (tree.APP / "one" / "masters.py").exists() and not (tree.APP / "one" / "page" / "masters").exists()
	assert not (tree.APP / "public" / "js" / "masters.js").exists()


def test_lists_are_kept_by_administrators_and_each_apps_managers():
	modules = SOURCE.split("def _modules(", 1)[1].split("\ndef ", 1)[0]
	assert "roles.administers()" in modules and "held & set(managers)" in modules
	kinds = SOURCE.split("def kinds(", 1)[1].split("\ndef ", 1)[0]
	assert "frappe.PermissionError" in kinds and 'frappe.has_permission(doctype, "read")' in SOURCE
	assert 'MASTER = ("read", "write", "create", "delete")' in (tree.APP / "one" / "access.py").read_text()
	assert "from onedesk.one.lists import kinds_of" in (tree.APP / "one" / "access.py").read_text()
	assert '"onedesk.one.access.settle"' in HOOKS
	assert "ignore_permissions" not in SOURCE


def test_every_controlcenter_ends_with_lists():
	settings = (tree.APP / "public" / "js" / "module_settings.js").read_text()
	assert "...onedesk.lists.tab(module), ...onedesk.module_settings.centers(module)" in settings
	assert 'bootinfo["one_lists"] = lists.listed()' in (tree.APP / "one" / "boot.py").read_text()
	assert 'frappe.xcall("onedesk.one.lists.kinds", { module })' in JS and "frappe.router.shell_slug(module)" in JS
	desk = (tree.APP / "public" / "js" / "desk.js").read_text()
	assert "(module && onedesk.lists.center(module))" in desk
	hr = (tree.APP / "public" / "js" / "one_hr" / "hr_control.js").read_text()
	# Everybody opens OneHR's settings; Holidays is the administrators' alone.
	assert "frappe.boot.one_administers ? [{ group: null, items: [holidays] }] : []" in hr


def test_a_modules_lists_are_a_tree_beside_any_of_them():
	assert "onedesk.interface.trees.push({ covers: (doctype) => !!onedesk.lists.module_of(doctype), draw: onedesk.lists.draw })" in JS
	assert '"/assets/onedesk/js/lists.js"' in HOOKS
	assert "win.tree({" in JS and "count:" in JS and "active:" in JS
	homes = SOURCE.split("def homes(", 1)[1].split("\ndef ", 1)[0]
	assert "center=settings&module={module}&at=lists" in homes and "f\"/desk/{doctype.lower()" in homes


def test_each_rail_with_lists_opens_its_controlcenter_on_them():
	for module, folder in _homes().items():
		path = next((tree.APP / folder / "sidebar").glob("*/*.json"))
		rows = json.loads(path.read_text())["items"]
		urls = [row.get("url") for row in rows if row.get("label") == "Lists"]
		# One's rail opens screens only; its Lists are in its settings
		# (docs/UI-NOTES.md, A rail row opens a screen).
		wanted = [] if module == "One" else [f"/desk/one?center=settings&module={module}&at=lists"]
		assert urls == wanted, (module, urls)


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
	assert '"Address Template": {"validate": "onedesk.one.lists.validate_address_template"}' in HOOKS


def test_contacts_and_addresses_are_the_workspaces_not_onecrms():
	one = json.loads((tree.APP / "one" / "sidebar" / "one" / "one.json").read_text())["items"]
	labels = [item.get("label") for item in one]
	at = labels.index("Address Book")
	assert labels[at + 1 : at + 4] == ["Contacts", "Addresses", "Centers"]
	assert all(item.get("is_default_module") for item in one[at + 1 : at + 3])
	assert "Masters" not in labels and "Setup" not in labels
	crm = json.loads((tree.APP / "one_crm" / "sidebar" / "onecrm" / "onecrm.json").read_text())["items"]
	assert not {item.get("link_to") for item in crm} & {"Contact", "Address"}


def test_a_list_has_one_home():
	"""A list is not linked from a rail or a workspace: its module's Lists is
	where it is."""
	held = {doctype for doctypes in _declared().values() for doctype in doctypes}
	places = [*tree.APP.glob("*/sidebar/*/*.json"), *tree.APP.glob("*/workspace/*/*.json")]
	for path in places:
		doc = json.loads(path.read_text())
		rows = doc.get("items") or doc.get("links") or []
		linked = {row.get("link_to") for row in rows if row.get("type") == "Link"}
		assert not linked & held, f"{path.name} links {sorted(linked & held)}, which a module's Lists holds"
	assert '"DocType", "Sales Stage"' in (tree.APP / "one_crm" / "home.py").read_text()
	for home in ("one_book", "one_crm", "one_hr", "one_inventory"):
		assert '"Masters"' not in (tree.APP / home / "home.py").read_text(), home


def test_a_value_is_placed_and_renamed_however_it_is_made():
	"""A tree's value goes under its root on every path (the create dialog's
	form, a OneAI card), and a card that changes the field a value is named
	from renames it."""
	for doctype in ("Customer Group", "Territory", "Item Group", "Supplier Group", "Department"):
		assert f'"{doctype}": {{"before_insert": "onedesk.one.lists.place"}}' in HOOKS, doctype
	proposals = (tree.APP / "one_ai" / "proposals.py").read_text()
	assert "held = _renamed(held, changes)" in proposals and "frappe.rename_doc(held.doctype" in proposals


def test_oneai_offers_on_every_list():
	assert "return {doctype: OFFERED for _module, doctype, _label, _one in kinds_of()}" in SOURCE
	ai = (tree.APP / "one" / "ai.py").read_text()
	assert "SUGGESTIONS.update(_lists.suggestions())" in ai
	assert '"page:masters"' not in ai
