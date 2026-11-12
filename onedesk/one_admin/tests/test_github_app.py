"""Connect GitHub's manifest, the app's JWT and the token it is exchanged for
(one_admin/github_app.py), the Actions secrets it writes, and the agent's
request for one (deploy/server/agent.py)."""

import base64
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
from nacl.public import PrivateKey, SealedBox

from onedesk.one_admin import faults, github_app, setup

AGENT = Path(__file__).resolve().parents[3] / "deploy" / "server" / "agent.py"


def _agent():
	spec = importlib.util.spec_from_file_location("one_agent_for_github", AGENT)
	agent = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(agent)
	return agent


def test_the_manifest_asks_to_read_the_code_write_secrets_and_start_workflows_and_nothing_else():
	made = github_app.manifest("One admin.example.com", "https://admin.example.com/")
	assert made["default_permissions"] == {"actions": "write", "contents": "read", "metadata": "read", "secrets": "write"}
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


def test_a_secret_is_sealed_to_the_repositorys_key():
	held = PrivateKey.generate()
	key = {"key_id": "k1", "key": base64.b64encode(bytes(held.public_key)).decode()}
	body = github_app.secret_body(key, "s3cret")
	assert body["key_id"] == "k1"
	assert SealedBox(held).decrypt(base64.b64decode(body["encrypted_value"])) == b"s3cret"
	with pytest.raises(ValueError):
		github_app.secret_body({"key_id": "k1"}, "s3cret")
	assert github_app.public_key_url("o/r") == "https://api.github.com/repos/o/r/actions/secrets/public-key"
	assert github_app.secret_url("o/r", "ONE_ADMIN_URL") == "https://api.github.com/repos/o/r/actions/secrets/ONE_ADMIN_URL"
	for wrong in ("GITHUB_TOKEN", "one", "A-B", "../x", ""):
		with pytest.raises(ValueError):
			github_app.secret_url("o/r", wrong)


class _Answer:
	def __init__(self, status: int, body: dict | None = None):
		self.status_code, self.ok, self._body, self.text = status, 200 <= status < 300, body or {}, json.dumps(body or {})

	def json(self):
		return self._body


class _Db:
	def __init__(self):
		self.defaults = {}

	def get_default(self, key):
		return self.defaults.get(key)

	def set_default(self, key, value):
		self.defaults[key] = value

	def commit(self):
		pass


def test_put_secret_mints_a_secrets_token_reads_the_key_and_puts_the_sealed_value(monkeypatch):
	held = PrivateKey.generate()
	asked, calls = [], []
	monkeypatch.setattr(github_app, "repository_token", lambda repository, permissions=None: asked.append((repository, permissions)) or {"token": "ghs_w"})
	monkeypatch.setattr(
		github_app.requests,
		"get",
		lambda url, **kw: calls.append(("GET", url, kw)) or _Answer(200, {"key_id": "k9", "key": base64.b64encode(bytes(held.public_key)).decode()}),
	)
	monkeypatch.setattr(github_app.requests, "put", lambda url, **kw: calls.append(("PUT", url, kw)) or _Answer(201))
	db = _Db()
	monkeypatch.setattr(github_app.frappe, "db", db, raising=False)
	monkeypatch.setattr(github_app.frappe.utils, "now", lambda: "2026-11-12 10:00:00")
	github_app.put_secret("CLOUDFLARE_ACCOUNT_ID", "acc", repository="o/r")
	assert asked == [("o/r", {"secrets": "write"})]
	(get, url_get, kw_get), (put, url_put, kw_put) = calls
	assert (get, url_get, put, url_put) == ("GET", "https://api.github.com/repos/o/r/actions/secrets/public-key", "PUT", "https://api.github.com/repos/o/r/actions/secrets/CLOUDFLARE_ACCOUNT_ID")
	assert kw_get["headers"]["Authorization"] == kw_put["headers"]["Authorization"] == "Bearer ghs_w"
	assert kw_put["json"]["key_id"] == "k9"
	assert SealedBox(held).decrypt(base64.b64decode(kw_put["json"]["encrypted_value"])) == b"acc"
	assert "CLOUDFLARE_ACCOUNT_ID" in json.loads(db.defaults[github_app.WRITTEN])


def test_put_secret_says_so_when_the_app_may_not_write_secrets(monkeypatch):
	def refused(repository, permissions=None):
		raise faults.Refused("not granted", status=422)

	monkeypatch.setattr(github_app, "repository_token", refused)
	monkeypatch.setattr(github_app, "_", lambda text: text)
	with pytest.raises(faults.Refused, match="Secrets: Read and write"):
		github_app.put_secret("ONE_ADMIN_URL", "https://admin.example.com")
	monkeypatch.setattr(github_app, "repository_token", lambda repository, permissions=None: {"token": "t"})
	monkeypatch.setattr(github_app.requests, "get", lambda url, **kw: _Answer(200, {"key_id": "k", "key": base64.b64encode(bytes(PrivateKey.generate().public_key)).decode()}))
	monkeypatch.setattr(github_app.requests, "put", lambda url, **kw: _Answer(403, {"message": "Resource not accessible by integration"}))
	with pytest.raises(faults.Refused, match="did not take ONE_ADMIN_URL"):
		github_app.put_secret("ONE_ADMIN_URL", "https://admin.example.com")


