"""OneAdmin's Set up Cloudflare: one key, everything found or made, nothing
of anybody else's taken."""

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SETUP = tree.APP / "one_admin" / "setup.py"
SOURCE = SETUP.read_text()
MAIL = tree.ROOT / "deploy" / "mail" / "worker.js"


def _method(name: str) -> str:
	for node in ast.walk(ast.parse(SOURCE)):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return ast.unparse(node)
	raise AssertionError(name)


def test_nothing_is_ever_deleted():
	assert '"DELETE"' not in SOURCE and "'DELETE'" not in SOURCE


def test_a_setting_already_filled_in_is_never_replaced():
	keep = _method("keep")
	assert "if value and (not self.settings.get(field))" in keep
	writes = re.findall(r"self\.settings\.(\w+) = ", SOURCE)
	assert not writes, "settings are written through keep() or own(), each saved at once"
	assert "frappe.db.commit()" in keep and "frappe.db.commit()" in _method("own")


def test_somebody_elses_record_or_route_is_left_as_it_is():
	assert "THEIRS" in _method("dns") and "THEIRS" in _method("route")
	puts = re.findall(r'self\.call\(\s*"PUT",\s*f"([^"]+)"', SOURCE)
	assert puts == [
		"/user/tokens/{held['id']}/value",
		"/user/tokens/{held['id']}",
		"/zones/{zone}/custom_hostnames/fallback_origin",
		"/zones/{zone}/email/routing/rules/catch_all",
		"{base}/{name}",
		"/accounts/{self.account}/workers/scripts/{name}",
	]
	custom = _method("custom_hostnames")
	assert custom.index("if held.get('origin'):") < custom.index("'PUT'"), "a held fallback origin is kept"


def test_our_workers_are_the_repositorys_code_and_redeploy_when_it_changes():
	deploy = _method("deploy")
	assert "hashlib.sha256" in deploy and "held.get(name) == wanted" in deploy
	assert 'DEPLOY / "edge" / "worker.js"' in SOURCE and 'DEPLOY / "mail" / "worker.js"' in SOURCE


def test_only_the_operator_may_press_it():
	assert "frappe.only_for(site.OPERATOR)" in _method("set_up")


def test_the_mail_worker_refuses_what_is_not_ours_and_stores_before_telling():
	js = MAIL.read_text()
	assert "host !== env.MAIL_DOMAIN" in js and 'setReject("No such address.")' in js
	assert js.index("await bucket.put(") < js.index("ctx.waitUntil(")
	assert "`${at}.${notice}`" in js, "the signature covers the notice's exact bytes"
	assert "bare.lastIndexOf(\".\")" in js, "the slug is after the last dot"


def test_the_workspace_certificate_is_ordered_once():
	"""`*.t.4dl.app` is two labels down, which the zone's free certificate does
	not cover. A pack that names both hosts, issued or pending, is kept."""
	certificate = _method("certificate")
	assert certificate.index("certificate_packs'") < certificate.index("certificate_packs/order")
	assert "'status': 'all'" in certificate and "wanted <= set(" in certificate
	assert "'type': 'advanced'" in certificate and "f'*.{domain}'" in certificate
	assert "self.certificate," in SOURCE


def _lifted(names: tuple) -> dict:
	import json

	space = {"json": json}
	for node in ast.parse(SOURCE).body:
		named = getattr(node.targets[0], "id", "") if isinstance(node, ast.Assign) else getattr(node, "name", "")
		if named in names:
			exec(ast.unparse(node), space)
	return space


def test_the_ai_gateway_keeps_what_it_holds_and_flags_on_every_call():
	"""Set up Cloudflare finds or makes the AI gateway and turns its
	Guardrails on, flagging, never blocking; what the gateway already holds
	is left as it is."""
	space = _lifted(("FLAGGED", "GUARDRAILS", "KEPT", "guarded"))
	made = space["guarded"]({"id": "one"})
	assert made["id"] == "one" and made["collect_logs"] is True and made["cache_ttl"] == 0
	assert made["guardrails"]["prompt"]["P1"] == "FLAG" and "P1" not in made["guardrails"]["response"]
	assert set(made["guardrails"]["prompt"].values()) == set(made["guardrails"]["response"].values()) == {"FLAG"}
	assert len(made["guardrails"]["response"]) == 13
	held = space["guarded"]({"id": "one", "cache_ttl": 300, "rate_limiting_limit": 50, "authentication": True, "created_at": "x"})
	assert held["cache_ttl"] == 300 and held["rate_limiting_limit"] == 50 and held["authentication"] is True
	assert "created_at" not in held, "only what the update takes is sent back"
	assert "self.ai_gateway," in SOURCE and "self.keep('ai_gateway', name)" in _method("ai_gateway")


