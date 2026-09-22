"""What the stand-in could not have told us, guarded so it stays fixed.

Every rule in this file was found by calling the real providers with real
credentials, and every one of them was invisible against a stand-in that
answered in whatever shape the stand-in was written to answer in. The samples
are the providers' own bodies, kept so the readers can be exercised without a
key and without a bill.
"""

import ast
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

GATEWAY = tree.APP / "one_admin" / "gateway.py"
SCHEMA = tree.APP / "one_ai" / "schema.py"
FAULTS = tree.APP / "one_admin" / "faults.py"
PROXY = tree.APP / "one_admin" / "proxy.py"
CATALOGUE = tree.APP / "one_admin" / "catalogue.py"
MODEL = tree.APP / "one_admin" / "doctype" / "ai_model" / "ai_model.py"
METER = tree.APP / "one_admin" / "meter.py"

#: The two readers, lifted out of `gateway.py` — they touch nothing but `json`.
LIFTED = ("_workers_ai_said", "_openai_calls", "_gemini_calls", "_gemini_turn")


def readers():
	body = ast.parse(GATEWAY.read_text(encoding="utf-8"))
	wanted = [n for n in body.body if isinstance(n, ast.FunctionDef) and n.name in LIFTED]
	assert len(wanted) == len(LIFTED), "a reader was renamed and this guard was not"
	room: dict = {"json": json}
	exec(compile(ast.Module(body=wanted, type_ignores=[]), str(GATEWAY), "exec"), room)
	return room


def spoken(where: Path, name: str) -> str:
	for node in ast.walk(ast.parse(where.read_text(encoding="utf-8"))):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return ast.unparse(node)
	raise AssertionError(f"{name} is not in {where.name}")


# ------------------------------------------- Workers AI answers in two shapes


def test_the_classic_shape_is_read():
	"""`result.response` — llama, mistral, the older text-generation models."""
	assert readers()["_workers_ai_said"]({"result": {"response": "hello"}}) == "hello"


def test_the_openai_shape_is_read():
	"""`result.choices[].message.content` — gpt-oss, gemma-4, qwen3, glm.

	Measured against the real API: gemma-4 answers only in this shape, and
	before this was read every call to it raised "answered 200 with nothing in
	it" while the model had in fact answered.
	"""
	body = {"result": {"choices": [{"message": {"role": "assistant", "content": "hello"}}]}}
	assert readers()["_workers_ai_said"](body) == "hello"


def test_thinking_out_loud_is_not_an_answer():
	"""gemma-4 and gpt-oss put reasoning in `reasoning_content`.

	Showing it would be showing somebody working notes and calling them a reply,
	so an empty `content` beside a full `reasoning_content` reads as empty.
	"""
	body = {"result": {"choices": [{"message": {"content": "", "reasoning_content": "The user said hi."}}]}}
	assert readers()["_workers_ai_said"](body) == ""


def test_a_reasoning_model_that_says_nothing_has_still_answered():
	"""gemma-4 given a small budget spends it on `reasoning_content` and omits
	`content` altogether. That is the model saying nothing, not a shape nobody
	has seen — and the difference decides whether a paid call raises."""
	room = readers()
	spent = {"choices": [{"finish_reason": "length", "message": {"reasoning_content": "hm"}}]}
	assert room["_workers_ai_said"](spent) == ""
	# A body with no choices at all is still unreadable, which is the case the
	# guard in `_answered` exists for.
	assert room["_workers_ai_said"]({"oops": True}) is None


def test_the_gateway_answers_without_a_result_wrapper():
	"""Cloudflare's OpenAI-compatible endpoint puts `choices` and `usage` at the
	top level; `/ai/run` wraps both in `result`. Reading one shape only is a
	call that answers fine and bills its hold because nothing was metered."""
	room = readers()
	assert room["_workers_ai_said"]({"choices": [{"message": {"content": "hi"}}]}) == "hi"
	assert "body or {}" in spoken(METER, "_workers_ai")


def test_workers_ai_goes_through_the_gateways_own_path():
	"""Measured: the direct API's per-model path answers 401 *through the
	gateway* with a token that works on the direct API — which reads as a
	credential problem and is a path problem."""
	source = GATEWAY.read_text(encoding="utf-8")
	assert '"path": lambda model: "v1/chat/completions"' in source
	assert '"model": model,' in source, "the model has to travel in the body now"


