"""Search by meaning: documents, mail and records as vectors, through the
account like every model call, and searched as the reader.

The pure parts are lifted out and run here: how text is cut, how a vector
is kept, how the nearest are found, how the words' list and the meaning's
list become one, and how each provider's answer is read."""

import array
import ast
import base64
import hashlib
import json
import math
import sys
from operator import mul
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
		("PIECE", "OVERLAP", "MOST_PIECES", "pieces", "pack", "unpack", "closest", "digest"),
		{"array": array, "base64": base64, "hashlib": hashlib, "math": math, "mul": mul},
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


def test_a_vector_is_kept_normalised_so_nearness_is_a_dot_product():
	room = _index()
	kept = room["unpack"](room["pack"]([3.0, 4.0]))
	assert abs(kept[0] - 0.6) < 1e-6 and abs(kept[1] - 0.8) < 1e-6
	query = room["unpack"](room["pack"]([1.0, 0.0]))
	rows = [(room["unpack"](room["pack"](v)), {"n": n}) for n, v in enumerate(([0.0, 1.0], [1.0, 0.1], [1.0, 1.0], [1.0]))]
	found = room["closest"](query, rows, 2)
	assert [meta["n"] for _score, meta in found] == [1, 2], "best first, and a vector of another length is skipped"


def test_the_words_and_the_meaning_are_one_list():
	room = _lifted(tree.APP / "one_intake" / "search.py", ("ranked_together",), {})
	words = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
	meaning = [{"name": "C"}, {"name": "D"}]
	said = [one["name"] for one in room["ranked_together"]([words, meaning])]
	assert said[0] == "C", "found by both is first"
	assert set(said) == {"A", "B", "C", "D"}


def test_each_provider_s_vectors_are_read_in_the_order_asked():
	body = ast.parse((tree.APP / "one_admin" / "gateway.py").read_text(encoding="utf-8"))
	node = next(n for n in body.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "EMBEDS")
	room = {"json": json}
	exec(compile(ast.Module(body=[node], type_ignores=[]), "gateway", "exec"), room)
	workers = room["EMBEDS"]["workers-ai"]
	assert workers["vectors"]({"data": [{"index": 1, "embedding": [2]}, {"index": 0, "embedding": [1]}]}) == [[1], [2]]
	assert workers["body"]("m", ["a"]) == {"model": "m", "input": ["a"]}
	google = room["EMBEDS"]["google-ai-studio"]
	assert google["vectors"]({"embeddings": [{"values": [1]}, {"values": [2]}]}) == [[1], [2]]
	assert google["path"]("text-embedding-004").endswith(":batchEmbedContents")


def test_a_search_is_checked_against_the_reader_and_costs_nothing_twice():
	source = INDEX.read_text(encoding="utf-8")
	nearest = source.split("def nearest(", 1)[1].split("\ndef ", 1)[0]
	assert "_may(*key)" in nearest, "every hit is checked against the reader"
	remember = source.split("def remember(", 1)[1].split("\ndef ", 1)[0]
	assert remember.index("digest(one)") < remember.index("embedded("), "unchanged text is never embedded again"
	assert "proxy.ai_embed" in source, "embedded through the account, billed to the workspace"
	hooks = (tree.APP / "hooks.py").read_text(encoding="utf-8")
	assert "onedesk.one_ai.index.changed" in hooks and "onedesk.one_ai.index.catch_up" in hooks
