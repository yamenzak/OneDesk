"""Masters, the short lists every app's records pick from (one/masters.py,
the masters page), and the shared Address Book in One's rail."""

import json
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "masters.py").read_text()
PAGE = tree.APP / "one" / "page" / "masters"
HOOKS = (tree.APP / "hooks.py").read_text()


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
		"OneInventory",
		"OneHR",
	}
	assert 'MANAGE = ("read", "write", "create", "delete")' in SOURCE
	assert '"onedesk.one.masters.settle"' in HOOKS
	assert '"Address Template": {"validate": "onedesk.one.masters.validate_address_template"}' in HOOKS
	settings = (tree.APP / "one" / "settings.py").read_text()
	assert '"lists"' not in settings and "address_templates" not in settings
	js = (tree.APP / "public" / "js" / "settings.js").read_text()
	assert "draw_lists" not in js and "draw_print_lists" not in js


def test_the_page_is_for_administrators_and_app_managers():
	page = json.loads((PAGE / "masters.json").read_text())
	assert page["name"] == "masters" and page["module"] == "One"
	roles = {one["role"] for one in page["roles"]}
	assert roles == {
		"Workspace Administrator",
		"Sales Manager",
		"Stock Manager",
		"Purchase Manager",
		"Item Manager",
		"HR Manager",
	}
	groups = SOURCE.split("def _groups(", 1)[1].split("\ndef ", 1)[0]
	assert "roles.administers()" in groups and "frappe.PermissionError" in groups
	for method in ("values", "add", "used"):
		assert "_kind(doctype)" in SOURCE.split(f"def {method}(", 1)[1].split("\ndef ", 1)[0], method
	assert '@frappe.whitelist(methods=["POST"])\ndef add(' in SOURCE
	assert "doc.insert()" in SOURCE and "ignore_permissions" not in SOURCE
	js = (PAGE / "masters.js").read_text()
	assert "frappe.client.rename_doc" in js and "frappe.client.delete" in js and "frappe.confirm(" in js


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
	assert at == labels.index("Numbering") + 1 and "Lists" not in labels
	assert one[at]["link_type"] == "Page" and one[at]["link_to"] == "masters"
