"""How a lead arrives: the web form, the inbox, duplicates and first replies."""

import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

CAPTURE = tree.APP / "one_crm" / "capture.py"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")


def _tail():
	space = {"re": re}
	for node in ast.parse(CAPTURE.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "DIGITS":
			exec(ast.unparse(node), space)
		if isinstance(node, ast.FunctionDef) and node.name == "tail":
			exec(ast.unparse(node), space)
	return space["tail"]


def test_one_number_however_it_is_typed():
	tail = _tail()
	assert tail("+971 50 123 4567") == tail("050-1234567") == tail("0501234567")
	assert tail("+971 50 123 4567") != tail("+971 50 123 4568")
	assert tail("123") == "", "an extension is not a phone number"
	assert tail(None) == ""


def test_the_mail_finds_its_lead_by_the_error_frappe_catches():
	"""frappe's mail receiver catches DuplicateEntryError, and only that, to look
	the sender up; any other refusal would lose the mail."""
	source = CAPTURE.read_text(encoding="utf-8")
	assert "raise frappe.DuplicateEntryError(" in source
	receive = Path("/home/frappe/bench1/apps/frappe/frappe/email/receive.py").read_text()
	assert "except frappe.DuplicateEntryError:" in receive


def test_every_way_in_is_hooked():
	assert '"before_insert": "onedesk.one_crm.capture.before_insert"' in HOOKS
	assert '"after_insert": "onedesk.one_crm.capture.assigned"' in HOOKS.split('"ToDo": {', 1)[1].split('}', 1)[0]
	for doctype in ("Communication", "Call Log"):
		assert f'"{doctype}": {{"after_insert": "onedesk.one_crm.capture.replied"}}' in HOOKS
	assert '"onedesk.one_crm.capture.defaults"' in HOOKS.split("after_migrate")[0], "on install only"


def test_the_web_form_writes_only_what_a_lead_has():
	form = json.loads((tree.APP / "one_crm" / "web_form" / "get_in_touch" / "get_in_touch.json").read_text())
	lead = json.loads(Path("/home/frappe/bench1/apps/erpnext/erpnext/crm/doctype/lead/lead.json").read_text())
	custom = json.loads((tree.APP / "one_crm" / "custom" / "lead.json").read_text())["custom_fields"]
	fields = {f["fieldname"] for f in lead["fields"]} | {f["fieldname"] for f in custom}
	assert form["doc_type"] == "Lead" and not form["login_required"]
	assert {f["fieldname"] for f in form["web_form_fields"]} <= fields
