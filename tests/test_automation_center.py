"""AutomationCenter: an automation's steps walked against what a trigger
knows, OneMail's rules as its blocks, and the rules moved in."""

import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import tree

from onedesk.one import registry

AUTOMATION = tree.APP / "one" / "automation"
MAIL = tree.APP / "one_mail"
KINDS = {
	"from": "text",
	"to": "text",
	"subject": "text",
	"text": "text",
	"domain": "text",
	"sender_is": "kind",
	"outside": "flag",
	"starts": "flag",
	"attachment": "flag",
	"after_hours": "flag",
	"holiday": "flag",
}


def _load(path: Path, names: tuple, **extra) -> dict:
	space = dict(extra)
	for node in ast.parse(path.read_text()).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in names:
			exec(ast.unparse(node), space)
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return space


def _flow() -> dict:
	names = ("OPS", "test", "holds", "said", "walk", "_answered", "asks", "needs_ai", "topics", "answers_of", "actions_in", "conditions_in", "problems")
	return _load(AUTOMATION / "flow.py", names, _=lambda text: text, registry=registry)


def _checks() -> dict:
	names = ("ONCE", "CREATES", "_moves", "_replies", "_forwards", "_someone", "_creates", "from_fields")
	space = _load(MAIL / "blocks.py", names, re=re, _=lambda text: text, registry=registry)
	return {
		"move": space["_moves"],
		"read": None,
		"star": None,
		"junk": None,
		"reply": space["_replies"],
		"forward": space["_forwards"],
		"assign": space["_someone"],
		"notify": space["_someone"],
		"link": None,
		"create": space["_creates"],
	}, space["from_fields"]


def test_conditions_nest_in_groups_of_all_or_any():
	flow = _flow()
	facts = {"from": "News news@shop.example", "subject": "Weekly Newsletter", "attachment": False, "sender_is": {"Customer"}, "outside": True}
	both = {"items": [{"field": "from", "value": "shop.example"}, {"field": "subject", "value": "newsletter"}]}
	assert flow["test"](both, facts, KINDS)
	assert not flow["test"]({"items": [{"field": "from", "value": "shop"}, {"field": "attachment", "value": True}]}, facts, KINDS), "all, by default"
	nested = {"items": [{"field": "outside", "value": True}, {"any": True, "items": [{"field": "subject", "value": "invoice"}, {"field": "sender_is", "op": "is", "value": "Customer"}]}]}
	assert flow["test"](nested, facts, KINDS)
	assert flow["test"]({"items": []}, facts, KINDS), "no conditions: every record"
	assert flow["holds"]({"field": "subject", "op": "not_contains", "value": "invoice, quote"}, facts, KINDS)
	assert flow["holds"]({"field": "sender_is", "op": "is_not", "value": "Supplier"}, facts, KINDS)
	assert not flow["holds"]({"field": "nowhere", "value": "x"}, facts, KINDS), "a condition no block declares holds for nothing"
	assert flow["said"]("Order 12", "starts_with", "order") and not flow["said"]("Order 12", "is", "order")


def test_steps_branch_stop_and_take_oneai_s_answer():
	flow = _flow()
	steps = [
		{"type": "if", "id": "i", "test": {"items": [{"field": "outside", "value": True}]}, "then": [{"type": "star"}], "else": [{"type": "read"}]},
		{"type": "ask", "id": "a", "ask": "pick", "labels": [{"label": "Quote", "then": [{"type": "stop"}]}, {"label": "Complaint", "then": [{"type": "notify", "user": "x"}]}], "else": [{"type": "junk"}]},
		{"type": "move", "folder": "F"},
	]
	assert flow["needs_ai"](steps) and not flow["needs_ai"](steps[:1])
	assert flow["topics"]("R", steps) == [("R#a#0", "Quote"), ("R#a#1", "Complaint")]
	done, stopped = flow["walk"](steps, {"outside": True}, KINDS, flow["answers_of"]("R", steps, {"R#a#0"}))
	assert [one["type"] for one in done] == ["star"] and stopped, "Quote says stop"
	done, stopped = flow["walk"](steps, {"outside": False}, KINDS, flow["answers_of"]("R", steps, {"R#a#1"}))
	assert [one["type"] for one in done] == ["read", "notify", "move"] and not stopped
	done, _ = flow["walk"](steps, {}, KINDS, flow["answers_of"]("R", steps, set()))
	assert [one["type"] for one in done] == ["read", "junk", "move"], "nothing found: Otherwise"
	done, _ = flow["walk"]([{"type": "agent", "agent": "one_book", "instruction": "Draft the bill."}], {}, KINDS)
	assert done[0]["type"] == "agent", "an agent is a block like any other"


