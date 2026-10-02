"""A round trip with a tool in it, and who is allowed to stop it.

Two providers spell one conversation three different ways — a model's own turn,
a tool it asked for, and the result it is handed back — and getting any of the
three wrong is a call that costs money and answers nonsense. The translators are
pure, so they are lifted out of `gateway.py` and run here against both dialects.

The rest is the rule that a loop is stopped by the side paying for it: the
rounds are counted on the admin side, on the turns it is handed, because a
workspace counting its own rounds is a workspace whose bug we bill for.
"""

import ast
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

GATEWAY = tree.APP / "one_admin" / "gateway.py"
ACTIONS = tree.APP / "one_admin" / "actions.py"
RUN = tree.APP / "one_ai" / "run.py"
TOOLS = tree.APP / "one_ai" / "tools.py"

#: The translators, which touch nothing but `json` and each other.
LIFTED = (
	"said",
	"_openai_turn",
	"_openai_calls",
	"_arguments",
	"_gemini_turn",
	"_gemini_calls",
	"_first_part",
)


def turns():
	"""The pure part of `gateway.py`, without importing frappe."""
	body = ast.parse(GATEWAY.read_text(encoding="utf-8"))
	wanted = [
		node
		for node in body.body
		if isinstance(node, ast.FunctionDef) and node.name in LIFTED
	]
	assert len(wanted) == len(LIFTED), "a translator was renamed and this guard was not"
	# `_openai_turn` reads the roles its own module names.
	wanted += [
		node
		for node in body.body
		if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "OPENAI_ROLES" for t in node.targets)
	]
	room: dict = {"json": json}
	exec(compile(ast.Module(body=wanted, type_ignores=[]), str(GATEWAY), "exec"), room)
	return room


def code(where: Path) -> str:
	"""Source with its prose stripped, so a guard does not read its own reasons."""
	body = ast.parse(where.read_text(encoding="utf-8"))
	for node in ast.walk(body):
		if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and ast.get_docstring(node):
			node.body = node.body[1:]
	return ast.unparse(body)


def spoken(where: Path, name: str) -> str:
	for node in ast.walk(ast.parse(where.read_text(encoding="utf-8"))):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return ast.unparse(node)
	raise AssertionError(f"{name} is not in {where.name}")


# --------------------------------------------------------- one turn, two ways


def test_a_plain_turn_is_the_same_thing_in_both_dialects():
	room = turns()
	one = room["said"]("what is on my list?")
	assert room["_openai_turn"](one) == {"role": "user", "content": "what is on my list?"}
	assert room["_gemini_turn"](one) == {
		"role": "user",
		"parts": [{"text": "what is on my list?"}],
	}


def test_a_model_asking_for_a_tool_keeps_its_arguments():
	room = turns()
	one = {
		"role": "model",
		"text": "",
		"calls": [{"id": "c1", "tool": "list_records", "args": {"doctype": "ToDo"}}],
	}

	openai = room["_openai_turn"](one)
	assert openai["role"] == "assistant"
	said = openai["tool_calls"][0]
	assert said["id"] == "c1"
	assert said["function"]["name"] == "list_records"
	# OpenAI's dialect carries the arguments as a JSON string, Google's as an
	# object, and a provider handed the other one answers as if there were none.
	assert json.loads(said["function"]["arguments"]) == {"doctype": "ToDo"}

	gemini = room["_gemini_turn"](one)
	assert gemini["role"] == "model"
	assert gemini["parts"][-1] == {"functionCall": {"name": "list_records", "args": {"doctype": "ToDo"}}}


def test_a_tool_result_goes_back_where_each_provider_looks_for_it():
	room = turns()
	one = {"role": "tool", "id": "c1", "tool": "list_records", "result": [{"name": "TODO-1"}]}

	openai = room["_openai_turn"](one)
	assert openai["role"] == "tool"
	assert openai["tool_call_id"] == "c1"
	assert json.loads(openai["content"]) == [{"name": "TODO-1"}]

	# Google has no tool role: a result is the user's next turn.
	gemini = room["_gemini_turn"](one)
	assert gemini["role"] == "user"
	answered = gemini["parts"][0]["functionResponse"]
	assert answered["name"] == "list_records"
	assert answered["response"] == {"result": [{"name": "TODO-1"}]}


@pytest.mark.parametrize(
	"arguments",
	[
		{"doctype": "ToDo", "limit": 3},
		json.dumps({"doctype": "ToDo", "limit": 3}),
	],
	ids=["an object", "a JSON string"],
)
def test_workers_ai_arguments_are_read_either_way(arguments):
	"""Measured: it has answered with both, and neither is documented as the one."""
	room = turns()
	body = {
		"result": {
			"response": "",
			"tool_calls": [{"id": "c1", "name": "list_records", "arguments": arguments}],
		}
	}
	assert room["_openai_calls"](body) == [
		{"id": "c1", "tool": "list_records", "args": {"doctype": "ToDo", "limit": 3}}
	]


