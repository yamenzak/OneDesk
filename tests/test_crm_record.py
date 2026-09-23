"""A lead's and a deal's page: what it answers, calls by hand, one timeline."""

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

RECORD = tree.APP / "one_crm" / "record.py"
CALL_LOG = Path("/home/frappe/bench1/apps/erpnext/erpnext/telephony/doctype/call_log/call_log.json")


def _constant(name):
	for node in ast.parse(RECORD.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name:
			return ast.literal_eval(node.value)


def test_every_outcome_is_a_call_log_status():
	fields = json.loads(CALL_LOG.read_text())["fields"]
	statuses = next(f["options"] for f in fields if f["fieldname"] == "status").split("\n")
	assert set(_constant("OUTCOME").values()) <= set(statuses)


def test_notes_are_comments_so_the_notes_tab_is_gone():
	hooks = (tree.APP / "hooks.py").read_text(encoding="utf-8")
	assert hooks.count('"onedesk.one_crm.record.settle"') == 2, "after install and after migrate"
	for doctype in ("lead", "opportunity"):
		setters = json.loads((tree.APP / "one_crm" / "custom" / f"{doctype}.json").read_text())["property_setters"]
		hidden = {row["field_name"] for row in setters if row["property"] == "hidden" and row["value"] == "1"}
		assert {"notes_tab", "notes_html"} <= hidden, doctype
	css = (tree.APP / "public" / "css" / "desk.css").read_text(encoding="utf-8")
	assert '[data-page-route="Opportunity"] .comment-box' in css, "nowhere to write a comment"


def test_both_pages_paint_the_band():
	for script in ("lead.js", "opportunity.js"):
		assert "onedesk.crm_record.refresh(frm)" in (tree.APP / "public" / "js" / script).read_text()
