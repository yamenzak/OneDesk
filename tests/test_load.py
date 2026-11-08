"""scripts/load.py: what each site costs the server, read from frappe's monitor log."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import load


def _line(site, kind, seconds, minute, method=None, scheduled=False):
	one = {"site": site, "transaction_type": kind, "duration": int(seconds * load.MICRO), "timestamp": f"2026-11-08 12:{minute:02d}:00+00:00"}
	if kind == "job":
		one["job"] = {"method": method, "scheduled": scheduled}
	return json.dumps(one)


def test_a_site_is_split_into_requests_scheduled_and_other_jobs():
	lines = [
		_line("a", "request", 2, 0),
		_line("a", "job", 6, 30, "tell.soon", scheduled=True),
		_line("a", "job", 3, 30, "intake.read"),
		"not json",
		_line("b", "request", 1, 0),
		_line("b", "request", 1, 30),
	]
	said = load.summary(load.entries(lines))
	assert said["a"]["hours"] == 0.5
	assert said["a"]["request_seconds_an_hour"] == 4 and said["a"]["scheduled_seconds_an_hour"] == 12 and said["a"]["job_seconds_an_hour"] == 6
	assert [one["job"] for one in said["a"]["costliest_jobs"]] == ["tell.soon", "intake.read"]
	assert said["b"]["requests_an_hour"] == 4
