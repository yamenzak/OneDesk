"""Keeping up with frappe, erpnext and hrms, one checkpoint at a time.

A checkpoint is the three apps at known commits, with a note in
docs/upstream/ that went through what changed since the last one:
everything One leans on that moved, and everything new upstream shipped,
each with a decision. `upstream.json` holds the current checkpoint and the
ones before it. docs/UPSTREAM.md says how to take the next one.

    python scripts/upstream.py               what landed since the checkpoint
    python scripts/upstream.py --fetch       fetch each app's upstream branch
    python scripts/upstream.py --draft       write the note for moving to upstream
    python scripts/upstream.py --update      move the bench to the note's commits
    python scripts/upstream.py --checkpoint  record the reviewed note
    python scripts/upstream.py --check       fail unless the bench is a reviewed checkpoint
"""

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from datetime import date
from functools import cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
RECORD = ROOT / "upstream.json"
NOTES = ROOT / "docs" / "upstream"
BENCH = Path("/home/frappe/bench1/apps")
SITE = os.environ.get("ONE_SITE", "onedesk.localhost")

APPS = ("frappe", "erpnext", "hrms")
REMOTE, BRANCH = "upstream", "develop"

MAX_DAYS_BEHIND = 14

#: How an item in a note is closed: ticked, and one of these, in bold, after a dash.
DECISIONS = ("Kept", "Corrected", "Adopted", "Not for us", "Later")
OPEN = re.compile(r"^- \[ \] ")
CLOSED = re.compile(r"^- \[x\] (.*)$", re.M)
META = re.compile(r"<!-- upstream (\{.*\}) -->")


# --- git -------------------------------------------------------------------


def git(app: str, *args: str) -> str:
	out = subprocess.run(["git", "-C", str(BENCH / app), *args], capture_output=True, text=True)
	return out.stdout.strip()


def head(app: str, ref: str = "HEAD") -> str:
	return git(app, "rev-parse", "--verify", "--quiet", ref)


def dated(app: str, sha: str) -> str:
	return git(app, "log", "-1", "--format=%cs", sha)


def version(app: str, sha: str) -> str:
	found = re.search(r'__version__ = "([^"]+)"', git(app, "show", f"{sha}:{app}/__init__.py"))
	return found.group(1) if found else "?"


def changed(app: str, since: str, now: str) -> list[str]:
	"""Paths changed between two commits, as `app/path`, the way overrides.py names them."""
	return [f"{app}/{name}" for name in git(app, "diff", "--name-only", since, now).splitlines()]


def shown(app: str, sha: str, path: str) -> str:
	return git(app, "show", f"{sha}:{path.split('/', 1)[1]}")


# --- what One leans on -----------------------------------------------------


def _hooks() -> dict:
	found = {}
	for node in ast.parse((ROOT / "onedesk" / "hooks.py").read_text()).body:
		if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
			try:
				found[node.targets[0].id] = ast.literal_eval(node.value)
			except ValueError:
				pass
	return found


@cache
def _doctype_files() -> dict[str, str]:
	"""Every upstream doctype's json, by the doctype's name."""
	found = {}
	for app in APPS:
		for path in (BENCH / app / app).glob("**/doctype/*/*.json"):
			if path.stem != path.parent.name:
				continue
			try:
				name = json.loads(path.read_text()).get("name")
			except ValueError:
				continue
			if name:
				found[name] = str(path.relative_to(BENCH))
	return found


def _module_file(dotted: str) -> str | None:
	parts = dotted.split(".")
	for cut in range(len(parts), 0, -1):
		base = BENCH / parts[0] / Path(*parts[:cut])
		for path in (base.with_suffix(".py"), base / "__init__.py"):
			if path.exists():
				return str(path.relative_to(BENCH))
	return None


