"""OneAdmin's keys live in the site's config, never in its database, so a
leaked backup or a read of the database gives nobody a key. A key typed into
One Admin Settings is moved to the config when the settings are saved, and
read from there. The Cloudflare master key is not kept at all: Set Up
Cloudflare forgets it when its run ends (README, Under the hood, Keys)."""

import frappe
from frappe.utils.password import remove_encrypted_password

SETTINGS = "One Admin Settings"
KEPT = (
	"cloudflare_token",
	"r2_secret",
	"stripe_secret_key",
	"stripe_webhook_secret",
	"ai_gateway_token",
	"openweather_key",
	"office_secret",
	"keeper_secret",
	"aws_secret_access_key",
	"github_token",
	"cloudflare_oauth_client_secret",
)
MASTER = "cloudflare_master_token"


def get(key: str) -> str | None:
	"""A key from the config; from the database only while one typed there
	has not been moved yet."""
	return frappe.conf.get(key) or _typed(key)


def _typed(key: str) -> str | None:
	from frappe.utils.password import get_decrypted_password

	return get_decrypted_password(SETTINGS, SETTINGS, key, raise_exception=False)


def keep(key: str, value: str) -> None:
	"""Write a key to this site's config."""
	if not value:
		return
	from frappe.installer import update_site_config

	update_site_config(key, value)
	frappe.conf[key] = value


def move() -> list[str]:
	"""Every key still in the database written to the config and taken out of
	the database: the keys moved."""
	moved = []
	for key in KEPT:
		value = _typed(key)
		if not value:
			continue
		keep(key, value)
		remove_encrypted_password(SETTINGS, SETTINGS, key)
		moved.append(key)
	return moved


def forget_master() -> None:
	"""Set Up Cloudflare's run is over: the master key goes, from the
	database and the config alike."""
	remove_encrypted_password(SETTINGS, SETTINGS, MASTER)
	if frappe.conf.get(MASTER):
		from frappe.installer import update_site_config

		update_site_config(MASTER, "None")
		frappe.conf.pop(MASTER, None)
