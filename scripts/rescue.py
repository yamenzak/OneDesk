"""The keys a new dev machine needs, in one file only a passphrase opens, and
the dev sites' nightly backups. deploy/local/README.md.

`pack` writes the kit and sends it to the locked backup bucket through the
keeper, under `rescue/`. `unpack` puts the keys back. `key` makes the public
key OneAdmin seals its config copy with. `open` opens a sealed copy. `nightly`
backs every dev site up to the keeper. `restore` puts the newest back.
`fetch` brings OneAdmin's newest sealed config and backup down from the
locked bucket with nothing but a sign-in to Cloudflare, for when OneAdmin
and its keeper secret are gone (one_admin/AGENTS.md, Rebuilding OneAdmin).

    python scripts/rescue.py pack [--out FILE] [--no-send]
    python scripts/rescue.py unpack FILE [--into DIR]
    python scripts/rescue.py key
    python scripts/rescue.py open FILE [--out FILE]
    python scripts/rescue.py nightly
    python scripts/rescue.py restore SITE [SITE ...]
    python scripts/rescue.py fetch [--keys FILE] [--into DIR]
"""

import argparse
import base64
import time
import getpass
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from onedesk.one_admin import cloudflare_signin, seal  # noqa: E402

HOME = Path.home()
BENCH = HOME / "one-bench"
SITES = BENCH / "sites"
SITE_COPIES = ".one-site-configs"
PUBLIC_KEY = HOME / ".one-config-key"
DEV_KEEPER = "https://one-keeper-dev.4dl.workers.dev"
KEPT = (".one-local", ".one-dev.json", ".one-keys-dev.json", ".one-keys-prod.json", ".one-config-key", ".ssh/one_servers", ".ssh/one_servers.pub", ".config/gh/hosts.yml")
KEPT_FOLDERS = (".one-servers", ".cloudflared")
SHORTEST = 12
FETCH_SALT = b"one-rescue-fetch"
PATIENCE = 900
API = "https://api.cloudflare.com/client/v4"
LOCKED = "one-backups"
OURS = "oneadmin"
READS = "Workers R2 Storage Bucket Item Read"
FETCH_FOR = 3600
SCOPES = "user-api-tokens.write account-api-tokens.write"
PARTS = {"database": "-database.sql.gz", "private": "-private-files.tar", "public": "-files.tar"}


def key_from(passphrase: str, salt: bytes) -> bytes:
	"""Pure."""
	return base64.urlsafe_b64encode(Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(passphrase.encode()))


def fetch_secret(passphrase: str) -> str:
	"""What a new machine shows the keeper to be given the kit. Pure."""
	return Scrypt(salt=FETCH_SALT, length=32, n=2**15, r=8, p=1).derive(passphrase.encode()).hex()


def sealed(files: dict[str, bytes], passphrase: str) -> bytes:
	"""The files, encrypted under the passphrase. Pure but for the salt."""
	salt = secrets.token_bytes(16)
	body = json.dumps({name: base64.b64encode(content).decode() for name, content in files.items()}).encode()
	return json.dumps({"salt": base64.b64encode(salt).decode(), "token": Fernet(key_from(passphrase, salt)).encrypt(body).decode()}).encode()


def opened(held: bytes, passphrase: str) -> dict[str, bytes]:
	"""Pure."""
	outer = json.loads(held)
	body = Fernet(key_from(passphrase, base64.b64decode(outer["salt"]))).decrypt(outer["token"].encode())
	return {name: base64.b64decode(content) for name, content in json.loads(body).items()}


def gathered() -> dict[str, bytes]:
	files = {name: (HOME / name).read_bytes() for name in KEPT if (HOME / name).exists()}
	for folder in KEPT_FOLDERS:
		files |= {str(path.relative_to(HOME)): path.read_bytes() for path in (HOME / folder).glob("*") if path.is_file()}
	for site in dev_sites():
		files[f"{SITE_COPIES}/{site}.json"] = (SITES / site / "site_config.json").read_bytes()
	return files


