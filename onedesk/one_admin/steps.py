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

from onedesk.one_admin import cloudflare, faults, hosts, press

#: Returned by a step that has started something and is waiting on press.
WAIT = "wait"

#: In order, per kind of job. The job records which step is next, so a worker
#: restart resumes rather than repeats.
#:
#: Every walk but `Provision` is the ladder — see `ladder.py` for what each rung
#: means and `lifecycle.py` for what starts one. They are here rather than in
#: their own module because they are the same kind of thing: an idempotent step
#: that talks to press, driven by the same runner and the same backoff.
ORDER = (
	"name_is_free",
	"create_site",
	"site_is_up",
	"route_it",
	"push_config",
	"live",
)

#: What each kind of job walks. `Provision` is `ORDER`, which is named
#: separately because it is the first step of a job whose kind is not set.
WALKS = {
	"Provision": ORDER,
	"Suspend": ("deactivate_site", "mark_suspended"),
	"Restore": ("activate_site", "route_it", "mark_live"),
	"Archive": ("note_backup", "archive_site", "unroute", "mark_archived"),
	"Drop": ("empty_storage", "mark_dropped"),
}

#: What each step is doing, in words an operator reads rather than the function
#: name. A job that stopped on `archive_site` tells somebody nothing; a job that
#: stopped while asking press to destroy the site tells them where to look.
#:
#: Every step in `WALKS` is named here, and a test fails on one that is not —
#: because the failure is silent: the screen falls back to the function name and
#: nobody notices it was meant to say something.
SAID = {
	"name_is_free": "Checking nobody has the name",
	"create_site": "Asking press for the site",
	"site_is_up": "Waiting for press to build it",
	"route_it": "Putting it on our own name",
	"push_config": "Telling the site who it is",
	"live": "Marking it live",
	"deactivate_site": "Asking press to stop serving it",
	"mark_suspended": "Marking it suspended",
	"activate_site": "Asking press to serve it again",
	"mark_live": "Marking it live",
	"note_backup": "Noting which backup press holds",
	"archive_site": "Asking press to destroy the site",
	"unroute": "Taking the name off the edge",
	"mark_archived": "Marking it archived",
	"empty_storage": "Deleting the files",
	"mark_dropped": "Marking it dropped",
}


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
		"press.api.site.exists", subdomain=tenant.slug, domain=_press_domain()
	)
	if taken:
		raise faults.Refused(f"{tenant.slug} is already taken on {_press_domain()}")


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
			"domain": _press_domain(),
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


def route_it(job, tenant) -> None:
	"""Put the workspace on our own name.

	One key at the edge, the slug against the press site name, which is all the
	Worker needs to rewrite `Host` and hand the request to press. Nothing is
	asked of press here, and that is the point: the name it serves is its own,
	so there is no DNS to verify and no certificate to issue. The browser is
	served by the wildcard on our zone.

	A plain PUT of a value we already know, so a retry is free.
	"""
	if not tenant.site:
		raise faults.Refused("there is no site to route to yet")
	tenant.db_set("domain", hosts.under(tenant.slug, _tenant_domain()))
	cloudflare.route(tenant.slug, tenant.site)


def push_config(job, tenant) -> None:
	"""Tell the site who it is, where admin is, and what it is called.

	The token is generated here and never again: only its hash is kept, on the
	tenant. If this step runs twice the site gets a second token and the first
	stops working, which is correct — the first one may be the one that leaked.

	A list of `{key, value, type}` rather than an object, because press has two
	`update_config`s and they disagree: the doc method takes a mapping and the
	whitelisted `press.api.site.update_config` — the only one a token reaches —
	iterates and reads `c.key`. Handed a mapping it iterates the keys as strings
	and dies on the first one.

	`host_name` is set here and not through press's `set_host_name`, which needs
	a `Site Domain` record first. Our name is deliberately not one of those: the
	workspace is reached at it because a Worker rewrites `Host`, and press is
	never told it exists. So the config key is written directly, and press's own
	`Site.host_name` stays the press name. Nothing overwrites this unless a
	customer later makes one of their own domains primary, which is exactly when
	it should change.
	"""
	token = secrets.token_urlsafe(32)
	tenant.db_set("token_hash", hashlib.sha256(token.encode()).hexdigest())
	press.call(
		"press.api.site.update_config",
		name=tenant.site,
		config=frappe.as_json(
			[
				{"key": "one_admin_url", "value": _admin_url(), "type": "String"},
				{"key": "one_tenant", "value": tenant.slug, "type": "String"},
				{"key": "one_token", "value": token, "type": "Password"},
				{"key": "host_name", "value": f"https://{tenant.domain}", "type": "String"},
			]
		),
	)


def live(job, tenant) -> None:
	tenant.db_set({"status": "Live", "live_on": now_datetime()})