def test_the_images_token_may_push_containers_on_the_account_only():
	groups = [
		{"id": "a", "name": "Account Settings Read", "scopes": [setup.ACCOUNT]},
		{"id": "c", "name": "Workers Containers Write", "scopes": [setup.ACCOUNT]},
		{"id": "w", "name": "Workers Scripts Write", "scopes": [setup.ACCOUNT]},
		{"id": "z", "name": "Zone Read", "scopes": [setup.ZONE]},
	]
	wanted, missing = setup.policies(groups, setup.IMAGES_NEEDS, "acc", ["zone"], [])
	assert missing == []
	assert wanted == [{"effect": "allow", "permission_groups": [{"id": "a"}, {"id": "c"}], "resources": {f"{setup.ACCOUNT}.acc": "*"}}]
	assert setup.token_for_env(None, setup.IMAGES) == "[one-prod] OneOS Images"


def test_only_production_writes_the_repositorys_secrets(monkeypatch):
	said = []
	run = setup.Setup.__new__(setup.Setup)
	run.env = "dev"
	run.note = lambda step, state, detail="": said.append((step, state, detail))
	monkeypatch.setattr(setup, "_", lambda text: text)
	monkeypatch.setattr(github_app, "put_secret", lambda *a, **kw: pytest.fail("dev wrote a secret"))
	run.github()
	assert said == [("github", setup.THEIRS, "left to production")]


def _production_run(monkeypatch, connected=True):
	said, put = [], []
	run = setup.Setup.__new__(setup.Setup)
	run.env, run.account = None, "acc"
	run.note = lambda step, state, detail="": said.append((step, state, detail))
	run.rolled_token = lambda name, needs: f"rolled {name}"
	monkeypatch.setattr(setup, "_", lambda text: text)
	monkeypatch.setattr(github_app, "connected", lambda: connected)
	monkeypatch.setattr(github_app, "put_secret", lambda name, value, repository=None: put.append((name, value)))
	monkeypatch.setattr(github_app, "write_release", lambda: ["ONE_RELEASE_SECRET", "ONE_ADMIN_URL"])
	return run, said, put


def test_production_writes_the_account_and_the_images_token_once_github_is_connected(monkeypatch):
	run, said, put = _production_run(monkeypatch)
	run.github()
	assert put == [("CLOUDFLARE_ACCOUNT_ID", "acc"), ("CLOUDFLARE_CONTAINERS_TOKEN", f"rolled {setup.IMAGES}")]
	assert said == [("github", setup.OURS, "CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_CONTAINERS_TOKEN, ONE_RELEASE_SECRET, ONE_ADMIN_URL")]
	run, said, put = _production_run(monkeypatch, connected=False)
	run.github()
	assert put == [] and said == [("github", setup.WAITING, "Connect GitHub, then set up again.")]


def test_a_refused_secret_fails_the_github_step_only(monkeypatch):
	run, said, put = _production_run(monkeypatch)

	def refused(name, value, repository=None):
		raise faults.Refused("GitHub did not take it")

	monkeypatch.setattr(github_app, "put_secret", refused)
	with pytest.raises(setup.Refused, match="did not take it"):
		run.github()


class _Conf(dict):
	pass


def test_the_release_secret_is_made_once_and_written_with_this_sites_address(monkeypatch):
	put, kept = [], []
	conf = _Conf()
	monkeypatch.setattr(github_app.frappe, "conf", conf, raising=False)
	monkeypatch.setattr(github_app.frappe.utils, "get_url", lambda: "https://admin.example.com/", raising=False)
	monkeypatch.setattr(github_app.vault, "keep", lambda key, value: kept.append(key) or conf.__setitem__(key, value))
	monkeypatch.setattr(github_app, "put_secret", lambda name, value, repository=None: put.append((name, value)))
	assert github_app.write_release() == ["ONE_RELEASE_SECRET", "ONE_ADMIN_URL"]
	made = conf["one_release_secret"]
	assert len(made) >= 32 and kept == ["one_release_secret"]
	assert put == [("ONE_RELEASE_SECRET", made), ("ONE_ADMIN_URL", "https://admin.example.com")]
	put.clear()
	github_app.write_release()
	assert kept == ["one_release_secret"] and put[0] == ("ONE_RELEASE_SECRET", made)


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


def test_a_workflow_is_started_where_github_starts_one():
	assert github_app.dispatch_url("yamenzak/OneDesk", "oneos-image.yml") == "https://api.github.com/repos/yamenzak/OneDesk/actions/workflows/oneos-image.yml/dispatches"
	assert github_app.manifest("One admin", "https://admin.example.com")["default_permissions"]["actions"] == "write"


def test_setup_knows_an_image_the_registry_does_not_have():
	from onedesk.one_admin import setup

	assert setup.image_missing("Error: manifest unknown: registry.cloudflare.com/acc/one-os:abc")
	assert setup.image_missing("The image registry.cloudflare.com/acc/one-os:abc does not exist")
	assert not setup.image_missing("Authentication error [code: 10000]")


def test_a_bucket_keeps_its_cors_rules_once_they_are_ours():
	from onedesk.one_admin import setup

	assert setup.same_cors({"rules": setup.CORS["rules"]}, setup.CORS)
	assert not setup.same_cors({"rules": []}, setup.CORS)
	assert not setup.same_cors(None, setup.CORS)


def test_a_failed_wrangler_run_shows_its_error_before_its_configuration():
	from onedesk.one_admin import setup

	said = setup.wrangler_said('✘ [ERROR] Image registry.cloudflare.com/acc/one-os:abc does not exist\n{\n  "configuration": {\n    "image": "x"\n  }\n}')
	assert said.startswith("✘ [ERROR] Image") and "configuration" not in said
	assert setup.image_missing(said)
	assert setup.wrangler_said("plain failure") == "plain failure"
