"""What provisioning does, one idempotent step at a time.

Every step must be safe to run twice. A step returns `None` when done or `WAIT`
when press has not finished; `faults.Again` retries and `faults.Refused` stops
the job. Nothing unwinds.
"""

import hashlib
import secrets

import frappe
import requests
from frappe import _lt
from frappe.utils import now_datetime

from onedesk.one_admin import cloudflare, faults, hosts, log, press, quota
from onedesk.one_storage import store

#: Returned by a step that has started something and is waiting on press.
WAIT = "wait"

#: In order, per kind of job. The job records which step is next, so a worker
#: restart resumes rather than repeats.
ORDER = (
	"place_it",
	"name_is_free",
	"create_site",
	"site_is_up",
	"route_it",
	"push_config",
	"invite_owner",
	"live",
)

#: What each kind of job walks. `Provision` is `ORDER`, which is named
#: separately because it is the first step of a job whose kind is not set.
WALKS = {
	"Provision": ORDER,
	"Suspend": ("deactivate_site", "mark_suspended"),
	"Restore": ("activate_site", "route_it", "mark_live"),
	"Archive": ("note_backup", "archive_site", "stop_billing", "unroute", "mark_archived"),
	"Drop": ("empty_storage", "mark_dropped"),
}

#: What each step is doing, in words an operator reads rather than the function
#: name. Every step in `WALKS` is named here, and a test fails on one that is not.
SAID = {
	"place_it": _lt("Choosing a server"),
	"name_is_free": _lt("Checking the name is free"),
	"create_site": _lt("Creating the site"),
	"site_is_up": _lt("Waiting for Frappe Cloud"),
	"route_it": _lt("Setting up the address"),
	"push_config": _lt("Configuring the site"),
	"invite_owner": _lt("Inviting the owner"),
	"live": _lt("Marking it live"),
	"deactivate_site": _lt("Deactivating the site"),
	"mark_suspended": _lt("Marking it suspended"),
	"activate_site": _lt("Activating the site"),
	"mark_live": _lt("Marking it live"),
	"note_backup": _lt("Recording the latest backup"),
	"archive_site": _lt("Archiving the site"),
	"stop_billing": _lt("Cancelling its subscription in Stripe"),
	"unroute": _lt("Removing the address"),
	"mark_archived": _lt("Marking it archived"),
	"empty_storage": _lt("Deleting the files"),
	"mark_dropped": _lt("Marking it dropped"),
}


#: Every app a workspace gets. The same on every bench, so a site is never
#: missing one because it landed somewhere else.
APPS = ("erpnext", "hrms", "onedesk")


def place_it(job, tenant) -> None:
	"""Which of our servers the site goes on.

	Chosen by the job, not on the signup page: on the bench group Settings names,
	on the emptiest open server that fits. None fitting fails the job, saying what
	to buy or add, and Resume places it once there is one.
	"""
	if tenant.site or (tenant.bench and tenant.server):
		return
	bench = tenant.bench or _setting("press_bench") or next(
		(one.get("name") for one in press.benches() or [] if one.get("name")), None
	)
	if not bench:
		raise faults.Refused("Frappe Cloud has no bench group to place a site on")
	held = {one.get("name") or one.get("app") for one in press.apps(bench) or [] if isinstance(one, dict)}
	missing = [one for one in APPS if one not in held]
	if missing:
		raise faults.Refused(
			f"{', '.join(missing)} is not on the bench group {bench}. Add it in Frappe Cloud, deploy, then resume"
		)
	row = _server_for(tenant.jurisdiction, bench)
	tenant.db_set({"bench": bench, "server": row.server, "cluster": row.region or _region_of(row.server)})


