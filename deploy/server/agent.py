"""One's agent on a box. Once a minute it reads OneAdmin's signed instructions
from R2, carries out the next one and reports how it went. It only ever calls
out, so no port opens: it builds a release as a new bench, moves a workspace
between benches, and drops a bench that has emptied.
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

HOME = Path.home()
CONFIG = HOME / ".one-agent.json"
DONE = HOME / ".one-agent-done"
LOCK = HOME / ".one-agent-lock"
MOVING = HOME / "moving"
BENCHES = HOME / "pilot" / "benches"
PILOT = str(HOME / "pilot" / "bin" / "pilot")
PYTHON = str(HOME / "pilot" / ".admin-venv" / "bin" / "python")
APPS = ("frappe", "erpnext", "hrms", "onedesk")
FLOW = "frappe-flow_server"
KEPT_OUT = ("installed_apps", "pilot_auth_token", "pilot_endpoint", "backup_retention")
KEPT_OUT_STARTING = ("db_", "maintenance", "pause_")
TIMEOUT = 8 * 3600
BUILD_MEMORY_MB = 2800


def run(*command: str, cwd: str | None = None) -> str:
	done = subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True, timeout=TIMEOUT)
	return done.stdout


def pilot(*args: str) -> str:
	return run(PILOT, "-y", *args)


def frappe_on(bench: str, site: str, *args: str) -> str:
	return run(PILOT, "-b", bench, "frappe", "--site", site, *args)


def signature(secret: str, body: str) -> str:
	return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


def store(config: dict):
	import boto3

	return boto3.client("s3", endpoint_url=config["r2_endpoint"], region_name="auto", aws_access_key_id=config["r2_key"], aws_secret_access_key=config["r2_secret"])


def merged_config(old: dict, new: dict, quiet: bool = False) -> dict:
	"""The new site's config with the old one's own keys, the encryption key
	among them, and never its database settings. A suspended site stays
	stopped; any other comes back on. Pure."""
	left_out = ("db_",) if quiet else KEPT_OUT_STARTING
	carried = {key: value for key, value in old.items() if not key.startswith(left_out) and key not in KEPT_OUT}
	return {**new, **carried}


def prepare(config: dict, one: dict) -> None:
	"""A release as a bench of its own, its screens from the registry."""
	name = one["bench"]
	bench = BENCHES / name
	if bench.exists():
		pilot("-b", name, "drop")
	pilot("new", name, "--frappe-branch", "develop", "--admin-password", config["pilot_password"])
	with open(bench / "bench.toml", "a") as file:
		file.write(f"\n[build]\nmemory_limit_mb = {BUILD_MEMORY_MB}\n")
	pilot("-b", name, "init", "--commit", one["frappe"])
	token = json.dumps({"provider": "github", "token": config["github_token"], "username": "x-access-token", "token_expires_at": None, "is_token_valid": True})
	descriptor = os.open(bench / ".bench.git.info", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
	with os.fdopen(descriptor, "w") as file:
		file.write(token)
	pilot("-b", name, "get-app", "https://github.com/frappe/erpnext", "--branch", "develop", "--commit", one["erpnext"], "--skip-assets")
	pilot("-b", name, "get-app", "https://github.com/frappe/hrms", "--branch", "develop", "--commit", one["hrms"], "--skip-assets")
	pilot("-b", name, "get-app", f"https://github.com/{one['repository']}", "--branch", one["branch"], "--commit", one["release"], "--skip-assets")
	_unpack(config, bench, one["release"])
	pilot("-b", name, "processes", "disable", FLOW)
	pilot("-b", name, "setup", "production", "--admin-domain", one["host"])
	pilot("-b", name, "restart")


def _unpack(config: dict, bench: Path, release: str) -> None:
	key = f"releases/{release}"
	r2 = store(config)
	about = json.loads(r2.get_object(Bucket=config["r2_bucket"], Key=f"{key}.json")["Body"].read())
	archive = bench / "release.tar.gz"
	r2.download_file(config["r2_bucket"], f"{key}.tar.gz", str(archive))
	digest = hashlib.sha256()
	with open(archive, "rb") as file:
		for chunk in iter(lambda: file.read(1 << 20), b""):
			digest.update(chunk)
	if digest.hexdigest() != about["sha256"]:
		raise RuntimeError("the release archive does not match its checksum")
	run("tar", "xzf", str(archive), cwd=str(bench))
	archive.unlink()
	for app in APPS:
		link = bench / "sites" / "assets" / app
		if link.is_symlink():
			link.unlink()
		link.symlink_to(bench / "apps" / app / app / "public")


def _newest(folder: Path, pattern: str, leave_out: str = "\0") -> str:
	found = [one for one in glob.glob(str(folder / pattern)) if leave_out not in one]
	return max(found, key=os.path.getmtime)


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


def _unlink(path: Path) -> None:
	if path.is_symlink():
		path.unlink()


def move(config: dict, one: dict) -> None:
	"""A workspace to another bench, by backup and restore. Whatever fails
	leaves it answering on the bench it was on."""
	site, was, to = one["site"], one["from"], one["to"]
	old = BENCHES / was / "sites"
	aside = f"old-{site}"
	work = MOVING / site
	shutil.rmtree(work, ignore_errors=True)
	work.mkdir(parents=True)
	frappe_on(was, site, "set-maintenance-mode", "on")
	moved = False
	try:
		frappe_on(was, site, "backup", "--with-files")
		held = old / site / "private" / "backups"
		parts = [_newest(held, "*-database.sql.gz"), _newest(held, "*-files.tar", "private-files"), _newest(held, "*-private-files.tar")]
		database, public, private = [shutil.copy2(one_part, work) for one_part in parts]
		before = json.loads((old / site / "site_config.json").read_text())
		_unlink(old / aside)
		pilot("-b", was, "rename-site", "--release-old-hostname", site, aside)
		moved = True
		_unlink(old / site)
		_restore(to, site, database, public, private)
		path = BENCHES / to / "sites" / site / "site_config.json"
		path.write_text(json.dumps(merged_config(before, json.loads(path.read_text()), bool(one.get("quiet"))), indent=1))
		pilot("-b", to, "restart")
		if not _answers(site):
			raise RuntimeError(f"{site} does not answer on {to}")
	except Exception:
		if (BENCHES / to / "sites" / site).exists():
			pilot("-b", to, "drop-site", site, "--no-backup")
		if moved:
			_unlink(old / site)
			pilot("-b", was, "rename-site", "--release-old-hostname", aside, site)
			_unlink(old / aside)
		frappe_on(was, site, "set-maintenance-mode", "off")
		pilot("-b", was, "restart")
		raise
	pilot("-b", was, "drop-site", aside)
	_unlink(old / site)
	shutil.rmtree(work, ignore_errors=True)


def _restore(bench: str, site: str, database: str, public: str, private: str) -> None:
	code = (
		"import sys, secrets\n"
		"from pathlib import Path\n"
		"from pilot.core.bench import Bench\n"
		"from pilot.core.site import provision_from_backup\n"
		"bench, site, database, public, private = sys.argv[1:6]\n"
		"provision_from_backup(Bench(Path.home() / 'pilot' / 'benches' / bench), site, database, admin_password=secrets.token_urlsafe(16), public_files=public, private_files=private)\n"
	)
	subprocess.run([PYTHON, "-c", code, bench, site, database, public, private], check=True, timeout=TIMEOUT, env={**os.environ, "PYTHONPATH": str(HOME / "pilot")}, capture_output=True, text=True)


def drop_bench(_config: dict, one: dict) -> None:
	pilot("-b", one["bench"], "drop")


def session_demo(_config: dict, one: dict) -> None:
	"""A session's demo company, built in its own site."""
	frappe_on(one["bench"], one["site"], "execute", "onedesk.one_demo.build.load", "--kwargs", json.dumps({"password": secrets.token_urlsafe(18)}))


def session_quiet(_config: dict, one: dict) -> None:
	"""A copy of a workspace, cut off from everything the workspace sends."""
	frappe_on(one["bench"], one["site"], "execute", "onedesk.one_admin.sessions.quieted")


KINDS = {"prepare": prepare, "move": move, "drop-bench": drop_bench, "session-demo": session_demo, "session-quiet": session_quiet}


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
			said = {**one, "ok": True}
		except subprocess.CalledProcessError as raised:
			said = {**one, "ok": False, "error": ((raised.stderr or "") + (raised.stdout or ""))[-1500:]}
		except Exception as raised:
			said = {**one, "ok": False, "error": str(raised)[-1500:]}
		mark.touch()
		(DONE / f"{one['id']}.report").write_text(json.dumps(said))
		if report(config, said):
			(DONE / f"{one['id']}.report").unlink()
		return


def main() -> None:
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
