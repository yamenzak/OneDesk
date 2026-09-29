"""Four Degree Labs' own workspace: the admin site, as a workspace of One.

The admin site uses One as any company does, OneAI included, and OneAI's
calls go through the same gateway and credit ledger as a customer's. So the
admin site is a Tenant of its own, **ours** (`is_house`), and three things
are true of it that are true of no customer:

* nobody bills it: it has no plan and no Stripe subscription, so the ladder
  never moves it;
* its OneAI is never refused for credits (`ledger.reserve`): its balance can
  go below nothing, and what it spends is what the provider charged us;
* its AI use is our cost, not a sale, so AI Usage does not count it as
  charged, and Home does not count it as a live customer.

`ensure` makes it once and links the admin site to it, the way `push_config`
links a customer's site to its Tenant.
"""

import hashlib
import secrets
from urllib.parse import urlparse

import frappe
from frappe.installer import update_site_config

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
	# A fresh token each time it is linked: the old one, if any, was only ever
	# on this site's own config.
	token = secrets.token_urlsafe(32)
	frappe.db.set_value(
		"Tenant", held, "token_hash", hashlib.sha256(token.encode()).hexdigest(), update_modified=False
	)
	update_site_config("one_tenant", held)
	update_site_config("one_token", token)
	if not frappe.conf.get("one_admin_url"):
		update_site_config("one_admin_url", frappe.utils.get_url())
	return held
