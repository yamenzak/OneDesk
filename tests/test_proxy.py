"""The one door a tenant knocks on, guarded without a site.

Every endpoint here is `allow_guest`, because the caller is a machine with a
bearer token rather than a person with a session. That makes Frappe's own
authentication not-in-the-path and ours load-bearing, so the things that would
quietly turn it off are held here.
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

PROXY = tree.APP / "one_admin" / "proxy.py"


def _module() -> ast.Module:
	return ast.parse(PROXY.read_text(encoding="utf-8"))


def _guest_endpoints() -> list[ast.FunctionDef]:
	found = []
	for node in _module().body:
		if not isinstance(node, ast.FunctionDef):
			continue
		for decorator in node.decorator_list:
			text = ast.unparse(decorator)
			if "whitelist" in text and "allow_guest=True" in text:
				found.append(node)
	return found


def _calls(node: ast.FunctionDef) -> set[str]:
	return {
		child.func.id
		for child in ast.walk(node)
		if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
	}


def test_there_is_an_endpoint_to_guard():
	assert _guest_endpoints()


def test_every_guest_endpoint_asks_who_is_calling():
	for node in _guest_endpoints():
		assert "caller" in _calls(node), (
			f"{node.name} is allow_guest and never calls caller(). That is an "
			"endpoint anybody on the internet may run."
		)


def test_every_guest_endpoint_is_rate_limited():
	for node in _guest_endpoints():
		limited = any("rate_limit" in ast.unparse(d) for d in node.decorator_list)
		assert limited, f"{node.name} is allow_guest and has no rate limit"


def test_the_token_is_compared_in_constant_time():
	source = PROXY.read_text(encoding="utf-8")
	assert "hmac.compare_digest" in source
	assert "token_hash ==" not in source, "a plain == on a secret leaks its prefix by timing"


def test_the_token_does_not_travel_in_the_authorization_header():
	"""Measured, not reasoned.

	Frappe's own `validate_auth_via_api_keys` reads `Authorization`, sees the
	word token and splits the rest on a colon into an API key and secret. A
	token of ours has no colon, so every call died with
	`InvalidAuthorizationToken` before reaching this module. Anybody tidying
	`X-One-Token` back to the conventional header would reintroduce that, and
	the symptom is every tenant losing its account at once.
	"""
	source = PROXY.read_text(encoding="utf-8")
	assert 'HEADER = "X-One-Token"' in source
	assert 'get_request_header("Authorization")' not in source


def test_every_way_of_being_wrong_says_the_same_thing():
	"""One refusal, so a caller who guessed a slug is not told they guessed it."""
	source = PROXY.read_text(encoding="utf-8")
	refusals = source.count("_refuse()")
	assert refusals >= 4, "each failing branch should end at the same _refuse()"
	assert source.count("AuthenticationError") == 1


def test_nothing_here_carries_bytes():
	"""Admin signs and records; R2 and Cloudflare carry."""
	source = PROXY.read_text(encoding="utf-8")
	for carrying in ("open(", "read()", "files=", "send_file"):
		assert carrying not in source, f"proxy.py does {carrying} — a file must never pass through admin"


def test_no_endpoint_takes_a_bucket_or_a_prefix_from_the_caller():
	"""A caller names a suffix. Everything else is worked out here.

	An endpoint taking `bucket` or `prefix` would let a workspace address
	somebody else's objects directly, which is the one thing the key rules
	exist to prevent.
	"""
	for node in _guest_endpoints():
		args = {a.arg for a in node.args.args}
		assert not (args & {"bucket", "prefix", "full_key", "path"}), (
			f"{node.name} takes {sorted(args)} — a caller must not name where"
		)


def test_every_signed_url_is_scoped_by_the_key_rules():
	"""`storage.py` must never build a key by concatenation."""
	source = (tree.APP / "one_admin" / "storage.py").read_text(encoding="utf-8")
	assert source.count("keys.under(") >= 3, "each of put, get and delete scopes its key"
	assert 'Key": key' not in source, "a raw caller key must never reach R2"
