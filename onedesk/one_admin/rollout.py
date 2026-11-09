"""What OneAdmin's Releases reads: each release, which server holds which
version, and each workspace's window. Nothing here changes anything."""

from collections import Counter
from datetime import timedelta

import frappe
from frappe.utils import get_datetime

from onedesk.one_admin import fleet, operator, releases, servers

ORDER = {"moving": 0, "terms": 1, "window": 2}


def _version(bench: dict) -> str:
	return bench.get("release") or bench["bench"]


def by_release(held: list[dict], workspaces: list[dict]) -> list[dict]:
	"""Each release, newest first, with the servers holding it and the
	workspaces on it. `held` is each server's benches, oldest first. Pure."""
	on = Counter((one["server"], one["bench"]) for one in workspaces)
	found = {}
	for row in held:
		newest = servers.newest_ready(row["benches"])
		for depth, bench in enumerate(reversed(row["benches"])):
			version = _version(bench)
			entry = found.setdefault(version, {"release": version, "rank": depth, "servers": [], "workspaces": 0, "current": False})
			count = on[(row["server"], bench["bench"])]
			entry["rank"] = min(entry["rank"], depth)
			entry["current"] = entry["current"] or bench["bench"] == newest
			entry["workspaces"] += count
			entry["servers"].append({"server": row["server"], "state": bench.get("state") or "ready", "workspaces": count, "current": bench["bench"] == newest})
	return sorted(found.values(), key=lambda one: one["rank"])


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


@frappe.whitelist()
@frappe.read_only()
def overview() -> dict:
	"""Releases: every release, every server's versions, and who is waiting."""
	operator._may()
	held = [{"server": one.server, "name": one.name, "benches": servers.benches(one)} for one in fleet.rows()]
	tenants = frappe.get_all(
		"Tenant",
		filters={"site": ["is", "set"], "status": ["not in", releases.GONE], "is_house": 0},
		fields=["name", "workspace_name", "status", "server", "bench", "update_at", "update_moving", "terms_pending"],
	)
	workspaces = [{"server": one.server, "bench": one.bench} for one in tenants]
	current = {one["server"]: servers.newest_ready(one["benches"]) for one in held}
	versions = {bench["bench"]: _version(bench) for one in held for bench in one["benches"]}
	return {
		"releases": [{**one, "state": state_of(one)} for one in by_release(held, workspaces)],
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
		"total": len(tenants),
		"waiting": waiting(tenants, current, versions),
	}
