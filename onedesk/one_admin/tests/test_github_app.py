"""Connect GitHub's manifest, the app's JWT and the token it is exchanged for
(one_admin/github_app.py), and the agent's request for one (deploy/server/agent.py)."""

import hashlib
import hmac
import importlib.util
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from onedesk.one_admin import github_app

AGENT = Path(__file__).resolve().parents[3] / "deploy" / "server" / "agent.py"


def _agent():
	spec = importlib.util.spec_from_file_location("one_agent_for_github", AGENT)
	agent = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(agent)
	return agent


def test_the_manifest_asks_to_read_the_code_and_nothing_else():
	made = github_app.manifest("One admin.example.com", "https://admin.example.com/")
	assert made["default_permissions"] == {"contents": "read", "metadata": "read"}
	assert made["default_events"] == [] and made["hook_attributes"]["active"] is False and made["public"] is False
	assert made["url"] == "https://admin.example.com"
	assert made["redirect_url"] == f"https://admin.example.com/api/method/{github_app.RETURN_TO}"
	assert made["setup_url"] == f"https://admin.example.com/api/method/{github_app.INSTALLED}"


def test_the_name_fits_githubs_limit():
	assert github_app.name_for("admin.4dl.app") == "One admin.4dl.app"
	assert len(github_app.name_for("a-very-long-admin-host.somewhere.example.com")) <= github_app.NAME_LONGEST


def test_the_manifest_goes_to_github_with_its_state_and_comes_back_as_an_app():
	link = urlparse(github_app.new_app_url("st"))
	assert f"{link.scheme}://{link.netloc}{link.path}" == "https://github.com/settings/apps/new"
	assert parse_qs(link.query)["state"] == ["st"]
	assert github_app.conversion_url("abc_12-3") == "https://api.github.com/app-manifests/abc_12-3/conversions"
	with pytest.raises(ValueError):
		github_app.conversion_url("../app")
	made = github_app.made_of({"id": 42, "slug": "one-admin", "name": "One admin", "pem": "PEM", "webhook_secret": None, "client_secret": "cs"})
	assert made == {"shown": {"github_app_name": "One admin", "github_app_slug": "one-admin", "github_app_id": "42"}, "private_key": "PEM"}
	with pytest.raises(ValueError):
		github_app.made_of({"id": 42, "slug": "one-admin"})
	assert github_app.install_url("one-admin") == "https://github.com/apps/one-admin/installations/new"


def test_the_jwt_is_signed_rs256_for_the_app_and_lasts_under_ten_minutes():
	key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
	pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()).decode()
	token = github_app.app_jwt("42", pem, now=1_000_000)
	assert jwt.get_unverified_header(token)["alg"] == "RS256"
	said = jwt.decode(token, key.public_key(), algorithms=["RS256"], options={"verify_exp": False, "verify_iat": False})
	assert said == {"iat": 999_940, "exp": 1_000_540, "iss": "42"}
	assert said["exp"] - said["iat"] <= 600


def test_the_token_reads_one_repository_only():
	url, body = github_app.token_asked("77", "yamenzak/onedesk")
	assert url == "https://api.github.com/app/installations/77/access_tokens"
	assert body == {"repositories": ["onedesk"], "permissions": {"contents": "read"}}
	assert github_app.installation_url("yamenzak/onedesk") == "https://api.github.com/repos/yamenzak/onedesk/installation"
	assert github_app.headers("j")["Authorization"] == "Bearer j"
	assert github_app.token_of({"token": "ghs_x", "expires_at": "2026-11-11T13:00:00Z", "permissions": {}}) == {"token": "ghs_x", "expires_at": "2026-11-11T13:00:00Z"}
	with pytest.raises(ValueError):
		github_app.token_of({"message": "Bad credentials"})


def test_a_box_is_believed_only_within_five_minutes():
	assert github_app.fresh(1000, 1200)
	assert not github_app.fresh(1000, 1400)
	assert not github_app.fresh("1000", 1000)
	assert not github_app.fresh(None, 1000)


def test_the_agent_signs_its_request_as_oneadmin_checks_it():
	from onedesk.one_admin.servers import signed

	agent = _agent()
	url, body, headers = agent.token_asked({"server": "one-1", "secret": "s3", "admin_url": "https://admin.example.com/"}, 1234)
	assert url == "https://admin.example.com/api/method/onedesk.one_admin.github_app.for_box"
	assert json.loads(body) == {"server": "one-1", "at": 1234}
	assert headers["X-One-Agent"] == signed("s3", body) == hmac.new(b"s3", body.encode(), hashlib.sha256).hexdigest()


def test_the_agent_falls_back_to_the_token_it_was_given():
	agent = _agent()
	assert agent.github_token({"server": "one-1", "secret": "", "admin_url": "", "github_token": "given"}) == "given"
	assert json.loads(agent.git_info("t"))["token"] == "t"
