"""Four Degree Labs' own workspace: the admin site, as a workspace of One.

The admin site uses One as any company does, so it is a Tenant of its own,
ours (`is_house`): nobody bills it, its OneAI is never refused for credits,
and its AI use is our cost, not a sale.
"""

import secrets
from urllib.parse import urlparse

import frappe
from frappe.installer import update_site_config
from frappe.utils import sha256_hash

from onedesk.one_admin import site

SLUG = "4dl"
NAME = "Four Degree Labs"


def slug() -> str | None:
	"""Our own workspace's id, if there is one."""
	return frappe.db.get_value("Tenant", {"is_house": 1}, "name")


def is_ours(tenant: str | None) -> bool:
	return bool(tenant) and bool(frappe.db.get_value("Tenant", tenant, "is_house"))


def ensure() -> str:
	"""Make our own workspace once, and point the admin site's OneAI at it."""
	site.require_admin()
	held = slug()
	if not held:
		url = frappe.utils.get_url()
		frappe.get_doc(
			{
				"doctype": "Tenant",
				"slug": SLUG,
				"workspace_name": NAME,
				"status": "Live",
				"status_since": frappe.utils.now_datetime(),
				"jurisdiction": "Global",
				"is_house": 1,
				"site": frappe.local.site,
				"domain": urlparse(url).hostname or frappe.local.site,
			}
		).insert(ignore_permissions=True)
		held = SLUG
	token = secrets.token_urlsafe(32)
	frappe.db.set_value(
		"Tenant", held, "token_hash", sha256_hash(token), update_modified=False
	)
	update_site_config("one_tenant", held)
	update_site_config("one_token", token)
	if not frappe.conf.get("one_admin_url"):
		update_site_config("one_admin_url", own_url())
	return held


def link() -> None:
	"""Link the admin site to our own workspace when it is not linked yet.
	The patch runs once, and on a new admin site that is at install, before
	the site is flagged as the admin site; this runs after every migrate."""
	held = slug()
	if held and frappe.conf.get("one_tenant") == held and frappe.conf.get("one_token") and frappe.conf.get("one_admin_url"):
		return
	ensure()


def own_url() -> str:
	"""The admin site's own address, which it calls itself on. Outside a
	request the framework says http unless the site holds a certificate, and
	a hosted site redirects http to https, which turns the call into a GET."""
	url = frappe.utils.get_url()
	host = urlparse(url).hostname or ""
	if url.startswith("http://") and host != "127.0.0.1" and host != "localhost" and not host.endswith(".localhost"):
		url = "https://" + url[len("http://") :]
	return url
