"""What an action is told, and what a workspace may not add to it.

A workspace names an action and its tier. The words a model is given, and
the model, are the account's (docs/AICENTER.md): nothing a workspace sends
reaches the instruction. Held here off the source.
"""

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tree

from onedesk.one_ai import models

ACTIONS = tree.APP / "one_admin" / "actions.py"
PROXY = tree.APP / "one_admin" / "proxy.py"
FIXTURE = tree.APP / "fixtures" / "ai_action.json"
ACTION = tree.APP / "one_ai" / "doctype" / "ai_action" / "ai_action.json"


def spoken(where, name: str) -> str:
	for node in ast.walk(ast.parse(where.read_text(encoding="utf-8"))):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return ast.unparse(node)
	raise AssertionError(f"{name} is not in {where.name}")


def _spec(path: Path) -> dict:
	return json.loads(path.read_text(encoding="utf-8"))


def _function(name: str) -> ast.FunctionDef:
	body = ast.parse(ACTIONS.read_text(encoding="utf-8"))
	return next(n for n in body.body if isinstance(n, ast.FunctionDef) and n.name == name)


def test_a_workspace_adds_nothing_to_the_instruction():
	"""The instruction is the persona and the action's own words, and takes
	nothing else."""
	said = _function("instruction")
	assert [a.arg for a in said.args.args] == ["asked"]
	assert "AND_THEN" not in ACTIONS.read_text(encoding="utf-8")


def test_the_door_takes_a_tier_and_never_a_model_or_words():
	"""A tenant sends its action, its tier and the conversation. The
	instruction is read here, from the copy a tenant cannot write."""
	run = ast.unparse(_function("run"))
	assert "instruction(asked)" in run
	body = ast.parse(PROXY.read_text(encoding="utf-8"))
	endpoint = next(n for n in body.body if isinstance(n, ast.FunctionDef) and n.name == "ai_run")
	assert {a.arg for a in endpoint.args.args} == {"action", "text", "tier", "reference", "turns", "tools"}


def test_only_the_operator_may_write_an_action():
	"""It exists on every site so a workspace knows what it may ask for. The
	copy that decides is the administrator's, and nobody on a tenant holds the
	role that can change it."""
	roles = {row["role"]: row for row in _spec(ACTION)["permissions"]}
	assert roles["One Operator"]["write"]
	assert "System Manager" in roles and not roles["System Manager"]["write"]


def test_every_action_is_a_kind_of_work_models_knows():
	"""An action runs on what `one_ai/models.py` names for its kind, so a
	capability or an action that maps to no kind would run on nothing."""
	said = ACTIONS.read_text(encoding="utf-8")
	capable = ast.literal_eval(said.split("CAPABLE = ", 1)[1].split("\n", 1)[0])
	builds = ast.literal_eval(said.split("BUILDS = ", 1)[1].split("\n", 1)[0])
	options = set(next(f["options"] for f in _spec(ACTION)["fields"] if f["fieldname"] == "capability").split("\n")) - {""}
	for row in _spec(FIXTURE):
		assert row["capability"] in options, row["key"]
		kind = "build" if row["key"] in builds else capable.get(row["capability"], "talk")
		assert kind in models.USE, f"{row['key']} is {kind}, which models.USE does not name"


def test_the_actions_ship_as_fixtures():
	hooks = (tree.APP / "hooks.py").read_text(encoding="utf-8")
	assert '"AI Action",' in hooks, "an action that is not a fixture arrives on no site"


def test_every_shipped_action_is_whole():
	rows = _spec(FIXTURE)
	assert len(rows) >= 2, "one action proves nothing about the shape"
	for row in rows:
		if row["capability"] == "Embedding":
			assert row["max_input_tokens"] > 0, f"{row['key']} holds nothing before it calls"
			continue
		assert row["instruction"].strip(), row["key"]
		assert row["max_output_tokens"] > 0, f"{row['key']} holds nothing before it calls"


def test_the_persona_says_what_not_to_do():
	"""It tells the model not to invent, and it is said before every action —
	one that only says what to write is one that fills gaps with plausible
	fiction. On the persona rather than the actions since the rule is true of
	all of them."""
	settings = _spec(tree.APP / "one_admin" / "doctype" / "one_admin_settings" / "one_admin_settings.json")
	said = next(f for f in settings["fields"] if f["fieldname"] == "persona")["default"].lower()
	assert "never invent" in said
	assert "cannot see" in said
	assert "suggest" in said


def test_a_workspace_holds_no_copy_of_the_instruction():
	"""`AI Action` is a fixture, so every site gets the row — the label, the
	capability and the caps.
	The instruction is not part of that, and shipping it while declining to
	render it would be a curtain rather than a wall: the row would be in the
	workspace's database and `frappe.client.get` reads it."""
	said = (tree.APP / "one_ai" / "instructions.py").read_text(encoding="utf-8")
	assert "site.is_admin()" in said
	assert '"instruction", ""' in said

	hooks = (tree.APP / "hooks.py").read_text(encoding="utf-8")
	for when in ("after_sync", "after_migrate"):
		at = hooks.index(when)
		block = hooks[at : hooks.index("]", at)]
		assert "onedesk.one_ai.instructions.trim" in block, f"{when} does not trim"
		assert block.index("site.apply") < block.index("instructions.trim")


def test_the_persona_is_said_once_rather_than_four_times():
	"""What is true of every action — who it is, that it does not invent, what
	it does with a tool — is one row on the account. Four fixtures repeating it
	is four places to edit and three chances to disagree."""
	said = spoken(tree.APP / "one_admin" / "actions.py", "instruction")
	assert "_persona()" in said
	assert said.index("_persona()") < said.index("asked.instruction")

	rules = ("you are oneai", "suggest", "count rather than list", "do not invent")
	for row in _spec(FIXTURE):
		for rule in rules:
			assert rule not in row["instruction"].lower(), (
				f"{row['name']} repeats the persona: {rule}"
			)


def test_the_persona_says_the_cards_are_already_on_screen():
	"""Otherwise it lists back every record the cards above it just drew."""
	import json

	settings = json.loads((tree.APP / "one_admin" / "doctype" / "one_admin_settings" / "one_admin_settings.json").read_text())
	persona = next(f for f in settings["fields"] if f["fieldname"] == "persona")["default"]
	assert "as a card" in persona
	assert "name the records you used" not in persona


def test_rounds_are_counted_per_question_not_per_conversation():
	"""Counted over the whole conversation, the sixth question of any chat was
	refused before it was asked."""
	body = (tree.APP / "one_admin" / "actions.py").read_text().split("def _conversation(", 1)[1].split("\ndef ", 1)[0]
	assert 'not one.get("context")' in body and "turns[asked + 1 :]" in body
