"""The rescue kit: setup.sh opens what rescue.py packs, it reaches the locked
bucket only through production's OneAdmin, and the test workspace's own
backup comes back whole."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import rescue
import tree

SETUP = (tree.ROOT / "deploy" / "local" / "setup.sh").read_text()


def _kit_script() -> str:
	return re.search(r"<<'RESCUE_KIT'\n(.*?)\nRESCUE_KIT\n", SETUP, re.S).group(1)


def test_setup_opens_the_kit_rescue_packs(tmp_path):
	"""setup.sh has no repository yet when it opens the kit, so it carries its
	own few lines: they must keep reading what rescue.py writes."""
	kit = tmp_path / "kit.one"
	kit.write_bytes(rescue.sealed({".ssh/one_servers": b"key", ".one-local": b"A=1"}, "a long rescue passphrase"))
	env = {**os.environ, "ONE_RESCUE_PASSPHRASE": "a long rescue passphrase", "ONE_RESCUE_KIT": str(kit), "ONE_RESCUE_INTO": str(tmp_path / "home")}
	subprocess.run([sys.executable, "-I", "-c", _kit_script()], env=env, check=True, cwd=tmp_path)
	assert (tmp_path / "home" / ".ssh" / "one_servers").read_bytes() == b"key"
	assert (tmp_path / "home" / ".one-local").read_bytes() == b"A=1"
	assert (tmp_path / "home" / ".one-local").stat().st_mode & 0o777 == 0o600


def test_setup_asks_productions_keeper_the_way_rescue_packs():
	assert rescue.FETCH_SALT.decode() in SETUP
	keeper = re.search(r'^KEEPER = "(.+)"$', (tree.APP / "one_admin" / "setup.py").read_text(), re.M).group(1)
	assert f"https://{keeper}.4dl.workers.dev" in SETUP and "-dev" not in keeper
	assert 'rescue.py restore "one.$DOMAIN"' in SETUP and "admin.$DOMAIN" not in SETUP


def test_the_kit_goes_through_oneadmin_and_never_holds_the_keepers_secret():
	body = rescue.kit_body(b'{"salt": "s", "token": "t"}', "a long rescue passphrase")
	assert set(body) == {"kit", "fetch_hash"} and len(body["fetch_hash"]) == 64
	source = (tree.ROOT / "scripts" / "rescue.py").read_text()
	assert "keeper_secret" not in source and "x-one-secret" not in source
	backups = (tree.APP / "one_admin" / "backups.py").read_text()
	keep = backups.split("def keep_rescue_kit(", 1)[1].split("\ndef ", 1)[0]
	assert "frappe.only_for(site.OPERATOR)" in keep and '"/rescue-key"' in keep
	assert rescue.KEEP_KIT == "onedesk.one_admin.backups.keep_rescue_kit"


def test_the_newest_night_with_a_database_is_chosen():
	key = "daily/one-4dl-dev/{}/{}/{}"
	keys = [key.format("2026-11-08", part, name) for part, name in (("database", "a.sql.gz"), ("config", "c.json"), ("public", "f.tar"))]
	keys += [key.format("2026-11-09", "public", "g.tar"), "daily/other/2026-11-10/database/z.sql.gz"]
	found = rescue.newest_whole(keys, "daily/one-4dl-dev/")
	assert set(found) == {"database", "config", "public"}
	assert found["database"].endswith("2026-11-08/database/a.sql.gz")
	assert rescue.newest_whole([], "daily/one-4dl-dev/") == {}


def test_restore_is_forced_and_names_what_came():
	args = rescue.restore_args("one.4dl.dev", {"database": Path("/t/db.sql.gz"), "private": Path("/t/p.tar")}, "pw")
	assert args[:4] == ["--site", "one.4dl.dev", "restore", "/t/db.sql.gz"] and "--force" in args
	assert "--with-private-files" in args and "--with-public-files" not in args


def test_a_kit_holds_the_dev_site_config(tmp_path, monkeypatch):
	sites = tmp_path / "one-bench" / "sites"
	for site, config in (("one.4dl.dev", {"one_dev": 1}), ("other", {})):
		(sites / site).mkdir(parents=True)
		(sites / site / "site_config.json").write_text(json.dumps(config))
	monkeypatch.setattr(rescue, "HOME", tmp_path)
	monkeypatch.setattr(rescue, "SITES", sites)
	assert ".one-site-configs/one.4dl.dev.json" in rescue.gathered()


def test_fetch_reads_only_the_locked_bucket_and_takes_the_newest_day():
	groups = [{"id": "r", "name": "Workers R2 Storage Bucket Item Read"}, {"id": "w", "name": "Workers R2 Storage Bucket Item Write"}]
	policy = rescue.read_policy(groups, "acc", "one-backups")
	assert policy == [{"effect": "allow", "permission_groups": [{"id": "r"}], "resources": {"com.cloudflare.edge.r2.bucket.acc_default_one-backups": "*"}}]
	key_id, secret = rescue.s3_of({"id": "t1", "value": "v"})
	assert key_id == "t1" and len(secret) == 64
	keys = ["daily/oneadmin/2026-11-10/database/a.sql.gz", "daily/oneadmin/2026-11-11/database/b.sql.gz", "daily/oneadmin/2026-11-11/private/c.tar"]
	assert rescue.newest_under(keys, "daily/oneadmin/") == keys[1:]
	assert rescue.newest_under([], "daily/oneadmin/") == []