def _press_domain() -> str:
	"""What press calls a site, which is press's own root domain and never ours.

	`Site.domain` on press is a Link to `Root Domain`, and a Root Domain carries
	the AWS keys its wildcard certificate is issued with. We are a customer, so
	there is no route by which `t.4dl.app` becomes one — passing it to
	`site.new` would fail a link validation. The site is created with press's
	name and reached at ours, and `route_it` is what makes those the same site.
	"""
	return frappe.get_cached_value("One Admin Settings", None, "press_domain") or "frappe.cloud"


def _tenant_domain() -> str:
	return frappe.get_cached_value("One Admin Settings", None, "tenant_domain") or "t.4dl.app"


def _admin_url() -> str:
	"""Where a tenant site sends everything it needs from us.

	Read from this site's own config rather than a field, because the answer is
	"wherever this site is", and a field would be a second place to be wrong
	after a move.
	"""
	return frappe.conf.get("one_admin_url") or frappe.utils.get_url()


# --- The ladder. One walk per rung, each step safe to run twice. ------------


def deactivate_site(job, tenant) -> None:
	"""Press stops serving the site; the data is untouched.

	`deactivate` puts the site in maintenance mode and tells the proxy to answer
	a deactivated page, so nobody can log in and nothing is lost. Running it on
	a site press already deactivated is a no-op there, which is what makes this
	safe to retry.
	"""
	if not tenant.site:
		raise faults.Refused("there is no site to suspend")
	press.call("press.api.site.deactivate", name=tenant.site)


def mark_suspended(job, tenant) -> None:
	_arrive(tenant, "Suspended", "press has stopped serving the site")


def activate_site(job, tenant) -> None:
	"""Press serves it again.

	Only ever reached from Suspended: an archived site has been destroyed and
	there is nothing to activate, which `lifecycle.restore` refuses before a job
	is ever made.
	"""
	if not tenant.site:
		raise faults.Refused("there is no site to bring back")
	press.call("press.api.site.activate", name=tenant.site)


def mark_live(job, tenant) -> None:
	_arrive(tenant, "Live", "paid")


def note_backup(job, tenant) -> None:
	"""Write down which backup press is holding, before the site goes.

	Recorded and not copied. Press takes an offsite backup as part of archiving
	and keeps it for as long as its own retention says; pulling four gigabytes
	through this site to put them in our R2 would move real bytes to no end,
	because restoring is press's `restore` from press's copy either way. What is
	worth keeping is the name, so somebody can ask for it.

	A workspace with no backup is not a reason to stop. It may be a site that
	never had one, and refusing to archive it would leave it running for free
	forever.
	"""
	if tenant.archived_backup:
		return
	held = press.call("press.api.site.backups", name=tenant.site) or []
	newest = next(
		(one for one in held if isinstance(one, dict) and one.get("offsite")),
		next((one for one in held if isinstance(one, dict)), None),
	)
	tenant.db_set("archived_backup", (newest or {}).get("name") or "")


def archive_site(job, tenant) -> None:
	"""Press destroys the site, taking its own offsite backup first.

	`force` is false: a site press will not archive is a site somebody should
	look at rather than one we should insist on.
	"""
	if not tenant.site:
		return
	press.call("press.api.site.archive", name=tenant.site, force=False)


def unroute(job, tenant) -> None:
	"""Take the name off the edge.

	After the site is gone rather than before, so a failed archive leaves a
	workspace that still answers. A DELETE of a key that is not there succeeds,
	so this is safe on a workspace that never had one.
	"""
	cloudflare.forget(tenant.slug)


def mark_archived(job, tenant) -> None:
	_arrive(tenant, "Archived", "the site is gone; the files are not")


def empty_storage(job, tenant) -> None:
	"""Delete everything under this workspace's prefix.

	The only step on the ladder that destroys something of ours, and the last
	one. It is idempotent in the way that matters: emptying an empty prefix
	succeeds, so a retry after a half-finished sweep finishes the job.
	"""
	from onedesk.one_admin import storage

	storage.empty(tenant)


def mark_dropped(job, tenant) -> None:
	_arrive(tenant, "Dropped", "the files are gone")


#: What a Tenant Event calls each rung. Only one differs: arriving at Live is
#: what somebody reading the log wants to see as Restored, because that is the
#: interesting half — nothing writes an event for a workspace that was always
#: Live.
CALLED = {"Live": "Restored"}


def _arrive(tenant, rung: str, why: str) -> None:
	"""Put the workspace on a rung and start its clock there.

	`status_since` is written with the status and never separately, because the
	two together are what the ladder reads: a status without a timestamp is a
	workspace the ladder refuses to touch.
	"""
	tenant.db_set({"status": rung, "status_since": now_datetime()})
	frappe.get_doc(
		{
			"doctype": "Tenant Event",
			"tenant": tenant.name,
			"kind": CALLED.get(rung, rung),
			"detail": why,
		}
	).insert(ignore_permissions=True)
