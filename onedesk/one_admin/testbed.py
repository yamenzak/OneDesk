"""Test workspaces: a site of ours that runs outside our servers, such as the
dev bench's, linked to this OneAdmin (`Tenant.is_test`). Nobody bills it,
OneAdmin never moves, updates or rebuilds it, it backs itself up through the
keeper, and its credits are given by hand. AGENTS.md, Test workspaces."""

import re
import secrets
from urllib.parse import urlparse

import frappe
from frappe import _lt
from frappe.utils import now_datetime, sha256_hash

from onedesk.one import registry
from onedesk.one_admin import features, hosts, site

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,39}$")
GB = 1000 * 1000 * 1000

SAID = {
	"updated": _lt("{0} is a test workspace. It is updated on its own machine, not from OneAdmin."),
	"moved": _lt("{0} is a test workspace. It isn't on our servers, so OneAdmin doesn't run jobs on it."),
	"billed": _lt("{0} is a test workspace and isn't billed."),
}


class Untouched(frappe.ValidationError):
	"""What OneAdmin does to a workspace on its servers, asked of a test one."""


def is_test(tenant) -> bool:
	"""Whether a workspace, by name or record, is a test workspace."""
	if isinstance(tenant, str):
		return bool(frappe.db.get_value("Tenant", tenant, "is_test"))
	held = getattr(tenant, "is_test", None)
	return bool(held if held is not None else frappe.db.get_value("Tenant", tenant.name, "is_test"))


def refuse(tenant, why: str) -> None:
	"""Stop here, saying why, when the workspace is a test workspace."""
	if is_test(tenant):
		name = tenant if isinstance(tenant, str) else tenant.name
		frappe.throw(str(SAID[why]).format(name), Untouched)


def slug_for(address: str) -> str:
	"""The workspace's id from its address: `one.4dl.dev` is `one-4dl-dev`. Pure."""
	slug = hosts.tidy(address).replace(".", "-")
	if not SLUG.match(slug):
		raise ValueError(address)
	return slug


def block(admin_url: str, slug: str, token: str, mail_secret: str, mail_domain: str, backup: dict, largest: int) -> dict:
	"""The site config a test workspace is linked with, as push_config writes
	it for a workspace on our servers. Pure."""
	return {
		"one_admin_url": admin_url,
		"one_tenant": slug,
		"one_token": token,
		"one_mail_secret": mail_secret,
		"one_mail_domain": mail_domain,
		"one_backup_secret": backup["one_backup_secret"],
		"one_keeper_url": backup["one_keeper_url"],
		"max_file_size": largest,
	}


def _top_plan() -> frappe._dict:
	found = frappe.get_all(
		"Offering",
		filters={"kind": "Plan", "enabled": 1},
		fields=["name", "seats", "storage_gb", "database_gb"],
		order_by="amount desc",
		limit=1,
	)
	if not found:
		frappe.throw(frappe._("There is no plan on sale. Add one to the Price List first."))
	return found[0]


@frappe.whitelist(methods=["POST"])
def new(address: str, workspace_name: str) -> dict:
	"""A test workspace for a site at `address`, made or linked again: a new
	token, mail route and backup secret every time, so the site config
	returned is the only copy. Shown once, to be pasted into
	deploy/local/link.sh on the machine that serves the site."""
	site.require_admin()
	frappe.only_for(site.OPERATOR)
	from onedesk.one_admin import backups, cloudflare, steps
	from onedesk.one_cloud import store

	try:
		address = hosts.tidy(address)
	except hosts.Unclaimable as raised:
		frappe.throw(raised.translated(frappe._))
	try:
		slug = slug_for(address)
	except ValueError:
		frappe.throw(frappe._("{0} is too long for a workspace address.").format(address))
	admin = steps._admin_url()
	if hosts.ours(address, steps._tenant_domain(), urlparse(admin).hostname):
		frappe.throw(frappe._("{0} is one of {1}'s own addresses.").format(address, registry.name("one")))
	held = frappe.db.get_value("Tenant", slug, ["name", "is_test"], as_dict=True)
	if held and not held.is_test:
		frappe.throw(frappe._("{0} is already a workspace.").format(slug))
	if frappe.db.exists("Tenant", {"site": address, "name": ["!=", slug]}):
		frappe.throw(frappe._("{0} is already a workspace.").format(address))
	name = (workspace_name or "").strip() or address
	if held:
		frappe.db.set_value("Tenant", slug, "workspace_name", name)
	else:
		plan = _top_plan()
		frappe.get_doc(
			{
				"doctype": "Tenant",
				"slug": slug,
				"workspace_name": name,
				"owner_email": frappe.session.user,
				"status": "Live",
				"status_since": now_datetime(),
				"live_on": now_datetime(),
				"is_test": 1,
				"offering": plan.name,
				"jurisdiction": "Global",
				"site": address,
				"domain": address,
				"seats": plan.seats or 0,
				"storage_limit": (plan.storage_gb or 0) * GB,
				"database_limit": (plan.database_gb or 0) * GB,
				"credits_a_month": 0,
				"features": features.rows(features.held("Offering", plan.name)),
			}
		).insert(ignore_permissions=True)
	tenant = frappe.get_doc("Tenant", slug)
	token = secrets.token_urlsafe(32)
	mail_secret = secrets.token_urlsafe(32)
	backup = backups.given(slug)
	cloudflare.mail_route(slug, cloudflare.mail_entry(tenant, mail_secret, [slug]))
	tenant.db_set({"token_hash": sha256_hash(token), "backup_ready": 1})
	return {
		"tenant": slug,
		"config": block(admin, slug, token, mail_secret, cloudflare.mail_domain(), backup, store.LARGEST),
	}
