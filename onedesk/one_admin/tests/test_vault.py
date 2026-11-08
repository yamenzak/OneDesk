"""OneAdmin's keys are read from the config and moved out of the database
(one_admin/vault.py)."""

from unittest import mock

from onedesk.one_admin import vault


def test_a_key_is_read_from_the_config_before_the_database():
	with mock.patch.object(vault.frappe, "conf", {"stripe_secret_key": "from-config"}), mock.patch.object(vault, "_typed", return_value="from-db"):
		assert vault.get("stripe_secret_key") == "from-config"
	with mock.patch.object(vault.frappe, "conf", {}), mock.patch.object(vault, "_typed", return_value="from-db"):
		assert vault.get("stripe_secret_key") == "from-db"


def test_moving_writes_each_typed_key_to_the_config_and_deletes_it():
	typed = {"cloudflare_token": "p", "r2_secret": "r"}
	with mock.patch.object(vault, "_typed", side_effect=typed.get), mock.patch.object(vault, "keep") as keep, mock.patch.object(vault, "remove_encrypted_password") as removed:
		assert vault.move() == ["cloudflare_token", "r2_secret"]
	assert [one.args for one in keep.call_args_list] == [("cloudflare_token", "p"), ("r2_secret", "r")]
	assert [one.args[2] for one in removed.call_args_list] == ["cloudflare_token", "r2_secret"]


def test_the_master_key_is_never_one_that_is_kept():
	assert vault.MASTER not in vault.KEPT