def test_a_rule_must_do_something_each_block_checks_its_own_and_old_rules_become_steps():
	flow = _flow()
	checks, from_fields = _checks()

	def problems(steps):
		return flow["problems"](steps, KINDS, checks)

	assert problems([{"type": "if", "test": {}, "then": [], "else": []}]) == ["Add at least one action."]
	assert "Choose the folder to move to." in problems([{"type": "move"}])
	assert "Write the address to forward to." in problems([{"type": "forward", "to": "nobody"}])
	assert "That cannot be set." in problems([{"type": "launch"}]), "a block nobody declares is refused"
	empty = [{"type": "if", "test": {"items": [{"any": True, "items": [{"field": "domain", "op": "is", "value": " "}]}]}, "then": [{"type": "junk"}]}]
	assert "Write what each condition looks for." in problems(empty), "an empty blank would match all mail"
	assert problems([{"type": "reply", "text": "Thanks", "once": "conversation"}]) == [], "an auto reply needs no If"
	assert "Give OneAI at least two labels to pick from." in problems([{"type": "ask", "ask": "pick", "labels": [{"label": "A"}], "then": [{"type": "star"}]}])
	old = {"from_contains": "shop", "subject_contains": "news", "match": "Any Condition", "move_to": "F", "star": 1, "stop": 1}
	steps = from_fields(old)
	assert steps[0]["test"] == {"any": True, "items": [{"field": "from", "op": "contains", "value": "shop"}, {"field": "subject", "op": "contains", "value": "news"}]}
	assert [one["type"] for one in steps[0]["then"]] == ["move", "star", "stop"]
	about = from_fields({"about": "soft drinks", "move_to": "F"})
	assert about[0]["type"] == "ask" and about[0]["question"] == "soft drinks" and flow["needs_ai"](about)


def _blocks(path: Path) -> list[ast.Call]:
	for node in ast.parse(path.read_text()).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "BLOCKS":
			return [one for one in node.value.elts if isinstance(one, ast.Call)]
	return []


def test_every_mail_rule_part_is_a_block_onemail_declares():
	"""What a mail rule could check and do is each a block of OneMail's, and an
	agent is OneAI's: the condition a step names and the action it does are
	found in the registry, never in the engine."""
	said = {(one.func.id, one.args[0].value) for one in _blocks(MAIL / "blocks.py") if isinstance(one.args[0], ast.Constant)}
	for key in KINDS:
		assert ("Condition", key) in said, key
	for key in ("move", "read", "star", "junk", "reply", "forward", "assign", "notify", "link", "create"):
		assert ("Action", key) in said, key
	assert ("Action", "agent") in {(one.func.id, one.args[0].value) for one in _blocks(tree.APP / "one_ai" / "blocks.py")}
	engine = (AUTOMATION / "engine.py").read_text() + (AUTOMATION / "flow.py").read_text()
	for word in ('"move"', '"reply"', "one_mail", "Communication"):
		assert word not in engine, f"the engine names {word}: a block says it"


def test_the_rules_move_in_and_run_from_automationcenter():
	"""Each Mail Rule becomes an Automation of its own name (so a reply sent
	once, a topic OneAI reads for and a record a rule made stay its own),
	the arrival runs the engine, and the doctype is gone."""
	patch = (MAIL / "patches" / "rules_are_automations.py").read_text()
	assert '"name": row.name' in patch and "if row.name in moved" in patch, "kept by name, and moved once"
	assert "doc.db_insert()" in patch, "kept as it was, not checked again"
	assert "onedesk.one_mail.patches.rules_are_automations" in (tree.APP / "patches.txt").read_text()
	assert not (MAIL / "doctype" / "mail_rule").exists() and not (MAIL / "flow.py").exists()
	rules = (MAIL / "rules.py").read_text()
	assert "engine.run(ARRIVES, made.email_account" in rules.split("def run_rules(", 1)[1].split("\ndef ", 1)[0]
	assert '"Automation": "onedesk.one.automation.who.allowed"' in tree.hooks()
	doctype = json.loads((tree.APP / "one" / "doctype" / "automation" / "automation.json").read_text())
	assert {one["fieldname"] for one in doctype["fields"]} >= {"title", "enabled", "priority", "trigger", "scope", "steps", "requested_by"}


def test_automationcenter_is_a_centre_and_its_builder_an_island():
	from onedesk.one.registry.model import CENTRE_KEYS

	assert "automation" in CENTRE_KEYS and registry.get("automation_center").centre.key == "automation"
	centre = (tree.APP / "public" / "js" / "one" / "automation_center.js").read_text()
	assert 'onedesk.centers.declare("automation"' in centre and 'mount_island("onedesk.automation"' in centre
	build = (tree.ROOT / "frontend" / "build-islands.mjs").read_text()
	assert '"onedesk.automation": "src/islands/automation.js"' in build
	builder = (tree.ROOT / "frontend" / "src" / "automation" / "AutomationBuilder.vue").read_text()
	assert 'from "@framework/ui/AutomationCanvas"' in builder, "frappe's own flow canvas"
	assert "/assets/onedesk/js/one/automation_center.js" in tree.hooks()