@cache
def _desk_js() -> dict[str, str]:
	"""Every upstream desk script's text, by `app/path`."""
	found = {}
	for app in APPS:
		for path in (BENCH / app / app / "public" / "js").glob("**/*.js"):
			found[str(path.relative_to(BENCH))] = path.read_text(errors="ignore")
	return found


def _defined_in(symbol: str, method: str) -> str | None:
	"""The upstream script that defines `symbol.method`, frappe.views.QueryReport's
	refresh or frappe.ui.form's save."""
	last = symbol.rsplit(".", 1)[-1]
	assigned = re.compile(rf"(^|[^\w.]){re.escape(symbol)}\.{re.escape(method)}\s*=", re.M)
	exact = re.compile(rf"(^|[^\w.]){re.escape(symbol)}\s*=\s*(class\b|\{{|function\b|new\b)", re.M)
	named = re.compile(rf"\bclass {re.escape(last)}\b")
	scripts = _desk_js()
	for pattern in (assigned, exact, named):
		hits = [path for path, text in scripts.items() if pattern.search(text) and (pattern is assigned or _body(text, method))]
		if hits:
			return sorted(hits, key=len)[0]
	# A registry entry, frappe.widget.widget_factory.chart = ChartWidget.
	parent, _, key = symbol.rpartition(".")
	for text in (t for t in scripts.values() if parent in t):
		found = re.search(rf"\b{re.escape(key)}\s*:\s*([A-Z]\w+)", text)
		if found:
			return _defined_in(found.group(1), method)
	# An object filled in elsewhere: $.extend(frappe.meta, { method() {} }).
	hits = [path for path, text in scripts.items() if symbol in text and _body(text, method)]
	return sorted(hits, key=len)[0] if hits else None


def _patches() -> dict[tuple[str, str], set[str]]:
	"""Each (desk symbol, method) our scripts replace or wrap, with the scripts."""
	found: dict[tuple[str, str], set[str]] = {}
	for path in sorted((ROOT / "onedesk" / "public" / "js").glob("*.js")):
		text = path.read_text()
		alias = {name: f"frappe.{symbol}" for name, symbol in re.findall(r"const (\w+) = (?:[\w.]+ && )*frappe\.([\w.]+);", text)}
		for owner, method in re.findall(r"([\w.]+)\.prototype\.(\w+)\s*=", text):
			symbol = alias.get(owner, owner)
			if symbol.startswith("frappe.") and not method.startswith(("one_", "__one")):
				found.setdefault((symbol, method), set()).add(path.name)
		for owner, method in re.findall(r"^\s*(frappe(?:\.\w+)+)\.(\w+)\s*=\s*(?:function|async|\()", text, re.M):
			found.setdefault((owner.removesuffix(".prototype"), method), set()).add(path.name)
	return found


def _body(text: str, method: str) -> str | None:
	"""A method's source, brace-matched from where it is defined."""
	start = re.search(rf"(^|\n)\s*(async\s+)?{re.escape(method)}\s*(\(|[:=]\s*(async\s*)?(function\b|\())", text)
	if not start:
		return None
	opened = text.find("{", start.end())
	depth = 0
	for at in range(max(opened, 0), len(text)):
		depth += {"{": 1, "}": -1}.get(text[at], 0)
		if depth == 0 and opened >= 0:
			return text[start.start() : at + 1]
	return None


