"""One's agent on a box. Once a minute it reads OneAdmin's signed instructions
from R2, carries out the next one and reports how it went. It only ever calls
out, so no port opens: it unpacks a release as a new bench, makes a spare site
from the release's template, moves a workspace between benches, and drops a
bench that has emptied.
"""

import fcntl
import glob
import hashlib
import hmac
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

SELF = Path(__file__).resolve()
HOME = Path.home()
CONFIG = HOME / ".one-agent.json"
DONE = HOME / ".one-agent-done"
LOCK = HOME / ".one-agent-lock"
TEMPLATES = HOME / "templates"
BENCHES = HOME / "pilot" / "benches"
PILOT_HOME = HOME / "pilot"
PILOT = str(PILOT_HOME / "bin" / "pilot")
PYTHON = str(HOME / "pilot" / ".admin-venv" / "bin" / "python")
APPS = ("frappe", "erpnext", "hrms", "onedesk")
FLOW = "frappe-flow_server"
QUIET = ("maintenance_mode", "pause_scheduler")
TEMPLATE = ("database.sql.gz", "site_config.json", "public", "private")
SETTLE = """
import json, sys
from pathlib import Path
from pilot.config import BenchConfig
from pilot.config.common_site_config import update_common_site_config
from pilot.core.bench import Bench
from pilot.core.bench.initializer import BenchInitializer
path, apps = Path(sys.argv[1]), json.loads(sys.argv[2])
with BenchConfig.open(path, mode="raw") as raw:
    listed = raw.setdefault("apps", [])
    new = [one for one in apps if not any(had.get("name") == one["name"] for had in listed)]
    listed.extend(new)
bench = Bench(path)
start = BenchInitializer(bench)
start._ensure_admin_password()
start._ensure_database_credentials()
bench.create_directories()
bench.write_common_site_config()
with update_common_site_config(bench.sites_path) as config:
    config.setdefault("server_script_enabled", True)
start._configure_redis()
start._ensure_admin_frontend(print)
start._generate_process_config()
"""
SPARE = """
import sys
from pathlib import Path
from pilot.core.bench import Bench
from pilot.core.site import Site
from pilot.core.site.apps import SiteApps
from pilot.core.site.commands import SiteCommands
bench, site, database, password = sys.argv[1:5]
reach = SiteCommands.db_args
SiteCommands.db_args = lambda self, db_type: [*reach(self, db_type), "--source-sql", database]
held = Bench(Path.home() / "pilot" / "benches" / bench)
made = Site.provision(held, site, [], password)
SiteApps(made).restore_installed_apps_copy()
held.processes.apply()
"""
ARRIVE = """
import sys
from pathlib import Path
from pilot.core.bench import Bench
from pilot.core.site.provisioning import SiteProvisioner
from pilot.managers.nginx import NginxManager
to, was, site = sys.argv[1:4]
root = Path.home() / "pilot" / "benches"
gone, here = Bench(root / was), Bench(root / to)
NginxManager(gone).reload_for_site_change()
SiteProvisioner(here, site, [], None).write_pilot_communication_config(here.site(site))
NginxManager(here).reload_for_site_change()
here.backups.install_schedule()
"""
RESTORE = """
import sys
from pathlib import Path
from pilot.core.bench import Bench
from pilot.core.site.commands import SiteCommands
bench, site, database = sys.argv[1:4]
SiteCommands(Bench(Path.home() / "pilot" / "benches" / bench).site(site)).restore(database)
"""
TIMEOUT = 8 * 3600
BUILD_MEMORY_MB = 2800
UPDATE = "update-agent"
LOADS = "import importlib.util, sys; spec = importlib.util.spec_from_file_location('agent', sys.argv[1]); agent = importlib.util.module_from_spec(spec); spec.loader.exec_module(agent); assert callable(agent.main) and sys.argv[2] in agent.KINDS"


