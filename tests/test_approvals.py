"""Approvals (one/approvals.py): what a condition the workspace writes may say,
an approval laid out for frappe's builder, whoever a step waits on told through
the hub, OneIntake taking a bill's approval step rather than submitting past it,
and OneAI's card. These read the code that says so, and the condition check
runs as it would."""

import ast
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "approvals.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()


def _plain_condition():
	"""plain_condition, run against a meta that knows grand_total and supplier."""
	tree_ = ast.parse(SOURCE)
	keep = [
		node
		for node in tree_.body
		if (isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "PLAIN" for t in node.targets))
		or (isinstance(node, ast.FunctionDef) and node.name == "plain_condition")
	]
	module = ast.Module(body=keep, type_ignores=[])
	space = {"ast": ast, "no_value_fields": ("Section Break", "Table")}
	exec(compile(module, "approvals", "exec"), space)
	fields = {
		"grand_total": types.SimpleNamespace(permlevel=0, fieldtype="Currency"),
		"supplier": types.SimpleNamespace(permlevel=0, fieldtype="Link"),
		"secret": types.SimpleNamespace(permlevel=1, fieldtype="Data"),
		"items": types.SimpleNamespace(permlevel=0, fieldtype="Table"),
	}
	meta = types.SimpleNamespace(get_field=fields.get)
	return lambda text: space["plain_condition"](meta, text)


def test_a_condition_compares_the_records_fields_with_plain_values():
	plain = _plain_condition()
	assert plain("")
	assert plain("doc.grand_total > 5000")
	assert plain("doc.grand_total <= 5000 and doc.supplier == 'Acme'")
	assert plain("doc.supplier in ('A', 'B') or not doc.grand_total")


def test_nothing_else_is_a_condition():
	plain = _plain_condition()
	for text in (
		"frappe.db.sql('select 1')",
		"doc.get('grand_total')",
		"doc",
		"doc.secret == 'x'",
		"doc.items",
		"doc.unknown > 1",
		"__import__('os')",
		"doc.grand_total > frappe.session.user",
		"[x for x in doc.items]",
		"doc.grand_total >",
	):
		assert not plain(text), text


def test_every_approval_is_told_through_the_hub_and_laid_out():
	validate = SOURCE.split("def validate(", 1)[1].split("\ndef ", 1)[0]
	assert "doc.send_email_alert = 0" in validate and "_laid_out(doc)" in validate
	assert '"Workflow Action": {"after_insert": "onedesk.one.approvals.waiting"}' in HOOKS
	notifications = (tree.APP / "one" / "notifications.py").read_text()
	assert '_lt("Approval Waiting")' in notifications


def test_intake_takes_the_approval_step_and_oneai_never_does():
	drafts = (tree.APP / "one_intake" / "drafts.py").read_text()
	submit_all = drafts.split("def submit_all(", 1)[1].split("\ndef ", 1)[0]
	assert "approvals.submitting(doc)" in submit_all and "apply_workflow(doc" in submit_all
	maybe = drafts.split("def maybe_submit(", 1)[1].split("\ndef ", 1)[0]
	assert "if approvals.submitting(doc):\n\t\treturn" in maybe


def test_oneai_suggests_an_approval_as_a_card():
	ai = (tree.APP / "one" / "ai.py").read_text()
	suggest = ai.split("def suggest_approval(", 1)[1].split("\ndef ", 1)[0]
	assert "approvals.plain_condition(" in suggest and 'proposals.propose(\n\t\t\t"Approval"' in suggest
	for tool in ("workspace_approvals", "suggest_approval"):
		assert f'"onedesk.one.ai.{tool}"' in HOOKS, tool
	proposals = (tree.APP / "one_ai" / "proposals.py").read_text()
	assert 'entry.kind == "Approval"' in proposals and "approvals.make(" in proposals


def test_the_builder_stays_in_ones_rail():
	desk = (tree.APP / "public" / "js" / "desk.js").read_text()
	assert '["workflow-builder", "dashboard-view"].includes(route[0])' in desk
