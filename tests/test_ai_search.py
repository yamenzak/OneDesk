"""Search on the workspace's own AI Search instance (docs/AICENTER.md,
Search): what a workspace writes, what the account asks, and what comes back."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree  # noqa: E402

ADMIN = (tree.APP / "one_admin" / "search.py").read_text()
WORKSPACE = (tree.APP / "one_ai" / "search.py").read_text()


def _lifted(source: str, names: tuple) -> dict:
	import ast
	import json
	import re

	space = {"json": json, "re": re}
	for node in ast.parse(source).body:
		named = getattr(node.targets[0], "id", "") if isinstance(node, ast.Assign) else getattr(node, "name", "")
		if named in names:
			exec(ast.unparse(node), space)
	return space


def test_each_workspace_has_an_instance_of_its_own_name():
	space = _lifted(ADMIN, ("name_for",))
	assert space["name_for"]("Sahara Glass") == "one-sahara-glass"
	assert space["name_for"]("acme.one.app") == "one-acme-one-app"


def test_typing_searches_by_keyword_and_asking_by_meaning_reranked():
	space = _lifted(ADMIN, ("RETRIEVAL", "MOST", "body", "PRICE"))
	typed = space["body"]("gulf sealants", "keyword", 10)["ai_search_options"]
	asked = space["body"]("who sold us silicone last year", "meaning", 500)["ai_search_options"]
	assert typed["retrieval"]["retrieval_type"] == "keyword" and not typed["reranking"]["enabled"]
	assert asked["retrieval"]["retrieval_type"] == "hybrid" and asked["reranking"]["enabled"]
	assert asked["retrieval"]["max_num_results"] == space["MOST"], "no more than AI Search returns"
	assert space["PRICE"]["meaning"] > space["PRICE"]["keyword"]


def test_hits_are_keys_and_text_from_chunks():
	space = _lifted(ADMIN, ("found",))
	answer = {"result": {"chunks": [{"text": "Gulf Sealants", "score": 0.8, "item": {"key": "search/reading/R-1.md"}}, {"text": "no key"}]}}
	assert space["found"](answer) == [{"key": "search/reading/R-1.md", "text": "Gulf Sealants", "score": 0.8}]


def test_nothing_is_written_or_asked_until_the_account_says_there_is_an_instance():
	assert "if not live():\n\t\treturn" in WORKSPACE and "if not live() or not" in WORKSPACE
	assert "proxy.ai_search_state" in WORKSPACE, "asked of the account, free"
	assert "index._may(*source)" in WORKSPACE, "nothing the reader may not open is shown"
	index = (tree.APP / "one_ai" / "index.py").read_text()
	assert "found = search.find(text, doctypes, most)" in index and "if found is not None:" in index, "the vectors answer until then"