def test_arguments_that_are_not_json_are_no_arguments_rather_than_a_traceback():
	room = turns()
	body = {"result": {"tool_calls": [{"name": "list_records", "arguments": "{oops"}]}}
	assert room["_openai_calls"](body) == [{"id": "list_records", "tool": "list_records", "args": {}}]


def test_a_call_with_no_name_in_it_is_dropped():
	room = turns()
	body = {"result": {"tool_calls": [{"id": "c1", "arguments": {}}]}}
	assert room["_openai_calls"](body) == []


def test_gemini_calls_and_words_come_out_of_the_same_parts():
	room = turns()
	body = {
		"candidates": [
			{
				"content": {
					"parts": [
						{"text": "looking"},
						{"functionCall": {"name": "count_records", "args": {"doctype": "ToDo"}}},
					]
				}
			}
		]
	}
	assert room["_first_part"](body) == "looking"
	assert room["_gemini_calls"](body) == [
		{
			"id": "count_records",
			"tool": "count_records",
			"args": {"doctype": "ToDo"},
			"signature": None,
		}
	]


def test_a_body_with_neither_words_nor_calls_reads_as_neither():
	"""Which is what makes `_answered` refuse rather than answer with a blank."""
	room = turns()
	assert room["_first_part"]({"candidates": []}) is None
	assert room["_gemini_calls"]({}) == []
	assert room["_openai_calls"]({}) == []


# ------------------------------------------------- who may stop the loop, and
# ------------------------------------------------- who may offer a tool at all


def test_the_rounds_are_counted_on_the_side_that_pays():
	"""Admin counts the model turns it is handed; the workspace only proposes."""
	said = spoken(ACTIONS, "_conversation")
	assert "gateway.ROUNDS" in said
	assert "raise Refused" in said
	assert "one.get('role') == 'model'" in said


def test_a_workspace_cannot_send_a_conversation_that_never_ends():
	"""The cap is in admin's module, not only in the tenant's loop."""
	assert "ROUNDS" in code(ACTIONS)


def test_tools_are_offered_only_where_the_action_says_so():
	said = spoken(ACTIONS, "run")
	assert "asked.may_use_tools" in said
	assert "tools=offered" in said


def test_a_tool_that_refuses_comes_back_as_a_result():
	"""A refusal a model can read beats a traceback where the answer was one line away."""
	said = spoken(RUN, "_tried")
	assert "except Exception" in said
	assert "'ran': False" in said
	# Read as a tree rather than as text, because the variable is called
	# `raised` and a grep for the keyword finds it.
	body = ast.parse(said).body[0]
	assert not [node for node in ast.walk(body) if isinstance(node, ast.Raise)]


def test_a_tool_answers_in_types_json_has():
	"""A date left as a date is the round that fails to serialise, not a display bug."""
	assert "_plain(answer)" in spoken(TOOLS, "run")
	plain = spoken(TOOLS, "_plain")
	for kind in ("datetime.date", "datetime.datetime", "decimal.Decimal"):
		assert kind in plain


def test_the_loop_stops_on_done_rather_than_on_a_guess():
	said = spoken(RUN, "ask")
	assert "out.get('done')" in said
	assert "rounds >= ROUNDS" in said


def test_a_model_turn_is_the_assistant_in_openais_dialect():
	"""Measured on Gemma 4: Workers AI refuses a conversation with a "model"
	turn in it, and any chat where the model spoke before a tool failed."""
	assert turns()["_openai_turn"]({"role": "model", "text": "Let me look."}) == {
		"role": "assistant",
		"content": "Let me look.",
	}


def test_an_empty_answer_is_asked_again_tool_or_no_tool():
	"""Measured on Gemma 4: asked to sort mail, it once answered nothing and
	called nothing, and the panel stayed blank. An empty answer is asked for
	again whether or not a tool was called."""
	source = (GATEWAY.parent.parent / "one_ai" / "run.py").read_text(encoding="utf-8")
	body = ast.parse(source)
	wanted = [n for n in body.body if isinstance(n, ast.FunctionDef) and n.name in ("_silent", "_used")]
	room: dict = {}
	exec(compile(ast.Module(body=wanted, type_ignores=[]), "run.py", "exec"), room)
	blank = {"turns": [{"role": "user", "text": "sort my mail"}, {"role": "model", "text": "", "calls": []}]}
	assert room["_silent"](blank, []) and not room["_used"](blank)
	answered = {"turns": [*blank["turns"][:1], {"role": "model", "text": "Done."}]}
	assert not room["_silent"](answered, [])
	assert not room["_silent"](blank, ["PROP-1"]), "a card is an answer"


