"""Whether what OneAdmin depends on is working: a scheduled check of each
service on the admin site, its answers kept as Health Check records for the
Status screen, and the operators told through tell.py when one starts
failing or recovers. README, Status."""

import concurrent.futures
import time

import frappe
import requests
from frappe import _
from frappe.utils import add_days, add_to_date, get_datetime, getdate, now_datetime, today

from onedesk.one_admin import backups, cloudflare, faults, gateway, ledger, mailing, operator, servers, site, storage, stripe, tell, vault

DOCTYPE = "Health Check"
WORKING, FAILING, NOT_SET_UP = "Working", "Failing", "Not Set Up"
WORKSPACES = "Workspaces"
BACKUPS = "Backups"
TIMEOUT = 15
STALE_MINUTES = 30
KEPT_DAYS = 30
PROBE = "no-such-workspace"
SITES_MISSES = "one_admin_health_sites"
ANSWERING = ("Live", "Overdue")
GAP_MINUTES = 15
GAPS = {BACKUPS: 90}
BACKUP_DAYS = 2
BUSIEST = 16
SENDING = "Sending"
SENDING_DAYS = 7
SENDING_LINE = 2.0
SENDING_FEWEST = 100
LAST_CHECKS = 8


class NotSetUp(Exception):
	"""The service is not configured here, so it cannot be said to fail."""


class Failing(Exception):
	"""What a check found wrong, in words for the Status screen."""


def _answered(status: int) -> Failing:
	return Failing(_("Answered {0}").format(status))


def _cloudflare() -> str:
	try:
		_account, token, _namespace = cloudflare._settings()
	except faults.Refused as reason:
		raise NotSetUp from reason
	answered = requests.get(f"{cloudflare.API}/user/tokens/verify", headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT)
	if not answered.ok:
		raise _answered(answered.status_code)
	return ""


def _edge() -> str:
	"""The router Worker answers a name no workspace holds with its own 404,
	so a wrong answer means the Worker did not."""
	domain = frappe.db.get_single_value("One Admin Settings", "tenant_domain")
	if not domain:
		raise NotSetUp
	answered = requests.get(f"https://{PROBE}.{domain}/", timeout=TIMEOUT, allow_redirects=False)
	if answered.status_code != 404 or "No workspace" not in answered.text:
		raise _answered(answered.status_code)
	return ""


def _r2() -> str:
	stored = frappe.get_cached_doc("One Admin Settings")
	buckets = [one for one, name in (("Global", stored.bucket_global), ("EU", stored.bucket_eu)) if name]
	if not (buckets and (frappe.conf.get("r2_key_id") or stored.r2_key_id) and vault.get("r2_secret")):
		raise NotSetUp
	for jurisdiction in buckets:
		storage._client(jurisdiction).list_objects_v2(Bucket=storage._bucket(jurisdiction), MaxKeys=1)
	return ""


def _keeper() -> str:
	try:
		url, headers = backups._keeper()
	except faults.Refused as reason:
		raise NotSetUp from reason
	answered = requests.get(f"{url}/backups", params={"prefix": "health/"}, headers=headers, timeout=TIMEOUT)
	if not answered.ok:
		raise _answered(answered.status_code)
	return ""


def _gateway() -> str:
	try:
		held = gateway._settings()
	except faults.Refused as reason:
		raise NotSetUp from reason
	answered = requests.get(f"{held['url'].rstrip('/')}/{held['account']}/{held['gateway']}", headers={gateway.HEADER: f"Bearer {held['token']}"}, timeout=TIMEOUT)
	if answered.status_code >= 500 or answered.status_code == 401:
		raise _answered(answered.status_code)
	return ""


def _mail() -> str:
	"""Whether One's own mails are leaving: none refused in the last hour and
	none stuck in the queue."""
	now = now_datetime()
	errors = frappe.db.count("Email Queue", {"status": "Error", "modified": [">", add_to_date(now, hours=-1)]})
	stuck = frappe.db.count("Email Queue", {"status": "Not Sent", "send_after": ["is", "not set"], "creation": ["<", add_to_date(now, minutes=-STALE_MINUTES)]})
	if errors or stuck:
		raise Failing(_("{0} not sent, {1} waiting").format(errors, stuck))
	return ""


def reputation(sent: int, bounced: int, suppressed: int) -> dict:
	"""Bounces and suppressions as a share of what was sent, and whether it
	is over the line: past `SENDING_LINE` percent once there are
	`SENDING_FEWEST` sends to judge by. Pure."""
	share = round(100 * (bounced + suppressed) / sent, 1) if sent else 0.0
	return {"sent": sent, "bounced": bounced, "suppressed": suppressed, "share": share, "over": sent >= SENDING_FEWEST and share > SENDING_LINE}