def test_one_s_tokens_are_allowed_only_what_was_found():
	"""Before the account and zone are known, OneAdmin may reach any of them;
	after, only those. OneAdmin Storage reaches only the two buckets. A name
	Cloudflare does not have is said, unless it is a * name."""
	space = _lifted(("ACCOUNT", "ZONE", "BUCKET", "TOKENS", "named", "plain", "policies", "same"))
	groups = [
		{"id": "a", "name": "Workers Scripts Write", "scopes": ["com.cloudflare.api.account"]},
		{"id": "z", "name": "DNS Write", "scopes": ["com.cloudflare.api.account.zone"]},
		{"id": "b", "name": "Workers R2 Storage Bucket Item Write", "scopes": ["com.cloudflare.edge.r2.bucket"]},
		{"id": "r", "name": "Email Sending Read", "scopes": ["com.cloudflare.api.account"]},
	]
	needs = (("Workers Scripts Write",), ("DNS Write", "DNS Edit"), ("Zone Read",), ("Email Sending*",))
	early, missing = space["policies"](groups, needs, None, None, [])
	assert missing == ["Zone Read"], "a * name with only a Read permission is left out quietly"
	assert {key for one in early for key in one["resources"]} == {"com.cloudflare.api.account.*", "com.cloudflare.api.account.zone.*"}
	late, _ = space["policies"](groups, needs, "acc", "zone", [])
	assert {key for one in late for key in one["resources"]} == {"com.cloudflare.api.account.acc", "com.cloudflare.api.account.zone.zone"}
	assert not space["same"](early, late) and space["same"](late, list(reversed(late)))
	storage, _ = space["policies"](groups, space["TOKENS"]["OneAdmin Storage"][1], "acc", "zone", [("default", "one-global"), ("eu", "one-eu")])
	assert storage == [{"effect": "allow", "permission_groups": [{"id": "b"}], "resources": {"com.cloudflare.edge.r2.bucket.acc_default_one-global": "*", "com.cloudflare.edge.r2.bucket.acc_eu_one-eu": "*"}}]


def test_a_role_scoped_to_single_resources_is_never_asked_for():
	"""Cloudflare lists roles scoped to single resources beside its
	permissions, some under the same name, and refuses a user token that
	holds one ("User tokens cannot reference roles with granular resource
	scopes"). Only a permission on the account, a zone or a bucket is taken."""
	space = _lifted(("ACCOUNT", "ZONE", "BUCKET", "named", "plain", "policies"))
	groups = [
		{"id": "role", "name": "DNS Write", "scopes": ["com.cloudflare.api.account.zone.dns_record"]},
		{"id": "z", "name": "DNS Write", "scopes": ["com.cloudflare.api.account.zone"]},
		{"id": "none", "name": "Email Sending Admin", "scopes": []},
	]
	made, missing = space["policies"](groups, (("DNS Write",), ("Email Sending*",)), "acc", "zone", [])
	assert made == [{"effect": "allow", "permission_groups": [{"id": "z"}], "resources": {"com.cloudflare.api.account.zone.zone": "*"}}]
	assert missing == []


def test_a_token_whose_secret_was_lost_is_rolled_not_made_again():
	ensure = _method("ensure_token")
	assert ensure.index("held_tokens()") < ensure.index("'POST', '/user/tokens'"), "looked for by name before anything is made"
	assert "/value" in ensure and "self.verified(value) != held['id']" in ensure
	assert ensure.index("self.store(") < ensure.index("self.note("), "a secret is saved before the step is said done"
	assert "token=self.master" in _method("permission_groups") and "token=self.master" in _method("held_tokens")


def test_one_run_at_a_time_in_the_background():
	assert "frappe.enqueue(" in _method("set_up") and "deduplicate=True" in _method("set_up")
	assert "nx=True" in _method("run") and "frappe.cache.delete(key)" in _method("run")


