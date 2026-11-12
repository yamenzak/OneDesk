"""What OneAdmin's Servers draws: each server's history from Pilot and from
Lightsail, and the traffic Cloudflare counted. Nothing is stored here. A read
is kept in the cache for a moment, and a source that cannot answer says why in
place of its figures, so one that is down or not permitted only empties its
own charts. README, Servers.
"""

from datetime import UTC, datetime, timedelta

import frappe
import requests
from botocore.config import Config
from botocore.exceptions import ClientError

from onedesk.one_admin import boxes, cloudflare, faults, fleet, operator, pilot, servers, vault
from onedesk.one_admin.setup import ACCOUNT_ANALYTICS, ZONE_ANALYTICS

GRAPHQL = f"{cloudflare.API}/graphql"
OK, REFUSED, UNREACHABLE = "ok", "refused", "unreachable"
READ_WAIT = 8
HISTORY_FOR = 25
TRAFFIC_FOR = 300
SPARK_POINTS = 48
CHART_POINTS = 180
CARD_WINDOW = "1h"
WINDOWS = {"1h": (3600, 300), "6h": (21600, 300), "24h": (86400, 900), "1w": (604800, 3600)}
SPAN = timedelta(hours=24) - timedelta(minutes=5)
GONE = ("Archived", "Dropped", "Failed")
REFUSALS = ("not authorized", "authorization denied", "permission", "does not have access")
AWS_CLIENT = Config(connect_timeout=5, read_timeout=READ_WAIT, retries={"max_attempts": 1})
CARD_METRICS = ("CPUUtilization", "BurstCapacityPercentage")
LIGHTSAIL = {
	"CPUUtilization": ("Percent", "Average", "cpu"),
	"BurstCapacityPercentage": ("Percent", "Average", "burst"),
	"DiskReadBytes": ("Bytes", "Sum", "read"),
	"DiskWriteBytes": ("Bytes", "Sum", "write"),
}
HOSTS_QUERY = """query($zone: String!, $since: Time!, $until: Time!, $like: String!) {
  viewer { zones(filter: {zoneTag: $zone}) {
    httpRequestsAdaptiveGroups(limit: 1000, filter: {datetime_geq: $since, datetime_leq: $until, clientRequestHTTPHost_like: $like}, orderBy: [count_DESC]) {
      count
      sum { edgeResponseBytes }
      dimensions { clientRequestHTTPHost }
    }
  } }
}"""
WORKERS_QUERY = """query($account: String!, $since: Time!, $until: Time!) {
  viewer { accounts(filter: {accountTag: $account}) {
    workersInvocationsAdaptive(limit: 2000, filter: {datetime_geq: $since, datetime_leq: $until}, orderBy: [datetimeHour_ASC]) {
      sum { requests errors }
      dimensions { scriptName datetimeHour }
    }
  } }
}"""
R2_QUERY = """query($account: String!, $since: Time!, $until: Time!) {
  viewer { accounts(filter: {accountTag: $account}) {
    r2OperationsAdaptiveGroups(limit: 1000, filter: {datetime_geq: $since, datetime_leq: $until}) {
      sum { requests }
      dimensions { bucketName }
    }
    r2StorageAdaptiveGroups(limit: 1000, filter: {datetime_geq: $since, datetime_leq: $until}) {
      max { payloadSize objectCount }
      dimensions { bucketName }
    }
  } }
}"""


def why(raised: Exception) -> str:
	"""Whether a source said no or simply did not answer. Pure."""
	if isinstance(raised, ClientError):
		code = raised.response.get("Error", {}).get("Code", "")
		return REFUSED if code in ("AccessDenied", "AccessDeniedException", "UnauthenticatedException", "UnauthorizedOperation") else UNREACHABLE
	if isinstance(raised, faults.Refused) and raised.status in (401, 403):
		return REFUSED
	return UNREACHABLE


def _source(fetch) -> dict:
	"""What a source gave, or why it gave nothing. Never raises."""
	try:
		return {"state": OK, "data": fetch()}
	except Exception as raised:
		return {"state": why(raised), "data": None}


def _empty() -> dict:
	return {"state": UNREACHABLE, "data": None}


def _held(key: str, lasts: int, fetch):
	"""A short-lived read: every open screen shares one call to the source."""
	cache = frappe.cache()
	found = cache.get_value(f"one_admin_metrics:{key}")
	if found is None:
		found = fetch()
		cache.set_value(f"one_admin_metrics:{key}", found, expires_in_sec=lasts)
	return found