def _reputation() -> dict:
	"""The last `SENDING_DAYS`: workspaces' sends charged (mailing.send),
	the admin site's own sent, and the addresses newly stopped (mailing.stopped)."""
	since = add_days(now_datetime(), -SENDING_DAYS)
	sent = ledger.mails_charged(since)
	sent += frappe.db.count("Email Queue", {"status": "Sent", "modified": [">", since]})
	stopped = {"global_unsubscribe": 1, "one_bounce": ["is", "set"], "creation": [">", since]}
	suppressed = frappe.db.count("Email Unsubscribe", {**stopped, "one_bounce": mailing.SUPPRESSED})
	bounced = frappe.db.count("Email Unsubscribe", stopped) - suppressed
	return reputation(sent, bounced, suppressed)


def _sending() -> str:
	"""Whether mail is still welcome: the share of sends that bounced or went
	to an address Cloudflare suppresses, failing over the line."""
	held = _reputation()
	if not held["sent"]:
		raise NotSetUp
	said = _("{0} bounced and {1} suppressed of {2} sent in {3} days ({4}%)").format(held["bounced"], held["suppressed"], held["sent"], SENDING_DAYS, held["share"])
	if held["over"]:
		raise Failing(said)
	return said


def _stripe() -> str:
	key = frappe.conf.get("stripe_key") or vault.get("stripe_secret_key")
	if not key:
		raise NotSetUp
	answered = requests.get(f"{stripe._base()}/balance", auth=(key, ""), timeout=TIMEOUT)
	if not answered.ok:
		raise _answered(answered.status_code)
	return ""


def _answers(address: str) -> bool:
	try:
		answered = requests.get(f"https://{address}/api/method/ping", timeout=TIMEOUT, allow_redirects=False)
	except requests.RequestException:
		return False
	return answered.status_code == 200


def tallied(held: dict, answers: dict) -> tuple[dict, list[tuple[str, str]]]:
	"""Each workspace's misses after this round and what to tell. Workspaces
	gone from `answers` are forgotten. Pure."""
	now, told = {}, []
	for name, answered in answers.items():
		misses, said = servers.after_a_check(int(held.get(name) or 0), answered)
		if misses:
			now[name] = misses
		if said:
			told.append((name, said))
	return now, told


def _held() -> dict:
	return frappe.parse_json(frappe.db.get_default(SITES_MISSES) or "{}") or {}


def _keep(held: dict) -> None:
	frappe.db.set_default(SITES_MISSES, frappe.as_json(held))


def _workspaces() -> str:
	"""Every workspace that should be answering, asked at once, each told once
	(`tallied`); Pilot's own word also counts (`pilot_said`)."""
	rows = frappe.get_all("Tenant", filters={"status": ["in", ANSWERING], "site": ["is", "set"], "domain": ["is", "set"]}, fields=["name", "workspace_name", "domain", "primary_domain"])
	if not rows:
		raise NotSetUp
	with concurrent.futures.ThreadPoolExecutor(max_workers=BUSIEST) as pool:
		said = pool.map(_answers, [one.primary_domain or one.domain for one in rows])
	held, told = tallied(_held(), dict(zip([one.name for one in rows], said, strict=True)))
	_keep(held)
	names = {one.name: one.workspace_name or one.name for one in rows}
	for name, change in told:
		tell.workspace_changed(names[name], change)
	down = sorted(names[name] for name, misses in held.items() if misses >= servers.MISSES)
	if down:
		raise Failing(_("Not answering: {0}").format(", ".join(down)))
	return ""


def _backups() -> str:
	"""A workspace with no backup kept today or yesterday, or OneAdmin itself,
	or OneAdmin's config with no key to seal its copy to."""
	try:
		backups._keeper()
	except faults.Refused as reason:
		raise NotSetUp from reason
	asked = frappe.get_all(
		"Tenant",
		filters={"status": ["in", backups.BACKED_UP], "is_house": 0, "site": ["is", "set"], "creation": ["<", add_days(today(), -BACKUP_DAYS)]},
		pluck="slug",
	)
	days = [today(), add_days(today(), -1)]
	missing = [one for one in [backups.OURS, *asked] if not any(backups.kept_on(one, day) for day in days)]
	said = [_("No recent backup: {0}").format(", ".join(missing))] if missing else []
	if not backups.copy_key():
		said.append(_("OneAdmin's config isn't copied: there is no Config Copy Key in Settings"))
	if said:
		raise Failing(". ".join(said))
	return ""


