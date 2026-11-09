"""The rescue kit: setup.sh opens what rescue.py packs, and the dev sites'
backups come back whole."""

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


def test_setup_and_rescue_ask_the_keeper_the_same_way():
	assert rescue.FETCH_SALT.decode() in SETUP
	assert rescue.DEV_KEEPER in SETUP


def test_the_newest_whole_backup_is_chosen():
	key = "daily/dev-one.4dl.dev/{}/{}/{}"
	objects = [{"key": key.format("2026-11-08", part, name)} for part, name in (("database", "a.sql.gz"), ("config", "c.one"), ("public", "f.tar"))]
	objects += [{"key": key.format("2026-11-09", "database", "b.sql.gz")}]
	objects += [{"key": "daily/dev-admin.4dl.dev/2026-11-10/database/z.sql.gz"}]
	found = rescue.newest_backup(objects, "one.4dl.dev")
	assert set(found) == {"database", "config", "public"}
	assert found["database"].endswith("2026-11-08/database/a.sql.gz")


def test_a_files_part_is_told_from_the_private_files():
	assert rescue.part_of("x-private-files.tar") == "private"
	assert rescue.part_of("x-files.tar") == "public"
	assert rescue.part_of("x-database.sql.gz") == "database"
	assert rescue.part_of("x-site_config_backup.json") is None


def test_restore_is_forced_and_names_what_came():
	args = rescue.restore_args("one.4dl.dev", {"database": Path("/t/db.sql.gz"), "private": Path("/t/p.tar")}, "pw")
	assert args[:4] == ["--site", "one.4dl.dev", "restore", "/t/db.sql.gz"] and "--force" in args
	assert "--with-private-files" in args and "--with-public-files" not in args


def test_a_kit_holds_the_dev_sites_configs(tmp_path, monkeypatch):
	sites = tmp_path / "one-bench" / "sites"
	for site, config in (("one.4dl.dev", {"one_dev": 1}), ("other", {})):
		(sites / site).mkdir(parents=True)
		(sites / site / "site_config.json").write_text(json.dumps(config))
	monkeypatch.setattr(rescue, "HOME", tmp_path)
	monkeypatch.setattr(rescue, "SITES", sites)
	assert ".one-site-configs/one.4dl.dev.json" in rescue.gathered()
