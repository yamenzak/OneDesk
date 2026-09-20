"""What landed in frappe, erpnext and hrms since we last looked.

`python scripts/upstream.py` prints it. `--record` writes today's shas to
upstream.json. `--check` exits non-zero when the record is too old — that is
what `tests/test_upstream.py` runs.

The point is the first line of every report: a directory like `ui/` can appear
upstream and sit there for a week while we rebuild what is in it.
"""

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECORD = ROOT / "upstream.json"
BENCH = Path("/home/frappe/bench1/apps")

APPS = ("frappe", "erpnext", "hrms")

#: Paths worth a line of their own in the report.
WATCHED = {
	"ui/": "the shared component library",
	"ui/island/decisions/": "how an island is hosted",
	"frappe/public/js/frappe/": "the desk",
	"*/doctype/*/": "doctypes",
}

MAX_DAYS_BEHIND = 14


def git(app: str, *args: str) -> str:
	out = subprocess.run(
		["git", f"--git-dir={BENCH / app}/.git", *args],
		capture_output=True,
		text=True,
	)
	return out.stdout.strip()


def recorded() -> dict:
	return json.loads(RECORD.read_text()) if RECORD.exists() else {}


def head(app: str) -> str:
	return git(app, "log", "-1", "--format=%H")


def report(was: dict) -> list[str]:
	lines = []
	for app in APPS:
		since = was.get(app, {}).get("sha")
		now = head(app)
		if not now:
			lines.append(f"{app}: no checkout")
			continue
		if since == now:
			lines.append(f"{app}: unchanged")
			continue
		if not since:
			lines.append(f"{app}: {now[:10]}, never recorded")
			continue
		names = git(app, "diff", "--name-only", f"{since}..{now}").splitlines()
		lines.append(f"{app}: {since[:10]} -> {now[:10]}, {len(names)} files")
		lines += [f"    {what}" for prefix, what in WATCHED.items() if _touched(names, prefix)]
		lines += [f"    new doctype: {d}" for d in _new_doctypes(app, since, now)]
	return lines


def _touched(names: list[str], prefix: str) -> bool:
	if "*" in prefix:
		head, _, tail = prefix.partition("*")
		return any(n.startswith(head) and tail.strip("*/") in n for n in names)
	return any(n.startswith(prefix) for n in names)


def _new_doctypes(app: str, since: str, now: str) -> list[str]:
	added = git(app, "diff", "--diff-filter=A", "--name-only", f"{since}..{now}").splitlines()
	found = []
	for name in added:
		parts = Path(name).parts
		if "doctype" in parts and Path(name).stem == Path(name).parent.name:
			found.append(Path(name).stem.replace("_", " ").title())
	return sorted(found)


def days_behind(was: dict) -> int:
	seen = was.get("recorded_on")
	return (date.today() - date.fromisoformat(seen)).days if seen else 10_000


def record() -> dict:
	data = {"recorded_on": date.today().isoformat()}
	for app in APPS:
		sha = head(app)
		if sha:
			data[app] = {"sha": sha, "date": git(app, "log", "-1", "--format=%cs")}
	RECORD.write_text(json.dumps(data, indent=2) + "\n")
	return data


def main() -> int:
	args = argparse.ArgumentParser()
	args.add_argument("--record", action="store_true")
	args.add_argument("--check", action="store_true")
	opts = args.parse_args()

	if opts.record:
		print(json.dumps(record(), indent=2))
		return 0

	was = recorded()
	if opts.check:
		behind = days_behind(was)
		if behind > MAX_DAYS_BEHIND:
			print(f"upstream.json is {behind} days old. Run `python scripts/upstream.py`.")
			return 1
		return 0

	print("\n".join(report(was)))
	return 0


if __name__ == "__main__":
	sys.exit(main())