CHECKS = {
	"Cloudflare": _cloudflare,
	"Edge Router": _edge,
	"R2": _r2,
	"Keeper": _keeper,
	"AI Gateway": _gateway,
	"Mail": _mail,
	SENDING: _sending,
	"Stripe": _stripe,
	WORKSPACES: _workspaces,
}
HOURLY = {BACKUPS: _backups}
SERVICES = [*CHECKS, *HOURLY]


def _said(reason: Exception) -> str:
	return str(reason)[:300] or type(reason).__name__


def _run(service: str, check) -> None:
	"""One check, its answer kept, and the operators told if it changed."""
	started = time.monotonic()
	try:
		state, detail = WORKING, check()
	except NotSetUp:
		state, detail = NOT_SET_UP, ""
	except Exception as reason:
		state, detail = FAILING, _said(reason)
	took = int((time.monotonic() - started) * 1000)
	frappe.get_doc({"doctype": DOCTYPE, "service": service, "state": state, "checked_at": now_datetime(), "took": took, "detail": detail}).insert(ignore_permissions=True)
	frappe.db.commit()
	if state != NOT_SET_UP and service != WORKSPACES:
		_noticed(service, state == WORKING, detail)


def _noticed(service: str, answered: bool, detail: str) -> None:
	key = f"one_admin_health_{frappe.scrub(service)}"
	was = frappe.utils.cint(frappe.db.get_default(key))
	misses, said = servers.after_a_check(was, answered)
	if misses != was:
		frappe.db.set_default(key, str(misses))
	if said:
		tell.service_changed(service, said, detail)


def watch() -> None:
	"""Every five minutes on the admin site: the checks, in the long queue so
	a slow service cannot hold the short one up."""
	if site.is_admin():
		frappe.enqueue("onedesk.one_admin.health.run", queue="long", timeout=300, job_id="one_admin_health", deduplicate=True)


def run() -> None:
	for service, check in CHECKS.items():
		_run(service, check)


def watch_backups() -> None:
	"""Hourly: a backup is made once a night, and asking after one is many calls."""
	if site.is_admin():
		frappe.enqueue("onedesk.one_admin.health.run_backups", queue="long", timeout=600, job_id="one_admin_health_backups", deduplicate=True)


def run_backups() -> None:
	for service, check in HOURLY.items():
		_run(service, check)


def prune() -> None:
	"""Daily: history older than the screen shows goes."""
	if site.is_admin():
		frappe.db.delete(DOCTYPE, [["checked_at", "is", "set"], ["checked_at", "<", add_days(today(), -KEPT_DAYS)]])


def pilot_said(sites: list[str], up: bool) -> None:
	"""A box's Pilot says workspaces went down or came back, told once per
	workspace however often the checks and Pilot both notice."""
	held = _held()
	for one in frappe.get_all("Tenant", filters={"site": ["in", sites or [""]]}, fields=["name", "workspace_name"]):
		was = int(held.get(one.name) or 0)
		if up:
			if was >= servers.MISSES:
				tell.workspace_changed(one.workspace_name or one.name, "back")
			held.pop(one.name, None)
		else:
			if was < servers.MISSES:
				tell.workspace_changed(one.workspace_name or one.name, "down")
			held[one.name] = max(was, servers.MISSES)
	_keep(held)


def stretches(rows: list) -> list[dict]:
	"""Failing checks in a row: when each began and ended, the ones long
	enough to have told anybody, newest first. Pure."""
	found: list[dict] = []
	for row in rows:
		last = found[-1] if found and found[-1]["service"] == row["service"] else None
		gap = GAPS.get(row["service"], GAP_MINUTES) * 60
		if last and (row["checked_at"] - last["ended"]).total_seconds() <= gap:
			last["ended"], last["checks"] = row["checked_at"], last["checks"] + 1
		else:
			found.append({"service": row["service"], "started": row["checked_at"], "ended": row["checked_at"], "checks": 1, "detail": row.get("detail") or ""})
	return sorted([one for one in found if one["checks"] >= servers.MISSES], key=lambda one: one["started"], reverse=True)


def _days(rows: list) -> list[dict]:
	"""A row per service per day, with the share of its checks that failed. Pure."""
	days: dict[tuple, dict] = {}
	for row in rows:
		day = days.setdefault((row["service"], str(row["day"])), {"service": row["service"], "day": str(row["day"]), "checks": 0, "failed": 0})
		day["checks"] += row["checks"]
		day["failed"] += row["checks"] if row["state"] == FAILING else 0
	return [{**one, "share": round(100 * one["failed"] / one["checks"], 1)} for one in days.values() if one["checks"]]


def _daily(start: str) -> list:
	from frappe.query_builder.functions import Count, Date

	table = frappe.qb.DocType(DOCTYPE)
	day = Date(table.checked_at)
	return (
		frappe.qb.from_(table)
		.select(table.service, table.state, day.as_("day"), Count("*").as_("checks"))
		.where(table.checked_at >= start)
		.where(table.state != NOT_SET_UP)
		.groupby(table.service, table.state, day)
	).run(as_dict=True)