def leans_on() -> dict[str, list[str]]:
	"""Upstream files One leans on, each with why. A desk script we patch is
	read by method instead (`patched`), since only that method matters."""
	import overrides

	why: dict[str, list[str]] = {}

	def add(path: str | None, reason: str) -> None:
		if path:
			why.setdefault(path, []).append(reason)

	for what, _, ours, theirs, _line in overrides.OVERRIDES:
		add(theirs, f"override: {what} ({ours})")
	docs = _doctype_files()
	for path in sorted((ROOT / "onedesk").glob("*/custom/*.json")):
		add(docs.get(json.loads(path.read_text()).get("doctype")), f"customized in {path.relative_to(ROOT)}")
	hooks = _hooks()
	for key in ("doc_events", "doctype_js", "doctype_list_js", "doctype_tree_js", "doctype_calendar_js", "override_doctype_class", "override_doctype_dashboards"):
		for name in hooks.get(key) or {}:
			add(docs.get(name), f"hooks.{key}")
			if key == "override_doctype_class" and docs.get(name):
				add(docs[name].removesuffix(".json") + ".py", f"hooks.{key}")
	for method in hooks.get("override_whitelisted_methods") or {}:
		add(_module_file(method), f"hooks.override_whitelisted_methods: {method}")
	vue = "".join(path.read_text() for path in (ROOT / "frontend" / "src").rglob("*.vue"))
	for name in sorted(set(re.findall(r"@framework/ui/(\w+)", vue))):
		add(f"frappe/ui/src/components/{name}/", f"islands import @framework/ui/{name}")
	add("frappe/ui/island/", "every island mounts through it")
	add("frappe/ui/vite/island/", "every island is built through it")
	return why


def patched() -> dict[tuple[str, str], tuple[str | None, set[str]]]:
	return {key: (_defined_in(*key), where) for key, where in _patches().items()}


# --- what moved, and what is new -------------------------------------------


def _subjects(app: str, since: str, now: str, path: str, limit: int = 3) -> list[str]:
	out = git(app, "log", "--no-merges", f"--since={dated(app, since)}", f"-{limit}", "--format=%s", now, "--", path.split("/", 1)[1])
	return [line for line in out.splitlines() if line]


def impact(app: str, since: str, now: str) -> list[str]:
	"""Each thing One leans on in `app` that moved between the two commits."""
	names = changed(app, since, now)
	lines = []
	for path, reasons in sorted(leans_on().items()):
		if not path.startswith(f"{app}/"):
			continue
		hit = [n for n in names if n == path or (path.endswith("/") and n.startswith(path))]
		if hit:
			said = "; ".join(_subjects(app, since, now, path)) or "see the diff"
			lines.append(f"`{path}` ({len(hit)} changed): {'; '.join(sorted(set(reasons)))}. Upstream: {said}")
	for (symbol, method), (path, where) in sorted(patched().items()):
		if path and path.startswith(f"{app}/"):
			was, now_ = _body(shown(app, since, path), method), _body(shown(app, now, path), method)
			if was != now_:
				state = "is gone from" if now_ is None else "changed in"
				lines.append(f"`{symbol}.{method}` {state} `{path}`, which {', '.join(sorted(where))} patches")
	return lines


def unmapped() -> list[str]:
	return [f"{symbol}.{method}" for (symbol, method), (path, _) in sorted(patched().items()) if not path]


def _hook_names(app: str, sha: str) -> set[str]:
	try:
		body = ast.parse(git(app, "show", f"{sha}:{app}/hooks.py")).body
	except SyntaxError:
		return set()
	return {n.targets[0].id for n in body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}


def novelties(app: str, since: str, now: str) -> list[str]:
	"""What upstream shipped that is new: features, doctypes, hooks, parts."""
	lines = []
	for row in git(app, "log", "--no-merges", f"--since={dated(app, since)}", "--format=%h%x09%s", now).splitlines():
		sha, _, subject = row.partition("\t")
		if re.match(r"^feat(\(|:|!)", subject):
			lines.append(f"{subject} ({sha})")
	for name in git(app, "diff", "--diff-filter=A", "--name-only", since, now).splitlines():
		path = Path(name)
		if "doctype" in path.parts and path.suffix == ".json" and path.stem == path.parent.name:
			lines.append(f"new doctype: {path.stem.replace('_', ' ').title()} (`{name}`)")
		if name.startswith("ui/src/components/") and name.count("/") == 4 and path.name in ("index.ts", "index.js"):
			lines.append(f"new frappe/ui part: `{path.parent.name}`")
	lines += [f"new hook: `{name}`" for name in sorted(_hook_names(app, now) - _hook_names(app, since))]
	return lines


