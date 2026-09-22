"""What provisioning does, one idempotent step at a time.

**Every step must be safe to run twice.** A network timeout leaves us genuinely
unable to tell whether the call landed, and the failure we refuse to accept is
creating two sites and billing a customer for both. So a step that creates
something looks first, and a step that sets something sets it to the same value
it would have set the first time.

A step returns `None` when it is done and the job may advance, or `WAIT` when it
has started something press has not finished — the runner comes back after a
backoff and runs the same step again. Raising `faults.Again` means the attempt
failed but the next one might not; raising `faults.Refused` stops the job and
records why.

**Nothing unwinds.** A half-provisioned site whose job failed is a site an
operator resumes, because unwinding is how you end up having taken money and
then deleted the thing it bought. The customer is told the truth, which is that
it is taking longer than it should.
"""

import hashlib
import secrets

import frappe
from frappe.utils import now_datetime

from onedesk.one_admin import faults, press

#: Returned by a step that has started something and is waiting on press.
WAIT = "wait"

#: In order. The job records which one is next, so a worker restart resumes
#: rather than repeats.
ORDER = (
	"name_is_free",
	"create_site",
	"site_is_up",
	"push_config",
	"live",
)

#: Every app a workspace gets. The same on every bench, so a site is never
#: missing one because it landed somewhere else.
APPS = ("erpnext", "hrms", "onedesk")


def name_is_free(job, tenant) -> None:
	"""Refuse early rather than half-way.

	press answers this without creating anything, so a slug somebody already has
	costs one call rather than a failed site.
	"""
	if tenant.site:
		return
	taken = press.call(
		"press.api.site.exists", subdomain=tenant.slug, domain=_domain_for(tenant)
	)
	if taken:
		raise faults.Refused(f"{tenant.slug} is already taken on {_domain_for(tenant)}")


def create_site(job, tenant) -> None:
	"""Ask press for the site, once.

	`tenant.site` is written the moment press answers, which is what makes this
	idempotent: a retry after a lost response finds the name already recorded
	and does nothing. The window where press has created a site and we have not
	recorded it is one database write wide, and `site_is_up` closes it by
	looking the slug up rather than trusting our own record.
	"""
	if tenant.site:
		return
	answered = press.call(
		"press.api.site.new",
		site={
			"name": tenant.slug,
			"domain": _domain_for(tenant),
			"group": tenant.bench,
			"cluster": tenant.cluster,
			"apps": list(APPS),
		},
	)
	tenant.db_set("site", (answered or {}).get("site") or tenant.slug)


def site_is_up(job, tenant) -> str | None:
	"""Wait for press to finish building it.

	Not a timeout of our own. press either finishes or tells us it failed, and a
	deadline here would only mean giving up on a site that was about to work.
	"""
	found = press.call("press.api.site.get", name=tenant.site) or {}
	status = (found.get("status") or "").lower()
	if status in ("active", "broken"):
		if status == "broken":
			raise faults.Refused(f"press built {tenant.site} and it came up broken")
		return None
	return WAIT


def push_config(job, tenant) -> None:
	"""Tell the site who it is, where admin is, and what it is called.

	The token is generated here and never again: only its hash is kept, on the
	tenant. If this step runs twice the site gets a second token and the first
	stops working, which is correct — the first one may be the one that leaked.
	"""
	token = secrets.token_urlsafe(32)
	tenant.db_set("token_hash", hashlib.sha256(token.encode()).hexdigest())
	press.call(
		"press.api.site.update_config",
		name=tenant.site,
		config=frappe.as_json(
			{
				"one_admin_url": _admin_url(),
				"one_tenant": tenant.slug,
				"one_token": token,
				"host_name": f"https://{tenant.domain}",
			}
		),
	)


def live(job, tenant) -> None:
	tenant.db_set({"status": "Live", "live_on": now_datetime()})


def _domain_for(tenant) -> str:
	return frappe.get_cached_value("One Admin Settings", None, "tenant_domain") or "t.4dl.app"


def _admin_url() -> str:
	"""Where a tenant site sends everything it needs from us.

	Read from this site's own config rather than a field, because the answer is
	"wherever this site is", and a field would be a second place to be wrong
	after a move.
	"""
	return frappe.conf.get("one_admin_url") or frappe.utils.get_url()