def dev_sites() -> list[str]:
	"""The sites of this machine marked one_dev."""
	return sorted(path.parent.name for path in SITES.glob("*/site_config.json") if json.loads(path.read_text()).get("one_dev"))


def admin_config() -> dict:
	"""The dev OneAdmin's config: the bench's, or the kit's while the bench
	has none."""
	for path in [*SITES.glob("*/site_config.json"), *(HOME / SITE_COPIES).glob("admin.*.json")]:
		config = json.loads(path.read_text())
		if config.get("one_admin") and config.get("keeper_secret"):
			return config
	raise SystemExit("No dev OneAdmin here with a keeper secret; unpack the rescue kit first.")


def keeper() -> tuple[str, dict]:
	config = admin_config()
	url = os.environ.get("ONE_KEEPER_URL") or config.get("keeper_url") or DEV_KEEPER
	return url.rstrip("/"), {"x-one-secret": config["keeper_secret"]}


def passphrase_asked(twice: bool) -> str:
	given = os.environ.get("ONE_RESCUE_PASSPHRASE") or getpass.getpass("Passphrase: ")
	if twice and not os.environ.get("ONE_RESCUE_PASSPHRASE") and given != getpass.getpass("Again: "):
		raise SystemExit("The passphrases do not match.")
	if twice and len(given) < SHORTEST:
		raise SystemExit(f"Use at least {SHORTEST} characters.")
	return given


def send(held: bytes, passphrase: str) -> str:
	url, headers = keeper()
	key = f"rescue/{datetime.now(UTC).strftime('%Y-%m-%d-%H%M')}.one"
	requests.put(f"{url}/backup/{key}", data=held, headers=headers, timeout=120).raise_for_status()
	answered = requests.post(f"{url}/rescue-key", json={"hash": hashlib.sha256(fetch_secret(passphrase).encode()).hexdigest()}, headers=headers, timeout=30)
	if not answered.ok:
		print("The keeper does not take a rescue key yet: run Set Up Cloudflare, then pack again.")
	return key


def pack(args) -> None:
	passphrase = passphrase_asked(True)
	held = sealed(gathered(), passphrase)
	if args.out:
		Path(args.out).write_bytes(held)
		print(f"written to {args.out}")
	if not args.no_send:
		print(f"kept as {send(held, passphrase)}")


def _written(path: Path, content: bytes) -> None:
	path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
	with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb") as file:
		file.write(content)


def unpack(args) -> None:
	into = Path(args.into) if args.into else HOME
	for name, content in opened(Path(args.file).read_bytes(), passphrase_asked(False)).items():
		_written(into / name, content)
		print(name)


def key(_args) -> None:
	"""Print the public key OneAdmin seals its config copy with, and keep it
	for this machine's own nightly backups."""
	public = seal.public_text(passphrase_asked(True))
	_written(PUBLIC_KEY, public.encode())
	print(public)


def open_copy(args) -> None:
	body = seal.opened(Path(args.file).read_bytes(), passphrase_asked(False))
	if args.out:
		_written(Path(args.out), body)
		print(f"written to {args.out}")
	else:
		sys.stdout.buffer.write(body)


def part_of(name: str) -> str | None:
	"""Which part of a backup a file of `bench backup` is. Pure."""
	return next((part for part, ending in PARTS.items() if name.endswith(ending)), None)


def _put(url: str, headers: dict, key: str, body) -> None:
	requests.put(f"{url}/backup/{key}", data=body, headers=headers, timeout=PATIENCE).raise_for_status()


def _bench(*args: str) -> None:
	subprocess.run([shutil.which("bench") or str(HOME / ".local/bin/bench"), *args], cwd=BENCH, check=True)


