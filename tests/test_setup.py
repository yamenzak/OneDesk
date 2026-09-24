"""One Admin's Set up Cloudflare: one key, everything found or made, nothing
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
	# Every write to a setting goes through keep, but for the two that are
	# kept by their own guard: the deployed hashes, and the R2 secret, which
	# is written only when its key id was empty.
	writes = re.findall(r"self\.settings\.(\w+) = ", SOURCE)
	assert set(writes) <= {"cloudflare_setup", "cloudflare_deployed", "r2_secret"}
	assert "if self.settings.r2_key_id:" in _method("r2_keys")


def test_somebody_elses_record_or_route_is_left_as_it_is():
	assert "THEIRS" in _method("dns") and "THEIRS" in _method("route")
	# The catch-all is the one thing taken over, and it is the only PUT on a
	# zone setting.
	puts = re.findall(r'self\.call\(\s*"PUT",\s*f"([^"]+)"', SOURCE)
	assert puts == ["/zones/{zone}/email/routing/rules/catch_all", "/accounts/{self.account}/workers/scripts/{name}"]


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
