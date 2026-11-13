"""A lead's and a deal's next step: what counts as open, and Home counting it."""

import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree
from tests.bench import APPS

NEXT = tree.APP / "one_crm" / "next.py"
HOME = tree.APP / "one_crm" / "home.py"
ERPNEXT = APPS / "erpnext/erpnext/crm/doctype"


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
	"""Today reads the open statuses and the owner from next.py itself, so
	what it counts as due is what is reminded."""
	home = HOME.read_text(encoding="utf-8")
	assert 'next_step.OPEN[doctype]' in home and "next_step.OWNER[doctype]" in home
	assert '"one_next_on", "is", "set" if due else "not set"' in home, "an empty step is never due"


def test_both_records_carry_the_step_and_remind():
	hooks = tree.hooks()
	for doctype in ("lead", "opportunity"):
		custom = json.loads((tree.APP / "one_crm" / "custom" / f"{doctype}.json").read_text())
		assert {"one_next_step", "one_next_on"} <= {f["fieldname"] for f in custom["custom_fields"]}
	assert '"onedesk.one_crm.tell.due"' in hooks, "a step come due is told every five minutes"
	assert '"name": "Next Step Due"' in (tree.APP / "one_crm" / "notifications.py").read_text(encoding="utf-8")


def test_the_form_offers_a_next_step_where_the_server_reminds():
	source = (tree.APP / "public" / "js" / "one_crm" / "next_step.js").read_text(encoding="utf-8")
	for doctype, statuses in _constant("OPEN").items():
		said = re.search(rf"{doctype}: (\[[^\]]*\])", source).group(1)
		assert tuple(json.loads(said)) == statuses, doctype


def test_the_lists_open_on_what_is_still_worked():
	"""A lead's and an opportunity's list open filtered to the statuses whose
	next step is reminded, the same list."""
	for doctype, statuses in _constant("OPEN").items():
		source = (tree.APP / "public" / "js" / "one_crm" / f"{doctype.lower()}_list.js").read_text(encoding="utf-8")
		said = re.search(r'settings\.filters = \[\["status", "in", (\[[^\]]*\])\]\]', source).group(1)
		assert tuple(json.loads(said)) == statuses, doctype