def nightly(_args) -> None:
	"""Every dev site backed up to the dev keeper under `daily/dev-<site>/`,
	its config sealed. Scheduled by always-on.sh."""
	if not PUBLIC_KEY.exists():
		raise SystemExit("No ~/.one-config-key: run scripts/rescue.py key once.")
	public = PUBLIC_KEY.read_text()
	url, headers = keeper()
	day = datetime.now(UTC).strftime("%Y-%m-%d")
	for site in dev_sites():
		with tempfile.TemporaryDirectory() as room:
			_bench("--site", site, "backup", "--with-files", "--backup-path", room)
			for path in Path(room).iterdir():
				part = part_of(path.name)
				if part:
					with path.open("rb") as body:
						_put(url, headers, f"daily/dev-{site}/{day}/{part}/{path.name}", body)
		config = seal.sealed((SITES / site / "site_config.json").read_bytes(), public)
		_put(url, headers, f"daily/dev-{site}/{day}/config/site_config.json.one", config)
		print(f"{site} kept for {day}")


def newest_backup(objects: list[dict], site: str) -> dict[str, str]:
	"""The newest day's parts of a site's backup, the day having a database
	and a sealed config. Pure."""
	days: dict[str, dict[str, str]] = {}
	for one in objects:
		pieces = one["key"].split("/")
		if len(pieces) == 5 and pieces[:2] == ["daily", f"dev-{site}"]:
			days.setdefault(pieces[2], {})[pieces[3]] = one["key"]
	whole = [day for day, parts in days.items() if {"database", "config"} <= set(parts)]
	return days[max(whole)] if whole else {}


def _listed(url: str, headers: dict, prefix: str) -> list[dict]:
	found, cursor = [], ""
	while True:
		answered = requests.get(f"{url}/backups", params={"prefix": prefix, "cursor": cursor}, headers=headers, timeout=60)
		answered.raise_for_status()
		said = answered.json()
		found += said.get("objects") or []
		cursor = said.get("cursor")
		if not cursor:
			return found


def _fetched(url: str, headers: dict, key: str, path: Path) -> None:
	with requests.get(f"{url}/backup/{key}", headers=headers, stream=True, timeout=PATIENCE) as held:
		held.raise_for_status()
		with path.open("wb") as file:
			shutil.copyfileobj(held.raw, file)


def _db_root_password() -> str:
	lines = (HOME / ".one-local").read_text().splitlines()
	return next(line.split("=", 1)[1] for line in lines if line.startswith("DB_ROOT_PASSWORD="))


def restore_args(site: str, files: dict[str, Path], root_password: str) -> list[str]:
	"""`bench restore`'s arguments, the files named only if they came. Pure."""
	args = ["--site", site, "restore", str(files["database"]), "--force", "--db-root-username", "root", "--db-root-password", root_password]
	for part, flag in (("public", "--with-public-files"), ("private", "--with-private-files")):
		if part in files:
			args += [flag, str(files[part])]
	return args


def restore(args) -> None:
	"""A dev site put back from its newest kept backup, its config first, so
	the database is made under the name and password the site had."""
	passphrase = passphrase_asked(False)
	url, headers = keeper()
	for site in args.sites:
		parts = newest_backup(_listed(url, headers, f"daily/dev-{site}/"), site)
		if not parts:
			print(f"{site}: no backup kept yet, left as it is")
			continue
		with tempfile.TemporaryDirectory() as room:
			files: dict[str, Path] = {}
			for part, stored in parts.items():
				files[part] = Path(room) / stored.rsplit("/", 1)[1]
				_fetched(url, headers, stored, files[part])
			_written(SITES / site / "site_config.json", seal.opened(files.pop("config").read_bytes(), passphrase))
			_bench(*restore_args(site, files, _db_root_password()))
		_bench("--site", site, "migrate")
		print(f"{site} restored")


def read_policy(groups: list[dict], account: str, bucket: str) -> list[dict]:
	"""A token's policy that reads one bucket and nothing else. Pure."""
	found = next((one for one in groups if one["name"] == READS), None)
	if not found:
		raise SystemExit(f"Cloudflare has no permission {READS}")
	return [{"effect": "allow", "permission_groups": [{"id": found["id"]}], "resources": {f"com.cloudflare.edge.r2.bucket.{account}_default_{bucket}": "*"}}]


