"""Search by meaning: documents, mail and records as vectors, through the
account like every model call, and searched as the reader.

The pure parts are lifted out and run here: how text is cut, how a vector
is kept, how the nearest are found, how the words' list and the meaning's
list become one, and how each provider's answer is read."""

import ast
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

INDEX = tree.APP / "one_ai" / "index.py"


def _lifted(where: Path, names: tuple, room: dict) -> dict:
	body = ast.parse(where.read_text(encoding="utf-8"))
	kept = [
		node
		for node in body.body
		if (isinstance(node, ast.FunctionDef) and node.name in names)
		or (
			isinstance(node, ast.Assign)
			and any(getattr(one, "id", None) in names for t in node.targets for one in [t, *getattr(t, "elts", [])])
		)
	]
	exec(compile(ast.Module(body=kept, type_ignores=[]), str(where), "exec"), room)
	return room


def _index():
	return _lifted(
		INDEX,
		("PIECE", "OVERLAP", "MOST_PIECES", "pieces", "normal", "digest"),
		{"hashlib": hashlib, "math": math},
	)


def test_text_is_cut_into_overlapping_pieces_at_a_space():
	room = _index()
	text = " ".join(f"word{n}" for n in range(1200))
	parts = room["pieces"](text)
	assert len(parts) > 1 and all(len(one) <= room["PIECE"] for one in parts)
	assert parts[0].split()[-1] in parts[1], "a sentence cut in two is whole in one of them"
	assert not any(one.startswith(" ") or one.endswith(" ") for one in parts)
	assert room["pieces"]("") == []
	assert len(room["pieces"]("x " * 200_000)) == room["MOST_PIECES"]


def test_a_vector_is_kept_at_length_one_so_near_in_meaning_is_near():
	room = _index()
	kept = room["normal"]([3.0, 4.0])
	assert abs(kept[0] - 0.6) < 1e-6 and abs(kept[1] - 0.8) < 1e-6
	assert room["normal"]([0.0, 0.0]) == [0.0, 0.0]


def test_a_filter_on_the_index_cannot_be_broken_out_of():
	room = _lifted(tree.APP / "one_ai" / "vectors.py", ("quoted", "where", "table_name"), {})
	assert room["quoted"]("O'Brien") == "'O''Brien'"
	said = room["where"]([("Customer", "O'Brien' or 1=1 --"), ("Item", "Bolt")])
	assert said == "(source_doctype = 'Customer' and source_name = 'O''Brien'' or 1=1 --') or (source_doctype = 'Item' and source_name = 'Bolt')"
	assert room["table_name"](768) == "pieces_768"


def test_the_words_and_the_meaning_are_one_list():
	room = _lifted(tree.APP / "one_ai" / "reading" / "search.py", ("ranked_together",), {})
	words = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
	meaning = [{"name": "C"}, {"name": "D"}]
	said = [one["name"] for one in room["ranked_together"]([words, meaning])]
	assert said[0] == "C", "found by both is first"
	assert set(said) == {"A", "B", "C", "D"}


def test_vectors_come_from_one_model_and_say_which():
	"""Measured on 2026-10-25: bge-m3 on `/ai/run` answers `result.data`, one
	vector per text in the order sent, and reports its tokens under `meta`.
	Every vector a search compares came from that one model."""
	said = (tree.APP / "one_admin" / "gateway.py").read_text(encoding="utf-8").split("def embed(", 1)[1].split("\ndef ", 1)[0]
	assert 'models.pick("embed")[:1]' in said
	assert '{"text": texts}' in said and '.get("data")' in said
	assert '"model": asked[0]' in said


def test_a_search_is_checked_against_the_reader_and_costs_nothing_twice():
	source = INDEX.read_text(encoding="utf-8")
	nearest = source.split("def nearest(", 1)[1].split("\ndef ", 1)[0]
	assert "_may(*key)" in nearest, "every hit is checked against the reader"
	remember = source.split("def remember(", 1)[1].split("\ndef ", 1)[0]
	assert remember.index("digest(one)") < remember.index("embedded("), "unchanged text is never embedded again"
	assert "proxy.ai_embed" in source, "embedded through the account, billed to the workspace"
	hooks = (tree.APP / "hooks.py").read_text(encoding="utf-8")
	assert "onedesk.one_ai.index.changed" in hooks and "onedesk.one_ai.index.catch_up" in hooks