# --- the ledger and its notes ----------------------------------------------


def recorded() -> dict:
	return json.loads(RECORD.read_text()) if RECORD.exists() else {}


def _meta(note: Path) -> dict:
	found = META.search(note.read_text())
	return json.loads(found.group(1)) if found else {}


def problems(text: str) -> list[str]:
	"""What keeps a note from closing a checkpoint: open items, ticks with no decision."""
	out = [f"open: {line[6:96]}" for line in text.splitlines() if OPEN.match(line)]
	for item in CLOSED.findall(text):
		if not any(f"**{word}**" in item for word in DECISIONS):
			out.append(f"no decision: {item[:90]}")
	return out


def draft() -> Path:
	"""The note for moving from the checkpoint to upstream's tip, every item open."""
	was = recorded()
	meta = {}
	for app in APPS:
		to = head(app, f"{REMOTE}/{BRANCH}") or head(app)
		since = was.get(app, {}).get("sha") or head(app)
		meta[app] = {"from": since, "to": to, "version": version(app, to), "date": dated(app, to)}
	out = [f"# Upstream checkpoint {date.today().isoformat()}\n", f"\n<!-- upstream {json.dumps(meta)} -->\n"]
	out.append("\n| App | Version | From | To | Commits |\n|---|---|---|---|---|\n")
	for app, one in meta.items():
		count = git(app, "rev-list", "--count", "--no-merges", f"--since={dated(app, one['from'])}", one["to"])
		out.append(f"| {app} | {one['version']} | `{one['from'][:10]}` {dated(app, one['from'])} | `{one['to'][:10]}` {one['date']} | {count} |\n")
	out.append(
		"\nEach item is closed by ticking it and saying after a dash what was done: "
		+ ", ".join(f"**{word}**" for word in DECISIONS)
		+ ". `--checkpoint` refuses while any is open. See docs/UPSTREAM.md.\n"
	)
	out.append("\n## What One leans on that moved\n")
	for app, one in meta.items():
		lines = impact(app, one["from"], one["to"])
		out.append(f"\n### {app}\n\n" + ("".join(f"- [ ] {line}\n" for line in lines) if lines else "Nothing.\n"))
	missing = unmapped()
	if missing:
		out.append("\n### Patched, but not found upstream\n\n" + "".join(f"- [ ] `{name}`\n" for name in missing))
	out.append("\n## What upstream shipped\n")
	for app, one in meta.items():
		lines = novelties(app, one["from"], one["to"])
		out.append(f"\n### {app}\n\n" + ("".join(f"- [ ] {line}\n" for line in lines) if lines else "Nothing.\n"))
	NOTES.mkdir(parents=True, exist_ok=True)
	note = NOTES / f"{date.today().isoformat()}.md"
	note.write_text("".join(out))
	return note


def latest_note() -> Path | None:
	notes = sorted(NOTES.glob("????-??-??.md"))
	return notes[-1] if notes else None


def update(note: Path) -> None:
	"""Move each app to the note's commits, then bring the site along.

	Each step runs as the bench's user. `ONE_BENCH_ENV` names a shell file
	sourced before each one, with the Node, certificate bundle and proxy the
	machine needs and the bench does not carry.
	The apps and One's built files are handed to the bench's user first, since
	a merge or a build stops at the first file it cannot write."""
	meta = _meta(note)
	bench = BENCH.parent
	setup = os.environ.get("ONE_BENCH_ENV")
	prefix = f". {setup} && " if setup else ""

	def run(cmd: str) -> list[str]:
		return ["su", "frappe", "-c", prefix + cmd] if os.geteuid() == 0 else ["bash", "-c", prefix + cmd]

	if os.geteuid() == 0:
		owned = [str(BENCH / app) for app in meta] + [str(ROOT / "onedesk" / "public" / "dist")]
		subprocess.run(["chown", "-R", "frappe:frappe", *owned], check=True)
	steps = [f"cd {bench} && bench --site {SITE} backup"]
	steps += [f"git -C {BENCH / app} merge --ff-only {one['to']}" for app, one in meta.items()]
	steps += [f"cd {bench} && bench setup requirements", f"cd {bench} && bench --site {SITE} migrate", f"cd {bench} && bench build"]
	for step in steps:
		print(f"$ {step}", flush=True)
		if subprocess.run(run(step)).returncode:
			raise SystemExit(f"stopped at: {step}")
	print("Restart the bench, review the note, then run --checkpoint.")


