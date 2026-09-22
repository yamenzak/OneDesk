"""What an action may be told, and what a workspace may add to it.

The rule this file exists for is one sentence: a workspace's instructions are
**added** to ours and can never replace them. It is the whole safety of the
feature and it is invisible when it works, so it is held here off the source.
"""

import ast
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

ACTIONS = tree.APP / "one_admin" / "actions.py"
PROXY = tree.APP / "one_admin" / "proxy.py"
FIXTURE = tree.APP / "fixtures" / "ai_action.json"
ACTION = tree.APP / "one_ai" / "doctype" / "ai_action" / "ai_action.json"
SETTING = tree.APP / "one_ai" / "doctype" / "ai_action_setting" / "ai_action_setting.json"


def _capability():
	import importlib.util

	at = tree.APP / "one_admin" / "capability.py"
	spec = importlib.util.spec_from_file_location("onedesk_cap_actions", at)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


capability = _capability()


def _spec(path: Path) -> dict:
	return json.loads(path.read_text(encoding="utf-8"))


def _function(name: str) -> ast.FunctionDef:
	body = ast.parse(ACTIONS.read_text(encoding="utf-8"))
	return next(n for n in body.body if isinstance(n, ast.FunctionDef) and n.name == name)


# ------------------------------------------------- ours first, theirs after


def test_a_workspace_adds_and_never_replaces():
	"""Read off the one line that joins the two, because there is nowhere else
	the order could be got wrong."""
	joined = next(
		ast.unparse(node)
		for node in ast.walk(_function("instruction"))
		if isinstance(node, ast.Return) and "AND_THEN" in ast.unparse(node)
	)
	assert joined.index("said") < joined.index("AND_THEN"), (
		f"a workspace's wording is being put first: {joined}"
	)
	assert "if extra else said" in joined, "an empty addition should leave ours alone"


def test_the_line_between_them_says_which_wins():
	said = ast.literal_eval(
		next(
			n.value
			for n in ast.parse(ACTIONS.read_text(encoding="utf-8")).body
			if isinstance(n, ast.Assign)
			and any(t.id == "AND_THEN" for t in n.targets if isinstance(t, ast.Name))
		)
	)
	assert "ignore" in said.lower() and "conflict" in said.lower()


def test_the_instruction_is_never_taken_from_the_caller():
	"""A tenant sends the model it picked and the wording it added. The
	instruction is read here, from the copy a tenant cannot write."""
	run = ast.unparse(_function("run"))
	assert "instruction(asked" in run
	body = ast.parse(PROXY.read_text(encoding="utf-8"))
	endpoint = next(
		n for n in body.body if isinstance(n, ast.FunctionDef) and n.name == "ai_run"
	)
	taken = {a.arg for a in endpoint.args.args}
	assert "instruction" not in taken and "system" not in taken, taken
	assert taken == {"action", "text", "model", "extra", "reference"}


def test_what_a_workspace_adds_is_bounded_at_both_ends():
	"""Its own doctype checks it, and so does admin — because what a tenant
	sends is what a tenant's administrator typed."""
	assert "MOST_EXTRA" in ACTIONS.read_text(encoding="utf-8")
	assert "MOST" in (
		tree.APP / "one_ai" / "doctype" / "ai_action_setting" / "ai_action_setting.py"
	).read_text(encoding="utf-8")


# --------------------------------------------------------- who may write what


def test_only_the_operator_may_write_an_action():
	"""It exists on every site so a workspace knows what it may ask for. The
	copy that decides is the administrator's, and nobody on a tenant holds the
	role that can change it."""
	roles = {row["role"]: row for row in _spec(ACTION)["permissions"]}
	assert roles["One Operator"]["write"]
	assert "System Manager" in roles and not roles["System Manager"]["write"]


def test_a_workspace_owns_its_own_setting():
	roles = {row["role"]: row for row in _spec(SETTING)["permissions"]}
	assert roles["System Manager"]["write"] and roles["System Manager"]["create"]
	assert "One Operator" not in roles, "an operator editing this would be editing a customer's"


# ------------------------------------------------------------ which model


@pytest.mark.parametrize(
	"model_says,action_needs,yes",
	[
		("Text Generation", "Text Generation", True),
		("Multimodal", "Text Generation", True),
		("Vision", "Text Generation", True),
		# Measured: a model that reads sound and nothing else turned up as a
		# candidate summariser, because it writes text back.
		("Transcription", "Text Generation", False),
		("Text Generation", "Vision", False),
		("Multimodal", "Vision", True),
		("Embedding", "Text Generation", False),
		("Image Generation", "Text Generation", False),
	],
)
def test_a_model_answers_only_a_job_it_can_do(model_says, action_needs, yes):
	assert capability.able(model_says, action_needs) is yes


def test_every_capability_covers_itself():
	for word in capability.WORDS:
		assert word in capability.covers(word), word


def _options(spec: dict, fieldname: str) -> set[str]:
	said = next(f["options"] for f in spec["fields"] if f["fieldname"] == fieldname)
	return set(said.split("\n")) - {""}


def test_the_selects_offer_the_words_the_table_knows():
	"""An option on one of them and not the other is a picker that shows
	nothing. `Other` is the exception and only on a model: it is what a model
	whose provider said something we do not recognise gets called, and nothing
	should ever need it or default to it."""
	model = _spec(tree.APP / "one_admin" / "doctype" / "ai_model" / "ai_model.json")
	assert _options(model, "capability") == set(capability.WORDS) | {"Other"}
	assert _options(model, "default_for") == set(capability.WORDS)
	assert _options(_spec(ACTION), "capability") == set(capability.WORDS)
	assert "Other" not in capability.COVERS


# ------------------------------------------------------------- the fixtures


def test_the_actions_ship_as_fixtures():
	hooks = (tree.APP / "hooks.py").read_text(encoding="utf-8")
	assert '"AI Action",' in hooks, "an action that is not a fixture arrives on no site"


def test_every_shipped_action_is_whole():
	rows = _spec(FIXTURE)
	assert len(rows) >= 2, "one action proves nothing about the shape"
	for row in rows:
		assert row["capability"] in capability.WORDS, row["key"]
		assert row["instruction"].strip(), row["key"]
		assert row["max_output_tokens"] > 0, f"{row['key']} holds nothing before it calls"


def test_a_shipped_instruction_says_what_not_to_do():
	"""Both of them tell the model not to invent. An action that only says what
	to write is an action that fills gaps with plausible fiction."""
	for row in _spec(FIXTURE):
		said = row["instruction"].lower()
		assert any(word in said for word in ("do not", "only")), row["key"]
