"""Test workspaces (one_admin/testbed.py): never billed, never moved or
updated by OneAdmin, linked by a block link.sh writes into a site's config.
OneAdmin's side is read here, as it runs on the admin site; link.sh is run
against a stand-in bench."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tree

from onedesk.one_admin import testbed

ADMIN = tree.APP / "one_admin"
LINK = tree.ROOT / "deploy" / "local" / "link.sh"
BACKUP = {"one_backup_secret": "b-secret", "one_keeper_url": "https://one-keeper.4dl.workers.dev"}


def _body(name: str, source: str) -> str:
	return source.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def _block() -> dict:
	return testbed.block("https://admin.4dl.app", "one-4dl-dev", "t-secret", "m-secret", "m.4dl.app", BACKUP, 104857600)


def test_the_slug_is_the_address_with_hyphens():
	assert testbed.slug_for("https://One.4dl.dev/app") == "one-4dl-dev"
	with pytest.raises(ValueError):
		testbed.slug_for("a-very-long-name-for-a-test-workspace.example.com")


def test_the_block_is_what_push_config_gives_a_workspace():
	steps = (ADMIN / "steps.py").read_text()
	pushed = _body("push_config", steps)
	for key in _block():
		assert f'"{key}"' in pushed, key
	assert set(_block()) == set(json.loads(LINK.read_text().split("KEYS='", 1)[1].split("'", 1)[0]))


def test_only_an_operator_makes_one_and_it_is_never_on_a_server():
	new = _body("new", (ADMIN / "testbed.py").read_text())
	assert "frappe.only_for(site.OPERATOR)" in new and "site.require_admin()" in new
	assert '"is_test": 1' in new and '"server"' not in new and '"jurisdiction": "Global"' in new
	assert '"credits_a_month": 0' in new and 'order_by="amount desc"' in (ADMIN / "testbed.py").read_text()
	assert "backups.given(slug)" in new and "cloudflare.mail_route(slug" in new
	tenant = json.loads((ADMIN / "doctype" / "tenant" / "tenant.json").read_text())
	field = {f["fieldname"]: f for f in tenant["fields"]}["is_test"]
	assert field["read_only"] and field["label"] == "Test Workspace"
	assert "onedesk.one_admin.testbed.new" in (ADMIN / "doctype" / "tenant" / "tenant_list.js").read_text()


@pytest.mark.parametrize(
	("file", "function", "why"),
	[
		("runner.py", "start", "moved"),
		("lifecycle.py", "fall", "moved"),
		("releases.py", "update_now", "updated"),
		("billing.py", "take", "billed"),
		("billing.py", "portal", "billed"),
		("billing.py", "card", "billed"),
		("topup.py", "buy", "billed"),
		("topup.py", "keep_settings", "billed"),
	],
)
def test_oneadmin_never_moves_updates_or_bills_one(file, function, why):
	assert f'testbed.refuse(tenant, "{why}")' in _body(function, (ADMIN / file).read_text())


def test_no_job_grants_mails_or_counts_one():
	assert '"is_test": 0' in _body("monthly", (ADMIN / "topup.py").read_text())
	assert '"is_test": 0' in _body("trials_ending", (ADMIN / "tell.py").read_text())
	assert "doc.is_test or not wants_a_pack(" in _body("charge", (ADMIN / "topup.py").read_text())
	assert 'tenant.get("is_test")' in _body("paid", (ADMIN / "lifecycle.py").read_text())
	assert "tenant.is_test" in _body("ask", (ADMIN / "closing.py").read_text())
	assert '"live": ("Tenant", {"status": "Live", "is_house": 0, "is_test": 0})' in (ADMIN / "home.py").read_text()
	for file in ("earnings.py", "console.py", "rollout.py", "metrics.py"):
		assert '"is_test": 0' in (ADMIN / file).read_text(), file


def test_backups_and_health_still_count_one():
	backups = (ADMIN / "backups.py").read_text()
	health = (ADMIN / "health.py").read_text()
	assert "is_test" not in backups.split("def nightly(", 1)[1] and "is_test" not in health


def _bench(tmp_path: Path) -> tuple[dict, Path]:
	bench = tmp_path / "bench"
	(bench / "sites" / "one.4dl.dev").mkdir(parents=True)
	(bench / "sites" / "one.4dl.dev" / "site_config.json").write_text("{}")
	stub = tmp_path / "bin"
	stub.mkdir()
	log = tmp_path / "calls"
	(stub / "bench").write_text(f'#!/usr/bin/env bash\necho "$*" >>{log}\ncase "$*" in *refresh*) echo \'{{"last_error": null}}\';; esac\n')
	(stub / "bench").chmod(0o755)
	return {**os.environ, "BENCH": str(bench), "PATH": f"{stub}:{os.environ['PATH']}"}, log


def _link(tmp_path: Path, block) -> tuple[subprocess.CompletedProcess, Path]:
	env, log = _bench(tmp_path)
	given = block if isinstance(block, str) else json.dumps(block)
	return subprocess.run(["bash", str(LINK), "one.4dl.dev"], input=given, env=env, capture_output=True, text=True), log


def test_link_writes_every_key_and_prints_no_secret(tmp_path):
	ran, log = _link(tmp_path, _block())
	assert ran.returncode == 0, ran.stderr
	calls = log.read_text().splitlines()
	assert "--site one.4dl.dev set-config one_token t-secret" in calls
	assert "--site one.4dl.dev set-config -p max_file_size 104857600" in calls
	assert calls[-1] == "--site one.4dl.dev execute onedesk.one.account.refresh"
	for secret in ("t-secret", "m-secret", "b-secret"):
		assert secret not in ran.stdout + ran.stderr


@pytest.mark.parametrize(
	"block",
	[
		"not json",
		{**_block(), "developer_mode": 1},
		{key: value for key, value in _block().items() if key != "one_token"},
		{**_block(), "one_admin_url": "http://admin.4dl.app"},
		{**_block(), "one_tenant": "Not A Slug"},
	],
)
def test_link_refuses_anything_but_the_block(tmp_path, block):
	ran, log = _link(tmp_path, block)
	assert ran.returncode != 0
	assert not log.exists()
