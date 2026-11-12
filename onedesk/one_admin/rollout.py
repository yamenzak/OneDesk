"""What OneAdmin's Releases reads: each release, which server holds which
version, and each workspace's window. Nothing here changes anything."""

import re
from collections import Counter
from datetime import UTC, datetime, timedelta

import frappe
from frappe.utils import convert_utc_to_system_timezone, get_datetime

from onedesk.one_admin import boxes, fleet, operator, releases, servers

ORDER = {"moving": 0, "terms": 1, "window": 2}
COMMIT = re.compile(r"^[0-9a-f]{40}$")
ABOUT = ("subject", "committed_at", "built_at", "built_in")
KEPT = 30 * 24 * 3600
UNREAD = 3600


def _version(bench: dict) -> str:
	return bench.get("release") or bench["bench"]


def by_release(held: list[dict], workspaces: list[dict]) -> list[dict]:
	"""Each release, newest first, with the servers holding it and the
	workspaces on it. `held` is each server's benches, oldest first. Pure."""
	on = Counter((one["server"], one["bench"]) for one in workspaces)
	names = {}
	for one in workspaces:
		names.setdefault((one["server"], one["bench"]), []).append({"name": one.get("name"), "workspace": one.get("workspace")})
	found = {}
	for row in held:
		newest = servers.newest_ready(row["benches"])
		for depth, bench in enumerate(reversed(row["benches"])):
			version = _version(bench)
			entry = found.setdefault(version, {"release": version, "rank": depth, "servers": [], "workspaces": 0, "current": False, "held": []})
			count = on[(row["server"], bench["bench"])]
			entry["rank"] = min(entry["rank"], depth)
			entry["current"] = entry["current"] or bench["bench"] == newest
			entry["workspaces"] += count
			entry["held"] += names.get((row["server"], bench["bench"]), [])
			entry["servers"].append(
				{
					"server": row["server"],
					"state": bench.get("state") or "ready",
					"workspaces": count,
					"current": bench["bench"] == newest,
					"prepared_at": bench.get("prepared_at"),
					"ready_at": bench.get("ready_at"),
				}
			)
	return sorted(found.values(), key=lambda one: one["rank"])


def prepared(release: dict) -> dict:
	"""When the release was first ready on a server, and the longest any
	server took to put it up, in seconds. Pure."""
	done = [one for one in release["servers"] if one.get("ready_at")]
	took = [(get_datetime(one["ready_at"]) - get_datetime(one["prepared_at"])).total_seconds() for one in done if one.get("prepared_at")]
	return {"ready_at": min((one["ready_at"] for one in done), default=None), "prepared_in": int(max(took)) if took else None}


def local(at) -> str | None:
	"""A moment the registry wrote, in seconds or ISO, as this site's clock reads it."""
	if not at:
		return None
	moment = datetime.fromtimestamp(at, tz=UTC) if isinstance(at, int | float) else datetime.fromisoformat(at)
	return str(convert_utc_to_system_timezone(moment.astimezone(UTC).replace(tzinfo=None)).replace(tzinfo=None))


def about(release: str) -> dict:
	"""What the registry says of a release: its commit's subject, when it was
	committed and built, and how long the build took. Kept, since a release
	never changes; nothing for a bench that is not a release, or when the
	registry cannot be read."""
	if not COMMIT.match(release or ""):
		return {}
	key = f"one_admin_release_{release}"
	held = frappe.cache.get_value(key)
	if held is not None:
		return held
	try:
		found = boxes.release_of(servers._keys(), release)
	except Exception:
		frappe.cache.set_value(key, {}, expires_in_sec=UNREAD)
		return {}
	held = {**{name: found.get(name) for name in ABOUT}, "committed_at": local(found.get("committed_at")), "built_at": local(found.get("built_at"))}
	frappe.cache.set_value(key, held, expires_in_sec=KEPT)
	return held


def state_of(release: dict) -> str:
	"""A release's state, by the furthest behind of its servers. Pure."""
	states = {one["state"] for one in release["servers"]}
	if "preparing" in states:
		return "preparing"
	return "dropping" if states == {"dropping"} else "ready"


def moves_by(update_at, terms_pending: bool) -> str | None:
	"""When a workspace waiting on the terms moves even so. Pure."""
	if not terms_pending or not update_at:
		return None
	return str(get_datetime(update_at) + timedelta(days=releases.HOLD_DAYS))


def waiting(tenants: list, current: dict, versions: dict) -> list[dict]:
	"""Each workspace with a move ahead: moving first, then on the terms, then
	by window. `current` is each server's newest bench, `versions` each
	bench's release. Pure."""
	rows = []
	for one in tenants:
		if not (one.update_at or one.update_moving or one.bench != current.get(one.server)):
			continue
		rows.append(
			{
				"name": one.name,
				"workspace": one.workspace_name or one.name,
				"server": one.server,
				"kind": "moving" if one.update_moving else "terms" if one.terms_pending else "window",
				"on": versions.get(one.bench, one.bench),
				"to": versions.get(current.get(one.server)),
				"at": str(one.update_at) if one.update_at else None,
				"moves_by": moves_by(one.update_at, bool(one.terms_pending)),
			}
		)
	return sorted(rows, key=lambda one: (ORDER[one["kind"]], one["at"] or "9999"))


def _read() -> dict:
	held = [{"server": one.server, "name": one.name, "benches": servers.benches(one)} for one in fleet.rows()]
	tenants = frappe.get_all(
		"Tenant",
		filters={"site": ["is", "set"], "status": ["not in", releases.GONE], "is_house": 0, "is_test": 0},
		fields=["name", "workspace_name", "status", "server", "bench", "update_at", "update_moving", "terms_pending"],
	)
	workspaces = [{"server": one.server, "bench": one.bench, "name": one.name, "workspace": one.workspace_name or one.name} for one in tenants]
	current = {one["server"]: servers.newest_ready(one["benches"]) for one in held}
	versions = {bench["bench"]: _version(bench) for one in held for bench in one["benches"]}
	return {
		"held": held,
		"workspaces": workspaces,
		"current": current,
		"releases": [{**one, "state": state_of(one)} for one in by_release(held, workspaces)],
		"total": len(tenants),
		"waiting": waiting(tenants, current, versions),
	}


def summary() -> dict:
	"""Home's part: workspaces by release and how many are waiting to move."""
	read = _read()
	return {
		"releases": [{"release": one["release"], "workspaces": one["workspaces"], "current": one["current"]} for one in read["releases"]],
		"total": read["total"],
		"waiting": Counter(one["kind"] for one in read["waiting"]),
	}


@frappe.whitelist()
@frappe.read_only()
def overview() -> dict:
	"""Releases: every release, every server's versions, and who is waiting."""
	operator._may()
	read = _read()
	held, workspaces, current = read["held"], read["workspaces"], read["current"]
	return {
		"releases": [{**one, **prepared(one), **about(one["release"])} for one in read["releases"]],
		"repository": servers.REPOSITORY,
		"servers": [
			{
				"server": one["server"],
				"name": one["name"],
				"benches": [
					{"release": _version(bench), "state": bench.get("state") or "ready", "current": bench["bench"] == current[one["server"]], "workspaces": sum(1 for other in workspaces if other["server"] == one["server"] and other["bench"] == bench["bench"])}
					for bench in reversed(one["benches"])
				],
			}
			for one in held
		],
		"total": read["total"],
		"waiting": read["waiting"],
	}