def s3_of(made: dict) -> tuple[str, str]:
	"""An R2 token as S3 credentials: its id, and the SHA-256 of its value. Pure."""
	return made["id"], hashlib.sha256(made["value"].encode()).hexdigest()


def newest_under(keys: list[str], prefix: str) -> list[str]:
	"""Every object of the newest day under a prefix of `<prefix><day>/…`. Pure."""
	days = sorted({key[len(prefix):].split("/", 1)[0] for key in keys if key.startswith(prefix)})
	return [key for key in keys if days and key.startswith(f"{prefix}{days[-1]}/")]


def fetch(args) -> None:
	import boto3

	keys = json.loads(Path(args.keys).expanduser().read_text())
	account = keys["cloudflare_account"]
	admin = keys.get("admin_url") or f"https://admin.{keys['origin_zone']}"
	token, revoke = cloudflare_signin.signed_in_here(keys["cloudflare_oauth_client_id"], keys["cloudflare_oauth_client_secret"], admin, keys.get("cloudflare_oauth_scopes", SCOPES))
	headers = {"Authorization": f"Bearer {token}"}
	made = None
	try:
		groups = requests.get(f"{API}/user/tokens/permission_groups", headers=headers, timeout=30).json()["result"]
		until = datetime.fromtimestamp(time.time() + FETCH_FOR, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
		body = {"name": "One rescue fetch", "policies": read_policy(groups, account, LOCKED), "expires_on": until}
		made = requests.post(f"{API}/user/tokens", headers=headers, json=body, timeout=30).json()["result"]
		key_id, secret = s3_of(made)
		client = boto3.client("s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com", aws_access_key_id=key_id, aws_secret_access_key=secret, region_name="auto")
		listed = []
		for prefix in (f"config/{OURS}/", f"daily/{OURS}/"):
			for _try in range(10):
				try:
					pages = client.get_paginator("list_objects_v2").paginate(Bucket=LOCKED, Prefix=prefix)
					listed += [one["Key"] for page in pages for one in page.get("Contents") or []]
					break
				except client.exceptions.ClientError:
					time.sleep(3)
		copies = sorted(key for key in listed if key.startswith(f"config/{OURS}/"))
		wanted = copies[-1:] + newest_under(listed, f"daily/{OURS}/")
		into = Path(args.into).expanduser()
		into.mkdir(mode=0o700, parents=True, exist_ok=True)
		for key in wanted:
			client.download_file(LOCKED, key, str(into / key.replace("/", "__")))
			print(f"fetched {key}")
		if not wanted:
			print("nothing kept yet")
	finally:
		if made:
			requests.delete(f"{API}/user/tokens/{made['id']}", headers=headers, timeout=30)
		revoke()


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	commands = parser.add_subparsers(required=True)
	one = commands.add_parser("pack")
	one.add_argument("--out")
	one.add_argument("--no-send", action="store_true")
	one.set_defaults(run=pack)
	two = commands.add_parser("unpack")
	two.add_argument("file")
	two.add_argument("--into")
	two.set_defaults(run=unpack)
	commands.add_parser("key").set_defaults(run=key)
	three = commands.add_parser("open")
	three.add_argument("file")
	three.add_argument("--out")
	three.set_defaults(run=open_copy)
	commands.add_parser("nightly").set_defaults(run=nightly)
	four = commands.add_parser("restore")
	four.add_argument("sites", nargs="+")
	four.set_defaults(run=restore)
	five = commands.add_parser("fetch")
	five.add_argument("--keys", default=str(HOME / ".one-keys-prod.json"))
	five.add_argument("--into", default=str(HOME / "one-rescue"))
	five.set_defaults(run=fetch)
	args = parser.parse_args()
	args.run(args)


if __name__ == "__main__":
	sys.exit(main())
