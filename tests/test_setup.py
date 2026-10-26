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
	assert set(writes) <= {"cloudflare_setup", "cloudflare_deployed", "r2_secret"}
	assert "if self.settings.r2_key_id:" in _method("r2_keys")


def test_somebody_elses_record_or_route_is_left_as_it_is():
	assert "THEIRS" in _method("dns") and "THEIRS" in _method("route")
	puts = re.findall(r'self\.call\(\s*"PUT",\s*f"([^"]+)"', SOURCE)
	assert puts == [
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
	space = {}
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
