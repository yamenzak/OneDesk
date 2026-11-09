"""Sign In to Cloudflare's address and its one-time token
(one_admin/cloudflare_signin.py)."""

import base64
import hashlib
from unittest import mock
from urllib.parse import parse_qs, urlparse

from onedesk.one_admin import cloudflare_signin as signin


def test_the_address_asks_for_a_code_with_pkce():
	link = urlparse(signin.authorize_url("id-1", "https://admin.example/back", "a.read b.write", "st", "chal"))
	query = parse_qs(link.query)
	assert f"{link.scheme}://{link.netloc}{link.path}" == signin.AUTHORIZE
	assert query["response_type"] == ["code"] and query["code_challenge_method"] == ["S256"]
	assert query["scope"] == ["a.read b.write"] and query["state"] == ["st"] and query["code_challenge"] == ["chal"]


def test_the_challenge_is_the_verifiers_hash():
	wanted = base64.urlsafe_b64encode(hashlib.sha256(b"v").digest()).rstrip(b"=").decode()
	assert signin.challenge_of("v") == wanted


def test_the_token_is_read_once():
	cache = {"one_cloudflare_signin_token": "sealed"}
	fake = mock.Mock(get_value=cache.get, delete_value=lambda key: cache.pop(key, None))
	with mock.patch.object(signin.frappe, "cache", fake), mock.patch.object(signin, "decrypt", lambda value: f"open-{value}"):
		assert signin.taken() == "open-sealed"
		assert signin.taken() is None


def test_a_run_ends_by_revoking():
	with mock.patch.object(signin, "_client", return_value=("id", "secret")), mock.patch.object(signin.requests, "post") as post:
		signin.discard("the-token")
	post.assert_called_once()
	assert post.call_args.args[0] == signin.REVOKE and post.call_args.kwargs["data"]["token"] == "the-token"
