"""The model a person picks in the OneAI panel, and the name a conversation
is given: who may pick, what may be picked, and that a name somebody gave is
kept."""

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

CHAT = tree.APP / "one_ai" / "chat.py"
ACTIONS = json.loads((tree.APP / "fixtures" / "ai_action.json").read_text(encoding="utf-8"))
SETTING = json.loads(
	(tree.APP / "one_ai" / "doctype" / "ai_action_setting" / "ai_action_setting.json").read_text(
		encoding="utf-8"
	)
)
AI_CHAT = json.loads(
	(tree.APP / "one_ai" / "doctype" / "ai_chat" / "ai_chat.json").read_text(encoding="utf-8")
)


def spoken(name: str) -> str:
	for node in ast.walk(ast.parse(CHAT.read_text(encoding="utf-8"))):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return ast.unparse(node)
	raise AssertionError(f"{name} is not in chat.py")


def test_only_somebody_the_workspace_lets_choose_may_pick():
	assert "roles.administers()" in spoken("may_choose")
	assert "people_choose" in spoken("may_choose")
	assert spoken("choose_model").index("may_choose()") < spoken("choose_model").index("set_default")
	assert "if not may_choose()" in spoken("models")


def test_a_model_the_workspace_does_not_offer_is_refused():
	said = spoken("choose_model")
	assert "not in {one['name'] for one in models()['models']}" in said
	assert "doc.check_permission('write')" in said


def test_a_pick_is_dropped_when_the_person_may_no_longer_choose():
	assert "if may_choose() else None" in spoken("_pinned")
	assert "if may_choose() else ''" in spoken("_usual")
	assert "pinned=_pinned(doc)" in spoken("_ran")


def test_the_panel_is_told_names_and_makers_never_prices():
	said = spoken("models")
	for price in ("read", "written", "per_million"):
		assert f"'{price}'" not in said


def test_a_name_somebody_gave_is_kept():
	assert "doc.titled = 1" in spoken("rename")
	said = spoken("_title")
	assert said.index("if doc.get('titled')") < said.index("run.once(")
	assert "'titled': 1" in said
	assert "one_ai_title" in said


def test_the_title_action_has_no_tools_and_few_words():
	titling = next(one for one in ACTIONS if one["name"] == "chat_title")
	assert not titling["may_use_tools"]
	assert titling["max_output_tokens"] <= 40


def test_the_fields_exist_where_the_code_reads_them():
	assert "people_choose" in {f["fieldname"] for f in SETTING["fields"]}
	held = {f["fieldname"]: f for f in AI_CHAT["fields"]}
	assert held["chosen_model"]["read_only"] and held["titled"]["hidden"]
