"""OneAdmin's keys live in the site's config, never in its database, so a
leaked backup or a read of the database gives nobody a key. A key typed into
One Admin Settings is moved to the config when the settings are saved, and
read from there. The Cloudflare master key is not kept at all: Set Up
Cloudflare forgets it when its run ends (README, Under the hood, Keys)."""

import frappe
from frappe.utils.password import remove_encrypted_password

SETTINGS = "One Admin Settings"
KEPT = (
	"press_token",
	"cloudflare_token",
	"r2_secret",
	"stripe_secret_key",
	"stripe_webhook_secret",
	"ai_gateway_token",
	"openweather_key",
	"office_secret",
	"keeper_secret",
	"aws_secret_access_key",
)
MASTER = "cloudflare_master_token"
ON_PRESS = "one_admin_press_site"


def get(key: str) -> str | None:
	"""A key from the config; from the database only while one typed there
	has not been moved yet."""
	return frappe.conf.get(key) or _typed(key)


def _typed(key: str) -> str | None:
	from frappe.utils.password import get_decrypted_password

	return get_decrypted_password(SETTINGS, SETTINGS, key, raise_exception=False)


def keep(key: str, value: str) -> None:
	"""Write a key to this site's config: through Frappe Cloud when the site
	runs there (it rewrites the file from its own record), else to the file."""
	if not value:
		return
	where = frappe.conf.get(ON_PRESS)
	if where:
		from onedesk.one_admin import press

		press.call("press.api.site.update_config", name=where, config=frappe.as_json([{"key": key, "value": value, "type": "Password"}]))
	else:
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
	if frappe.conf.get(MASTER) and not frappe.conf.get(ON_PRESS):
		from frappe.installer import update_site_config

		update_site_config(MASTER, "None")
		frappe.conf.pop(MASTER, None)
