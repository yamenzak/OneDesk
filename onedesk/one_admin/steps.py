"""What provisioning does, one idempotent step at a time.

Every step must be safe to run twice. A step returns `None` when done or `WAIT`
when the server has not finished; `faults.Again` retries and `faults.Refused` stops
the job. Nothing unwinds.
"""

import hashlib
import secrets

import frappe
import requests
from frappe import _lt
from frappe.utils import now_datetime

from onedesk.one_admin import cloudflare, faults, hosts, log, pilot, quota
from onedesk.one_storage import store

WAIT = "wait"

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

WALKS = {
	"Provision": ORDER,
	"Suspend": ("deactivate_site", "mark_suspended"),
	"Restore": ("activate_site", "route_it", "mark_live"),
	"Archive": ("note_backup", "archive_site", "stop_billing", "unroute", "mark_archived"),
	"Drop": ("empty_storage", "mark_dropped"),
	"Rebuild": ("forget_site", "place_it", "name_is_free", "create_site", "site_is_up", "upload_backup", "restore_site", "site_is_up", "route_it", "push_config", "mark_live"),
	"Roll Back": ("upload_backup", "restore_site", "site_is_up", "mark_live"),
	"Install App": ("app_on_bench", "install_app", "app_is_installed", "app_installed"),
}

SAID = {
	"place_it": _lt("Choosing a server"),
	"name_is_free": _lt("Checking the name is free"),
	"create_site": _lt("Creating the site"),
	"site_is_up": _lt("Waiting for the server"),
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
	"app_on_bench": _lt("Checking the app is on the server"),
	"install_app": _lt("Installing the app"),
	"app_is_installed": _lt("Waiting for the server"),
	"app_installed": _lt("Marking it installed"),
	"upload_backup": _lt("Sending the backup to the server"),
	"forget_site": _lt("Leaving the old site behind"),
	"restore_site": _lt("Restoring the backup"),
}


APPS = ("erpnext", "hrms", "onedesk")
BENCH = "main"


def _app(job) -> str:
	from onedesk.one_admin import private

	app = private.wanted(job).get("app")
	if not app:
		raise faults.Refused("the job doesn't say which app to install")
	return app


def _installed_on(tenant) -> set:
	found = pilot.call(tenant.server, "GET", f"/sites/{tenant.site}/apps") or {}
	rows = found.get("apps") if isinstance(found, dict) else found
	return {one.get("name") or one.get("app") for one in rows or [] if isinstance(one, dict)}


def app_on_bench(job, tenant) -> None:
	"""A private app is installed from the server, so it has to be on it.
	Missing, the job fails saying so; Resume installs it once it is there."""
	app = _app(job)
	if not tenant.site or not tenant.server:
		raise faults.Refused("the workspace has no site to install on yet")
	held = pilot.call(tenant.server, "GET", "/apps") or []
	rows = held.get("apps") if isinstance(held, dict) else held
	if app not in {one.get("name") for one in rows or [] if isinstance(one, dict)}:
		raise faults.Refused(f"{app} is not on {tenant.server}. Add it there, then resume")


def install_app(job, tenant) -> None:
	"""Pilot installs it on the site: its doctypes, patches, fixtures and
	after_install. Once: an app already there is not asked for again."""
	app = _app(job)
	if app in _installed_on(tenant):
		return
	pilot.call(tenant.server, "POST", f"/sites/{tenant.site}/apps", key=f"{job.name}:app", json={"app": app})


def app_is_installed(job, tenant) -> str | None:
	return None if _app(job) in _installed_on(tenant) else WAIT


def app_installed(job, tenant) -> None:
	from onedesk.one_admin import private

	private.installed(job)


def place_it(job, tenant) -> None:
	"""The emptiest open server that may take this workspace. None with room
	fails the job, saying so, and Resume places it once there is one."""
	if tenant.site or tenant.server:
		return
	eu = tenant.jurisdiction == "EU"
	rows = [one for one in _servers() if one.open and one.server and one.pilot_host and (one.eu or not eu)]
	kind = "open server that takes EU workspaces" if eu else "open server"
	if not rows:
		raise faults.Refused(f"Settings lists no {kind}. List one under Servers, then resume")
	counts = quota.held_on_servers()
	room = [one for one in rows if not one.capacity or counts.get(one.server, 0) < one.capacity]
	if not room:
		raise faults.Refused(f"Every {kind} is full. Add a server, list it under Servers in Settings, then resume")
	room.sort(key=lambda one: counts.get(one.server, 0) / (one.capacity or 1000))
	tenant.db_set({"bench": BENCH, "server": room[0].server, "cluster": room[0].region})