def thin(rows: list, most: int) -> list:
	"""At most `most` of a list, evenly taken, keeping the newest. Pure."""
	if len(rows) <= most:
		return rows
	step = len(rows) / most
	return [*(rows[int(at * step)] for at in range(most - 1)), rows[-1]]


def _sum(point: dict, *keys: str) -> float | None:
	found = [point[key] for key in keys if point.get(key) is not None]
	return round(sum(found), 2) if found else None


def system_rows(history: dict) -> list[dict]:
	"""Pilot's monitor history in the charts' names, CPU as what was busy and
	memory as a share of the box. Pure."""
	system = history.get("system") or {}
	total = system.get("memory_total_bytes")
	rows = []
	for point in system.get("points") or []:
		used = point.get("Used")
		rows.append(
			{
				"time": point["time"],
				"user": point.get("Busy User"),
				"system": point.get("Busy System"),
				"iowait": point.get("Busy IOWait"),
				"other": _sum(point, "Busy IRQ", "Busy Other"),
				"cpu": _sum(point, "Busy User", "Busy System", "Busy IOWait", "Busy IRQ", "Busy Other"),
				"used": used,
				"cached": point.get("Cached + Buffers"),
				"swap": point.get("Swap Used"),
				"memory": round(used / total * 100, 2) if used is not None and total else None,
				"load1": point.get("Load1"),
				"load5": point.get("Load5"),
				"load15": point.get("Load15"),
				"disk": point.get("Root Disk"),
				"received": point.get("Received"),
				"sent": point.get("Sent"),
				"read": point.get("Read"),
				"write": point.get("Write"),
			}
		)
	return rows


def database_rows(history: dict) -> list[dict]:
	"""Pilot's database history in the charts' names. Pure."""
	return [
		{
			"time": point["time"],
			"select": point.get("Select"),
			"insert": point.get("Insert"),
			"update": point.get("Update"),
			"delete": point.get("Delete"),
			"other": point.get("Other"),
			"connected": point.get("Connected"),
			"allowed": point.get("Max Connections"),
		}
		for point in history.get("points") or []
	]


def by_time(readings: dict[str, list[tuple[int, float]]]) -> list[dict]:
	"""Lightsail's separate metrics as one row a moment, oldest first. Pure."""
	rows: dict[int, dict] = {}
	for name, points in readings.items():
		for at, value in points:
			rows.setdefault(at, {"time": at})[name] = value
	return [rows[at] for at in sorted(rows)]


def per_second(rows: list[dict], period: int) -> list[dict]:
	"""Lightsail's bytes per period as the bytes a second Pilot reports. Pure."""
	return [{**one, **{key: round(one[key] / period, 2) for key in ("read", "write") if one.get(key) is not None}} for one in rows]


def latest(rows: list[dict], key: str):
	"""The newest reading of `key`. Pure."""
	return next((one[key] for one in reversed(rows) if one.get(key) is not None), None)


def card_series(system: list[dict], lightsail: list[dict]) -> dict:
	"""A card's three sparklines and its burst. CPU falls back on Lightsail's
	when Pilot gave nothing. Pure."""
	cpu = [one["cpu"] for one in system] or [one.get("cpu") for one in lightsail]
	return {
		"cpu": thin(cpu, SPARK_POINTS),
		"memory": thin([one["memory"] for one in system], SPARK_POINTS),
		"disk": thin([one["disk"] for one in system], SPARK_POINTS),
		"burst": latest(lightsail, "burst"),
	}


def _pilot(row, path: str, window: str) -> dict:
	"""A history from the server's Pilot. A server the five-minute check found
	down is not asked, so an open screen does not wait on it."""
	if not row.pilot_host or row.status == "Down":
		return _empty()
	return _held(f"pilot:{row.server}:{path}:{window}", HISTORY_FOR, lambda: _source(lambda: pilot.call(row.server, "GET", path, params={"window": window}, wait=READ_WAIT) or {}))


def _lightsail_read(client, name: str, metric: str, seconds: int, period: int) -> list[tuple[int, float]]:
	unit, statistic, _ = LIGHTSAIL[metric]
	until = datetime.now(UTC)
	answer = client.get_instance_metric_data(instanceName=name, metricName=metric, period=period, startTime=until - timedelta(seconds=seconds), endTime=until, unit=unit, statistics=[statistic])
	key = statistic.lower()
	return sorted((int(point["timestamp"].timestamp() * 1000), point[key]) for point in answer.get("metricData") or [] if key in point)


