"""Every link in a space's rail opens for the people the space is for
(one/reach.py). erpnext and hrms keep a few of what the rails link to for
their System Manager, which nobody on a workspace holds; each space's
access.py gives them to its own roles. These read the code that says so."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

HOOKS = (tree.APP / "hooks.py").read_text()

#: What each space gives, and to whom: what reach.check found refused.
GIVEN = {
	"one_book": (
		"Bank Reconciliation Tool",
		"Bank Statement Import",
		"Opening Invoice Creation Tool",
		"Purchase Taxes and Charges Template",
	),
	"one_inventory": ("Asset", "Asset Category", "Asset Repair", "Item Price", "Quality Inspection"),
	"one_project": ("Projects Settings",),
	"one_hr": ("Travel Request", "Purpose of Travel", "Employee Advance", "Vehicle Log"),
	"one_crm": ("Email Campaign", "Email Group", "UTM Source", "Assignment Rule"),
}


def test_every_space_gives_what_its_rail_needs_on_every_migrate():
	for module, doctypes in GIVEN.items():
		source = (tree.APP / module / "access.py").read_text()
		assert "roles.give(GIVEN)" in source, module
		for doctype in doctypes:
			assert f'"{doctype}"' in source, (module, doctype)
		assert HOOKS.count(f'"onedesk.{module}.access.settle"') == 2, module


def test_a_role_that_reads_already_keeps_what_it_has():
	roles = (tree.APP / "one" / "roles.py").read_text()
	give = roles.split("def give(", 1)[1].split("\ndef ", 1)[0]
	assert '"read": 1' in give and "continue" in give
	assert "ptype in SUBMITTING and not submits" in give
	assert "System Manager" not in give


def test_the_rail_links_nothing_that_is_gone_or_set_elsewhere():
	rail = json.loads((tree.APP / "one_crm" / "sidebar" / "onecrm" / "onecrm.json").read_text())
	linked = {item.get("link_to") for item in rail["items"]}
	assert "Newsletter" not in linked, "frappe no longer ships it"
	assert "Email Account" not in linked, "the workspace's mailboxes are Settings › Mail"


def test_a_sales_managers_assignment_rule_shares_out_leads_by_their_fields():
	access = (tree.APP / "one_crm" / "access.py").read_text()
	assert 'SHARED_OUT = ("Lead", "Opportunity")' in access
	rule = access.split("def assignment_rule(", 1)[1].split("\ndef ", 1)[0]
	assert "layer.held()" in rule and "plain(meta" in rule
	assert '"Assignment Rule": {"validate": "onedesk.one_crm.access.assignment_rule"}' in HOOKS
	assert '"Assignment Rule": "onedesk.one_crm.access.has_permission"' in HOOKS
	assert '"Assignment Rule": "onedesk.one_crm.access.query"' in HOOKS
	plain = access.split("def plain(", 1)[1].split("\ndef ", 1)[0]
	assert "df.permlevel" in plain and "ast.Call" not in access.split("PLAIN = (", 1)[1].split(")", 1)[0]


def test_reach_reads_the_rails_against_the_roles_people_hands_out():
	reach = (tree.APP / "one" / "reach.py").read_text()
	assert "from onedesk.one.settings import APPS" in reach
	assert "{*users, *managers, *EVERYBODY}" in reach


def test_a_rail_address_into_a_kind_follows_who_may_read_it():
	"""OneCRM's Pipeline is an address, not a DocType link, so frappe shows it
	to whoever sees the rail; the boot leaves it out for somebody who may not
	read Opportunity, as frappe does its own links."""
	import re

	reach = (tree.APP / "one" / "reach.py").read_text()
	into = re.compile(re.search(r'_INTO = re\.compile\(r"(.+?)"\)', reach).group(1))
	assert into.match("/desk/opportunity/view/kanban/Pipeline").group(1) == "opportunity"
	assert into.match("/desk/sales-invoice?status=Unpaid").group(1) == "sales-invoice"
	assert 'frappe.has_permission(kind, "read")' in reach
	boot = (tree.APP / "one" / "boot.py").read_text()
	assert 'reach.unopened(bootinfo.get("module_sidebars"))' in boot
	rail = json.loads((tree.APP / "one_crm" / "sidebar" / "onecrm" / "onecrm.json").read_text())
	pipeline = next(item for item in rail["items"] if item.get("label") == "Pipeline")
	assert into.match(pipeline["url"]), "the Pipeline is read as an address into Opportunity"
