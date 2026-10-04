"""The short lists every app's records pick from, and the shared Address Book
(one/lists.py, One's rail)."""

import json
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "lists.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()


def _regex():
	"""The tag patterns, read out of lists.py without frappe."""
	import re

	found = {}
	for name in ("TAG", "FIELD", "IF", "END", "WORDS"):
		line = next(one for one in SOURCE.splitlines() if one.startswith(f"{name} = re.compile("))
		found[name] = eval(line.split(" = ", 1)[1], {"re": re})
	return types.SimpleNamespace(**found)


def test_the_lists_are_granted_to_the_administrator_and_wired():
	for doctype in ("Salutation", "Gender", "Print Heading", "Address Template"):
		assert f'"{doctype}": ("read", "write", "create", "delete")' in SOURCE, doctype
	assert '"onedesk.one.lists.settle"' in HOOKS
	assert '"Address Template": {"validate": "onedesk.one.lists.validate_address_template"}' in HOOKS
	settings = (tree.APP / "one" / "settings.py").read_text()
	assert '("lists", _lt("Lists"), "list", "workspace")' in settings and '"lists": _lists' in settings
	assert '"address_templates": lists.address_templates()' in settings
	js = (tree.APP / "public" / "js" / "settings.js").read_text()
	assert "draw_lists(data)" in js and "draw_print_lists(data)" in js and "static removable(" in js


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
	assert "Lists" in labels and labels.index("Lists") == labels.index("Numbering") + 1