def _servers() -> list:
	return frappe.get_cached_doc("One Admin Settings").get("servers") or []


def _origin(server: str) -> str:
	"""The address that reaches a server's tunnel. The edge dials it for the
	workspace's own name."""
	found = next((one.origin_host for one in _servers() if one.server == server), None)
	if not found:
		raise faults.Refused(f"Settings lists no Origin Address for {server}")
	return found


def _site_name(tenant) -> str:
	"""A site is named for the address it answers at."""
	return hosts.under(tenant.slug, _tenant_domain())


def name_is_free(job, tenant) -> None:
	"""Refuse early rather than half-way."""
	if tenant.site:
		return
	if pilot.call(tenant.server, "GET", f"/sites/{_site_name(tenant)}"):
		raise faults.Refused(f"{tenant.slug} is already taken on {tenant.server}")


def create_site(job, tenant) -> None:
	"""Ask Pilot for the site, once: the job's name makes a repeat the same
	task, so a retry after a lost answer starts nothing."""
	if tenant.site:
		return
	name = _site_name(tenant)
	answered = pilot.call(tenant.server, "POST", "/sites", key=f"{job.name}:site", json={"name": name, "apps": ["frappe", *APPS]})
	_remember_task(job, answered)
	tenant.db_set("site", name)


def _remember_task(job, answered) -> None:
	payload = frappe.parse_json(job.payload or "{}") or {}
	payload["task"] = (answered or {}).get("task_id")
	job.db_set("payload", frappe.as_json(payload))


def site_is_up(job, tenant) -> str | None:
	"""Wait for Pilot's task. No deadline of our own: Pilot either finishes or
	says it failed."""
	task = (frappe.parse_json(job.payload or "{}") or {}).get("task")
	if not task:
		return None
	return None if pilot.task(tenant.server, task) == "done" else WAIT


def route_it(job, tenant) -> None:
	"""Put the workspace on our own name.

	One key at the edge: the slug against the site and the server's address.
	A plain PUT of a value we already know, so a retry is free.
	"""
	if not tenant.site:
		raise faults.Refused("there is no site to route to yet")
	tenant.db_set("domain", hosts.under(tenant.slug, _tenant_domain()))
	cloudflare.route(tenant.slug, f"{tenant.site} {_origin(tenant.server)}")


def push_config(job, tenant) -> None:
	"""Tell the site who it is, where admin is, and what it is called.

	The token is generated here and never again: only its hash is kept, on the
	tenant. The site is named for its address, so it needs no `host_name`.
	"""
	from onedesk.one_admin import backups

	token = secrets.token_urlsafe(32)
	tenant.db_set("token_hash", hashlib.sha256(token.encode()).hexdigest())
	mail_secret = secrets.token_urlsafe(32)
	backup = backups.given(tenant.slug)
	pilot.call(
		tenant.server,
		"PATCH",
		f"/sites/{tenant.site}/configuration",
		json={
			"one_admin_url": _admin_url(),
			"one_tenant": tenant.slug,
			"one_token": token,
			"max_file_size": store.LARGEST,
			"one_mail_secret": mail_secret,
			"one_mail_domain": cloudflare.mail_domain(),
			"one_backup_secret": backup["one_backup_secret"],
			"one_keeper_url": backup["one_keeper_url"],
		},
	)
	tenant.db_set("backup_ready", 1)
	cloudflare.mail_route(tenant.slug, cloudflare.mail_entry(tenant, mail_secret, [tenant.slug]))


