"""A lead's and a deal's next step: what counts as open, and Home counting it."""

import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

NEXT = tree.APP / "one_crm" / "next.py"
WORKSPACE = tree.APP / "one_crm" / "workspace" / "onecrm" / "onecrm.json"
ERPNEXT = Path("/home/frappe/bench1/apps/erpnext/erpnext/crm/doctype")


def _constant(name):
	for node in ast.parse(NEXT.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name:
			return ast.literal_eval(node.value)


def test_every_open_status_is_one_erpnext_has():
	for doctype, statuses in _constant("OPEN").items():
		meta = json.loads((ERPNEXT / doctype.lower() / f"{doctype.lower()}.json").read_text())
		options = next(f["options"] for f in meta["fields"] if f["fieldname"] == "status").split("\n")
		assert set(statuses) <= set(options), f"{doctype} has no status {set(statuses) - set(options)}"


def test_home_counts_what_the_reminders_count_as_open():
	"""Home's shortcuts are frappe filter expressions, so the open statuses are
	written there a second time; they must be the same list."""
	shortcuts = json.loads(WORKSPACE.read_text(encoding="utf-8"))["shortcuts"]
	open_ = _constant("OPEN")
	owner = _constant("OWNER")
	mine = [one for one in shortcuts if "frappe.session.user" in one["stats_filter"]]
	assert len(mine) == 4
	for one in mine:
		doctype = one["link_to"]
		said = re.search(r'"status","in",(\[[^\]]*\])', one["stats_filter"]).group(1)
		assert tuple(json.loads(said)) == open_[doctype], one["label"]
		assert f'"{owner[doctype]}","=",frappe.session.user' in one["stats_filter"], one["label"]
		assert one.get("format") == "{}", "a count of 0 draws an empty badge without a format"


def test_both_records_carry_the_step_and_remind():
	hooks = (tree.APP / "hooks.py").read_text(encoding="utf-8")
	for doctype in ("lead", "opportunity"):
		custom = json.loads((tree.APP / "one_crm" / "custom" / f"{doctype}.json").read_text())
		assert {"one_next_step", "one_next_on"} <= {f["fieldname"] for f in custom["custom_fields"]}
	assert hooks.count('"onedesk.one_crm.next.on_update"') == 2


def test_the_form_offers_a_next_step_where_the_server_reminds():
	source = (tree.APP / "public" / "js" / "next_step.js").read_text(encoding="utf-8")
	for doctype, statuses in _constant("OPEN").items():
		said = re.search(rf"{doctype}: (\[[^\]]*\])", source).group(1)
		assert tuple(json.loads(said)) == statuses, doctype
