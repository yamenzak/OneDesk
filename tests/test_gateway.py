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

#: What a provider key looks like in code that sends one. `Authorization` is the
#: header a direct provider call uses and is exactly what the gateway exists to
#: keep us from needing; the rest are the query parameters the two providers
#: accept a key in.
A_PROVIDER_KEY = ("Authorization", "x-goog-api-key", "api_key", "?key=")


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


def test_only_one_model_is_named_and_it_is_the_first_one():
	"""An action names a capability and a workspace names a model. Until the
	catalogue exists there has to be exactly one exception, and it is here."""
	named = [
		node.value
		for node in ast.walk(ast.parse(source()))
		if isinstance(node, ast.Constant)
		and isinstance(node.value, str)
		and node.value.startswith("@cf/")
	]
	assert len(named) == 1, f"{named} — one model is named in this app, in FIRST"

	elsewhere = [
		path.relative_to(tree.ROOT)
		for path in tree.sources()
		if path != GATEWAY and "@cf/" in path.read_text(encoding="utf-8")
	]
	assert not elsewhere, f"{elsewhere} name a model. Only gateway.FIRST may."


def test_a_two_hundred_with_nothing_in_it_is_not_an_empty_answer():
	"""Measured against the shape rather than a provider: treating an
	unrecognised 200 as "" is how a changed response starts returning blanks.

	Neither words nor a tool call, because a round that only asks for a tool is
	a perfectly good answer with no text in it.
	"""
	assert "answered 200 with nothing in it" in source()
	assert "words is None and (not wants)" in code()
