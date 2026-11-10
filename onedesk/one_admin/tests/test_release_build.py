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