def strip(days: list[dict], service: str, upto: str, count: int = KEPT_DAYS) -> list[dict]:
	"""The service's last `count` days, oldest first, each with the share of
	its checks that failed, or None for a day with none. Pure."""
	held = {one["day"]: one["share"] for one in days if one["service"] == service}
	last = getdate(upto)
	return [{"day": str(day), "share": held.get(str(day))} for day in (add_days(last, step - count + 1) for step in range(count))]


WINDOWS = {"24h": (24, 60), "7d": (7 * 24, 6 * 60), "30d": (KEPT_DAYS * 24, 24 * 60)}


def buckets(rows: list, start, minutes: int, count: int) -> list[dict]:
	"""Checks in `count` spans of `minutes` from `start`: when each began, how
	long a check took on average and how many failed. A span with no checks
	keeps its place with nothing in it. Pure."""
	held = [{"at": str(add_to_date(start, minutes=minutes * step)), "checks": 0, "failed": 0, "took": 0} for step in range(count)]
	for row in rows:
		at = int((get_datetime(row["checked_at"]) - get_datetime(start)).total_seconds() // (minutes * 60))
		if 0 <= at < count:
			held[at]["checks"] += 1
			held[at]["failed"] += 1 if row["state"] == FAILING else 0
			held[at]["took"] += row.get("took") or 0
	return [{**one, "took": round(one["took"] / one["checks"]) if one["checks"] else None} for one in held]


def _latest(service: str) -> dict | None:
	found = frappe.get_all(DOCTYPE, filters={"service": service}, fields=["state", "checked_at", "detail", "took"], order_by="checked_at desc", limit=1)
	return found[0] if found else None


@frappe.whitelist()
@frappe.read_only()
def board() -> dict:
	"""The Status screen: each service now, thirty days of each, and what failed."""
	operator._may()
	start = add_days(today(), -KEPT_DAYS)
	days = _days(_daily(start))
	services = []
	for service in SERVICES:
		last = _latest(service)
		owned = [one for one in days if one["service"] == service]
		checks = sum(one["checks"] for one in owned)
		failed = sum(one["failed"] for one in owned)
		services.append(
			{
				"service": service,
				"state": last.state if last else NOT_SET_UP,
				"checked_at": last.checked_at if last else None,
				"detail": (last.detail or "") if last else "",
				"took": last.took if last else None,
				"uptime": round(100 * (checks - failed) / checks, 2) if checks else None,
				"checks": checks,
				"strip": strip(days, service, today()),
				"trend": _trend(service),
			}
		)
	failing = frappe.get_all(DOCTYPE, filters={"state": FAILING, "checked_at": [">=", start]}, fields=["service", "checked_at", "detail"], order_by="service asc, checked_at asc", limit=5000)
	checks = sum(one["checks"] for one in days)
	failed = sum(one["failed"] for one in days)
	return {"services": services, "days": days, "incidents": stretches(failing)[:20], "uptime": round(100 * (checks - failed) / checks, 2) if checks else None}


def _checks(service: str, start) -> list:
	return frappe.get_all(DOCTYPE, filters={"service": service, "checked_at": [">=", start], "state": ["!=", NOT_SET_UP]}, fields=["checked_at", "state", "took", "detail"], order_by="checked_at asc", limit=KEPT_DAYS * 24 * 12 + 1)


def _hour():
	return now_datetime().replace(minute=0, second=0, microsecond=0)


def _trend(service: str) -> list:
	"""How long the service took to answer, hour by hour over the last day."""
	start = add_to_date(_hour(), hours=-24)
	return [one["took"] for one in buckets(_checks(service, start), start, 60, 25)]


@frappe.whitelist()
@frappe.read_only()
def history(service: str, window: str = "24h") -> dict:
	"""One service on the Status screen: how it answered over the window,
	what failed, and its last checks."""
	operator._may()
	if service not in SERVICES or window not in WINDOWS:
		frappe.throw(_("Not a service or a window the Status screen shows."))
	hours, minutes = WINDOWS[window]
	start = add_to_date(_hour(), hours=-hours)
	rows = _checks(service, start)
	failing = [{**row, "service": service} for row in rows if row.state == FAILING]
	last = frappe.get_all(DOCTYPE, filters={"service": service}, fields=["name", "checked_at", "state", "took", "detail"], order_by="checked_at desc", limit=LAST_CHECKS)
	return {
		"service": service,
		"buckets": buckets(rows, start, minutes, hours * 60 // minutes + 1),
		"incidents": stretches(failing),
		"checks": last,
	}
