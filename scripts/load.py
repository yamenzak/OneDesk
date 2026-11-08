"""What each site costs the server, from frappe's monitor log.

Turn the monitor on for a site (`bench --site SITE set-config -p monitor 1`)
and frappe writes every request and background job, with its duration, to
`logs/monitor.json.log`. This reads it and says, per site and per hour, how
many seconds of work its requests, its scheduled jobs and its other jobs
took, and which jobs cost the most. Scheduled jobs run whether anybody uses
the site or not, so they are what an idle workspace costs; requests are
what its people cost. OneAdmin's calculator takes its server share from
these figures (docs: the OneAdmin plan, Measuring).

    python3 scripts/load.py [--log PATH] [--top 10] [--json]
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

LOG = Path(__file__).resolve().parents[3] / "logs" / "monitor.json.log"
MICRO = 1_000_000


def entries(lines) -> list[dict]:
	"""The log's lines that parse, oldest first. Pure."""
	out = []
	for line in lines:
		try:
			one = json.loads(line)
		except ValueError:
			continue
		if isinstance(one, dict) and one.get("site") and one.get("timestamp"):
			out.append(one)
	return out


def _when(one: dict) -> datetime:
	return datetime.fromisoformat(one["timestamp"])


def summary(rows: list[dict], top: int = 10) -> dict:
	"""Per site: the hours covered, seconds of work an hour for requests,
	scheduled jobs and other jobs, request count an hour, and the costliest
	jobs. Pure."""
	sites = defaultdict(lambda: {"first": None, "last": None, "request": 0.0, "requests": 0, "scheduled": 0.0, "jobs": 0.0, "by_job": defaultdict(float)})
	for one in rows:
		held = sites[one["site"]]
		when = _when(one)
		held["first"] = min(held["first"] or when, when)
		held["last"] = max(held["last"] or when, when)
		seconds = (one.get("duration") or 0) / MICRO
		if one.get("transaction_type") == "request":
			held["request"] += seconds
			held["requests"] += 1
			continue
		job = one.get("job") or {}
		held["scheduled" if job.get("scheduled") else "jobs"] += seconds
		held["by_job"][job.get("method") or "?"] += seconds
	out = {}
	for site, held in sorted(sites.items()):
		hours = max((held["last"] - held["first"]).total_seconds() / 3600, 1 / 60)
		out[site] = {
			"hours": round(hours, 2),
			"request_seconds_an_hour": round(held["request"] / hours, 2),
			"requests_an_hour": round(held["requests"] / hours, 1),
			"scheduled_seconds_an_hour": round(held["scheduled"] / hours, 2),
			"job_seconds_an_hour": round(held["jobs"] / hours, 2),
			"costliest_jobs": [
				{"job": name, "seconds_an_hour": round(seconds / hours, 2)}
				for name, seconds in sorted(held["by_job"].items(), key=lambda pair: -pair[1])[:top]
			],
		}
	return out


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
	parser.add_argument("--log", type=Path, default=LOG)
	parser.add_argument("--top", type=int, default=10)
	parser.add_argument("--json", action="store_true")
	args = parser.parse_args()
	if not args.log.exists():
		print(f"no monitor log at {args.log}; turn the monitor on for a site first", file=sys.stderr)
		return 1
	said = summary(entries(args.log.read_text(encoding="utf-8").splitlines()), args.top)
	if args.json:
		print(json.dumps(said, indent=1))
		return 0
	for site, one in said.items():
		print(f"{site}  ({one['hours']} h)")
		print(f"  requests   {one['requests_an_hour']:>8} an hour, {one['request_seconds_an_hour']:>8} s of work an hour")
		print(f"  scheduled  {one['scheduled_seconds_an_hour']:>8} s of work an hour (an idle site's cost)")
		print(f"  other jobs {one['job_seconds_an_hour']:>8} s of work an hour")
		for job in one["costliest_jobs"]:
			print(f"    {job['seconds_an_hour']:>8}  {job['job']}")
	return 0


if __name__ == "__main__":
	sys.exit(main())