def _server_for(jurisdiction: str, bench: str):
	"""The emptiest open server that may take this workspace and carries the
	bench group. Emptiest by the share of its limit used; a server with no
	limit counts as holding a thousand."""
	eu = jurisdiction == "EU"
	rows = [one for one in _servers() if one.open and one.server and (one.eu or not eu)]
	kind = "open server that takes EU workspaces" if eu else "open server"
	if not rows:
		raise faults.Refused(f"Settings lists no {kind}. List one under Servers, then resume")
	counts = quota.held_on_servers()
	room = [one for one in rows if not one.capacity or counts.get(one.server, 0) < one.capacity]
	if not room:
		raise faults.Refused(
			f"Every {kind} is full. Buy a server in Frappe Cloud, add it to the bench group {bench}, "
			"list it under Servers in Settings, then resume"
		)
	room.sort(key=lambda one: counts.get(one.server, 0) / (one.capacity or 1000))
	for one in room:
		carried = {group.get("name") for group in press.call("press.api.bench.all", server=one.server) or []}
		if bench in carried:
			return one
	raise faults.Refused(
		f"The bench group {bench} is not on {', '.join(one.server for one in room)}. "
		"Add the server to it in Frappe Cloud, deploy, then resume"
	)


def _servers() -> list:
	return frappe.get_cached_doc("One Admin Settings").get("servers") or []


