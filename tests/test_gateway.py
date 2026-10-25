"""The provider key never leaves Cloudflare, and nothing else names a model.

Both of these are invisible when they work and expensive when they stop. A
provider key that reaches this app is a key in a backup, in a traceback and on
whatever laptop restores the site next; a model named in application code is a
model somebody has to find and change the week a provider withdraws it.

Read off the source without frappe, like the rest of this suite.
"""

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

GATEWAY = tree.APP / "one_admin" / "gateway.py"

A_PROVIDER_KEY = ("x-goog-api-key", "api_key", "?key=")


def source() -> str:
	return GATEWAY.read_text(encoding="utf-8")


def code() -> str:
	"""The source with its prose removed.

	The docstrings explain why `Authorization` is not here, so a guard that
	grepped the whole file would fail on its own reason for existing.
	"""
	body = ast.parse(source())
	for node in ast.walk(body):
		if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
			node.body = [n for n in node.body if not _is_docstring(n)]
	return ast.unparse(body)


def _is_docstring(node) -> bool:
	return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)


@pytest.mark.parametrize("said", A_PROVIDER_KEY)
def test_no_provider_key_is_ever_sent(said):
	assert said not in code(), (
		f"gateway.py sends {said}. The provider key is stored in the gateway and "
		"attached there; a key that reaches this site is a key in every backup of it."
	)


def test_the_gateway_is_authorised_by_its_own_header():
	assert 'HEADER = "cf-aig-authorization"' in source()
	assert "cf-aig-authorization" in code()


def test_authorization_carries_only_our_cloudflare_token():
	"""Cloudflare's REST endpoints take our own token as `Authorization`, with
	the gateway named beside it; nothing else ever goes in that header, and
	it never goes to a provider's address."""
	said = code()
	assert said.count("'Authorization'") == 1
	assert "headers['Authorization'] = f\"Bearer {settings['token']}\"" in said
	assert "headers[GATEWAY] = settings['gateway']" in said


def test_cloudflare_keeps_no_content():
	assert 'UNSEEN = {"cf-aig-collect-log-payload": "false"}' in source()
	assert "**UNSEEN" in code()


def test_the_settings_hold_no_provider_key():
	"""Not a field for one, either — a place to put a key is a key somebody puts."""
	import json

	spec = json.loads(
		(
			tree.APP / "one_admin" / "doctype" / "one_admin_settings" / "one_admin_settings.json"
		).read_text()
	)
	named = [
		field["fieldname"]
		for field in spec["fields"]
		if any(word in field["fieldname"] for word in ("gemini", "openai", "anthropic", "provider"))
	]
	assert not named, f"{named} would hold a provider key on this site"


def test_an_unconfigured_gateway_refuses_rather_than_falling_back():
	"""The fallback would be calling a provider directly, which is the thing."""
	assert "raise Refused(" in source()
	body = ast.parse(source())
	settings = next(
		node
		for node in ast.walk(body)
		if isinstance(node, ast.FunctionDef) and node.name == "_settings"
	)
	assert "missing" in ast.unparse(settings)


def test_only_models_py_names_a_model():
	"""Models are named in one_ai/models.py (docs/AICENTER.md, Models), and
	nowhere else: the gateway knows a Workers AI id from a Google one by its
	prefix, and nothing more."""
	import re

	named = [
		node.value
		for node in ast.walk(ast.parse(source()))
		if isinstance(node, ast.Constant)
		and isinstance(node.value, str)
		and re.match(r"(@cf|google)/\w", node.value)
	]
	assert not named, f"gateway.py names {named}; models.py does"

	elsewhere = [
		path.relative_to(tree.ROOT)
		for path in tree.sources()
		if path not in (GATEWAY, tree.APP / "one_ai" / "models.py") and re.search(r"@cf/\w", path.read_text(encoding="utf-8"))
	]
	assert not elsewhere, f"{elsewhere} name a model. Only one_ai/models.py may."

def test_a_two_hundred_with_nothing_in_it_is_not_an_empty_answer():
	"""Measured against the shape rather than a provider: treating an
	unrecognised 200 as "" is how a changed response starts returning blanks.

	Neither words nor a tool call, because a round that only asks for a tool is
	a perfectly good answer with no text in it.
	"""
	assert "answered 200 with nothing in it" in source()
	assert "words is None and (not wants)" in code()


def test_a_small_budget_is_not_spent_thinking():
	"""Measured: Gemma 4 on the chat's 800 tokens thought until "length" and
	said nothing, twice in a row. Below `THINKS` a Workers AI model is told not
	to think."""
	assert "THINKS = " in source()
	assert "if most >= THINKS else {'chat_template_kwargs': {'enable_thinking': False}}" in code()