def test_advanced_certificate_manager_is_checked_before_ordering():
	space = _lifted(("acm",))
	assert space["acm"](None) and space["acm"]({"advanced": {"allocated": 1}})
	assert not space["acm"]({"advanced": {"allocated": 0}})
	certificate = _method("certificate")
	assert certificate.index("acm(") < certificate.index("certificate_packs/order")


def test_a_new_token_is_waited_for_and_the_workers_wait_for_kv():
	"""Cloudflare answers Authentication error for a few seconds after a
	token is made, and a Worker bound to no KV namespace is refused; so the
	first account call is retried and the Workers wait for the namespace."""
	patiently = _method("patiently")
	assert "Authentication error" in patiently and "time.sleep(wait)" in patiently
	assert "self.patiently(" in _method("kv")
	for step in ("router", "mailer"):
		body = _method(step)
		assert body.index("if not self.settings.cloudflare_kv") < body.index("self.deploy(")


def test_another_environment_names_everything_it_makes_and_brings_its_own_domains():
	"""A second OneAdmin on the same account (dev) never shares a Worker, a
	KV, a bucket, a gateway or a token with production: each carries the
	environment in its name. Production, with Environment empty, keeps the
	names it has always had, and only production has the 4dl.app defaults."""
	space = _lifted(("for_env", "token_for_env", "within"))
	assert space["for_env"](None, "one-mail") == "one-mail" and space["for_env"]("dev", "one-mail") == "one-mail-dev"
	assert space["token_for_env"](None, "OneAI") == "[one-prod] OneAI" and space["token_for_env"]("dev", "OneAI") == "[one-dev] OneAI"
	zones = [{"name": "4dl.app"}, {"name": "4dl.dev"}]
	assert space["within"](zones, "d.4dl.app")["name"] == "4dl.app" and space["within"](zones, "m.4dl.dev")["name"] == "4dl.dev"
	assert space["within"](zones, "4dl.com") is None
	init = _method("__init__")
	for made in ("KV_TITLE", "ROUTER", "MAILER"):
		assert f"for_env(self.env, {made})" in init
	assert "for_env(self.env, GATEWAY)" in _method("ai_gateway") and "for_env(self.env, default)" in _method("buckets")
	assert "token_for_env(self.env, name)" in _method("ensure_token")
	zone = _method("find_zone")
	assert "None if self.env else 't.4dl.app'" in zone and "None if self.env else 'm.4dl.app'" in zone
	assert "'' if self.env else 'noreply@4dl.app'" in _method("sender")
	assert "KV_TITLE" not in _method("kv") and "self.router_name" in _method("router") and "self.mailer_name" in _method("mailer")


def test_the_mail_zone_is_its_own_and_another_workers_catch_all_is_left_alone():
	"""Email Routing's catch-all belongs to a whole zone: setup takes mail
	in on the mail domain's zone, and leaves a catch-all that already hands
	mail to another Worker as it is."""
	for step in ("mail_routing", "catch_all", "mail_sending"):
		assert 'self.mail_zone["id"]' in _method(step).replace("'", '"')
	catch = _method("catch_all")
	assert catch.index("THEIRS") < catch.index("'PUT'")
	space = _lifted(("ACCOUNT", "ZONE", "BUCKET", "named", "plain", "policies"))
	groups = [{"id": "z", "name": "DNS Write", "scopes": ["com.cloudflare.api.account.zone"]}]
	both, _ = space["policies"](groups, (("DNS Write",),), "acc", ["app", "dev"], [])
	assert set(both[0]["resources"]) == {"com.cloudflare.api.account.zone.app", "com.cloudflare.api.account.zone.dev"}


def test_production_s_first_tokens_are_renamed_not_made_again():
	"""Production's tokens were made under bare names (OneAdmin, OneAI,
	OneAdmin Storage). Found by that name when the labelled one is not
	there, they are renamed in place; another environment never takes them."""
	ensure = _method("ensure_token")
	assert "None if self.env else next((one for one in tokens if one['name'] == name), None)" in ensure
	assert "held.get('name') != called" in ensure


def test_a_storage_token_with_no_secret_kept_is_rolled():
	"""The storage token's secret is kept only as its hash. A run that saved
	the id and not the secret would otherwise read as held for ever, and
	OneAdmin would say no file can be kept on every run after."""
	ensure = _method("ensure_token")
	assert "self.settings.r2_key_id == held['id'] and vault.get('r2_secret')" in ensure