def _lifted(where: Path, names: tuple, room: dict) -> dict:
	"""Named top-level functions and assignments out of a module, run alone."""
	body = ast.parse(where.read_text(encoding="utf-8"))
	wanted = [
		n
		for n in body.body
		if (isinstance(n, ast.FunctionDef) and n.name in names)
		or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in names for t in n.targets))
	]
	exec(compile(ast.Module(body=wanted, type_ignores=[]), str(where), "exec"), room)
	return room


def test_a_call_gemma_wrote_as_text_is_read_as_a_call():
	"""Measured on Gemma 4: Workers AI now and then hands its tool-call tokens
	back as the answer, and the person was shown `<|tool_call>:waiting_for_answer{...}`."""
	import re

	room = _lifted(GATEWAY, ("LEAKED", "_CALL", "_QUOTED", "_KEY", "_leaked"), {"re": re, "json": json})
	said = '<|tool_call>call:waiting_for_answer{account:<|"|>me@x.test<|"|>,folder:<|"|>Inbox, then: more<|"|>,most:5}<tool_call|>'
	wants, words = room["_leaked"](said)
	assert wants == [
		{
			"id": "waiting_for_answer-leaked-0",
			"tool": "waiting_for_answer",
			"args": {"account": "me@x.test", "folder": "Inbox, then: more", "most": 5},
		}
	]
	assert words == ""
	# Words around it stay words; a call that does not read is left alone.
	assert room["_leaked"]("Looking. <|tool_call>call:my_day{}<tool_call|>")[1] == "Looking."
	broken = "<|tool_call>call:my_day{a:<tool_call|>"
	assert room["_leaked"](broken) == ([], broken)
	# Only that syntax: free-form text is never read as a call.
	assert room["_leaked"]("call my_day {}") == ([], "call my_day {}")
	assert "LEAKED in words" in spoken(GATEWAY, "_answered")


def test_the_last_round_the_account_takes_is_told_to_answer():
	"""The account refuses a sixth model turn, and a run that reached it ended
	in that refusal. The fifth is told to answer with what it has."""
	room = _lifted(RUN, ("_spoken",), {})
	asked = [{"role": "user", "text": "q"}]
	looked = [{"role": "model", "calls": [{}]}, {"role": "tool"}]
	assert room["_spoken"](asked + looked * 4) == 4
	# A nudge is not the person speaking, and does not start the count again.
	assert room["_spoken"](asked + looked * 2 + [{"role": "user", "context": True}] + looked) == 3
	said = spoken(RUN, "ask")
	assert "_spoken(turns) >= ROUNDS - 1" in said
	assert "or last" in said


def test_a_model_the_person_picked_holds_through_a_handover():
	said = spoken(RUN, "ask")
	assert "if pinned:" in said
	assert "{**mine(action), **({'model': pinned} if pinned else {})}" in said


def test_gemmas_thinking_marker_never_reaches_the_person():
	"""Measured on Gemma 4: an answer began `:thought` on a line of its own."""
	import re

	room = _lifted(GATEWAY, ("THINKING", "CHANNEL", "_without_thinking"), {"re": re})
	clean = room["_without_thinking"]
	assert clean(":thought\nI could not add it.") == "I could not add it."
	assert clean("<|channel>thought\nweighing it<channel|>The answer.") == "The answer."
	assert clean("I thought about it.\nYes.") == "I thought about it.\nYes."


def test_extension_code_sent_on_one_line_is_read_as_its_lines():
	"""Measured on Gemma 4: a whole extension came with its line breaks
	written out as `\\n`, and the review refused it as not Python."""
	room = _lifted(tree.APP / "one_studio" / "ai.py", ("_unescaped",), {})
	assert room["_unescaped"]('if doc.x:\\n\\tfrappe.throw(\\"No\\")') == 'if doc.x:\n\tfrappe.throw("No")'
	kept = 'a = 1\nb = "x\\ny"'
	assert room["_unescaped"](kept) == kept, "code with real lines is left as written"
	assert "code=_unescaped(code)" in spoken(tree.APP / "one_studio" / "ai.py", "write_extension")


def test_an_action_with_no_tools_is_never_told_to_look_something_up():
	"""A summary carries figures and has nothing to look them up with."""
	said = spoken(RUN, "ask")
	assert "tooled and (not cards) and (not doubted)" in said
	assert "tooled and (not called) and (not doubted)" in said
	assert "tooled = _tooled(action)" in said