def _region_of(server: str) -> str | None:
	"""The Frappe Cloud region a server is in, asked for when Settings has not
	read it back yet."""
	found = press.call("press.api.server.get", timeout=press.READ_TIMEOUT, name=server) or {}
	return (found.get("region_info") or {}).get("name")


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
	# Our own server: press puts a site there only when it is named with the
	# bench group's version, and on one of its free Unlimited plans.
	group = press.call("press.api.bench.get", name=tenant.bench) or {}
	answered = press.call(
		"press.api.site.new",
		site={
			"name": tenant.slug,
			"domain": _press_domain(),
			"group": tenant.bench,
			"cluster": tenant.cluster,
			"server": tenant.server,
			"version": group.get("version"),
			"plan": _setting("press_plan") or "Unlimited - Hetzner",
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

	One key at the edge, the slug against the press site name; nothing is asked
	of press. A plain PUT of a value we already know, so a retry is free.
	"""
	if not tenant.site:
		raise faults.Refused("there is no site to route to yet")
	tenant.db_set("domain", hosts.under(tenant.slug, _tenant_domain()))
	cloudflare.route(tenant.slug, tenant.site)


def push_config(job, tenant) -> None:
	"""Tell the site who it is, where admin is, and what it is called.

	The token is generated here and never again: only its hash is kept, on the
	tenant. Also sets `max_file_size` and `host_name`.
	"""
	token = secrets.token_urlsafe(32)
	tenant.db_set("token_hash", hashlib.sha256(token.encode()).hexdigest())
	mail_secret = secrets.token_urlsafe(32)
	press.call(
		"press.api.site.update_config",
		name=tenant.site,
		config=frappe.as_json(
			[
				{"key": "one_admin_url", "value": _admin_url(), "type": "String"},
				{"key": "one_tenant", "value": tenant.slug, "type": "String"},
				{"key": "one_token", "value": token, "type": "Password"},
				{"key": "host_name", "value": f"https://{tenant.domain}", "type": "String"},
				# Every request's size limit, which the site itself cannot
				# raise: a tenant is limited by storage, not by file size.
				{"key": "max_file_size", "value": store.LARGEST, "type": "Number"},
				# Mail at <slug>@<mail domain>: the Worker signs its notices
				# with this, and the site checks them with it (one_mail/inbound.py).
				{"key": "one_mail_secret", "value": mail_secret, "type": "Password"},
				{"key": "one_mail_domain", "value": cloudflare.mail_domain(), "type": "String"},
			]
		),
	)
	cloudflare.mail_route(tenant.slug, cloudflare.mail_entry(tenant, mail_secret, [tenant.slug]))


def invite_owner(job, tenant) -> str | None:
	"""Have the new site invite whoever paid for it as its first administrator.

	The site does it (`account.wake`, one/owner.py), since we cannot sign in to
	it. Safe to run twice; a site that has not read its new config yet waits.
	"""
	if not tenant.get("owner_email"):
		return None
	try:
		answer = requests.post(
			f"https://{tenant.site}/api/method/onedesk.one.account.wake", timeout=30
		)
	except requests.RequestException as raised:
		raise faults.Again(f"the site could not be reached: {raised}") from raised
	if answer.status_code != 200:
		raise faults.Again(f"the site answered {answer.status_code}")
	if not (answer.json().get("message") or {}).get("administered"):
		return WAIT
	return None


def live(job, tenant) -> None:
	tenant.db_set({"status": "Live", "live_on": now_datetime(), "status_since": now_datetime()}, notify=True)
	# The owner hears it is ready; their invitation left a step ago.
	from onedesk.one_admin import signup, tell

	signup.built(tenant)
	tell.ready(tenant)


def _press_domain() -> str:
	"""What press calls a site, which is press's own root domain and never ours.

	`Site.domain` on press is a Link to `Root Domain`, and a Root Domain carries
	the AWS keys its wildcard certificate is issued with. We are a customer, so
	there is no route by which `t.4dl.app` becomes one — passing it to
	`site.new` would fail a link validation. The site is created with press's
	name and reached at ours, and `route_it` is what makes those the same site.
	"""
	return frappe.get_cached_value("One Admin Settings", None, "press_domain") or "frappe.cloud"


def _setting(field: str) -> str | None:
	return (frappe.get_cached_value("One Admin Settings", None, field) or "").strip() or None


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
	_arrive(tenant, "Suspended", log.said("stopped"), job)


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
	_arrive(tenant, "Live", log.said("paid"), job)


def note_backup(job, tenant) -> None:
	"""Write down which backup press is holding, before the site goes.

	Recorded and not copied. A workspace with no backup is not a reason to stop.
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


def stop_billing(job, tenant) -> None:
	"""Cancel the workspace's subscription, now that the workspace is gone.

	Without this Stripe keeps invoicing a workspace that no longer exists, and
	a customer who comes back pays for nothing. After the site is archived, so
	a failed archive leaves a workspace still billed and still there. Safe
	twice: a subscription Stripe has already cancelled answers as missing.
	"""
	if not tenant.get("stripe_subscription"):
		return
	from onedesk.one_admin import stripe

	stripe.cancel(tenant.stripe_subscription)


def unroute(job, tenant) -> None:
	"""Take the name off the edge.

	After the site is gone rather than before, so a failed archive leaves a
	workspace that still answers. A DELETE of a key that is not there succeeds,
	so this is safe on a workspace that never had one. The customer's own
	names go with it (domains.unroute).
	"""
	from onedesk.one_admin import domains

	domains.unroute(tenant)


def mark_archived(job, tenant) -> None:
	_arrive(tenant, "Archived", log.said("archived"), job)


def empty_storage(job, tenant) -> None:
	"""Delete everything under this workspace's prefix.

	The only step on the ladder that destroys something of ours, and the last
	one. It is idempotent in the way that matters: emptying an empty prefix
	succeeds, so a retry after a half-finished sweep finishes the job.
	"""
	from onedesk.one_admin import storage

	storage.empty(tenant)


def mark_dropped(job, tenant) -> None:
	_arrive(tenant, "Dropped", log.said("dropped"), job)


#: What a Tenant Event calls each rung. Only one differs: arriving at Live is
#: Restored, since nothing writes an event for a workspace that was always Live.
CALLED = {"Live": "Restored"}


def _arrive(tenant, rung: str, why: str, job=None) -> None:
	"""Put the workspace on a rung and start its clock there.

	`status_since` is written with the status and never separately, because the
	two together are what the ladder reads: a status without a timestamp is a
	workspace the ladder refuses to touch.
	"""
	was = tenant.status
	# `notify` publishes the change, so an open form and list show it at once.
	tenant.db_set({"status": rung, "status_since": now_datetime()}, notify=True)
	# Who did it and which job, in the log (one_admin/log.py).
	log.write(tenant.name, CALLED.get(rung, rung), why, job=job)
	# Overdue and Suspended are told to the operator, and Suspended, Archived
	# and Live again to the owner; see one_admin/tell.py.
	from onedesk.one_admin import tell

	tell.owing(tenant, rung, why)
	tell.owner(tenant, rung, was)