def run(*command: str, cwd: str | None = None, env: dict | None = None) -> str:
	done = subprocess.run(command, cwd=cwd, env=env, check=True, capture_output=True, text=True, timeout=TIMEOUT)
	return done.stdout


def on_pilot(code: str, *args: str) -> str:
	"""Pilot's own code, in Pilot's Python, for what its commands do not offer."""
	return run(PYTHON, "-c", code, *args, env={**os.environ, "PYTHONPATH": str(PILOT_HOME)})


def pilot(*args: str) -> str:
	return run(PILOT, "-y", *args)


def frappe_on(bench: str, site: str, *args: str) -> str:
	return run(PILOT, "-b", bench, "frappe", "--site", site, *args)


def signature(secret: str, body: str) -> str:
	return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


def store(config: dict):
	import boto3

	return boto3.client("s3", endpoint_url=config["r2_endpoint"], region_name="auto", aws_access_key_id=config["r2_key"], aws_secret_access_key=config["r2_secret"])


def arrived(config: dict, before: dict, quiet: bool = False) -> dict:
	"""A moved site's config on its new bench: a suspended site stays stopped
	as it was, any other comes back on. Pure."""
	kept = {key: value for key, value in config.items() if key not in QUIET}
	if quiet:
		kept.update({key: before[key] for key in QUIET if key in before})
	return kept


def listed_apps(one: dict) -> list[dict]:
	"""The apps a ready-made bench holds, as bench.toml lists them. Pure."""
	return [
		{"name": "erpnext", "repo": "https://github.com/frappe/erpnext", "branch": "develop"},
		{"name": "hrms", "repo": "https://github.com/frappe/hrms", "branch": "develop"},
		{"name": "onedesk", "repo": f"https://github.com/{one['repository']}", "branch": one["branch"]},
	]


def git_info(token: str) -> str:
	"""Pilot's .bench.git.info for a token. Pure."""
	return json.dumps({"provider": "github", "token": token, "username": "x-access-token", "token_expires_at": None, "is_token_valid": True})


def token_asked(config: dict, now: int) -> tuple[str, str, dict]:
	"""The request for a GitHub token: OneAdmin's address, the body and its
	signature. Pure."""
	body = json.dumps({"server": config["server"], "at": now})
	url = f"{config['admin_url'].rstrip('/')}/api/method/onedesk.one_admin.github_app.for_box"
	return url, body, {"Content-Type": "application/json", "User-Agent": "OneAgent/1.0", "X-One-Agent": signature(config["secret"], body)}


def github_token(config: dict) -> str:
	"""A token that reads One's code for an hour, asked of OneAdmin's GitHub
	App; the token this box was given when OneAdmin gives none."""
	if config.get("admin_url") and config.get("secret"):
		url, body, headers = token_asked(config, int(time.time()))
		try:
			with urllib.request.urlopen(urllib.request.Request(url, data=body.encode(), headers=headers, method="POST"), timeout=30) as answered:
				token = (json.loads(answered.read()).get("message") or {}).get("token")
			if token:
				return token
		except (OSError, ValueError):
			pass
	return config.get("github_token") or ""


