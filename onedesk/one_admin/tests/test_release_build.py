"""What the release build publishes (deploy/release/upload.py) and how
OneAdmin hears of it (releases.released)."""

import importlib.util
from pathlib import Path

from onedesk.one_admin import releases

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("upload", ROOT / "deploy" / "release" / "upload.py")
upload = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(upload)


def test_the_template_shares_nothing_a_site_must_hold_alone():
	config = {
		"db_name": "_a",
		"db_password": "p",
		"encryption_key": "k",
		"admin_password": "x",
		"pilot_auth_token": "t",
		"onedesk_vapid_private": "v",
		"host_name": "h",
		"one_mail_secret": "s",
		"maintenance_mode": 1,
		"max_file_size": 10,
		"server_script_enabled": 1,
	}
	assert upload.shareable(config) == {"max_file_size": 10, "server_script_enabled": 1}


def test_the_workflow_and_the_admin_sign_alike():
	assert upload.signed("s", "body") == releases.servers.signed("s", "body")


def test_a_release_call_is_only_believed_while_it_is_fresh():
	assert releases.fresh(1000, 1000 + releases.FRESH_FOR)
	assert not releases.fresh(1000, 1001 + releases.FRESH_FOR)
	assert not releases.fresh("1000", 1000)
	assert not releases.fresh(None, 1000)


def test_a_private_app_is_read_from_its_hooks_without_running_them(tmp_path):
	app = tmp_path / "private" / "acme" / "acme"
	app.mkdir(parents=True)
	(app / "hooks.py").write_text('import os\napp_name = "acme"\nos.remove("/")\none_private_app = {"title": "Acme Fleet", "said": "Acme\'s vans."}\nafter_install = "acme.install.after_install"\n')
	(tmp_path / "private" / "loose").mkdir()
	(tmp_path / "private" / "loose" / "hooks.py").write_text('one_private_app = {"title": "Loose"}\n')
	plain = tmp_path / "private" / "plain" / "plain"
	plain.mkdir(parents=True)
	(plain / "hooks.py").write_text('app_name = "plain"\n')
	assert upload.declared(tmp_path) == [{"app": "acme", "title": "Acme Fleet", "said": "Acme's vans.", "icon": ""}]
	assert upload.assigned("x = {'a': 1}\ny = len(x)\nz: int = 2\n") == {"x": {"a": 1}}


def test_every_private_app_here_declares_itself():
	names = sorted(path.name for path in (ROOT / "private").iterdir() if (path / path.name / "hooks.py").exists())
	assert [one["app"] for one in upload.declared()] == names
	assert all(one["title"] != one["app"] and one["said"] for one in upload.declared())