def _lightsail(row, window: str, metrics: tuple[str, ...]) -> dict:
	"""What Lightsail measured from outside the box, whatever state it is in."""
	if row.provider != "AWS":
		return _empty()

	def read() -> list[dict]:
		client = boxes._aws(servers._keys(), row.region or boxes.REGION, config=AWS_CLIENT)
		seconds, period = WINDOWS[window]
		return per_second(by_time({LIGHTSAIL[metric][2]: _lightsail_read(client, row.server, metric, seconds, period) for metric in metrics}), period)

	return _held(f"aws:{row.server}:{window}:{len(metrics)}", HISTORY_FOR, lambda: _source(read))


def _row(server: str):
	found = fleet.row_of(server)
	if not found:
		frappe.throw(frappe._("{0} is not a server.").format(server), frappe.DoesNotExistError)
	return found


def _workspaces() -> dict[str, list[dict]]:
	found: dict[str, list[dict]] = {}
	for one in frappe.get_all("Tenant", filters={"status": ["not in", GONE], "is_house": 0, "is_test": 0}, fields=["workspace_name", "slug", "server"]):
		found.setdefault(one.server, []).append({"name": one.workspace_name or one.slug, "slug": one.slug})
	return found


def _release(row) -> tuple[str | None, str | None]:
	"""A server's running release and the one being prepared, each a short id."""
	rows = servers.benches(row)
	current = next((one.get("release") for one in reversed(rows) if one.get("state") == "ready"), None)
	coming = next((one.get("release") for one in rows if one.get("state") == "preparing"), None)
	return (current or "")[:7] or None, (coming or "")[:7] or None


@frappe.whitelist()
def cards() -> list[dict]:
	"""Every server from the records alone: the page draws these at once and
	each card asks for its own readings."""
	operator._may()
	held = _workspaces()
	rows = []
	for row in fleet.rows():
		release, coming = _release(row)
		on = held.get(row.server, [])
		rows.append(
			{
				"server": row.server,
				"provider": row.provider,
				"region": row.region,
				"status": row.status,
				"capacity": row.capacity,
				"held": row.workspaces or len(on),
				"workspaces": on,
				"release": release,
				"coming": coming,
				"memory": row.memory_used,
				"disk": row.disk_used,
				"memory_limit": servers.MEMORY_LIMIT,
				"disk_limit": servers.DISK_LIMIT,
			}
		)
	return rows


@frappe.whitelist()
def card(server: str) -> dict:
	"""One server's sparklines over the last hour."""
	operator._may()
	row = _row(server)
	monitor = _pilot(row, "/monitor/history", CARD_WINDOW)
	lightsail = _lightsail(row, CARD_WINDOW, CARD_METRICS)
	return {"state": monitor["state"], **card_series(system_rows(monitor["data"] or {}), lightsail["data"] or [])}


@frappe.whitelist()
def charts(server: str, window: str = "1h") -> dict:
	"""One server's charts over a window: what Pilot has, what the database
	did, and what Lightsail measured."""
	operator._may()
	if window not in WINDOWS:
		frappe.throw(frappe._("{0} is not a window.").format(window))
	row = _row(server)
	monitor = _pilot(row, "/monitor/history", window)
	database = _pilot(row, "/database/history", window)
	lightsail = _lightsail(row, window, tuple(LIGHTSAIL))
	return {
		"window": window,
		"provider": row.provider,
		"states": {"pilot": monitor["state"], "database": database["state"], "lightsail": lightsail["state"]},
		"system": thin(system_rows(monitor["data"] or {}), CHART_POINTS),
		"database": thin(database_rows(database["data"] or {}), CHART_POINTS),
		"lightsail": lightsail["data"] or [],
	}


def graphql(token: str, query: str, variables: dict) -> dict:
	"""One Analytics query. A refusal raises one `why` can recognise."""
	answer = requests.post(GRAPHQL, headers={"Authorization": f"Bearer {token}"}, json={"query": query, "variables": variables}, timeout=READ_WAIT)
	if answer.status_code in (401, 403):
		raise faults.Refused("Cloudflare refused analytics", answer.status_code)
	body = answer.json()
	if body.get("errors"):
		text = " ".join(one.get("message", "") for one in body["errors"])
		raise faults.Refused(f"Cloudflare analytics: {text}", 403 if refused(body["errors"]) else 500)
	return body["data"]["viewer"]