def checkpoint(note: Path) -> dict:
	meta = _meta(note)
	off = [app for app, one in meta.items() if head(app) != one["to"]]
	if off:
		raise SystemExit(f"the bench is not at the note's commits ({', '.join(off)}). Run --update first.")
	left = problems(note.read_text())
	if left:
		raise SystemExit("the note is not reviewed:\n  " + "\n  ".join(left[:30]))
	was = recorded()
	history = was.pop("history", [])
	if was:
		history.append(was)
	data = {"recorded_on": date.today().isoformat(), "note": str(note.relative_to(ROOT))}
	for app, one in meta.items():
		data[app] = {"sha": one["to"], "date": one["date"], "version": one["version"]}
	data["history"] = history
	RECORD.write_text(json.dumps(data, indent=2) + "\n")
	return data


def check() -> list[str]:
	was = recorded()
	out = []
	for app in APPS:
		sha, now = was.get(app, {}).get("sha"), head(app)
		if sha and now and sha != now:
			out.append(f"{app} moved without a checkpoint: the bench is at {now[:10]}, upstream.json at {sha[:10]}.")
	if was.get("note"):
		out += [f"{was['note']}: {problem}" for problem in problems((ROOT / was["note"]).read_text())]
	else:
		out.append("upstream.json names no reviewed note. Take a checkpoint (docs/UPSTREAM.md).")
	seen = was.get("recorded_on")
	behind = (date.today() - date.fromisoformat(seen)).days if seen else 10_000
	if behind > MAX_DAYS_BEHIND:
		out.append(f"the last checkpoint is {behind} days old. Take the next one (docs/UPSTREAM.md).")
	return out


def report() -> list[str]:
	was = recorded()
	lines = []
	for app in APPS:
		since, now = was.get(app, {}).get("sha"), head(app, f"{REMOTE}/{BRANCH}") or head(app)
		if not since:
			lines.append(f"{app}: never recorded")
		elif since == now:
			lines.append(f"{app}: nothing new since the checkpoint (fetch with --fetch)")
		else:
			moved, new = impact(app, since, now), novelties(app, since, now)
			lines.append(f"{app}: {since[:10]} -> {now[:10]}, {len(moved)} things we lean on moved, {len(new)} new things")
			lines += [f"    {line}" for line in moved]
	return lines


def main() -> int:
	args = argparse.ArgumentParser()
	for flag in ("fetch", "draft", "update", "checkpoint", "check"):
		args.add_argument(f"--{flag}", action="store_true")
	opts = args.parse_args()

	if opts.fetch:
		for app in APPS:
			git(app, "fetch", REMOTE, BRANCH)
			print(f"{app}: {REMOTE}/{BRANCH} at {head(app, f'{REMOTE}/{BRANCH}')[:10]}")
		return 0
	if opts.draft:
		print(draft().relative_to(ROOT))
		return 0
	if opts.update or opts.checkpoint:
		note = latest_note()
		if not note:
			raise SystemExit("no note in docs/upstream. Run --draft first.")
		if opts.update:
			update(note)
		else:
			print(json.dumps(checkpoint(note), indent=2))
		return 0
	if opts.check:
		wrong = check()
		print("\n".join(wrong))
		return 1 if wrong else 0
	print("\n".join(report()))
	return 0


if __name__ == "__main__":
	sys.exit(main())