def invite_owner(job, tenant) -> str | None:
	"""Have the new site invite whoever paid for it as its first administrator.

	The site does it (`account.wake`, one_account/owner.py), since we cannot sign in to
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
	from onedesk.one_admin import signup, tell

	signup.built(tenant)
	tell.ready(tenant)


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


def deactivate_site(job, tenant) -> None:
	"""The site stops answering and its jobs pause; the data is untouched. The
	web process reads the change when it next recycles, within minutes."""
	if not tenant.site:
		raise faults.Refused("there is no site to suspend")
	_still_going(job, tenant)
	_quiet(tenant, 1)


def _quiet(tenant, on: int) -> None:
	body = {"maintenance_mode": on, "pause_scheduler": on, "allow_reads_during_maintenance": 0 if on else None}
	pilot.call(tenant.server, "PATCH", f"/sites/{tenant.site}/configuration", json=body)


def mark_suspended(job, tenant) -> None:
	_arrive(tenant, "Suspended", log.said("stopped"), job)


def activate_site(job, tenant) -> None:
	"""It answers again. Only reached from Suspended: an archived site has
	gone, which `lifecycle.restore` refuses before a job is made."""
	if not tenant.site:
		raise faults.Refused("there is no site to bring back")
	_quiet(tenant, 0)


def mark_live(job, tenant) -> None:
	_arrive(tenant, "Live", log.said("paid"), job)


def upload_backup(job, tenant) -> None:
	"""The backup chosen for this job (its payload's `day` and `where`) sent
	from the locked bucket to the site's server. Once: a job that has sent
	it keeps the upload's id."""
	from onedesk.one_admin import backups

	payload = frappe.parse_json(job.payload or "{}") or {}
	if payload.get("upload"):
		return
	held = backups.chosen(tenant.slug, payload.get("day"), payload.get("where") or "daily")
	payload["upload"], payload["parts"] = backups.to_server(tenant.server, tenant.site, held["parts"])
	job.db_set("payload", frappe.as_json(payload))


def forget_site(job, tenant) -> None:
	"""A rebuilt workspace gets a new site, wherever there is room."""
	if tenant.site or tenant.server:
		tenant.db_set({"site": None, "server": None})


def restore_site(job, tenant) -> None:
	"""The site put back to the backup sent, by its server."""
	payload = frappe.parse_json(job.payload or "{}") or {}
	if payload.get("restore_asked"):
		return
	body = {"parts": payload.get("parts") or [], "upload_id": payload.get("upload")}
	answered = pilot.call(tenant.server, "POST", f"/sites/{tenant.site}/actions/restore", key=f"{job.name}:restore", json=body)
	payload["task"] = (answered or {}).get("task_id")
	payload["restore_asked"] = True
	job.db_set("payload", frappe.as_json(payload))


def note_backup(job, tenant) -> None:
	"""Write down the server's newest backup, before the site goes, and
	keep it and the workspace's files in the locked backup bucket
	(backups.archived): a keeper that does not answer stops the step, to be
	tried again, rather than archive a workspace nothing kept. A workspace
	with no backup, or no site, is not a reason to stop.
	"""
	if tenant.archived_backup or not tenant.site:
		return
	from onedesk.one_admin import backups

	backups.archived(tenant)
	held = pilot.call(tenant.server, "GET", f"/sites/{tenant.site}/backups?limit=1") or []
	tenant.db_set("archived_backup", held[0].get("created_at") if held else "")


def archive_site(job, tenant) -> None:
	"""Pilot drops the site, backing it up first. The last step that can
	still be called off (_still_going)."""
	_still_going(job, tenant)
	if not tenant.site:
		return
	if pilot.call(tenant.server, "GET", f"/sites/{tenant.site}") is None:
		return
	pilot.call(tenant.server, "DELETE", f"/sites/{tenant.site}", key=f"{job.name}:drop")


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
	_still_going(job, tenant)
	from onedesk.one_admin import storage

	storage.empty(tenant)


def mark_dropped(job, tenant) -> None:
	_arrive(tenant, "Dropped", log.said("dropped"), job)


class CalledOff(Exception):
	"""The workspace is no longer meant to go where this job takes it. The
	job ends without doing the rest (runner._called_off)."""


STILL = {"Suspend": ("Overdue",), "Archive": ("Suspended", "Failed"), "Drop": ("Archived",)}


def _still_going(job, tenant) -> None:
	"""Before a step that cannot be undone, ask again whether the workspace is
	still meant to go down. The job may be days old: paid since, a restore
	queued, or a closing taken back. An Archive from a closing day goes from
	Live or Overdue while the day stands."""
	closing = job.kind == "Archive" and tenant.get("closing_on") and tenant.status in ("Live", "Overdue")
	restoring = frappe.db.exists(
		"Provisioning Job", {"tenant": tenant.name, "kind": "Restore", "status": ["in", ("Pending", "Waiting")]}
	)
	if restoring or not (closing or tenant.status in STILL.get(job.kind, ())):
		raise CalledOff(f"{tenant.name} is {tenant.status}{' and being restored' if restoring else ''}, so nothing was done")


CALLED = {"Live": "Restored"}


def _arrive(tenant, rung: str, why: str, job=None) -> None:
	"""Put the workspace on a rung and start its clock there.

	`status_since` is written with the status and never separately, because the
	two together are what the ladder reads: a status without a timestamp is a
	workspace the ladder refuses to touch.
	"""
	was = tenant.status
	tenant.db_set({"status": rung, "status_since": now_datetime()}, notify=True)
	log.write(tenant.name, CALLED.get(rung, rung), why, job=job)
	from onedesk.one_admin import tell

	tell.owing(tenant, rung, why)
	tell.owner(tenant, rung, was, why)