def refused(errors: list[dict]) -> bool:
	"""Whether Cloudflare's errors say the token may not read this: an error
	coded `authz`, as Workers' "authorization denied" is, or one that says
	so in words. Pure."""
	return any((one.get("extensions") or {}).get("code") == "authz" or any(word in (one.get("message") or "").lower() for word in REFUSALS) for one in errors)


def requests_by_workspace(groups: list[dict], domain: str, tenants: dict[str, dict]) -> list[dict]:
	"""Requests counted per workspace address, largest first; an address that
	is no workspace is left out. Pure."""
	suffix = f".{domain}"
	rows = []
	for one in groups:
		host = one["dimensions"]["clientRequestHTTPHost"]
		tenant = tenants.get(host[: -len(suffix)] if host.endswith(suffix) else "")
		if tenant:
			rows.append({"workspace": tenant["name"], "server": tenant["server"], "requests": one["count"], "bytes": (one.get("sum") or {}).get("edgeResponseBytes") or 0})
	return sorted(rows, key=lambda row: row["requests"], reverse=True)


def workers_by_hour(groups: list[dict]) -> list[dict]:
	"""A row per Worker and hour, for a chart split by Worker. Pure."""
	return [{"hour": one["dimensions"]["datetimeHour"], "script": one["dimensions"]["scriptName"], "requests": one["sum"]["requests"], "errors": one["sum"]["errors"]} for one in groups]


def buckets(account: dict) -> list[dict]:
	"""A row per R2 bucket: what it holds and how often it was asked. Pure."""
	rows: dict[str, dict] = {}
	for one in account.get("r2StorageAdaptiveGroups") or []:
		name = one["dimensions"]["bucketName"]
		rows[name] = {"bucket": name, "size": one["max"]["payloadSize"], "objects": one["max"]["objectCount"], "requests": 0}
	for one in account.get("r2OperationsAdaptiveGroups") or []:
		name = one["dimensions"]["bucketName"]
		rows.setdefault(name, {"bucket": name, "size": 0, "objects": 0, "requests": 0})["requests"] = one["sum"]["requests"]
	return sorted(rows.values(), key=lambda row: row["size"], reverse=True)


def _tenants() -> dict[str, dict]:
	rows = frappe.get_all("Tenant", filters={"status": ["not in", GONE]}, fields=["slug", "workspace_name", "server"])
	return {one.slug: {"name": one.workspace_name or one.slug, "server": one.server} for one in rows}


def _traffic() -> dict:
	held = frappe.get_cached_doc("One Admin Settings")
	account = frappe.conf.get("cloudflare_account") or held.cloudflare_account
	zone = frappe.conf.get("cloudflare_zone") or held.cloudflare_zone
	domain = held.tenant_domain
	token = vault.get("cloudflare_token")
	if not (account and token):
		return {"workspaces": _empty(), "workers": _empty(), "r2": _empty()}
	until = datetime.now(UTC)
	span = {"since": (until - SPAN).strftime("%Y-%m-%dT%H:%M:%SZ"), "until": until.strftime("%Y-%m-%dT%H:%M:%SZ")}
	tenants = _tenants()

	def hosts() -> list[dict]:
		groups = graphql(token, HOSTS_QUERY, {**span, "zone": zone, "like": f"%.{domain}"})["zones"][0]["httpRequestsAdaptiveGroups"]
		return requests_by_workspace(groups, domain, tenants)

	return {
		"workspaces": _source(hosts) if zone and domain else _empty(),
		"workers": _source(lambda: workers_by_hour(graphql(token, WORKERS_QUERY, {**span, "account": account})["accounts"][0]["workersInvocationsAdaptive"])),
		"r2": _source(lambda: buckets(graphql(token, R2_QUERY, {**span, "account": account})["accounts"][0])),
	}


@frappe.whitelist()
def traffic() -> dict:
	"""What Cloudflare counted over the last day: requests per workspace, each
	Worker by the hour, and each R2 bucket. A part the token may not read
	names the permission it needs."""
	operator._may()
	return {**_held("traffic", TRAFFIC_FOR, _traffic), "needs": {"workspaces": ZONE_ANALYTICS, "workers": ACCOUNT_ANALYTICS, "r2": ACCOUNT_ANALYTICS}}