def test_a_tool_call_is_found_in_either_shape():
	said = readers()["_openai_calls"]
	classic = {"result": {"tool_calls": [{"id": "c1", "name": "count_records", "arguments": {"doctype": "ToDo"}}]}}
	openai = {
		"result": {
			"choices": [
				{"message": {"tool_calls": [{"id": "c1", "function": {"name": "count_records", "arguments": '{"doctype": "ToDo"}'}}]}}
			]
		}
	}
	for body in (classic, openai):
		assert said(body) == [{"id": "c1", "tool": "count_records", "args": {"doctype": "ToDo"}}]


# --------------------------------------------- Google is stricter about schema


def test_an_array_parameter_declares_what_is_in_it():
	"""Measured: gemini-2.5-flash-lite answers 400 with
	`properties[fields].items: missing field` for an array with no `items`.
	OpenAI's dialect accepts it, so the stricter reading is the one written."""
	said = spoken(SCHEMA, "_typed")
	assert "'array'" in said and "'items'" in said


def test_function_calling_asks_for_the_version_that_has_it():
	"""Google answers v1 with "Function calling is not enabled for api version
	v1", and the catalogue already lists from v1beta — one version for both."""
	source = GATEWAY.read_text(encoding="utf-8")
	assert "v1beta/models/{model}:generateContent" in source
	assert "v1/models/{model}:generateContent" not in source.replace("v1beta/models", "")


def test_gemini_threes_thought_signature_is_carried_back():
	"""Gemini 3 answers a functionCall with a `thoughtSignature` and refuses the
	next request without it: "Function call is missing a thought_signature in
	functionCall parts". 2.5 sends none and needs none, so it is carried when
	there is one and left off when there is not."""
	room = readers()
	body = {
		"candidates": [
			{
				"content": {
					"parts": [
						{
							"functionCall": {"name": "count_records", "args": {"doctype": "ToDo"}, "id": "call_1"},
							"thoughtSignature": "EuIDCt8D",
						}
					]
				}
			}
		]
	}
	asked = room["_gemini_calls"](body)
	assert asked == [
		{"id": "call_1", "tool": "count_records", "args": {"doctype": "ToDo"}, "signature": "EuIDCt8D"}
	]

	back = room["_gemini_turn"]({"role": "model", "text": "", "calls": asked})
	assert back["parts"][0]["thoughtSignature"] == "EuIDCt8D"

	# And nothing invented where the model sent none.
	asked[0]["signature"] = None
	assert "thoughtSignature" not in room["_gemini_turn"]({"role": "model", "calls": asked})["parts"][0]


# ------------------------------------------ a refusal keeps its name and words


def test_the_other_sides_exception_type_wins_over_the_status():
	"""Frappe answers every thrown exception with a 500, so a permanent refusal
	arrives looking like a server having a bad moment and gets retried for ever."""
	said = spoken(FAULTS, "raised")
	assert "said" in said
	assert "'Refused'" in said and "'Again'" in said


def test_the_proxy_throws_rather_than_letting_a_fault_propagate():
	"""An unhandled exception's body carries `exc_type` and nothing else, so the
	sentence saying why never reaches the workspace."""
	said = spoken(PROXY, "ai_run")
	assert "faults.Refused" in said
	assert "frappe.throw" in said


# ------------------------------- a provider may reclassify or drop a model


def test_a_withdrawn_model_lets_go_of_its_default():
	"""Cloudflare dropped llama-3.1-8b-fp8-fast while it was the default, and
	every attempt to name a replacement was refused by a row for a model that
	no longer exists."""
	assert "'default_for': None" in spoken(CATALOGUE, "_withdraw")
	assert "'status': ['!=', 'Withdrawn']" in spoken(MODEL, "validate")


def test_a_reclassified_model_loses_a_default_it_can_no_longer_do():
	"""Cloudflare moved llama-3.2-11b-vision from Vision to Text Generation, and
	the validation that refused it stopped the whole nightly sync."""
	said = spoken(CATALOGUE, "_write")
	assert "capability.able" in said
	assert "model.default_for = None" in said