def _write_config(path: Path, config: dict) -> None:
	new = path.with_name(f".{path.name}.new")
	descriptor = os.open(new, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
	with os.fdopen(descriptor, "w") as file:
		file.write(json.dumps(config, indent=1, sort_keys=True))
	os.replace(new, path)


def _about(config: dict, release: str) -> dict:
	return json.loads(store(config).get_object(Bucket=config["r2_bucket"], Key=f"releases/{release}.json")["Body"].read())


def _fetch(config: dict, key: str, sha256: str, path: Path) -> Path:
	"""A file from the registry, refused unless it matches its checksum."""
	store(config).download_file(config["r2_bucket"], key, str(path))
	digest = hashlib.sha256()
	with open(path, "rb") as file:
		for chunk in iter(lambda: file.read(1 << 20), b""):
			digest.update(chunk)
	if digest.hexdigest() != sha256:
		path.unlink()
		raise RuntimeError(f"{key} does not match its checksum")
	return path


def prepare(config: dict, one: dict) -> None:
	"""A release as a bench of its own: the bench the release build made,
	unpacked where it was built, or built here from its commits when the
	release has none or it does not start."""
	name = one["bench"]
	bench = BENCHES / name
	if bench.exists():
		pilot("-b", name, "drop")
	about = _about(config, one["release"])
	try:
		if not about.get("bench"):
			raise LookupError("the release carries no bench")
		_ready_made(config, one, about)
	except Exception as raised:
		print(f"{name} is built from its commits: {raised}")
		if bench.exists():
			pilot("-b", name, "drop")
		_from_commits(config, one)
	pilot("-b", name, "processes", "disable", FLOW)
	pilot("-b", name, "setup", "production", "--admin-domain", one["host"])
	pilot("-b", name, "restart")


def _new_bench(config: dict, name: str) -> Path:
	bench = BENCHES / name
	pilot("new", name, "--frappe-branch", "develop", "--admin-password", config["pilot_password"])
	with open(bench / "bench.toml", "a") as file:
		file.write(f"\n[build]\nmemory_limit_mb = {BUILD_MEMORY_MB}\n")
	return bench


def _ready_made(config: dict, one: dict, about: dict) -> None:
	"""The bench from the release, at the path, user and Python it was built
	with, so its virtualenv works as it is; then what `pilot init` would still
	do, without cloning or building anything."""
	name = one["bench"]
	bench = _new_bench(config, name)
	archive = _fetch(config, f"releases/{one['release']}.bench.tar.gz", about["bench"]["sha256"], BENCHES / f".{name}.tar.gz")
	try:
		run("tar", "xzf", str(archive), "-C", str(HOME), "--skip-old-files", f"pilot/benches/{name}", *about["bench"].get("python", []))
	finally:
		archive.unlink(missing_ok=True)
	run(str(bench / "env" / "bin" / "python"), "-c", f"import {', '.join(APPS)}")
	on_pilot(SETTLE, str(bench), json.dumps(listed_apps(one)))


def _from_commits(config: dict, one: dict) -> None:
	name = one["bench"]
	bench = _new_bench(config, name)
	pilot("-b", name, "init", "--commit", one["frappe"])
	pilot("-b", name, "get-app", "https://github.com/frappe/erpnext", "--branch", "develop", "--commit", one["erpnext"], "--skip-assets")
	pilot("-b", name, "get-app", "https://github.com/frappe/hrms", "--branch", "develop", "--commit", one["hrms"], "--skip-assets")
	held = bench / ".bench.git.info"
	descriptor = os.open(held, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
	with os.fdopen(descriptor, "w") as file:
		file.write(git_info(github_token(config)))
	try:
		pilot("-b", name, "get-app", f"https://github.com/{one['repository']}", "--branch", one["branch"], "--commit", one["release"], "--skip-assets")
	finally:
		held.unlink(missing_ok=True)
	_unpack(config, bench, one["release"])


def _unpack(config: dict, bench: Path, release: str) -> None:
	about = _about(config, release)
	archive = _fetch(config, f"releases/{release}.tar.gz", about["sha256"], bench / "release.tar.gz")
	run("tar", "xzf", str(archive), cwd=str(bench))
	archive.unlink()
	for app in APPS:
		link = bench / "sites" / "assets" / app
		if link.is_symlink():
			link.unlink()
		link.symlink_to(bench / "apps" / app / app / "public")


def _template(config: dict, release: str) -> Path:
	"""The release's template site, fetched once and kept until the next
	release's is."""
	held = TEMPLATES / release
	if (held / ".ready").exists():
		return held
	TEMPLATES.mkdir(exist_ok=True)
	for other in TEMPLATES.iterdir():
		shutil.rmtree(other, ignore_errors=True)
	held.mkdir()
	archive = _fetch(config, f"releases/{release}.site.tar.gz", _about(config, release)["template"]["sha256"], TEMPLATES / f".{release}.tar.gz")
	try:
		run("tar", "xzf", str(archive), "-C", str(held), *TEMPLATE)
	finally:
		archive.unlink(missing_ok=True)
	(held / ".ready").touch()
	return held


def spare(config: dict, one: dict) -> None:
	"""A spare site: the release's template restored under a new name, with
	its own database, user and password, encryption key and Administrator
	password, and its scheduler paused until it is claimed."""
	bench, site = one["bench"], one["site"]
	held = _template(config, one["release"])
	password = secrets.token_urlsafe(18)
	on_pilot(SPARE, bench, site, str(held / "database.sql.gz"), password)
	path = BENCHES / bench / "sites" / site
	for part in ("public/files", "private/files"):
		shutil.copytree(held / part, path / part, dirs_exist_ok=True)
	made = path / "site_config.json"
	_write_config(made, {**json.loads((held / "site_config.json").read_text()), **json.loads(made.read_text()), "pause_scheduler": 1})
	frappe_on(bench, site, "set-admin-password", password)


def _newest(folder: Path, pattern: str) -> str:
	return max(glob.glob(str(folder / pattern)), key=os.path.getmtime)


def _answers(site: str) -> bool:
	for _ in range(30):
		try:
			asked = urllib.request.Request("http://127.0.0.1/login", headers={"Host": site})
			if urllib.request.urlopen(asked, timeout=20).status == 200:
				return True
		except OSError:
			pass
		time.sleep(5)
	return False


def move(config: dict, one: dict) -> None:
	"""A workspace to another bench of this box. Both benches use the box's
	one MariaDB, so the database stays where it is: the site's folder moves
	and is migrated there. A copy of the database is taken first and put back
	if the migrate fails; whatever fails leaves it answering on the bench it
	was on."""
	site, was, to = one["site"], one["from"], one["to"]
	old, new = BENCHES / was / "sites" / site, BENCHES / to / "sites" / site
	if new.exists() or new.is_symlink():
		raise RuntimeError(f"{site} is already on {to}")
	before = json.loads((old / "site_config.json").read_text())
	frappe_on(was, site, "set-maintenance-mode", "on")
	copy = None
	moved = migrating = False
	try:
		frappe_on(was, site, "backup")
		copy = Path(_newest(old / "private" / "backups", "*-database.sql.gz")).name
		os.rename(old, new)
		moved = True
		on_pilot(ARRIVE, to, was, site)
		migrating = True
		frappe_on(to, site, "migrate")
		_write_config(new / "site_config.json", arrived(json.loads((new / "site_config.json").read_text()), before, bool(one.get("quiet"))))
		if not _answers(site):
			raise RuntimeError(f"{site} does not answer on {to}")
	except Exception:
		if moved:
			if new.exists():
				os.rename(new, old)
			on_pilot(ARRIVE, was, to, site)
		if migrating:
			on_pilot(RESTORE, was, site, str(old / "private" / "backups" / copy))
		_write_config(old / "site_config.json", before)
		frappe_on(was, site, "clear-cache")
		raise
	(new / "private" / "backups" / copy).unlink(missing_ok=True)


def drop_bench(_config: dict, one: dict) -> None:
	pilot("-b", one["bench"], "drop")


def session_demo(_config: dict, one: dict) -> None:
	"""A session's demo company, built in its own site."""
	frappe_on(one["bench"], one["site"], "execute", "onedesk.one_demo.build.load", "--kwargs", json.dumps({"password": secrets.token_urlsafe(18)}))


def session_quiet(_config: dict, one: dict) -> None:
	"""A copy of a workspace, cut off from everything the workspace sends."""
	frappe_on(one["bench"], one["site"], "execute", "onedesk.one_admin.sessions.quieted")


def update_agent(_config: dict, one: dict) -> None:
	"""This file replaced by a signed new one, taken up by the next run. The
	new one is loaded in a process of its own first, and must still know this
	instruction; whatever fails leaves this one where it is."""
	new = SELF.with_name(f".{SELF.stem}.new.py")
	try:
		descriptor = os.open(new, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, SELF.stat().st_mode & 0o777)
		with os.fdopen(descriptor, "w") as file:
			file.write(one["source"])
			file.flush()
			os.fsync(file.fileno())
		run(sys.executable, "-B", "-c", LOADS, str(new), UPDATE)
		os.replace(new, SELF)
	finally:
		new.unlink(missing_ok=True)


KINDS = {"prepare": prepare, "spare": spare, "move": move, "drop-bench": drop_bench, "session-demo": session_demo, "session-quiet": session_quiet, UPDATE: update_agent}


def report(config: dict, said: dict) -> bool:
	body = json.dumps({"server": config["server"], **said})
	asked = urllib.request.Request(
		f"{config['admin_url'].rstrip('/')}/api/method/onedesk.one_admin.servers.reported",
		data=body.encode(),
		headers={"Content-Type": "application/json", "User-Agent": "OneAgent/1.0", "X-One-Agent": signature(config["secret"], body)},
		method="POST",
	)
	try:
		return urllib.request.urlopen(asked, timeout=30).status == 200
	except OSError:
		return False


def instructions(config: dict) -> list[dict]:
	"""What OneAdmin has written for this box and signed, oldest first."""
	r2 = store(config)
	prefix = f"servers/{config['server']}/"
	found = []
	for one in sorted(r2.list_objects_v2(Bucket=config["r2_bucket"], Prefix=prefix).get("Contents", []), key=lambda row: row["Key"]):
		held = json.loads(r2.get_object(Bucket=config["r2_bucket"], Key=one["Key"])["Body"].read())
		if hmac.compare_digest(signature(config["secret"], held["body"]), held["signature"]):
			found.append(json.loads(held["body"]))
	return found


def told(one: dict, **how) -> dict:
	"""What goes back to OneAdmin: the instruction without the agent it carried. Pure."""
	return {**{key: value for key, value in one.items() if key != "source"}, **how}


def tick() -> None:
	config = json.loads(CONFIG.read_text())
	DONE.mkdir(exist_ok=True)
	for mark in sorted(DONE.glob("*.report")):
		if report(config, json.loads(mark.read_text())):
			mark.unlink()
	for one in instructions(config):
		mark = DONE / one["id"]
		if mark.exists():
			continue
		try:
			KINDS[one["kind"]](config, one)
			said = told(one, ok=True)
		except subprocess.CalledProcessError as raised:
			said = told(one, ok=False, error=((raised.stderr or "") + (raised.stdout or ""))[-1500:])
		except Exception as raised:
			said = told(one, ok=False, error=str(raised)[-1500:])
		mark.touch()
		(DONE / f"{one['id']}.report").write_text(json.dumps(said))
		if report(config, said):
			(DONE / f"{one['id']}.report").unlink()
		return


def booting() -> dict:
	"""First boot's values, before this box has a config."""
	return {"server": os.environ.get("ONE_SERVER", ""), "secret": os.environ.get("ONE_AGENT_SECRET", ""), "admin_url": os.environ.get("ONE_ADMIN_URL", ""), "github_token": os.environ.get("ONE_GITHUB_TOKEN", "")}


def main() -> None:
	if sys.argv[1:] == ["github-token"]:
		print(github_token(booting()))
		return
	with open(LOCK, "w") as held:
		try:
			fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
		except BlockingIOError:
			return
		if sys.argv[1:] == ["prepare"]:
			prepare(json.loads(CONFIG.read_text()), json.loads(sys.stdin.read()))
		else:
			tick()


if __name__ == "__main__":
	main()
